/* Dashboard Soldes Clients → onglet « Suivi des paiements par bon ».
 * Chaque bon (commande livrée, vente directe du van, vente au bureau) avec ce que le client a payé
 * et ce qu'il reste à payer ; vue par client (cliquer pour voir ses bons) ou liste de tous les bons.
 * Données : GET /API/clients/suivi_paiements/?du=&au= */
(function () {
    'use strict';

    var ETATS = { paye: 'Payé', partiel: 'Payé en partie', non_paye: 'Non payé' };
    var ICONES = { paye: 'fa-check-circle', partiel: 'fa-adjust', non_paye: 'fa-times-circle' };
    var TYPES = { commande: 'Commande livrée', vente: 'Vente directe (van)', vente_pc: 'Vente au bureau' };
    var MODES = { especes: 'Espèces', cheque: 'Chèque', carte: 'Carte', virement: 'Virement', credit: 'À crédit', non_paye: 'Non payé' };

    var donnees = null;          // {du, au, bons:[], clients:[]}
    var clientsParId = {};
    var onglet = 'ensemble';
    var vue = 'clients';         // 'clients' | 'bons'
    var ouverts = {};            // clients dépliés
    var triClients = { col: 'reste', sens: -1 };
    var triBons = { col: 'date', sens: -1 };
    var recherche = '';
    var limite = 300;
    var requete = 0;
    var minuterieRecherche = null;

    // ---------- Utilitaires ----------
    function $id(id) { return document.getElementById(id); }
    function esc(s) {
        return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }
    function num(v) { var n = parseFloat(v); return isNaN(n) ? 0 : n; }
    function argent(v) {
        return new Intl.NumberFormat('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(num(v)) + ' DA';
    }
    function pad(n) { return (n < 10 ? '0' : '') + n; }
    function iso(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
    function dateCourte(s) {
        if (!s) return '';
        var d = new Date(s);
        return isNaN(d) ? '' : pad(d.getDate()) + '/' + pad(d.getMonth() + 1) + '/' + d.getFullYear();
    }
    function heure(s) {
        if (!s) return '';
        var d = new Date(s);
        return isNaN(d) ? '' : pad(d.getHours()) + ':' + pad(d.getMinutes());
    }
    function dateLisible(isoJour) {
        if (!isoJour) return '';
        var p = isoJour.split('-');
        return p[2] + '/' + p[1] + '/' + p[0];
    }
    function cookie(nom) {
        var m = document.cookie.match('(?:^|; )' + nom + '=([^;]*)');
        return m ? decodeURIComponent(m[1]) : '';
    }
    function badgeEtat(e) {
        return '<span class="sp-badge ' + e + '"><i class="fas ' + ICONES[e] + '"></i>' + ETATS[e] + '</span>';
    }
    function badgeSituation(c) {
        var s = num(c.situation);
        if (s > 0.01) return '<span class="sp-badge dette" title="Tout ce que le client doit aujourd\'hui, toutes périodes confondues">Doit ' + argent(s) + '</span>';
        if (s < -0.01) return '<span class="sp-badge avance" title="Le client a payé d\'avance">Avance ' + argent(-s) + '</span>';
        return '<span class="sp-badge ajour"><i class="fas fa-check"></i>À jour</span>';
    }
    function iconeTri(t, col) {
        if (t.col !== col) return '<i class="fas fa-sort"></i>';
        return '<i class="fas fa-sort-' + (t.sens > 0 ? 'up' : 'down') + '"></i>';
    }

    // ---------- Filtres ----------
    function valeur(id) { var e = $id(id); return e ? e.value : ''; }

    function bonsFiltres() {
        if (!donnees) return [];
        var etat = valeur('spEtat'), type = valeur('spType'), client = valeur('spClient'), vendeur = valeur('spVendeur');
        var q = recherche.trim().toLowerCase();
        return donnees.bons.filter(function (b) {
            if (etat === 'a_payer' ? b.etat === 'paye' : (etat && b.etat !== etat)) return false;
            if (type && b.type !== type) return false;
            if (client && String(b.client_id) !== client) return false;
            if (vendeur && b.vendeur !== vendeur) return false;
            if (q) {
                var c = clientsParId[b.client_id] || {};
                var texte = (b.reference + ' ' + (c.nom || '') + ' ' + (c.telephone || '') + ' ' + b.vendeur).toLowerCase();
                if (texte.indexOf(q) < 0) return false;
            }
            return true;
        });
    }

    function parClient(bons) {
        var map = {};
        bons.forEach(function (b) {
            var g = map[b.client_id];
            if (!g) {
                var c = clientsParId[b.client_id] || { id: b.client_id, nom: '?', telephone: '', situation: 0, dette_anterieure: 0 };
                g = map[b.client_id] = { client: c, bons: [], total: 0, paye: 0, reste: 0, nb: { paye: 0, partiel: 0, non_paye: 0 } };
            }
            g.bons.push(b);
            g.total += num(b.total); g.paye += num(b.paye); g.reste += num(b.reste);
            g.nb[b.etat]++;
        });
        var liste = Object.keys(map).map(function (k) { return map[k]; });
        var t = triClients;
        liste.sort(function (a, b) {
            var va, vb;
            if (t.col === 'client') { va = a.client.nom.toLowerCase(); vb = b.client.nom.toLowerCase(); }
            else if (t.col === 'bons') { va = a.bons.length; vb = b.bons.length; }
            else if (t.col === 'situation') { va = num(a.client.situation); vb = num(b.client.situation); }
            else if (t.col === 'pct') { va = a.total ? a.paye / a.total : 1; vb = b.total ? b.paye / b.total : 1; }
            else { va = a[t.col]; vb = b[t.col]; }
            if (va < vb) return -t.sens;
            if (va > vb) return t.sens;
            return a.client.nom.localeCompare(b.client.nom);
        });
        return liste;
    }

    function trierBons(bons) {
        var t = triBons;
        return bons.slice().sort(function (a, b) {
            var va, vb;
            if (t.col === 'client') { va = (clientsParId[a.client_id] || {}).nom || ''; vb = (clientsParId[b.client_id] || {}).nom || ''; }
            else if (t.col === 'date' || t.col === 'dernier_paiement') { va = a[t.col] || ''; vb = b[t.col] || ''; }
            else if (t.col === 'reference' || t.col === 'vendeur' || t.col === 'etat') { va = (a[t.col] || '').toLowerCase(); vb = (b[t.col] || '').toLowerCase(); }
            else { va = num(a[t.col]); vb = num(b[t.col]); }
            if (va < vb) return -t.sens;
            if (va > vb) return t.sens;
            return 0;
        });
    }

    function lienBon(b) {
        return '<a href="#" class="sp-ref sp-lien" title="Voir le bon" onclick="event.stopPropagation();spVoirBon(\'' + esc(b.cle) +
            '\');return false;"><i class="fas fa-file-alt"></i>' + esc(b.reference || '—') + '</a>';
    }

    function nbCartons(q, upc) {
        upc = parseInt(upc, 10);
        if (!(upc > 1)) return '-';
        q = Math.abs(Math.round(num(q))) || 0;
        var ct = Math.floor(q / upc), reste = q % upc;
        if (!reste) return String(ct);
        return ct ? ct + ' + ' + reste + '/' + upc : reste + '/' + upc;
    }
    function qte(v) { var n = num(v); return n % 1 ? n.toFixed(2).replace('.', ',') : String(n); }

    // ---------- Détail d'un bon ----------
    var bonOuvert = null;

    function fenetre() {
        var f = $id('spFenetre');
        if (!f) {
            f = document.createElement('div');
            f.id = 'spFenetre';
            f.className = 'sp-fenetre';
            f.innerHTML = '<div class="sp-fenetre-boite" role="dialog" aria-modal="true"></div>';
            f.addEventListener('click', function (e) { if (e.target === f) fermerBon(); });
            document.body.appendChild(f);
            document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && $id('spFenetre') && $id('spFenetre').classList.contains('ouverte')) fermerBon(); });
        }
        return f;
    }

    function fermerBon() {
        var f = $id('spFenetre');
        if (f) f.classList.remove('ouverte');
        bonOuvert = null;
    }

    function contenuBon(d) {
        var c = d.client || {};
        var info = function (l, v) { return v ? '<div><span>' + l + '</span><b>' + v + '</b></div>' : ''; };
        var lignes = d.lignes.map(function (l) {
            return '<tr><td><b>' + esc(l.designation) + '</b>' + (l.reference ? '<div class="sp-tel">' + esc(l.reference) + '</div>' : '') + '</td>' +
                '<td class="c">' + qte(l.quantite) + '</td><td class="c">' + nbCartons(l.quantite, l.unites_par_carton) + '</td>' +
                '<td class="r">' + argent(l.prix_unitaire) + '</td><td class="r"><b>' + argent(l.montant) + '</b></td></tr>';
        }).join('') || '<tr><td colspan="5" class="sp-zero c">Aucun produit</td></tr>';
        var paiements = d.paiements.length ? '<table class="sp-table sp-sous"><thead><tr><th>Date</th><th>Mode</th><th class="r">Montant</th></tr></thead><tbody>' +
            d.paiements.map(function (p) {
                var neg = num(p.montant) < 0;
                return '<tr><td>' + dateCourte(p.date) + ' <span class="sp-tel">' + heure(p.date) + '</span></td><td>' +
                    (neg ? 'Rendu au client' : esc(MODES[p.mode] || p.mode || '')) + '</td><td class="r"><b>' + argent(p.montant) + '</b></td></tr>';
            }).join('') + '</tbody></table>'
            : '<div class="sp-aucun-paiement"><i class="fas fa-info-circle mr-1"></i>Aucun paiement reçu pour ce bon.</div>';
        return '<div class="sp-fenetre-tete">' +
            '<div><div class="sp-fenetre-type">' + esc(d.libelle) + '</div><div class="sp-fenetre-ref">' + esc(d.reference) + '</div></div>' +
            '<div>' + badgeEtat(d.etat) + '<button type="button" class="sp-fermer" title="Fermer" onclick="spFermerBon()">&times;</button></div></div>' +
            '<div class="sp-fenetre-corps">' +
            '<div class="sp-infos">' +
            info('Client', esc(c.nom) + (c.telephone ? ' <span class="sp-tel">' + esc(c.telephone) + '</span>' : '')) +
            info(d.type === 'commande' ? 'Livrée le' : 'Date', dateCourte(d.date) + ' ' + heure(d.date)) +
            (d.date_commande ? info('Commandée le', dateCourte(d.date_commande)) : '') +
            info(d.type === 'vente' ? 'Vendeur' : 'Pré-vendeur', esc(d.vendeur)) +
            info('Livreur', esc(d.livreur)) +
            info('Adresse', esc(c.adresse)) +
            '</div>' +
            '<div class="sp-titre-bloc">Produits</div>' +
            '<div class="sp-table-wrap"><table class="sp-table sp-sous"><thead><tr><th>Produit</th><th class="c">Qté (pièces)</th><th class="c">Nb cartons</th>' +
            '<th class="r">Prix unitaire' + (d.prix_ht ? ' HT' : '') + '</th><th class="r">Montant</th></tr></thead><tbody>' + lignes + '</tbody></table></div>' +
            '<div class="sp-totaux">' +
            (num(d.total_ht) && num(d.total_ht) !== num(d.total) ? '<div><span>Total HT</span><b>' + argent(d.total_ht) + '</b></div>' : '') +
            '<div class="gros"><span>Total TTC</span><b>' + argent(d.total) + '</b></div>' +
            '<div class="vert"><span>Payé</span><b>' + argent(d.paye) + '</b></div>' +
            '<div class="' + (num(d.reste) > 0.01 ? 'rouge' : 'vert') + '"><span>Reste à payer</span><b>' + argent(d.reste) + '</b></div>' +
            '</div>' +
            '<div class="sp-titre-bloc">Paiements</div>' + paiements +
            (d.notes ? '<div class="sp-titre-bloc">Notes</div><div class="sp-notes">' + esc(d.notes) + '</div>' : '') +
            '</div>' +
            '<div class="sp-fenetre-pied"><button type="button" onclick="spFermerBon()">Fermer</button>' +
            '<button type="button" class="principal" onclick="spImprimerBon()"><i class="fas fa-print mr-1"></i>Imprimer le bon</button></div>';
    }

    function voirBon(cle) {
        var f = fenetre(), boite = f.firstChild;
        boite.innerHTML = '<div class="sp-chargement"><i class="fas fa-spinner fa-spin fa-2x"></i><div class="mt-2">Chargement du bon…</div></div>';
        f.classList.add('ouverte');
        bonOuvert = null;
        fetch('/API/clients/detail_bon/?cle=' + encodeURIComponent(cle), { credentials: 'same-origin' })
            .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
            .then(function (d) { bonOuvert = d; boite.innerHTML = contenuBon(d); })
            .catch(function (e) {
                console.error('[SUIVI PAIEMENTS] bon', e);
                boite.innerHTML = '<div class="sp-vide"><i class="fas fa-exclamation-triangle" style="color:#f87171"></i>' +
                    '<div style="font-weight:700;color:#475569">Impossible d\'ouvrir ce bon</div><div class="mt-3">' +
                    '<button type="button" class="btn btn-outline-primary btn-sm" onclick="spVoirBon(\'' + esc(cle) + '\')">Réessayer</button> ' +
                    '<button type="button" class="btn btn-light btn-sm" onclick="spFermerBon()">Fermer</button></div></div>';
            });
    }

    function imprimerBon() {
        var d = bonOuvert;
        if (!d) return;
        var c = d.client || {};
        var w = window.open('', '_blank');
        if (!w) return;
        var lignes = d.lignes.map(function (l) {
            return '<tr><td>' + esc(l.designation) + (l.reference ? '<br><small>' + esc(l.reference) + '</small>' : '') + '</td><td class="c">' +
                qte(l.quantite) + '</td><td class="c">' + nbCartons(l.quantite, l.unites_par_carton) + '</td><td class="r">' + argent(l.prix_unitaire) +
                '</td><td class="r">' + argent(l.montant) + '</td></tr>';
        }).join('');
        var paiements = d.paiements.map(function (p) {
            return '<tr><td>' + dateCourte(p.date) + '</td><td>' + (num(p.montant) < 0 ? 'Rendu au client' : esc(MODES[p.mode] || p.mode || '')) +
                '</td><td class="r">' + argent(p.montant) + '</td></tr>';
        }).join('');
        w.document.write('<!doctype html><html><head><meta charset="utf-8"><title>' + esc(d.reference) + '</title><style>' +
            'body{font-family:Arial,sans-serif;font-size:12px;color:#111;margin:24px}h1{font-size:18px;margin:0}.ref{font-size:14px;color:#444;margin:2px 0 14px}' +
            '.cols{display:flex;justify-content:space-between;gap:20px;margin-bottom:14px}.cols div{line-height:1.6}' +
            'table{width:100%;border-collapse:collapse;margin-bottom:12px}th,td{border:1px solid #bbb;padding:5px 7px;text-align:left}th{background:#eee}' +
            '.r{text-align:right}.c{text-align:center}.tot{width:300px;margin-left:auto}.tot td{border:0;border-bottom:1px solid #ddd}' +
            '.tot .g td{font-size:14px;font-weight:bold}.etat{display:inline-block;padding:3px 10px;border:1px solid #999;border-radius:12px;font-weight:bold}' +
            'h2{font-size:13px;margin:16px 0 6px}</style></head><body>' +
            '<h1>' + esc(d.libelle) + '</h1><div class="ref">N° ' + esc(d.reference) + ' · <span class="etat">' + ETATS[d.etat] + '</span></div>' +
            '<div class="cols"><div><b>Client :</b> ' + esc(c.nom) + '<br>' + (c.telephone ? '<b>Téléphone :</b> ' + esc(c.telephone) + '<br>' : '') +
            (c.adresse ? '<b>Adresse :</b> ' + esc(c.adresse) : '') + '</div><div><b>Date :</b> ' + dateCourte(d.date) + ' ' + heure(d.date) + '<br>' +
            (d.vendeur ? '<b>' + (d.type === 'vente' ? 'Vendeur' : 'Pré-vendeur') + ' :</b> ' + esc(d.vendeur) + '<br>' : '') +
            (d.livreur ? '<b>Livreur :</b> ' + esc(d.livreur) : '') + '</div></div>' +
            '<table><thead><tr><th>Produit</th><th class="c">Qté (pièces)</th><th class="c">Nb cartons</th><th class="r">Prix unitaire' + (d.prix_ht ? ' HT' : '') +
            '</th><th class="r">Montant</th></tr></thead><tbody>' + lignes + '</tbody></table>' +
            '<table class="tot">' + (num(d.total_ht) && num(d.total_ht) !== num(d.total) ? '<tr><td>Total HT</td><td class="r">' + argent(d.total_ht) + '</td></tr>' : '') +
            '<tr class="g"><td>Total TTC</td><td class="r">' + argent(d.total) + '</td></tr><tr><td>Payé</td><td class="r">' + argent(d.paye) +
            '</td></tr><tr class="g"><td>Reste à payer</td><td class="r">' + argent(d.reste) + '</td></tr></table>' +
            (paiements ? '<h2>Paiements</h2><table><thead><tr><th>Date</th><th>Mode</th><th class="r">Montant</th></tr></thead><tbody>' + paiements + '</tbody></table>' : '') +
            '</body></html>');
        w.document.close();
        w.focus();
        setTimeout(function () { w.print(); }, 300);
    }

    // ---------- Rendu ----------
    function kpi(classe, valeurHtml, libelle, sous) {
        return '<div class="sp-kpi ' + classe + '"><div class="v">' + valeurHtml + '</div><div class="l">' + libelle + '</div>' +
            (sous ? '<div class="s">' + sous + '</div>' : '') + '</div>';
    }

    function libellePeriode() {
        if (!donnees) return '';
        if (!donnees.du && !donnees.au) return 'Toutes les dates';
        if (donnees.du === donnees.au) return 'Le ' + dateLisible(donnees.du);
        return 'Du ' + (donnees.du ? dateLisible(donnees.du) : '…') + ' au ' + (donnees.au ? dateLisible(donnees.au) : '…');
    }

    function sectionKpis(bons, groupes) {
        var total = 0, paye = 0, reste = 0, nb = { paye: 0, partiel: 0, non_paye: 0 };
        bons.forEach(function (b) { total += num(b.total); paye += num(b.paye); reste += num(b.reste); nb[b.etat]++; });
        var pct = total ? Math.round(paye / total * 100) : 0;
        var doivent = groupes.filter(function (g) { return g.reste > 0.01; }).length;
        var detteAnt = 0, nbAnt = 0;
        (donnees.clients || []).forEach(function (c) { if (num(c.dette_anterieure) > 0.01) { detteAnt += num(c.dette_anterieure); nbAnt++; } });
        return '<div class="sp-kpis">' +
            kpi('violet', bons.length, 'Bons', groupes.length + ' client' + (groupes.length > 1 ? 's' : '')) +
            kpi('bleu', argent(total), 'Total des bons', libellePeriode()) +
            kpi('vert', argent(paye), 'Déjà payé', pct + ' % du total') +
            kpi('rouge', argent(reste), 'Reste à encaisser', doivent + ' client' + (doivent > 1 ? 's' : '') + ' doi' + (doivent > 1 ? 'vent' : 't') + ' de l\'argent') +
            kpi('orange', nb.non_paye + ' <small style="font-size:.8rem;color:#94a3b8;">/ ' + nb.partiel + '</small>', 'Non payés / en partie', nb.paye + ' bon' + (nb.paye > 1 ? 's' : '') + ' payé' + (nb.paye > 1 ? 's' : '')) +
            kpi('gris', argent(detteAnt), 'Dettes antérieures', nbAnt ? nbAnt + ' client' + (nbAnt > 1 ? 's' : '') + ' · hors bons, toutes dates' : 'Aucune') +
            '</div>';
    }

    function barreOutils(nbLignes) {
        return '<div class="sp-barre-outils">' +
            '<div class="sp-vues">' +
            '<button type="button" class="' + (vue === 'clients' ? 'actif' : '') + '" onclick="spVue(\'clients\')"><i class="fas fa-users mr-1"></i>Par client</button>' +
            '<button type="button" class="' + (vue === 'bons' ? 'actif' : '') + '" onclick="spVue(\'bons\')"><i class="fas fa-list mr-1"></i>Tous les bons</button>' +
            '</div>' +
            '<div class="sp-actions">' +
            (vue === 'clients' && nbLignes ? '<button type="button" onclick="spToutDeplier()"><i class="fas fa-expand-alt mr-1"></i>' +
                (Object.keys(ouverts).length ? 'Tout replier' : 'Tout déplier') + '</button>' : '') +
            '<button type="button" class="sp-xls" onclick="spExporter()"><i class="fas fa-file-excel mr-1"></i>Exporter Excel</button>' +
            '<button type="button" onclick="spImprimer()"><i class="fas fa-print mr-1"></i>Imprimer</button>' +
            '</div></div>';
    }

    function sousTableBons(g) {
        var lignes = trierBons(g.bons).map(function (b) {
            return '<tr>' +
                '<td>' + dateCourte(b.date) + ' <span class="sp-tel">' + heure(b.date) + '</span></td>' +
                '<td>' + lienBon(b) + '<span class="sp-type">' + TYPES[b.type] + '</span></td>' +
                '<td>' + esc(b.vendeur || '—') + '</td>' +
                '<td class="r">' + argent(b.total) + '</td>' +
                '<td class="r">' + argent(b.paye) + '</td>' +
                '<td class="r">' + (num(b.reste) > 0.01 ? '<span class="sp-reste">' + argent(b.reste) + '</span>' : '<span class="sp-zero">0,00 DA</span>') + '</td>' +
                '<td>' + badgeEtat(b.etat) + '</td>' +
                '<td>' + (b.dernier_paiement ? dateCourte(b.dernier_paiement) : '<span class="sp-zero">—</span>') + '</td>' +
                '<td>' + esc(MODES[b.mode] || b.mode || '') + '</td>' +
                '</tr>';
        }).join('');
        var ant = num(g.client.dette_anterieure);
        return (ant > 0.01 ? '<div class="sp-dette-ant"><i class="fas fa-exclamation-triangle mr-1"></i>Ce client a aussi une <b>dette antérieure</b> de ' +
                argent(ant) + ' (saisie sans bon), comptée dans sa situation globale.</div>' : '<div style="height:10px"></div>') +
            '<table class="sp-sous sp-table"><thead><tr>' +
            '<th>Date</th><th>Bon</th><th>Pré-vendeur / livreur</th><th class="r">Montant</th><th class="r">Payé</th>' +
            '<th class="r">Reste</th><th>État</th><th>Dernier paiement</th><th>Mode</th>' +
            '</tr></thead><tbody>' + lignes + '</tbody></table>';
    }

    function sectionClients(groupes) {
        if (!groupes.length) return etatVide();
        var cols = [
            ['client', 'Client', ''], ['bons', 'Bons', 'c'], ['total', 'Total des bons', 'r'], ['paye', 'Payé', 'r'],
            ['pct', 'Avancement', ''], ['reste', 'Reste à payer', 'r'], ['situation', 'Situation globale', '']
        ];
        var tete = '<tr>' + cols.map(function (c) {
            return '<th class="tri ' + c[2] + '" onclick="spTrierClients(\'' + c[0] + '\')">' + c[1] + iconeTri(triClients, c[0]) + '</th>';
        }).join('') + '</tr>';
        var t = { total: 0, paye: 0, reste: 0, bons: 0, nb: { paye: 0, partiel: 0, non_paye: 0 } };
        var corps = groupes.map(function (g) {
            var id = g.client.id, ouvert = !!ouverts[id];
            var pct = g.total ? Math.round(g.paye / g.total * 100) : 100;
            t.total += g.total; t.paye += g.paye; t.reste += g.reste; t.bons += g.bons.length;
            t.nb.paye += g.nb.paye; t.nb.partiel += g.nb.partiel; t.nb.non_paye += g.nb.non_paye;
            return '<tr class="sp-client' + (ouvert ? ' ouvert' : '') + '" data-client="' + id + '" onclick="spBasculer(' + id + ')">' +
                '<td><i class="fas fa-chevron-right sp-chev"></i> <span class="sp-nom">' + esc(g.client.nom) + '</span>' +
                (g.client.telephone ? '<div class="sp-tel" style="margin-left:20px">' + esc(g.client.telephone) + '</div>' : '') + '</td>' +
                '<td class="c"><div class="sp-compteurs" title="Payés / en partie / non payés">' +
                '<span class="p' + (g.nb.paye ? '' : ' z') + '">' + g.nb.paye + '</span>' +
                '<span class="pa' + (g.nb.partiel ? '' : ' z') + '">' + g.nb.partiel + '</span>' +
                '<span class="n' + (g.nb.non_paye ? '' : ' z') + '">' + g.nb.non_paye + '</span></div></td>' +
                '<td class="r">' + argent(g.total) + '</td>' +
                '<td class="r">' + argent(g.paye) + '</td>' +
                '<td class="nw"><span class="sp-prog"><i style="width:' + pct + '%"></i></span><span class="sp-pct">' + pct + ' %</span></td>' +
                '<td class="r">' + (g.reste > 0.01 ? '<span class="sp-reste">' + argent(g.reste) + '</span>' : '<span class="sp-zero">0,00 DA</span>') + '</td>' +
                '<td>' + badgeSituation(g.client) + '</td>' +
                '</tr>' +
                (ouvert ? '<tr class="sp-detail"><td colspan="7">' + sousTableBons(g) + '</td></tr>' : '');
        }).join('');
        var pctT = t.total ? Math.round(t.paye / t.total * 100) : 100;
        var pied = '<tr><td>Total : ' + groupes.length + ' client' + (groupes.length > 1 ? 's' : '') + '</td>' +
            '<td class="c"><div class="sp-compteurs"><span class="p">' + t.nb.paye + '</span><span class="pa">' + t.nb.partiel +
            '</span><span class="n">' + t.nb.non_paye + '</span></div></td>' +
            '<td class="r">' + argent(t.total) + '</td><td class="r">' + argent(t.paye) + '</td>' +
            '<td class="nw"><span class="sp-prog"><i style="width:' + pctT + '%"></i></span><span class="sp-pct">' + pctT + ' %</span></td>' +
            '<td class="r sp-reste">' + argent(t.reste) + '</td><td></td></tr>';
        return '<div class="sp-carte"><div class="sp-table-wrap"><table class="sp-table" id="spTableClients"><thead>' + tete +
            '</thead><tbody>' + corps + '</tbody><tfoot>' + pied + '</tfoot></table></div>' +
            '<div class="sp-note"><i class="fas fa-lightbulb mr-1"></i>Bons : <b style="color:#065f46">payés</b> · ' +
            '<b style="color:#92400e">payés en partie</b> · <b style="color:#991b1b">non payés</b>. ' +
            'La <b>situation globale</b> est tout ce que le client doit aujourd\'hui (toutes dates, dette antérieure comprise, moins son avance).</div></div>';
    }

    function sectionBons(bons) {
        if (!bons.length) return etatVide();
        var cols = [
            ['date', 'Date', ''], ['reference', 'Bon', ''], ['client', 'Client', ''], ['vendeur', 'Pré-vendeur / livreur', ''],
            ['total', 'Montant', 'r'], ['paye', 'Payé', 'r'], ['reste', 'Reste', 'r'], ['etat', 'État', ''],
            ['dernier_paiement', 'Dernier paiement', ''], ['mode', 'Mode', '']
        ];
        var tete = '<tr>' + cols.map(function (c) {
            return '<th class="tri ' + c[2] + '" onclick="spTrierBons(\'' + c[0] + '\')">' + c[1] + iconeTri(triBons, c[0]) + '</th>';
        }).join('') + '</tr>';
        var tries = trierBons(bons);
        var t = { total: 0, paye: 0, reste: 0 };
        tries.forEach(function (b) { t.total += num(b.total); t.paye += num(b.paye); t.reste += num(b.reste); });
        var corps = tries.slice(0, limite).map(function (b) {
            var c = clientsParId[b.client_id] || {};
            return '<tr>' +
                '<td>' + dateCourte(b.date) + ' <span class="sp-tel">' + heure(b.date) + '</span></td>' +
                '<td>' + lienBon(b) + '<span class="sp-type">' + TYPES[b.type] + '</span></td>' +
                '<td><span class="sp-nom">' + esc(c.nom || '?') + '</span>' + (c.telephone ? '<div class="sp-tel">' + esc(c.telephone) + '</div>' : '') + '</td>' +
                '<td>' + esc(b.vendeur || '—') + '</td>' +
                '<td class="r">' + argent(b.total) + '</td>' +
                '<td class="r">' + argent(b.paye) + '</td>' +
                '<td class="r">' + (num(b.reste) > 0.01 ? '<span class="sp-reste">' + argent(b.reste) + '</span>' : '<span class="sp-zero">0,00 DA</span>') + '</td>' +
                '<td>' + badgeEtat(b.etat) + '</td>' +
                '<td>' + (b.dernier_paiement ? dateCourte(b.dernier_paiement) : '<span class="sp-zero">—</span>') + '</td>' +
                '<td>' + esc(MODES[b.mode] || b.mode || '') + '</td>' +
                '</tr>';
        }).join('');
        var plus = tries.length > limite ? '<div class="sp-plus"><button type="button" onclick="spPlus()">Afficher ' +
            Math.min(300, tries.length - limite) + ' bons de plus (' + (tries.length - limite) + ' restants)</button></div>' : '';
        var pied = '<tr><td colspan="4">Total : ' + tries.length + ' bon' + (tries.length > 1 ? 's' : '') + '</td>' +
            '<td class="r">' + argent(t.total) + '</td><td class="r">' + argent(t.paye) + '</td><td class="r sp-reste">' + argent(t.reste) +
            '</td><td colspan="3"></td></tr>';
        return '<div class="sp-carte"><div class="sp-table-wrap"><table class="sp-table" id="spTableBons"><thead>' + tete +
            '</thead><tbody>' + corps + '</tbody><tfoot>' + pied + '</tfoot></table></div>' + plus + '</div>';
    }

    function etatVide() {
        var filtre = valeur('spEtat') || valeur('spType') || valeur('spClient') || valeur('spVendeur') || recherche;
        return '<div class="sp-carte sp-vide"><i class="fas fa-file-invoice"></i>' +
            '<div style="font-weight:700;color:#475569;font-size:1.05rem">Aucun bon ' + (filtre ? 'ne correspond aux filtres' : 'sur cette période') + '</div>' +
            '<div style="margin-top:6px">' + (filtre ? 'Changez les filtres ou ' : 'Choisissez une autre période, par exemple ') +
            '<a href="#" onclick="spRaccourci(\'tout\');return false;">toutes les dates</a>.</div></div>';
    }

    function remplirSelects() {
        var sc = $id('spClient'), sv = $id('spVendeur');
        if (!sc || !sv || !donnees) return;
        var cAvant = sc.value, vAvant = sv.value;
        var idsAvecBons = {};
        donnees.bons.forEach(function (b) { idsAvecBons[b.client_id] = true; });
        var clients = donnees.clients.filter(function (c) { return idsAvecBons[c.id]; })
            .sort(function (a, b) { return a.nom.localeCompare(b.nom); });
        sc.innerHTML = '<option value="">Tous les clients (' + clients.length + ')</option>' + clients.map(function (c) {
            return '<option value="' + c.id + '"' + (String(c.id) === cAvant ? ' selected' : '') + '>' + esc(c.nom) + '</option>';
        }).join('');
        var vendeurs = {};
        donnees.bons.forEach(function (b) { if (b.vendeur) vendeurs[b.vendeur] = true; });
        sv.innerHTML = '<option value="">Tous</option>' + Object.keys(vendeurs).sort().map(function (v) {
            return '<option' + (v === vAvant ? ' selected' : '') + '>' + esc(v) + '</option>';
        }).join('');
        if (window.jQuery) { jQuery(sc).trigger('change.select2'); jQuery(sv).trigger('change.select2'); }
    }

    function afficher() {
        var zone = $id('spContenu');
        if (!zone || !donnees) return;
        var bons = bonsFiltres();
        var groupes = parClient(bons);
        zone.innerHTML = sectionKpis(bons, groupes) + barreOutils(groupes.length) +
            (vue === 'clients' ? sectionClients(groupes) : sectionBons(bons));
    }

    // ---------- Chargement ----------
    function marquerRaccourci() {
        var du = valeur('spDu'), au = valeur('spAu');
        var boutons = document.querySelectorAll('#spRoot [data-sp-raccourci]');
        for (var i = 0; i < boutons.length; i++) {
            var b = bornes(boutons[i].getAttribute('data-sp-raccourci'));
            boutons[i].classList.toggle('actif', b.du === du && b.au === au);
        }
    }

    function bornes(nom) {
        var a = new Date(), du, au = iso(a);
        if (nom === 'mois') du = iso(new Date(a.getFullYear(), a.getMonth(), 1));
        else if (nom === 'mois_dernier') {
            du = iso(new Date(a.getFullYear(), a.getMonth() - 1, 1));
            au = iso(new Date(a.getFullYear(), a.getMonth(), 0));
        }
        else if (nom === 'trimestre') du = iso(new Date(a.getFullYear(), a.getMonth() - 3, a.getDate()));
        else if (nom === 'annee') du = iso(new Date(a.getFullYear(), 0, 1));
        else { du = ''; au = ''; }
        return { du: du, au: au };
    }

    function charger() {
        var zone = $id('spContenu');
        if (!zone) return;
        var du = valeur('spDu'), au = valeur('spAu');
        if (du && au && du > au) { $id('spDu').value = au; $id('spAu').value = du; du = valeur('spDu'); au = valeur('spAu'); }
        marquerRaccourci();
        var n = ++requete;
        zone.innerHTML = '<div class="sp-carte sp-chargement"><i class="fas fa-spinner fa-spin fa-2x"></i><div class="mt-2">Chargement des bons…</div></div>';
        fetch('/API/clients/suivi_paiements/?du=' + encodeURIComponent(du) + '&au=' + encodeURIComponent(au), {
            credentials: 'same-origin', headers: { 'X-CSRFToken': cookie('csrftoken') }
        }).then(function (r) {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        }).then(function (d) {
            if (n !== requete) return;
            donnees = d;
            clientsParId = {};
            d.clients.forEach(function (c) { clientsParId[c.id] = c; });
            ouverts = {};
            limite = 300;
            remplirSelects();
            afficher();
        }).catch(function (e) {
            if (n !== requete) return;
            console.error('[SUIVI PAIEMENTS]', e);
            zone.innerHTML = '<div class="sp-carte sp-vide"><i class="fas fa-exclamation-triangle" style="color:#f87171"></i>' +
                '<div style="font-weight:700;color:#475569">Impossible de charger les bons</div>' +
                '<div style="margin:6px 0 12px">Vérifiez la connexion puis réessayez.</div>' +
                '<button type="button" class="btn btn-outline-primary btn-sm" onclick="spCharger()"><i class="fas fa-redo mr-1"></i>Réessayer</button></div>';
        });
    }

    // ---------- Export / impression ----------
    function lignesExport() {
        var bons = trierBons(bonsFiltres());
        if (vue === 'clients') {
            var ordre = {};
            parClient(bons).forEach(function (g, i) { ordre[g.client.id] = i; });
            bons.sort(function (a, b) { return (ordre[a.client_id] - ordre[b.client_id]) || 0; });
        }
        return bons;
    }

    function exporter() {
        if (!donnees) return;
        var sep = ';';
        function cel(v) { v = String(v == null ? '' : v); return /[;"\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; }
        function nb(v) { return num(v).toFixed(2).replace('.', ','); }
        var out = [];
        out.push(['Suivi des paiements par bon', libellePeriode()].map(cel).join(sep));
        out.push('');
        out.push('PAR CLIENT');
        out.push(['Client', 'Téléphone', 'Nb bons', 'Payés', 'Payés en partie', 'Non payés', 'Total des bons', 'Payé', 'Reste à payer',
            'Dette antérieure', 'Situation globale (doit +, avance -)'].map(cel).join(sep));
        var bons = lignesExport();
        parClient(bons).forEach(function (g) {
            out.push([g.client.nom, g.client.telephone, g.bons.length, g.nb.paye, g.nb.partiel, g.nb.non_paye,
                nb(g.total), nb(g.paye), nb(g.reste), nb(g.client.dette_anterieure), nb(g.client.situation)].map(cel).join(sep));
        });
        out.push('');
        out.push('DÉTAIL DES BONS');
        out.push(['Date', 'Heure', 'Bon', 'Type', 'Client', 'Téléphone', 'Pré-vendeur / livreur', 'Montant', 'Payé', 'Reste',
            'État', 'Dernier paiement', 'Mode'].map(cel).join(sep));
        bons.forEach(function (b) {
            var c = clientsParId[b.client_id] || {};
            out.push([dateCourte(b.date), heure(b.date), b.reference, TYPES[b.type], c.nom, c.telephone, b.vendeur,
                nb(b.total), nb(b.paye), nb(b.reste), ETATS[b.etat], dateCourte(b.dernier_paiement), MODES[b.mode] || b.mode].map(cel).join(sep));
        });
        var nom = 'suivi_paiements_' + (donnees.du || 'debut') + '_' + (donnees.au || 'aujourdhui') + '.csv';
        var blob = new Blob(['﻿' + out.join('\r\n')], { type: 'text/csv;charset=utf-8' });
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = nom;
        document.body.appendChild(a);
        a.click();
        setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
    }

    function imprimer() {
        if (!donnees) return;
        var bons = lignesExport();
        var groupes = parClient(bons);
        var filtres = [];
        var e = $id('spEtat'), ty = $id('spType'), cl = $id('spClient'), ve = $id('spVendeur');
        if (e && e.value) filtres.push('État : ' + e.options[e.selectedIndex].text);
        if (ty && ty.value) filtres.push('Type : ' + ty.options[ty.selectedIndex].text);
        if (cl && cl.value) filtres.push('Client : ' + cl.options[cl.selectedIndex].text);
        if (ve && ve.value) filtres.push('Vendeur : ' + ve.value);
        if (recherche) filtres.push('Recherche : « ' + recherche + ' »');
        var html = groupes.map(function (g) {
            return '<h3>' + esc(g.client.nom) + (g.client.telephone ? ' <small>' + esc(g.client.telephone) + '</small>' : '') +
                '<span class="sit">Reste : ' + argent(g.reste) + ' · Situation globale : ' +
                (num(g.client.situation) > 0.01 ? 'doit ' + argent(g.client.situation) : num(g.client.situation) < -0.01 ? 'avance ' + argent(-num(g.client.situation)) : 'à jour') +
                '</span></h3><table><thead><tr><th>Date</th><th>Bon</th><th>Pré-vendeur / livreur</th><th class="r">Montant</th>' +
                '<th class="r">Payé</th><th class="r">Reste</th><th>État</th><th>Dernier paiement</th></tr></thead><tbody>' +
                trierBons(g.bons).map(function (b) {
                    return '<tr><td>' + dateCourte(b.date) + '</td><td>' + esc(b.reference) + '<br><small>' + TYPES[b.type] + '</small></td><td>' +
                        esc(b.vendeur) + '</td><td class="r">' + argent(b.total) + '</td><td class="r">' + argent(b.paye) +
                        '</td><td class="r"><b>' + argent(b.reste) + '</b></td><td class="e-' + b.etat + '">' + ETATS[b.etat] + '</td><td>' +
                        dateCourte(b.dernier_paiement) + '</td></tr>';
                }).join('') +
                '</tbody><tfoot><tr><td colspan="3">' + g.bons.length + ' bon(s)</td><td class="r">' + argent(g.total) + '</td><td class="r">' +
                argent(g.paye) + '</td><td class="r">' + argent(g.reste) + '</td><td colspan="2"></td></tr></tfoot></table>';
        }).join('');
        var total = 0, paye = 0, reste = 0;
        bons.forEach(function (b) { total += num(b.total); paye += num(b.paye); reste += num(b.reste); });
        var w = window.open('', '_blank');
        if (!w) return;
        w.document.write('<!doctype html><html><head><meta charset="utf-8"><title>Suivi des paiements par bon</title><style>' +
            'body{font-family:Arial,sans-serif;font-size:12px;color:#111;margin:20px}h1{font-size:18px;margin:0 0 4px}' +
            '.sous{color:#555;margin-bottom:12px}.resume{display:flex;gap:18px;margin:10px 0 16px;padding:8px 12px;background:#f3f4f6;border-radius:6px}' +
            'h3{font-size:13px;margin:16px 0 4px;display:flex;justify-content:space-between;border-bottom:1px solid #999;padding-bottom:3px}' +
            'h3 small{color:#666;font-weight:normal}.sit{font-weight:normal;font-size:12px}table{width:100%;border-collapse:collapse;margin-bottom:6px}' +
            'th,td{border:1px solid #ccc;padding:4px 6px;text-align:left}th{background:#eee}.r{text-align:right}tfoot td{font-weight:bold;background:#f7f7f7}' +
            '.e-paye{color:#065f46}.e-partiel{color:#92400e}.e-non_paye{color:#991b1b;font-weight:bold}h3,table{page-break-inside:avoid}' +
            '</style></head><body><h1>Suivi des paiements par bon</h1><div class="sous">' + libellePeriode() +
            (filtres.length ? ' · ' + esc(filtres.join(' · ')) : '') + ' · imprimé le ' + dateCourte(new Date().toISOString()) + '</div>' +
            '<div class="resume"><span><b>' + bons.length + '</b> bons</span><span>Total : <b>' + argent(total) + '</b></span><span>Payé : <b>' +
            argent(paye) + '</b></span><span>Reste à encaisser : <b>' + argent(reste) + '</b></span></div>' +
            (html || '<p>Aucun bon.</p>') + '</body></html>');
        w.document.close();
        w.focus();
        setTimeout(function () { w.print(); }, 300);
    }

    // ---------- Onglets ----------
    function choisirOnglet(nom) {
        onglet = nom;
        var ens = $id('csdVueEnsemble'), sp = $id('spRoot');
        if (!ens || !sp) return;
        ens.style.display = nom === 'suivi' ? 'none' : '';
        sp.style.display = nom === 'suivi' ? '' : 'none';
        var boutons = document.querySelectorAll('[data-csd-onglet]');
        for (var i = 0; i < boutons.length; i++) boutons[i].classList.toggle('actif', boutons[i].getAttribute('data-csd-onglet') === nom);
        try { localStorage.setItem('csd_onglet', nom); } catch (e) { /* stockage indisponible */ }
        if (nom === 'suivi' && !donnees) charger();
    }

    function init() {
        var racine = $id('spRoot');
        if (!racine || racine.__spInit) return;   // déjà initialisé pour cet affichage de la page
        racine.__spInit = true;
        donnees = null;
        ouverts = {};
        recherche = '';
        var b = bornes('annee');
        $id('spDu').value = b.du;
        $id('spAu').value = b.au;
        var rb = $id('refresh-btn');
        if (rb && !rb.__sp) {
            rb.__sp = true;
            rb.addEventListener('click', function () { if (onglet === 'suivi') charger(); });
        }
        var memo = 'ensemble';
        try { memo = localStorage.getItem('csd_onglet') || 'ensemble'; } catch (e) { /* stockage indisponible */ }
        choisirOnglet(memo === 'suivi' ? 'suivi' : 'ensemble');
    }

    document.addEventListener('fragment:loaded', function (e) {
        if (e.detail && e.detail.name === 'clients_solde_dashboard') setTimeout(init, 0);
    });

    // ---------- API globale (boutons de la page) ----------
    window.spInit = init;
    window.spOnglet = choisirOnglet;
    window.spCharger = charger;
    window.spAfficher = function () { ouverts = {}; limite = 300; afficher(); };
    window.spDatesChangees = charger;
    window.spRaccourci = function (nom) {
        var b = bornes(nom);
        $id('spDu').value = b.du;
        $id('spAu').value = b.au;
        charger();
    };
    window.spRechercher = function (texte) {
        clearTimeout(minuterieRecherche);
        minuterieRecherche = setTimeout(function () { recherche = texte || ''; limite = 300; afficher(); }, 200);
    };
    window.spVue = function (v) { vue = v; afficher(); };
    window.spBasculer = function (id) {
        if (ouverts[id]) delete ouverts[id]; else ouverts[id] = true;
        afficher();
    };
    window.spToutDeplier = function () {
        if (Object.keys(ouverts).length) ouverts = {};
        else parClient(bonsFiltres()).forEach(function (g) { ouverts[g.client.id] = true; });
        afficher();
    };
    window.spTrierClients = function (col) {
        triClients = { col: col, sens: triClients.col === col ? -triClients.sens : (col === 'client' ? 1 : -1) };
        afficher();
    };
    window.spTrierBons = function (col) {
        triBons = { col: col, sens: triBons.col === col ? -triBons.sens : (col === 'client' || col === 'reference' || col === 'vendeur' ? 1 : -1) };
        afficher();
    };
    window.spPlus = function () { limite += 300; afficher(); };
    window.spExporter = exporter;
    window.spVoirBon = voirBon;
    window.spFermerBon = fermerBon;
    window.spImprimerBon = imprimerBon;
    window.spImprimer = imprimer;
})();
