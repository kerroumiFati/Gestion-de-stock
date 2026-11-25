/**
 * recap_commandes.js — page « Récapitulatif des commandes » (menu Rapports & Analyses).
 *
 * Pour la période choisie (un jour ou « du … au … ») :
 *   - indicateurs (commandes, pré-vendeurs, produits, montant, encaissé, reste) ;
 *   1. quantités de chaque produit commandées par chaque pré-vendeur (+ total, nb de cartons) ;
 *   2. une carte par pré-vendeur avec toutes ses commandes (client, produits, montants).
 * Pré-vendeur = celui qui a passé la commande (passee_par), sinon le livreur.
 * Commandes annulées : masquées par défaut, jamais comptées dans les totaux.
 * Données : GET /API/distribution/commandes/?date_debut=...&date_fin=...
 */
(function () {
    'use strict';

    var commandesJour = [];   // toutes les commandes de la période (y compris annulées)
    var requete = 0;
    var majLe = null;
    var fermes = {};          // cartes pré-vendeurs repliées
    var clientsVisibles = {}; // produit -> détail des clients affiché (true / false)
    var onglet = 'recap';     // 'recap' ou 'tableau'
    var triTableau = { col: 'date', sens: 1 };
    var rechercheTableau = '';
    var limiteTableau = 300;  // lignes affichées dans le tableau détaillé (bouton « Afficher plus »)

    var STATUTS = {
        pending: 'En attente', confirmed: 'Confirmée', preparing: 'En préparation',
        ready: 'Prête', delivered: 'Livrée', cancelled: 'Annulée'
    };
    var COULEURS = ['#2563eb', '#7c3aed', '#db2777', '#ea580c', '#059669', '#0891b2', '#4f46e5', '#b45309', '#be123c', '#0f766e'];

    function el(id) { return document.getElementById(id); }
    function n(v) { return parseFloat(v) || 0; }
    function fmtQ(q) { return Number.isInteger(q) ? String(q) : q.toFixed(2); }
    function pluriel(k, mot) { return k + ' ' + mot + (k > 1 ? 's' : ''); }

    function esc(v) {
        return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }

    function argent(v) {
        return new Intl.NumberFormat('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(v || 0) + ' DA';
    }

    function jourLocal(d) {
        d = d instanceof Date ? d : new Date(d);
        return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
    }

    function decalerJour(jour, delta) {
        var d = new Date(jour + 'T12:00:00');
        d.setDate(d.getDate() + delta);
        return jourLocal(d);
    }

    function dateLongue(jour) {
        return new Date(jour + 'T12:00:00').toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
    }

    function dateCourte(jour) {
        return new Date(jour + 'T12:00:00').toLocaleDateString('fr-FR');
    }

    function ecartJours(du, au) {
        return Math.round((new Date(au + 'T12:00:00') - new Date(du + 'T12:00:00')) / 86400000);
    }

    // Période choisie : { du, au, unJour } (dates incluses, remises dans l'ordre si inversées)
    function periode() {
        var du = el('rcDu').value, au = el('rcAu').value || du;
        if (!du) du = au;
        if (du && au && au < du) { var t = du; du = au; au = t; }
        return { du: du, au: au, unJour: du === au };
    }

    function libellePeriode(p) {
        if (p.unJour) return dateLongue(p.du);
        return 'Du ' + dateCourte(p.du) + ' au ' + dateCourte(p.au) + ' (' + (ecartJours(p.du, p.au) + 1) + ' jours)';
    }

    // Heure de la commande ; date + heure quand la période couvre plusieurs jours
    function horodatage(c) {
        var d = new Date(c.date_commande);
        var h = d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
        return periode().unJour ? h : d.toLocaleDateString('fr-FR') + ' ' + h;
    }

    // Nombre de cartons : 1 u (carton de 8) -> 1/8 ; 8 u -> 1 ; 10 u -> 1 + 2/8 ; '-' sans carton
    function nbCartons(q, upc) {
        upc = parseInt(upc, 10);
        if (!(upc > 1)) return '-';
        q = Math.abs(Math.round(q)) || 0;
        var ct = Math.floor(q / upc), reste = q % upc;
        if (!reste) return String(ct);
        return ct ? ct + ' + ' + reste + '/' + upc : reste + '/' + upc;
    }

    function initiales(nom) {
        return String(nom || '?').split(/\s+/).filter(Boolean).slice(0, 2).map(function (m) { return m[0]; }).join('').toUpperCase();
    }

    function vendeurId(c) { return String(c.passee_par || c.livreur || 0); }
    function vendeurNom(c) { return c.passee_par_nom || c.livreur_nom || 'Sans pré-vendeur'; }

    // ---------- Filtre produit ----------
    // Un produit choisi : seules les commandes qui le contiennent, seules ses lignes, et ses montants
    // (le payé / reste d'une commande concerne toute la commande : il n'est pas affiché dans ce cas).
    function filtreProduit() { return el('rcProduit') ? el('rcProduit').value : ''; }

    function lignesDe(c) {
        var fp = filtreProduit();
        return (c.lignes || []).filter(function (l) { return !fp || String(l.produit) === fp; });
    }

    function montantCmd(c) {
        if (!filtreProduit()) return n(c.montant_total_ttc);
        return lignesDe(c).reduce(function (s, l) { return s + n(l.montant_ttc); }, 0);
    }

    // ---------- Calcul ----------
    function calculer() {
        var filtreV = el('rcVendeur').value, fp = filtreProduit();
        var voirAnnulees = el('rcAnnulees').checked;
        var cmds = commandesJour.filter(function (c) {
            return (!filtreV || vendeurId(c) === filtreV) && (!fp || lignesDe(c).length > 0);
        });
        var actives = cmds.filter(function (c) { return c.statut !== 'cancelled'; });
        var visibles = voirAnnulees ? cmds : actives;

        var vendeurs = new Map();
        visibles.forEach(function (c) {
            var id = vendeurId(c);
            if (!vendeurs.has(id)) vendeurs.set(id, { id: id, nom: vendeurNom(c), commandes: [] });
            vendeurs.get(id).commandes.push(c);
        });
        var listeV = Array.from(vendeurs.values()).sort(function (x, y) { return x.nom.localeCompare(y.nom, 'fr'); });
        listeV.forEach(function (v) {
            var act = v.commandes.filter(function (c) { return c.statut !== 'cancelled'; });
            v.nbActives = act.length;
            v.nbAnnulees = v.commandes.length - act.length;
            v.ttc = act.reduce(function (s, c) { return s + montantCmd(c); }, 0);
            v.paye = fp ? 0 : act.reduce(function (s, c) { return s + Math.min(n(c.montant_paye), n(c.montant_total_ttc)); }, 0);
            v.reste = fp ? 0 : act.reduce(function (s, c) { return s + Math.max(0, n(c.montant_total_ttc) - n(c.montant_paye)); }, 0);
            v.quantite = act.reduce(function (s, c) { return s + lignesDe(c).reduce(function (q, l) { return q + n(l.quantite); }, 0); }, 0);
            v.clients = new Set(act.map(function (c) { return c.client; })).size;
        });
        var vendeursProduits = listeV.filter(function (v) { return v.nbActives > 0; });

        var produits = new Map();
        actives.forEach(function (c) {
            lignesDe(c).forEach(function (l) {
                if (!produits.has(l.produit)) {
                    produits.set(l.produit, { designation: l.produit_designation || '-', reference: l.produit_reference || '',
                        upc: l.produit_unites_par_carton, parV: new Map(), total: 0, montant: 0, nbCmd: new Set(), clients: new Map() });
                }
                var p = produits.get(l.produit), q = n(l.quantite), v = vendeurId(c);
                p.parV.set(v, (p.parV.get(v) || 0) + q);
                p.total += q; p.montant += n(l.montant_ttc); p.nbCmd.add(c.id);
                var cleClient = String(c.client) + '|' + v;
                if (!p.clients.has(cleClient)) {
                    p.clients.set(cleClient, { nom: [c.client_prenom, c.client_nom].filter(Boolean).join(' ') || '-',
                        vendeur: vendeurNom(c), quantite: 0, montant: 0, commandes: [] });
                }
                var cl = p.clients.get(cleClient);
                cl.quantite += q; cl.montant += n(l.montant_ttc);
                if (cl.commandes.indexOf(c.reference) === -1) cl.commandes.push(c.reference);
            });
        });
        var listeP = Array.from(produits.entries()).map(function (e) {
            var p = e[1];
            p.id = String(e[0]);
            p.listeClients = Array.from(p.clients.values()).sort(function (x, y) { return y.quantite - x.quantite || x.nom.localeCompare(y.nom, 'fr'); });
            p.nbClients = new Set(p.listeClients.map(function (cl) { return cl.nom; })).size;
            return p;
        }).sort(function (x, y) { return x.designation.localeCompare(y.designation, 'fr'); });

        var t = { commandes: actives.length, annulees: cmds.length - actives.length, ttc: 0, paye: 0, reste: 0 };
        actives.forEach(function (c) {
            t.ttc += montantCmd(c);
            if (!fp) {
                t.paye += Math.min(n(c.montant_paye), n(c.montant_total_ttc));
                t.reste += Math.max(0, n(c.montant_total_ttc) - n(c.montant_paye));
            }
        });
        return { listeV: listeV, vendeursProduits: vendeursProduits, listeP: listeP, totaux: t, modeProduit: !!fp,
                 produit: fp ? listeP[0] : null,
                 nbClients: new Set(actives.map(function (c) { return c.client; })).size,
                 nbVendeurs: new Set(actives.map(vendeurId)).size };
    }

    // ---------- Affichage écran ----------
    function kpi(icone, couleur, valeur, libelle) {
        return '<div class="rc-kpi"><div class="ic ' + couleur + '"><i class="fas ' + icone + '"></i></div>' +
            '<div><div class="v">' + valeur + '</div><div class="l">' + libelle + '</div></div></div>';
    }

    function celluleQte(q, upc, cls) {
        if (!q) return '<td class="c ' + (cls || '') + '"><span class="rc-zero">—</span></td>';
        var ct = nbCartons(q, upc);
        return '<td class="c ' + (cls || '') + '"><div class="rc-q">' + fmtQ(q) + '</div>' +
            (ct !== '-' ? '<span class="rc-ct" title="Nombre de cartons">' + ct + ' ct</span>' : '') + '</td>';
    }

    // Détail des clients d'un produit, affiché sous sa ligne
    function detailClients(p, nbCols) {
        var lignes = p.listeClients.map(function (cl) {
            var ct = nbCartons(cl.quantite, p.upc);
            return '<tr><td><i class="fas fa-store text-muted mr-1"></i> <b>' + esc(cl.nom) + '</b></td><td>' + esc(cl.vendeur) + '</td>' +
                '<td class="rc-cmds">' + cl.commandes.map(esc).join(', ') + '</td>' +
                '<td class="c"><b>' + fmtQ(cl.quantite) + '</b>' + (ct !== '-' ? ' <span class="rc-ct">' + ct + ' ct</span>' : '') + '</td>' +
                '<td class="r">' + argent(cl.montant) + '</td></tr>';
        }).join('');
        return '<tr class="rc-detail-clients" data-pour="' + esc(p.id) + '"' + (clientsVisibles[p.id] ? '' : ' style="display:none"') + '><td colspan="' + nbCols + '">' +
            '<table class="rc-sous-table"><thead><tr><th>Client</th><th>Pré-vendeur</th><th>Commande(s)</th><th class="c">Quantité</th><th class="r">Montant TTC</th></tr></thead>' +
            '<tbody>' + lignes + '</tbody></table></td></tr>';
    }

    function sectionProduits(r) {
        var vs = r.vendeursProduits, nbCols = vs.length + 5;
        // Peu de produits (ou un produit choisi) : clients affichés d'office ; sinon au clic
        var ouvrirTout = r.listeP.length <= 8;
        r.listeP.forEach(function (p) { if (clientsVisibles[p.id] === undefined) clientsVisibles[p.id] = ouvrirTout; });
        var corps = r.listeP.map(function (p) {
            var ouvert = !!clientsVisibles[p.id];
            var apercu = p.listeClients.slice(0, 2).map(function (cl) { return esc(cl.nom); }).join(', ') + (p.nbClients > 2 ? '…' : '');
            return '<tr class="rc-ligne-produit" data-produit="' + esc((p.designation + ' ' + p.reference).toLowerCase()) + '" data-id="' + esc(p.id) + '">' +
                '<td><div class="rc-prod-nom">' + esc(p.designation) + '</div>' +
                (p.reference ? '<div class="rc-prod-ref">' + esc(p.reference) + '</div>' : '') + '</td>' +
                '<td><button type="button" class="rc-btn-clients' + (ouvert ? ' ouvert' : '') + '" onclick="recapCommandesClientsProduit(\'' + esc(p.id) + '\')" ' +
                'title="Afficher / masquer les clients qui ont commandé ce produit"><i class="fas fa-chevron-right"></i> ' +
                pluriel(p.nbClients, 'client') + '</button><div class="rc-apercu-clients">' + apercu + '</div></td>' +
                vs.map(function (v) { return celluleQte(p.parV.get(v.id) || 0, p.upc); }).join('') +
                celluleQte(p.total, p.upc, 'col-total') +
                '<td class="c">' + p.nbCmd.size + '</td><td class="r">' + argent(p.montant) + '</td></tr>' +
                detailClients(p, nbCols);
        }).join('');
        return '<div class="rc-panneau rc-section">' +
            '<div class="rc-section-tete"><div><h2><span class="num">1</span> Quantités par produit</h2>' +
            '<div class="aide">Combien de chaque produit chaque pré-vendeur a commandé, et pour quels clients. La colonne <b>Total</b> sert à préparer la marchandise.</div></div>' +
            '<div class="d-flex flex-wrap align-items-center" style="gap:8px">' +
            '<button class="btn btn-sm btn-light" onclick="recapCommandesTousClients(true)"><i class="fas fa-users"></i> Afficher tous les clients</button>' +
            '<button class="btn btn-sm btn-light" onclick="recapCommandesTousClients(false)"><i class="fas fa-eye-slash"></i> Masquer</button>' +
            '<div class="rc-recherche"><i class="fas fa-search"></i><input type="search" class="form-control" id="rcRechercheProduit" ' +
            'placeholder="Produit ou client…" oninput="recapCommandesFiltrerProduits(this.value)"></div></div></div>' +
            '<div class="rc-table-wrap"><table class="rc-table"><thead><tr><th>Produit</th><th>Clients</th>' +
            vs.map(function (v) { return '<th class="c">' + esc(v.nom) + '</th>'; }).join('') +
            '<th class="c col-total">Total</th><th class="c">Commandes</th><th class="r">Montant TTC</th></tr></thead><tbody>' + corps +
            '<tr class="rc-aucun-produit" style="display:none"><td colspan="' + nbCols + '" class="c text-muted py-4">Aucun produit ni client ne correspond à la recherche.</td></tr>' +
            '</tbody><tfoot><tr><td>Total</td><td>' + pluriel(r.nbClients, 'client') + '</td>' +
            vs.map(function (v) { return '<td class="r">' + argent(v.ttc) + '</td>'; }).join('') +
            '<td class="r col-total">' + argent(r.totaux.ttc) + '</td><td class="c">' + r.totaux.commandes + '</td><td class="r">' + argent(r.totaux.ttc) + '</td></tr></tfoot></table></div>' +
            '<div class="rc-astuce"><i class="fas fa-info-circle"></i> « ct » = nombre de cartons. Exemple, carton de 8 : 1 pièce = 1/8, 10 pièces = 1 + 2/8.</div></div>';
    }

    function carteVendeur(v, index) {
        var mp = !!filtreProduit();
        var couleur = COULEURS[index % COULEURS.length];
        var pct = v.ttc > 0 ? Math.round(v.paye / v.ttc * 100) : 0;
        var lignes = v.commandes.map(function (c, i) {
            var annulee = c.statut === 'cancelled';
            var reste = annulee ? 0 : Math.max(0, n(c.montant_total_ttc) - n(c.montant_paye));
            var prods = lignesDe(c).map(function (l) {
                var ct = nbCartons(n(l.quantite), l.produit_unites_par_carton);
                return '<span class="rc-puce">' + esc(l.produit_designation || '-') + ' × <b>' + fmtQ(n(l.quantite)) + '</b>' +
                    (ct !== '-' ? ' <small class="text-primary">(' + ct + ' ct)</small>' : '') + '</span>';
            }).join('') || '<span class="text-muted">—</span>';
            return '<tr' + (annulee ? ' class="rc-annulee"' : '') + '><td class="c text-muted">' + (i + 1) + '</td>' +
                '<td><div class="rc-ref">' + esc(c.reference) + '</div><div class="rc-heure"><i class="far fa-clock"></i> ' +
                horodatage(c) + '</div></td>' +
                '<td><div class="font-weight-bold">' + esc([c.client_prenom, c.client_nom].filter(Boolean).join(' ')) + '</div>' +
                (c.livreur_nom && c.livreur_nom !== v.nom ? '<div class="rc-heure"><i class="fas fa-truck"></i> Livreur : ' + esc(c.livreur_nom) + '</div>' : '') + '</td>' +
                '<td>' + prods + '</td>' +
                '<td><span class="rc-badge st-' + esc(c.statut) + '">' + esc(STATUTS[c.statut] || c.statut) + '</span></td>' +
                '<td class="r font-weight-bold">' + argent(montantCmd(c)) + '</td>' +
                (mp ? '' : '<td class="r">' + argent(annulee ? 0 : n(c.montant_paye)) + '</td>' +
                '<td class="r ' + (reste > 0 ? 'rc-reste-du' : 'rc-reste-ok') + '">' + (annulee ? '—' : argent(reste)) + '</td>') + '</tr>';
        }).join('');
        return '<div class="rc-vendeur' + (fermes[v.id] ? ' ferme' : '') + '" data-vendeur="' + esc(v.id) + '">' +
            '<div class="rc-vendeur-tete" onclick="recapCommandesBasculer(\'' + esc(v.id) + '\')" title="Cliquer pour afficher / masquer les commandes">' +
            '<i class="fas fa-chevron-down rc-chevron"></i>' +
            '<div class="rc-avatar" style="background:' + couleur + '">' + esc(initiales(v.nom)) + '</div>' +
            '<div><div class="rc-vendeur-nom">' + esc(v.nom) + '</div><div class="rc-vendeur-sous">' +
            pluriel(v.nbActives, 'commande') + ' · ' + pluriel(v.clients, 'client') +
            (v.nbAnnulees ? ' · <span class="text-muted">' + pluriel(v.nbAnnulees, 'annulée') + '</span>' : '') + '</div></div>' +
            '<div class="rc-vendeur-chiffres">' +
            (mp
                ? '<div class="rc-chiffre"><div class="l">Quantité</div><div class="v">' + fmtQ(v.quantite) +
                  (function () { var ct = nbCartons(v.quantite, v.commandes[0] && lignesDe(v.commandes[0])[0] ? lignesDe(v.commandes[0])[0].produit_unites_par_carton : 1);
                                 return ct !== '-' ? ' <span class="rc-ct">' + ct + ' ct</span>' : ''; })() + '</div></div>' +
                  '<div class="rc-chiffre"><div class="l">Montant</div><div class="v">' + argent(v.ttc) + '</div></div>'
                : '<div class="rc-chiffre"><div class="l">Total</div><div class="v">' + argent(v.ttc) + '</div></div>' +
                  '<div class="rc-chiffre"><div class="l">Encaissé</div><div class="v vert">' + argent(v.paye) + '</div></div>' +
                  '<div class="rc-chiffre"><div class="l">Reste</div><div class="v ' + (v.reste > 0 ? 'rouge' : 'vert') + '">' + argent(v.reste) + '</div></div>' +
                  '<div class="rc-chiffre rc-barre-paiement"><div class="l">Payé ' + pct + ' %</div><div class="progress"><div class="progress-bar bg-success" style="width:' + pct + '%"></div></div></div>') +
            '</div></div>' +
            '<div class="rc-vendeur-corps"><div class="rc-table-wrap" style="max-height:none"><table class="rc-table"><thead><tr>' +
            '<th class="c">#</th><th>Commande</th><th>Client</th><th>' + (mp ? 'Produit' : 'Produits commandés') + '</th><th>Statut</th>' +
            (mp ? '<th class="r">Montant du produit</th>' : '<th class="r">Total TTC</th><th class="r">Payé</th><th class="r">Reste</th>') +
            '</tr></thead><tbody>' + lignes + '</tbody></table></div></div></div>';
    }

    function sectionVendeurs(r) {
        return '<div class="rc-panneau rc-section">' +
            '<div class="rc-section-tete"><div><h2><span class="num">2</span> Commandes de chaque pré-vendeur</h2>' +
            '<div class="aide">Cliquez sur un pré-vendeur pour afficher ou masquer ses commandes.</div></div>' +
            '<div class="d-flex" style="gap:6px"><button class="btn btn-sm btn-light" onclick="recapCommandesToutBasculer(false)"><i class="fas fa-expand-alt"></i> Tout ouvrir</button>' +
            '<button class="btn btn-sm btn-light" onclick="recapCommandesToutBasculer(true)"><i class="fas fa-compress-alt"></i> Tout fermer</button></div></div>' +
            r.listeV.map(carteVendeur).join('') + '<div style="height:4px"></div></div>';
    }

    function etatVide(p) {
        return '<div class="rc-panneau rc-vide"><div class="ic"><i class="fas fa-inbox"></i></div>' +
            '<h3>Aucune commande ' + (p.unJour ? 'pour le ' + esc(dateLongue(p.du)) : esc(libellePeriode(p).replace(/^Du/, 'du'))) + '</h3>' +
            '<p>Les commandes apparaissent ici dès que les pré-vendeurs les envoient depuis l\'application mobile.<br>' +
            'Vous pouvez choisir une autre période, par exemple « Ce mois-ci ».</p>' +
            '<button class="btn btn-outline-primary rc-btn" onclick="recapCommandesDecaler(-1)"><i class="fas fa-chevron-left"></i> ' +
            (p.unJour ? 'Voir la veille' : 'Période précédente') + '</button> ' +
            '<button class="btn btn-light rc-btn" onclick="recapCommandesRaccourci(\'mois\')"><i class="far fa-calendar-alt"></i> Voir ce mois-ci</button></div>';
    }

    function mettreAJourProduits() {
        var sel = el('rcProduit'), actuel = sel.value;
        var vus = new Map();
        commandesJour.forEach(function (c) {
            (c.lignes || []).forEach(function (l) {
                vus.set(String(l.produit), (l.produit_designation || '-') + (l.produit_reference ? ' (' + l.produit_reference + ')' : ''));
            });
        });
        var opts = Array.from(vus.entries()).sort(function (a, b) { return a[1].localeCompare(b[1], 'fr'); });
        sel.innerHTML = '<option value="">Tous les produits</option>' +
            opts.map(function (o) { return '<option value="' + esc(o[0]) + '">' + esc(o[1]) + '</option>'; }).join('');
        sel.value = vus.has(actuel) ? actuel : '';
        if (window.jQuery && jQuery(sel).data('select2')) jQuery(sel).trigger('change.select2');
    }

    function mettreAJourVendeurs() {
        var sel = el('rcVendeur'), actuel = sel.value;
        var vus = new Map();
        commandesJour.forEach(function (c) { vus.set(vendeurId(c), vendeurNom(c)); });
        var opts = Array.from(vus.entries()).sort(function (a, b) { return a[1].localeCompare(b[1], 'fr'); });
        sel.innerHTML = '<option value="">Tous les pré-vendeurs</option>' +
            opts.map(function (o) { return '<option value="' + esc(o[0]) + '">' + esc(o[1]) + '</option>'; }).join('');
        sel.value = vus.has(actuel) ? actuel : '';
    }

    function enTete() {
        var p = periode();
        el('rcDateLongue').textContent = p.du ? libellePeriode(p) : '';
        el('rcMaj').textContent = majLe ? 'Mis à jour à ' + majLe.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) : '';
        document.querySelectorAll('[data-raccourci]').forEach(function (b) {
            var r = bornesRaccourci(b.getAttribute('data-raccourci'));
            b.classList.toggle('active', r.du === p.du && r.au === p.au);
        });
    }

    function afficher() {
        var cible = el('rcContenu'), p = periode();
        enTete();
        if (!cible || !p.du) return;
        var r = calculer();
        if (!r.totaux.commandes && !(el('rcAnnulees').checked && r.totaux.annulees)) {
            cible.innerHTML = (commandesJour.length && (el('rcVendeur').value || filtreProduit()))
                ? '<div class="rc-panneau rc-vide"><div class="ic"><i class="fas fa-filter"></i></div><h3>Aucune commande ne correspond aux filtres sur cette période</h3>' +
                  '<p>Choisissez « Tous les produits » ou « Tous les pré-vendeurs » pour voir les autres commandes.</p></div>'
                : etatVide(p);
            return;
        }
        var t = r.totaux, pr = r.produit;
        var kpiCommandes = kpi('fa-shopping-basket', 'ic-bleu', t.commandes, 'Commandes' + (t.annulees ? ' <span class="text-muted">(+' + t.annulees + ' annulée' + (t.annulees > 1 ? 's' : '') + ')</span>' : ''));
        var ctProduit = pr ? nbCartons(pr.total, pr.upc) : '-';
        cible.innerHTML =
            (pr ? '<div class="alert alert-info d-flex align-items-center" style="border-radius:12px;gap:10px"><i class="fas fa-filter"></i><div>Affichage limité au produit <b>' +
                  esc(pr.designation) + '</b> : seules les commandes qui le contiennent sont listées, avec le montant de ce produit.</div>' +
                  '<button class="btn btn-sm btn-outline-info ml-auto" style="white-space:nowrap" onclick="recapCommandesTousProduits()">Tous les produits</button></div>' : '') +
            '<div class="rc-kpis">' + kpiCommandes +
            kpi('fa-user-tie', 'ic-violet', r.nbVendeurs, 'Pré-vendeurs') +
            (pr
                ? kpi('fa-store', 'ic-orange', r.nbClients, 'Clients') +
                  kpi('fa-cubes', 'ic-gris', fmtQ(pr.total), 'Quantité commandée') +
                  kpi('fa-box', 'ic-bleu', ctProduit === '-' ? '—' : ctProduit, 'Nombre de cartons') +
                  kpi('fa-coins', 'ic-vert', argent(t.ttc), 'Montant du produit TTC')
                : kpi('fa-boxes', 'ic-orange', r.listeP.length, 'Produits') +
                  kpi('fa-coins', 'ic-gris', argent(t.ttc), 'Montant total TTC') +
                  kpi('fa-hand-holding-usd', 'ic-vert', argent(t.paye), 'Déjà encaissé') +
                  kpi('fa-exclamation-circle', 'ic-rouge', argent(t.reste), 'Reste à encaisser')) +
            '</div>' +
            (onglet === 'tableau' ? sectionTableau(r)
                : (r.listeP.length ? sectionProduits(r) : '') + sectionVendeurs(r));
        if (onglet === 'tableau') rendreLignesTableau();
    }

    // ---------- Chargement ----------
    function charger() {
        if (!el('rcDu')) return;
        var p = periode();
        if (!p.du) return;
        el('rcDu').value = p.du; el('rcAu').value = p.au;
        var num = ++requete;
        enTete();
        el('rcContenu').innerHTML = '<div class="rc-panneau" style="padding:22px">' +
            '<div class="text-muted mb-2"><i class="fas fa-spinner fa-spin"></i> Chargement des commandes…</div>' +
            '<div class="rc-squelette" style="width:60%"></div><div class="rc-squelette"></div><div class="rc-squelette" style="width:85%"></div><div class="rc-squelette" style="width:70%"></div></div>';
        // Marge d'un jour de chaque côté pour le fuseau horaire ; on garde ensuite les jours locaux de la période
        var url = '/API/distribution/commandes/?date_debut=' + decalerJour(p.du, -1) + '&date_fin=' + decalerJour(p.au, 2);
        fetch(url, { credentials: 'same-origin', headers: { 'Accept': 'application/json' } })
            .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
            .then(function (data) {
                if (num !== requete) return;
                var liste = Array.isArray(data) ? data : (data.results || []);
                commandesJour = liste.filter(function (c) { var j = jourLocal(c.date_commande); return j >= p.du && j <= p.au; })
                    .sort(function (x, y) { return String(x.date_commande).localeCompare(String(y.date_commande)); });
                majLe = new Date();
                fermes = {};
                clientsVisibles = {};
                limiteTableau = 300;
                // Longue période : cartes des pré-vendeurs repliées au départ (lecture plus facile)
                if (commandesJour.length > 40) commandesJour.forEach(function (c) { fermes[vendeurId(c)] = true; });
                mettreAJourVendeurs();
                mettreAJourProduits();
                afficher();
            })
            .catch(function (err) {
                if (num !== requete) return;
                console.error('[RECAP COMMANDES]', err);
                el('rcContenu').innerHTML = '<div class="rc-panneau rc-vide"><div class="ic" style="background:#fee2e2;color:#b91c1c"><i class="fas fa-wifi"></i></div>' +
                    '<h3>Impossible de charger les commandes</h3><p>Vérifiez la connexion internet puis réessayez.</p>' +
                    '<button class="btn btn-primary rc-btn" onclick="recapCommandesCharger()"><i class="fas fa-redo"></i> Réessayer</button></div>';
            });
    }

    // Décale la période de sa propre durée (un jour -> jour précédent / suivant)
    function decaler(sens) {
        var p = periode();
        if (!p.du) { raccourci('aujourdhui'); return; }
        var duree = ecartJours(p.du, p.au) + 1;
        el('rcDu').value = decalerJour(p.du, sens * duree);
        el('rcAu').value = decalerJour(p.au, sens * duree);
        charger();
    }

    function bornesRaccourci(nom) {
        var auj = jourLocal(new Date()), d = new Date();
        if (nom === 'hier') { var h = decalerJour(auj, -1); return { du: h, au: h }; }
        if (nom === 'semaine') return { du: decalerJour(auj, -((d.getDay() + 6) % 7)), au: auj };   // depuis lundi
        if (nom === 'mois') return { du: auj.slice(0, 8) + '01', au: auj };
        if (nom === 'annee') return { du: auj.slice(0, 5) + '01-01', au: auj };
        return { du: auj, au: auj };
    }

    function raccourci(nom) {
        var b = bornesRaccourci(nom);
        el('rcDu').value = b.du; el('rcAu').value = b.au;
        charger();
    }

    // Date de début après la date de fin (ou l'inverse) : on aligne l'autre date
    function datesChangees(quel) {
        var du = el('rcDu').value, au = el('rcAu').value;
        if (quel === 'du' && du && (!au || au < du)) el('rcAu').value = du;
        if (quel === 'au' && au && (!du || du > au)) el('rcDu').value = au;
        charger();
    }

    function basculer(id) {
        fermes[id] = !fermes[id];
        var carte = document.querySelector('.rc-vendeur[data-vendeur="' + CSS.escape(id) + '"]');
        if (carte) carte.classList.toggle('ferme', !!fermes[id]);
    }

    function toutBasculer(fermer) {
        document.querySelectorAll('.rc-vendeur').forEach(function (c) {
            fermes[c.getAttribute('data-vendeur')] = fermer;
            c.classList.toggle('ferme', fermer);
        });
    }

    // Recherche dans le nom / la référence du produit et dans les noms de clients
    function filtrerProduits(texte) {
        texte = String(texte || '').trim().toLowerCase();
        var lignes = document.querySelectorAll('#rcContenu tr.rc-ligne-produit'), visibles = 0;
        lignes.forEach(function (tr) {
            var id = tr.getAttribute('data-id');
            var detail = document.querySelector('#rcContenu tr.rc-detail-clients[data-pour="' + CSS.escape(id) + '"]');
            var parProduit = !texte || tr.getAttribute('data-produit').indexOf(texte) !== -1;
            var parClient = !!texte && !!detail && detail.textContent.toLowerCase().indexOf(texte) !== -1;
            var ok = parProduit || parClient;
            tr.style.display = ok ? '' : 'none';
            if (detail) {
                detail.querySelectorAll('tbody tr').forEach(function (l) {
                    l.style.display = (!parClient || parProduit || l.textContent.toLowerCase().indexOf(texte) !== -1) ? '' : 'none';
                });
                detail.style.display = ok && (clientsVisibles[id] || (parClient && !parProduit)) ? '' : 'none';
            }
            if (ok) visibles++;
        });
        var aucun = document.querySelector('#rcContenu .rc-aucun-produit');
        if (aucun) aucun.style.display = visibles ? 'none' : '';
    }

    function clientsProduit(id) {
        clientsVisibles[id] = !clientsVisibles[id];
        var detail = document.querySelector('#rcContenu tr.rc-detail-clients[data-pour="' + CSS.escape(id) + '"]');
        var btn = document.querySelector('#rcContenu tr.rc-ligne-produit[data-id="' + CSS.escape(id) + '"] .rc-btn-clients');
        if (detail) detail.style.display = clientsVisibles[id] ? '' : 'none';
        if (btn) btn.classList.toggle('ouvert', clientsVisibles[id]);
    }

    function tousClients(afficherTout) {
        document.querySelectorAll('#rcContenu tr.rc-ligne-produit').forEach(function (tr) {
            var id = tr.getAttribute('data-id');
            clientsVisibles[id] = afficherTout;
            var detail = document.querySelector('#rcContenu tr.rc-detail-clients[data-pour="' + CSS.escape(id) + '"]');
            if (detail && tr.style.display !== 'none') detail.style.display = afficherTout ? '' : 'none';
            var btn = tr.querySelector('.rc-btn-clients');
            if (btn) btn.classList.toggle('ouvert', afficherTout);
        });
    }


    // ---------- Onglet « Tableau détaillé » : une ligne par produit de chaque commande ----------
    // Quantités : commandée (au départ), modifiée (avant livraison, si différente), livrée, écart.
    var COLONNES = [
        { cle: 'produit', titre: 'Produit' },
        { cle: 'date', titre: 'Commande / date' },
        { cle: 'client', titre: 'Client' },
        { cle: 'vendeur', titre: 'Pré-vendeur' },
        { cle: 'commandee', titre: 'Qté commandée', cls: 'c' },
        { cle: 'modifiee', titre: 'Qté modifiée', cls: 'c' },
        { cle: 'livree', titre: 'Qté livrée', cls: 'c' },
        { cle: 'ecart', titre: 'Écart', cls: 'c' },
        { cle: 'cartons', titre: 'Cartons', cls: 'c' },
        { cle: 'montant', titre: 'Montant TTC', cls: 'r' },
        { cle: 'etat', titre: 'État' }
    ];
    var seulementEcarts = false;

    function nn(v) { return v === null || v === undefined || v === '' ? null : n(v); }

    function lignesTableau() {
        var r = calculer(), lignes = [], fp = filtreProduit();
        r.listeV.forEach(function (v) {
            v.commandes.forEach(function (c) {
                var livree = c.statut === 'delivered';
                var base = {
                    commande: c.reference || '', date: c.date_commande, client: [c.client_prenom, c.client_nom].filter(Boolean).join(' ') || '-',
                    vendeur: v.nom, livreur: c.livreur_nom || '-', statut: c.statut, etat: STATUTS[c.statut] || c.statut, annulee: c.statut === 'cancelled'
                };
                lignesDe(c).forEach(function (l) {
                    var actuelle = n(l.quantite);
                    var commandee = nn(l.quantite_commandee);
                    if (commandee === null) commandee = actuelle;
                    var qLivree = livree ? (nn(l.quantite_livree) !== null ? nn(l.quantite_livree) : actuelle) : null;
                    var avant = livree ? nn(l.quantite_avant_livraison) : actuelle;
                    var finale = qLivree !== null ? qLivree : actuelle;
                    lignes.push(Object.assign({}, base, {
                        produit: l.produit_designation || '-', reference: l.produit_reference || '', upc: l.produit_unites_par_carton,
                        commandee: commandee, modifiee: avant !== null && avant !== commandee ? avant : null, livree: qLivree,
                        finale: finale, ecart: finale - commandee, cartons: nbCartons(finale, l.produit_unites_par_carton),
                        prix: n(l.prix_unitaire_ht), montant: n(l.montant_ttc), remarque: commandee === 0 ? 'Ajouté' : ''
                    }));
                });
                // Produits retirés après la commande : commandés, puis plus rien
                (c.lignes_retirees || []).forEach(function (rt) {
                    if (fp && String(rt.produit) !== fp) return;
                    var commandee = n(rt.quantite_commandee);
                    lignes.push(Object.assign({}, base, {
                        produit: rt.designation || '-', reference: rt.reference || '', upc: rt.produit_unites_par_carton,
                        commandee: commandee, modifiee: 0, livree: livree ? 0 : null, finale: 0, ecart: -commandee,
                        cartons: nbCartons(0, rt.produit_unites_par_carton), prix: 0, montant: 0, remarque: 'Retiré'
                    }));
                });
            });
        });
        if (seulementEcarts) lignes = lignes.filter(function (x) { return x.ecart !== 0 || x.modifiee !== null || x.remarque; });
        var texte = rechercheTableau.trim().toLowerCase();
        if (texte) {
            lignes = lignes.filter(function (x) {
                return [x.produit, x.reference, x.commande, x.client, x.vendeur, x.livreur, x.etat, x.remarque].join(' ').toLowerCase().indexOf(texte) !== -1;
            });
        }
        var col = triTableau.col, sens = triTableau.sens;
        lignes.sort(function (a, b) {
            var va = a[col], vb = b[col];
            if (col === 'cartons') { va = a.upc > 1 ? a.finale / a.upc : -1; vb = b.upc > 1 ? b.finale / b.upc : -1; }
            if (va === null) va = -Infinity;
            if (vb === null) vb = -Infinity;
            var res = (typeof va === 'number' && typeof vb === 'number') ? (va === vb ? 0 : va < vb ? -1 : 1)
                : String(va).localeCompare(String(vb), 'fr');
            return res * sens || String(a.date).localeCompare(String(b.date));
        });
        return lignes;
    }

    function sectionTableau(r) {
        return '<div class="rc-panneau rc-section">' +
            '<div class="rc-section-tete"><div><h2><i class="fas fa-table text-primary"></i> Tableau détaillé</h2>' +
            '<div class="aide" style="margin-left:0">Une ligne par produit de chaque commande : quantité commandée, modifiée, livrée et l\'écart. ' +
            'Cliquez sur le titre d\'une colonne pour trier.</div></div>' +
            '<div class="d-flex flex-wrap align-items-center" style="gap:12px">' +
            '<div class="custom-control custom-switch"><input type="checkbox" class="custom-control-input" id="rcSeulementEcarts"' +
            (seulementEcarts ? ' checked' : '') + ' onchange="recapCommandesSeulementEcarts(this.checked)">' +
            '<label class="custom-control-label" for="rcSeulementEcarts" style="font-weight:600;font-size:.88rem">Seulement les lignes modifiées</label></div>' +
            '<span class="rc-compteur" id="rcCompteur"></span>' +
            '<div class="rc-recherche"><i class="fas fa-search"></i><input type="search" class="form-control" id="rcRechercheTableau" ' +
            'placeholder="Produit, client, commande…" value="' + esc(rechercheTableau) + '" oninput="recapCommandesRechercheTableau(this.value)"></div></div></div>' +
            '<div class="rc-table-wrap"><table class="rc-table rc-plat"><thead><tr>' +
            COLONNES.map(function (c) {
                var actif = triTableau.col === c.cle;
                return '<th class="triable ' + (c.cls || '') + (actif ? ' trie' : '') + '" onclick="recapCommandesTrier(\'' + c.cle + '\')">' + c.titre +
                    '<i class="fas tri ' + (actif ? (triTableau.sens > 0 ? 'fa-sort-up' : 'fa-sort-down') : 'fa-sort') + '"></i></th>';
            }).join('') +
            '</tr></thead><tbody id="rcCorpsTableau"></tbody><tfoot id="rcPiedTableau"></tfoot></table></div>' +
            '<div class="rc-astuce"><i class="fas fa-info-circle"></i> <b>Qté modifiée</b> : quantité changée après la commande (par le pré-vendeur, le livreur ou le bureau), avant la livraison. ' +
            '<b>Écart</b> = quantité livrée (ou actuelle si pas encore livrée) − quantité commandée. Les commandes enregistrées avant cette mise à jour n\'ont pas d\'historique.</div>' +
            '<div id="rcPlusTableau"></div></div>';
    }

    function celluleEcart(e) {
        if (!e) return '<span class="rc-zero">—</span>';
        return '<span class="rc-ecart ' + (e < 0 ? 'moins' : 'plus') + '">' + (e > 0 ? '+' : '−') + fmtQ(Math.abs(e)) + '</span>';
    }

    function rendreLignesTableau() {
        var corps = el('rcCorpsTableau');
        if (!corps) return;
        var lignes = lignesTableau(), visibles = lignes.slice(0, limiteTableau);
        var unJour = periode().unJour;
        corps.innerHTML = visibles.length ? visibles.map(function (x) {
            var d = new Date(x.date);
            var quand = unJour ? d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
                : d.toLocaleDateString('fr-FR') + ' ' + d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
            var tag = x.remarque ? ' <span class="rc-tag ' + (x.remarque === 'Retiré' ? 'retire' : 'ajoute') + '">' + x.remarque + '</span>' : '';
            return '<tr' + (x.annulee ? ' class="rc-annulee"' : '') + '>' +
                '<td><div class="rc-prod-nom">' + esc(x.produit) + tag + '</div>' + (x.reference ? '<div class="rc-prod-ref">' + esc(x.reference) + '</div>' : '') + '</td>' +
                '<td><div class="rc-ref">' + esc(x.commande) + '</div><div class="rc-heure"><i class="far fa-clock"></i> ' + quand + '</div></td>' +
                '<td><b>' + esc(x.client) + '</b></td>' +
                '<td>' + esc(x.vendeur) + (x.livreur !== '-' && x.livreur !== x.vendeur ? '<div class="rc-heure"><i class="fas fa-truck"></i> ' + esc(x.livreur) + '</div>' : '') + '</td>' +
                '<td class="c"><span class="rc-q">' + fmtQ(x.commandee) + '</span></td>' +
                '<td class="c">' + (x.modifiee !== null ? '<span class="rc-q rc-modif">' + fmtQ(x.modifiee) + '</span>' : '<span class="rc-zero">—</span>') + '</td>' +
                '<td class="c">' + (x.livree !== null ? '<span class="rc-q rc-livre">' + fmtQ(x.livree) + '</span>' : '<span class="rc-zero" title="Pas encore livrée">—</span>') + '</td>' +
                '<td class="c">' + celluleEcart(x.ecart) + '</td>' +
                '<td class="c">' + (x.cartons !== '-' ? '<span class="rc-ct">' + x.cartons + '</span>' : '<span class="rc-zero">—</span>') + '</td>' +
                '<td class="r font-weight-bold">' + argent(x.montant) + '</td>' +
                '<td><span class="rc-badge st-' + esc(x.statut) + '">' + esc(x.etat) + '</span></td></tr>';
        }).join('') : '<tr><td colspan="' + COLONNES.length + '" class="c text-muted py-4">Aucune ligne ne correspond.</td></tr>';
        var actives = lignes.filter(function (x) { return !x.annulee; });
        var somme = function (cle) { return actives.reduce(function (s, x) { return s + (x[cle] || 0); }, 0); };
        var unProduit = new Set(actives.map(function (x) { return x.produit; })).size === 1;
        el('rcPiedTableau').innerHTML = '<tr><td colspan="4">Total' + (lignes.length !== actives.length ? ' <small class="text-muted">(hors annulées)</small>' : '') + '</td>' +
            '<td class="c">' + fmtQ(somme('commandee')) + '</td><td></td>' +
            '<td class="c">' + (actives.some(function (x) { return x.livree !== null; }) ? fmtQ(somme('livree')) : '') + '</td>' +
            '<td class="c">' + celluleEcart(somme('ecart')) + '</td>' +
            '<td class="c">' + (unProduit && actives.length ? nbCartons(somme('finale'), actives[0].upc) : '') + '</td>' +
            '<td class="r">' + argent(somme('montant')) + '</td><td></td></tr>';
        el('rcCompteur').textContent = lignes.length > visibles.length
            ? visibles.length + ' lignes affichées sur ' + lignes.length : pluriel(lignes.length, 'ligne');
        el('rcPlusTableau').innerHTML = lignes.length > visibles.length
            ? '<div class="text-center p-3"><button class="btn btn-outline-primary rc-btn" onclick="recapCommandesPlusTableau()">' +
              '<i class="fas fa-angle-double-down"></i> Afficher plus de lignes</button></div>' : '';
    }

    function choisirOnglet(nom) {
        onglet = nom;
        document.querySelectorAll('.rc-onglets [data-onglet]').forEach(function (a) {
            a.classList.toggle('active', a.getAttribute('data-onglet') === nom);
        });
        afficher();
    }

    function trier(col) {
        triTableau = { col: col, sens: triTableau.col === col ? -triTableau.sens : 1 };
        var section = document.querySelector('#rcContenu .rc-plat');
        if (section) {
            section.querySelectorAll('thead th').forEach(function (th, i) {
                var actif = COLONNES[i].cle === triTableau.col;
                th.classList.toggle('trie', actif);
                th.querySelector('.tri').className = 'fas tri ' + (actif ? (triTableau.sens > 0 ? 'fa-sort-up' : 'fa-sort-down') : 'fa-sort');
            });
        }
        rendreLignesTableau();
    }

    function exporterTableau(p) {
        var lignes = lignesTableau();
        var cell = function (v) {
            var t = String(v == null ? '' : v);
            return /[";\n]/.test(t) ? '"' + t.replace(/"/g, '""') + '"' : t;
        };
        var nombre = function (v) { return v === null || v === undefined ? '' : String(Math.round(v * 100) / 100).replace('.', ','); };
        var out = [['Tableau détaillé des commandes', libellePeriode(p)], [],
            ['Produit', 'Référence', 'Commande', 'Date', 'Client', 'Pré-vendeur', 'Livreur', 'Qté commandée', 'Qté modifiée', 'Qté livrée',
             'Écart', 'Cartons', 'Prix unit. HT', 'Montant TTC', 'État', 'Remarque']];
        lignes.forEach(function (x) {
            var d = new Date(x.date);
            out.push([x.produit, x.reference, x.commande, d.toLocaleDateString('fr-FR') + ' ' + d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }),
                x.client, x.vendeur, x.livreur, nombre(x.commandee), nombre(x.modifiee), nombre(x.livree), nombre(x.ecart),
                x.cartons === '-' ? '' : x.cartons, nombre(x.prix), nombre(x.montant), x.etat, x.remarque]);
        });
        return out.map(function (l) { return l.map(cell).join(';'); }).join('\r\n');
    }

    function imprimerTableau(p, f) {
        var lignes = lignesTableau();
        var actives = lignes.filter(function (x) { return !x.annulee; });
        var somme = function (cle) { return actives.reduce(function (s, x) { return s + (x[cle] || 0); }, 0); };
        var q = function (v) { return v === null ? '—' : fmtQ(v); };
        var ec = function (e) { return e ? (e > 0 ? '+' : '−') + fmtQ(Math.abs(e)) : '—'; };
        f.document.write('<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Tableau détaillé des commandes</title><style>' +
            '@page { size: A4 landscape; margin: 1cm; } body { font-family: Arial, sans-serif; font-size: 9pt; color: #222; margin: 0; padding: 12px; }' +
            'h1 { font-size: 15pt; margin: 0 0 8px; } table { width: 100%; border-collapse: collapse; } th, td { border: 1px solid #ccc; padding: 3px 5px; text-align: left; }' +
            'thead th { background: #f3f3f3; } .c { text-align: center; } .r { text-align: right; white-space: nowrap; } tr.annulee td { color: #999; text-decoration: line-through; }' +
            'thead { display: table-header-group; } tr { page-break-inside: avoid; } tfoot td { font-weight: bold; background: #fafafa; } .moins { color: #b91c1c; font-weight: bold; } .plus { color: #15803d; font-weight: bold; }' +
            '</style></head><body><h1>Tableau détaillé des commandes — ' + esc(libellePeriode(p)) + '</h1><table><thead><tr>' +
            COLONNES.map(function (c) { return '<th class="' + (c.cls || '') + '">' + c.titre + '</th>'; }).join('') + '</tr></thead><tbody>' +
            lignes.map(function (x) {
                var d = new Date(x.date);
                return '<tr' + (x.annulee ? ' class="annulee"' : '') + '><td>' + esc(x.produit) + (x.remarque ? ' <b>(' + x.remarque + ')</b>' : '') + '</td><td>' +
                    esc(x.commande) + '<br><small>' + d.toLocaleDateString('fr-FR') + ' ' + d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) +
                    '</small></td><td>' + esc(x.client) + '</td><td>' + esc(x.vendeur) + '</td><td class="c">' + q(x.commandee) + '</td><td class="c">' + q(x.modifiee) +
                    '</td><td class="c">' + q(x.livree) + '</td><td class="c ' + (x.ecart < 0 ? 'moins' : x.ecart > 0 ? 'plus' : '') + '">' + ec(x.ecart) + '</td><td class="c">' +
                    (x.cartons === '-' ? '' : x.cartons) + '</td><td class="r">' + argent(x.montant) + '</td><td>' + esc(x.etat) + '</td></tr>';
            }).join('') + '</tbody><tfoot><tr><td colspan="4">Total</td><td class="c">' + fmtQ(somme('commandee')) + '</td><td></td><td class="c">' +
            (actives.some(function (x) { return x.livree !== null; }) ? fmtQ(somme('livree')) : '') + '</td><td class="c">' + ec(somme('ecart')) +
            '</td><td></td><td class="r">' + argent(somme('montant')) + '</td><td></td></tr></tfoot></table>' +
            '<script>window.onload = function () { window.print(); }<' + '/script></body></html>');
        f.document.close();
    }

    // ---------- Impression ----------
    function imprimer() {
        var p = periode();
        if (!p.du) return;
        var r = calculer();
        var f = window.open('', '_blank');
        if (!f) { alert('Autorisez les fenêtres pop-up pour imprimer le récapitulatif'); return; }
        if (onglet === 'tableau') { imprimerTableau(p, f); return; }
        var vs = r.vendeursProduits;
        var cel = function (q, upc, cls) {
            if (!q) return '<td class="c vide">—</td>';
            var ct = nbCartons(q, upc);
            return '<td class="c ' + (cls || '') + '"><b>' + fmtQ(q) + '</b>' + (ct !== '-' ? '<br><small>' + ct + ' ct</small>' : '') + '</td>';
        };
        var produits = r.listeP.length ? '<h2>1. Quantités par produit et par pré-vendeur</h2><table><thead><tr><th>Produit</th><th>Clients (quantité)</th>' +
            vs.map(function (v) { return '<th class="c">' + esc(v.nom) + '</th>'; }).join('') +
            '<th class="c tot">Total</th><th class="c">Cmd</th><th class="r">Montant TTC</th></tr></thead><tbody>' +
            r.listeP.map(function (p) {
                return '<tr><td>' + esc(p.designation) + (p.reference ? ' <small>(' + esc(p.reference) + ')</small>' : '') + '</td>' +
                    '<td class="prods">' + p.listeClients.map(function (cl) { return esc(cl.nom) + ' (' + fmtQ(cl.quantite) + ')'; }).join(', ') + '</td>' +
                    vs.map(function (v) { return cel(p.parV.get(v.id) || 0, p.upc); }).join('') + cel(p.total, p.upc, 'tot') +
                    '<td class="c">' + p.nbCmd.size + '</td><td class="r">' + argent(p.montant) + '</td></tr>';
            }).join('') + '</tbody><tfoot><tr><th>Total</th><th>' + pluriel(r.nbClients, 'client') + '</th>' + vs.map(function (v) { return '<th class="r">' + argent(v.ttc) + '</th>'; }).join('') +
            '<th class="r tot">' + argent(r.totaux.ttc) + '</th><th class="c">' + r.totaux.commandes + '</th><th class="r">' + argent(r.totaux.ttc) + '</th></tr></tfoot></table>' : '';
        var mp = r.modeProduit;
        var vendeurs = '<h2>2. Commandes de chaque pré-vendeur</h2>' + r.listeV.map(function (v) {
            return '<h3>' + esc(v.nom) + ' <small>— ' + pluriel(v.nbActives, 'commande') + ' · ' + argent(v.ttc) + '</small></h3>' +
                '<table><thead><tr><th class="c">#</th><th>Commande</th><th>Client</th><th>' + (mp ? 'Produit' : 'Produits commandés') + '</th><th>Statut</th>' +
                (mp ? '<th class="r">Montant du produit</th>' : '<th class="r">Total TTC</th><th class="r">Payé</th><th class="r">Reste</th>') + '</tr></thead><tbody>' +
                v.commandes.map(function (c, i) {
                    var annulee = c.statut === 'cancelled';
                    var reste = annulee ? 0 : Math.max(0, n(c.montant_total_ttc) - n(c.montant_paye));
                    return '<tr' + (annulee ? ' class="annulee"' : '') + '><td class="c">' + (i + 1) + '</td><td>' + esc(c.reference) + '<br><small>' +
                        horodatage(c) + '</small></td><td>' +
                        esc([c.client_prenom, c.client_nom].filter(Boolean).join(' ')) + '</td><td class="prods">' +
                        (lignesDe(c).map(function (l) {
                            var ct = nbCartons(n(l.quantite), l.produit_unites_par_carton);
                            return esc(l.produit_designation || '-') + ' × <b>' + fmtQ(n(l.quantite)) + '</b>' + (ct !== '-' ? ' <small>(' + ct + ' ct)</small>' : '');
                        }).join('<br>') || '-') + '</td><td>' + esc(STATUTS[c.statut] || c.statut) + '</td><td class="r">' + argent(montantCmd(c)) + '</td>' +
                        (mp ? '' : '<td class="r">' + argent(annulee ? 0 : n(c.montant_paye)) + '</td><td class="r">' + argent(reste) + '</td>') + '</tr>';
                }).join('') + '</tbody><tfoot><tr><th colspan="5">Total ' + esc(v.nom) + '</th><th class="r">' + argent(v.ttc) + '</th>' +
                (mp ? '' : '<th class="r">' + argent(v.paye) + '</th><th class="r">' + argent(v.reste) + '</th>') + '</tr></tfoot></table>';
        }).join('');
        var t = r.totaux, filtreV = el('rcVendeur'), filtreP = el('rcProduit');
        f.document.write('<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Récapitulatif des commandes ' + p.du + (p.unJour ? '' : ' au ' + p.au) + '</title><style>' +
            '@page { size: A4 landscape; margin: 1cm; } body { font-family: Arial, sans-serif; font-size: 9.5pt; color: #222; margin: 0; padding: 12px; }' +
            'h1 { font-size: 16pt; margin: 0 0 4px; } .sous { color: #555; margin-bottom: 10px; }' +
            '.kpis { display: flex; gap: 8px; margin: 8px 0 4px; } .kpis div { flex: 1; border: 1px solid #ccc; border-radius: 6px; padding: 6px 8px; }' +
            '.kpis b { display: block; font-size: 12pt; } .kpis span { font-size: 8pt; color: #666; }' +
            'h2 { font-size: 12pt; margin: 16px 0 6px; padding: 5px 8px; background: #eef2f7; border-left: 4px solid #2563eb; }' +
            'h3 { font-size: 11pt; margin: 12px 0 4px; } h3 small { font-weight: normal; color: #555; }' +
            'table { width: 100%; border-collapse: collapse; margin-bottom: 6px; } th, td { border: 1px solid #ccc; padding: 3px 6px; text-align: left; vertical-align: top; }' +
            'thead th { background: #f3f3f3; } tfoot th { background: #fafafa; } .c { text-align: center; } .r { text-align: right; white-space: nowrap; }' +
            '.tot { background: #fff8e1; } td.vide { color: #bbb; } small { color: #666; } td.prods { font-size: 9pt; }' +
            'tr.annulee td { color: #999; text-decoration: line-through; } thead { display: table-header-group; } tr { page-break-inside: avoid; }' +
            '.pied { margin-top: 14px; font-size: 8pt; color: #777; text-align: center; }' +
            '</style></head><body><h1>Récapitulatif des commandes — ' + esc(libellePeriode(p)) + '</h1>' +
            '<div class="sous">' + (filtreV.value ? 'Pré-vendeur : ' + esc(filtreV.options[filtreV.selectedIndex].text) : 'Tous les pré-vendeurs') +
            ' · ' + (filtreP.value ? 'Produit : ' + esc(filtreP.options[filtreP.selectedIndex].text) : 'Tous les produits') + '</div>' +
            '<div class="kpis"><div><b>' + t.commandes + '</b><span>Commandes</span></div><div><b>' + r.nbVendeurs + '</b><span>Pré-vendeurs</span></div>' +
            (mp ? '<div><b>' + fmtQ(r.produit.total) + '</b><span>Quantité commandée</span></div><div><b>' + nbCartons(r.produit.total, r.produit.upc) +
                  '</b><span>Nombre de cartons</span></div><div><b>' + argent(t.ttc) + '</b><span>Montant du produit TTC</span></div>'
                : '<div><b>' + r.listeP.length + '</b><span>Produits</span></div><div><b>' + argent(t.ttc) + '</b><span>Montant total TTC</span></div>' +
                  '<div><b>' + argent(t.paye) + '</b><span>Encaissé</span></div><div><b>' + argent(t.reste) + '</b><span>Reste à encaisser</span></div>') + '</div>' +
            produits + vendeurs +
            '<div class="pied">Document généré le ' + new Date().toLocaleDateString('fr-FR') + ' à ' + new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) + '</div>' +
            '<script>window.onload = function () { window.print(); }<' + '/script></body></html>');
        f.document.close();
    }

    // ---------- Export Excel (CSV, séparateur ; pour Excel en français) ----------
    function exporter() {
        var p = periode();
        if (!p.du) return;
        if (onglet === 'tableau') {
            telecharger('\ufeff' + exporterTableau(p), 'tableau-commandes-' + p.du + (p.unJour ? '' : '_au_' + p.au) + '.csv');
            return;
        }
        var r = calculer();
        var cell = function (v) {
            var s = String(v == null ? '' : v);
            return /[";\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
        };
        var nombre = function (v) { return String(Math.round(v * 100) / 100).replace('.', ','); };
        var lignes = [];
        lignes.push(['Récapitulatif des commandes', libellePeriode(p)]);
        if (r.modeProduit) lignes.push(['Produit', r.produit.designation + (r.produit.reference ? ' (' + r.produit.reference + ')' : '')]);
        lignes.push([]);
        lignes.push(['QUANTITÉS PAR PRODUIT ET PAR PRÉ-VENDEUR']);
        lignes.push(['Produit', 'Référence'].concat(r.vendeursProduits.map(function (v) { return v.nom; }), ['Total', 'Nb cartons', 'Commandes', 'Montant TTC']));
        r.listeP.forEach(function (p) {
            lignes.push([p.designation, p.reference].concat(
                r.vendeursProduits.map(function (v) { return nombre(p.parV.get(v.id) || 0); }),
                [nombre(p.total), nbCartons(p.total, p.upc), p.nbCmd.size, nombre(p.montant)]));
        });
        lignes.push([]);
        lignes.push(['CLIENTS DE CHAQUE PRODUIT']);
        lignes.push(['Produit', 'Référence', 'Client', 'Pré-vendeur', 'Commande(s)', 'Quantité', 'Nb cartons', 'Montant TTC']);
        r.listeP.forEach(function (p) {
            p.listeClients.forEach(function (cl) {
                lignes.push([p.designation, p.reference, cl.nom, cl.vendeur, cl.commandes.join(', '), nombre(cl.quantite), nbCartons(cl.quantite, p.upc), nombre(cl.montant)]);
            });
        });
        lignes.push([]);
        lignes.push(['COMMANDES DE CHAQUE PRÉ-VENDEUR']);
        lignes.push(['Pré-vendeur', 'Commande', 'Date', 'Client', 'Livreur', 'Statut', 'Produit', 'Quantité', 'Nb cartons', 'Montant ligne TTC', 'Total commande TTC', 'Payé', 'Reste']);
        r.listeV.forEach(function (v) {
            v.commandes.forEach(function (c) {
                var annulee = c.statut === 'cancelled';
                var reste = annulee ? 0 : Math.max(0, n(c.montant_total_ttc) - n(c.montant_paye));
                var d = new Date(c.date_commande);
                var base = [v.nom, c.reference, d.toLocaleDateString('fr-FR') + ' ' + d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }),
                    [c.client_prenom, c.client_nom].filter(Boolean).join(' '), c.livreur_nom || '', STATUTS[c.statut] || c.statut];
                var ls = lignesDe(c).length ? lignesDe(c) : [null];
                ls.forEach(function (l, i) {
                    lignes.push(base.concat(l ? [l.produit_designation || '', nombre(n(l.quantite)), nbCartons(n(l.quantite), l.produit_unites_par_carton), nombre(n(l.montant_ttc))] : ['', '', '', ''],
                        i === 0 ? (r.modeProduit ? [nombre(montantCmd(c)), '', ''] : [nombre(n(c.montant_total_ttc)), nombre(annulee ? 0 : n(c.montant_paye)), nombre(reste)]) : ['', '', '']));
                });
            });
            lignes.push(['Total ' + v.nom, '', '', '', '', '', '', r.modeProduit ? nombre(v.quantite) : '', '', '', nombre(v.ttc),
                r.modeProduit ? '' : nombre(v.paye), r.modeProduit ? '' : nombre(v.reste)]);
        });
        var csv = '\ufeff' + lignes.map(function (l) { return l.map(cell).join(';'); }).join('\r\n');
        telecharger(csv, 'recapitulatif-commandes-' + p.du + (p.unJour ? '' : '_au_' + p.au) + '.csv');
    }

    function telecharger(contenu, nom) {
        var a = document.createElement('a');
        a.href = URL.createObjectURL(new Blob([contenu], { type: 'text/csv;charset=utf-8' }));
        a.download = nom;
        document.body.appendChild(a); a.click();
        setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
    }

    function init() {
        if (!el('rcDu')) return;
        if (!el('rcDu').value) { var b = bornesRaccourci('aujourdhui'); el('rcDu').value = b.du; el('rcAu').value = b.au; }
        charger();
    }

    window.recapCommandesDecaler = decaler;
    window.recapCommandesOnglet = choisirOnglet;
    window.recapCommandesTrier = trier;
    window.recapCommandesRechercheTableau = function (v) { rechercheTableau = v; limiteTableau = 300; rendreLignesTableau(); };
    window.recapCommandesPlusTableau = function () { limiteTableau += 300; rendreLignesTableau(); };
    window.recapCommandesSeulementEcarts = function (v) { seulementEcarts = !!v; limiteTableau = 300; rendreLignesTableau(); };
    window.recapCommandesClientsProduit = clientsProduit;
    window.recapCommandesTousClients = tousClients;
    window.recapCommandesTousProduits = function () {
        el('rcProduit').value = '';
        if (window.jQuery && jQuery('#rcProduit').data('select2')) jQuery('#rcProduit').trigger('change.select2');
        afficher();
    };
    window.recapCommandesRaccourci = raccourci;
    window.recapCommandesDatesChangees = datesChangees;
    window.recapCommandesCharger = charger;
    window.recapCommandesAfficher = afficher;
    window.recapCommandesImprimer = imprimer;
    window.recapCommandesExporter = exporter;
    window.recapCommandesBasculer = basculer;
    window.recapCommandesToutBasculer = toutBasculer;
    window.recapCommandesFiltrerProduits = filtrerProduits;

    document.addEventListener('fragment:loaded', function (e) {
        if (e && e.detail && e.detail.name === 'recap_commandes') init();
    });
})();
