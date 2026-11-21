/*
 * Bon de livraison — modèle UNIQUE côté web.
 *
 * Reproduit le BL du serveur (API/views.py → BonLivraisonViewSet.printable) pour que tous
 * les bons de livraison aient le même format : Ventes (ventes mobiles), Commandes clients…
 * Le même modèle existe dans l'app mobile : MobileApp/src/features/facture/invoiceTemplate.ts
 * (generateDeliveryNoteHTML). Toute modification doit être faite aux trois endroits.
 *
 * Utilisation :
 *   BonLivraison.chargerEntreprise().then(function (entreprise) {
 *     BonLivraison.imprimer({ numero, dateLivraison, dateVente, reference, entreprise,
 *       client: { nom, adresse, telephone, email, rc, nif, nis, ai },
 *       lignes: [{ designation, quantite, unitesParCarton, prixUnitaire, montant }],
 *       totalHT, tva, tauxTVA, totalTTC, livreur, previsionnel });
 *   });
 *
 * previsionnel: true → « BL prévisionnel » d'une commande pas encore livrée (quantités
 * commandées, date de livraison prévue), clairement marqué sur le document.
 */
(function (window) {
  'use strict';

  function esc(v) {
    return String(v === null || v === undefined ? '' : v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // « 1 234,56 DA » (même format que le serveur et l'app mobile)
  function formatDA(v) {
    var parts = (Number(v) || 0).toFixed(2).split('.');
    return parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + ',' + parts[1] + ' DA';
  }

  function formatQte(q) {
    return String(Number(q) || 0).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  }

  // ── Montant en toutes lettres (copie de _nombre_en_lettres, API/views.py) ──
  var UNITES = ['', 'Un', 'Deux', 'Trois', 'Quatre', 'Cinq', 'Six', 'Sept', 'Huit', 'Neuf',
    'Dix', 'Onze', 'Douze', 'Treize', 'Quatorze', 'Quinze', 'Seize',
    'Dix-Sept', 'Dix-Huit', 'Dix-Neuf'];
  var DIZAINES = ['', 'Dix', 'Vingt', 'Trente', 'Quarante', 'Cinquante',
    'Soixante', 'Soixante', 'Quatre-Vingt', 'Quatre-Vingt'];

  function inf100(n) {
    if (n === 0) return '';
    if (n < 20) return UNITES[n];
    var d = Math.floor(n / 10), u = n % 10;
    if (d === 7) return u === 1 ? 'Soixante-et-Onze' : (u ? 'Soixante-' + UNITES[10 + u] : 'Soixante-Dix');
    if (d === 8) return u === 0 ? 'Quatre-Vingts' : 'Quatre-Vingt-' + UNITES[u];
    if (d === 9) return 'Quatre-Vingt-' + UNITES[10 + u];
    var sep = u === 1 ? '-et-' : '-';
    return DIZAINES[d] + (u ? sep + UNITES[u] : '');
  }

  function inf1000(n) {
    if (n === 0) return '';
    var parts = [];
    var c = Math.floor(n / 100), reste = n % 100;
    if (c === 1) parts.push('Cent');
    else if (c > 1) parts.push(UNITES[c] + (reste === 0 ? ' Cents' : ' Cent'));
    if (reste) parts.push(inf100(reste));
    return parts.filter(Boolean).join(' ');
  }

  function entierEnLettres(n) {
    if (n === 0) return 'Zéro';
    var parts = [];
    var milliards = Math.floor(n / 1e9); n = n % 1e9;
    if (milliards === 1) parts.push('Un Milliard');
    else if (milliards > 1) parts.push(inf1000(milliards) + ' Milliards');
    var millions = Math.floor(n / 1e6); n = n % 1e6;
    if (millions === 1) parts.push('Un Million');
    else if (millions > 1) parts.push(inf1000(millions) + ' Millions');
    var milliers = Math.floor(n / 1000); n = n % 1000;
    if (milliers === 1) parts.push('Mille');
    else if (milliers > 1) parts.push(inf1000(milliers) + ' Mille');
    if (n) parts.push(inf1000(n));
    return parts.filter(Boolean).join(' ');
  }

  function nombreEnLettres(montant) {
    var totalCentimes = Math.round((Number(montant) || 0) * 100);
    var entier = Math.floor(totalCentimes / 100);
    var centimes = totalCentimes % 100;
    var result = entierEnLettres(entier) + ' Dinars';
    if (centimes) result += ' et ' + (inf100(centimes) || 'Zéro') + ' Centimes';
    return result;
  }

  // ── Modèle HTML ──────────────────────────────────────────────────────────
  function html(data) {
    var e = data.entreprise || {};
    var c = data.client || {};
    var adresseSociete = esc(e.adresse).replace(/\n/g, '<br>');
    var avecTVA = Math.abs(Number(data.tva) || 0) >= 0.01;
    var prev = !!data.previsionnel;
    var titre = prev ? 'Bon de Livraison prévisionnel' : 'Bon de Livraison';

    var lignes = (data.lignes || []).map(function (l) {
      var upc = parseInt(l.unitesParCarton, 10);
      return '<tr>' +
        '<td>' + esc(l.designation) + '</td>' +
        '<td class="r">' + formatQte(l.quantite) + ' Unité(s)</td>' +
        '<td class="c">' + (upc > 1 ? upc : '-') + '</td>' +
        '<td class="r">' + formatDA(l.prixUnitaire) + '</td>' +
        '<td class="r">' + (Number(l.remise) ? esc(l.remise) + ' %' : '—') + '</td>' +
        '<td class="r">' + (Number(l.tauxTva) ? esc(l.tauxTva) + ' %' : '—') + '</td>' +
        '<td class="r">' + formatDA(l.montant) + '</td>' +
        '</tr>';
    }).join('');

    var fiscal = '';
    if (c.rc || c.nif) fiscal += '<div class="fiscal">RC : ' + esc(c.rc) + '&nbsp;&nbsp;&nbsp;NIF : ' + esc(c.nif) + '</div>';
    if (c.nis || c.ai) fiscal += '<div class="fiscal">NIS : ' + esc(c.nis) + '&nbsp;&nbsp;&nbsp;ART : ' + esc(c.ai) + '</div>';
    if (c.telephone || c.email) {
      fiscal += '<div class="fiscal">Tél : ' + esc(c.telephone) +
        (c.email ? '&nbsp;&nbsp;&nbsp;Email : ' + esc(c.email) : '') + '</div>';
    }

    var fiscSociete = [e.rc && 'RC : ' + esc(e.rc), e.nif && 'NIF : ' + esc(e.nif), e.nis && 'NIS : ' + esc(e.nis)]
      .filter(Boolean).join('<br>');

    return '<!DOCTYPE html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n' +
      '<title>' + titre + ' ' + esc(data.numero) + '</title>\n<style>\n' + CSS + '\n</style>\n</head>\n<body>\n' +
      (data.sansBoutonImprimer ? '' : '<button class="print-btn" onclick="window.print()">🖨 Imprimer</button>\n') +
      '<div class="header">' +
        '<div class="logo">' + esc(e.nom) + '</div>' +
        '<div class="company-info"><strong>' + esc(e.nom) + '</strong><br>' + adresseSociete + '<br>' +
          (e.telephone ? 'Tél : ' + esc(e.telephone) : '') +
          (e.email ? '&nbsp;&nbsp;|&nbsp;&nbsp;' + esc(e.email) : '') +
        '</div>' +
      '</div>' +
      '<div class="client-block">' +
        '<div class="client-name">' + esc(c.nom) + '</div>' +
        '<div>' + esc(c.adresse) + '</div>' + fiscal +
      '</div>' +
      '<div class="facture-title">' + titre + ' ' + esc(data.numero) + '</div>' +
      (prev ? '<div class="prev-banner">BL PRÉVISIONNEL — commande non encore livrée. ' +
        'Quantités commandées ; les quantités réellement livrées figureront sur le BL définitif.</div>' : '') +
      '<table class="dates-row"><thead><tr>' +
        '<th>' + (prev ? 'Date de livraison prévue' : 'Date de livraison') + '</th><th>Date de vente</th><th>N° BL</th><th>N° Vente / Référence</th>' +
      '</tr></thead><tbody><tr>' +
        '<td>' + esc(data.dateLivraison || '—') + '</td>' +
        '<td>' + esc(data.dateVente || '—') + '</td>' +
        '<td>' + esc(data.numero || '—') + '</td>' +
        '<td>' + esc(data.reference || '—') + '</td>' +
      '</tr></tbody></table>' +
      '<table class="items-table"><thead><tr>' +
        '<th>Désignation</th><th class="r">Quantité</th><th class="c">Qté / carton</th>' +
        '<th class="r">Prix unitaire</th><th class="r">Remise</th><th class="r">TVA</th><th class="r">Montant</th>' +
      '</tr></thead><tbody>' + lignes + '</tbody></table>' +
      '<div class="totals-wrap"><table class="totals-table">' +
        '<tr><td class="label">Montant hors taxes</td><td class="amount">' + formatDA(data.totalHT) + '</td></tr>' +
        (avecTVA ? '<tr><td class="label">TVA' + (data.tauxTVA ? ' (' + esc(data.tauxTVA) + ' %)' : '') + '</td><td class="amount">' + formatDA(data.tva) + '</td></tr>' : '') +
        '<tr class="row-total"><td class="label">Total</td><td class="amount">' + formatDA(data.totalTTC) + '</td></tr>' +
        '<tr class="row-ttc"><td>NET TTC</td><td class="amount">' + formatDA(data.totalTTC) + '</td></tr>' +
        '<tr><td colspan="2" class="mention">Montant total en toutes lettres</td></tr>' +
        '<tr><td colspan="2" class="mention">Les montants sont indiqués en Dinars Algériens (DA)</td></tr>' +
      '</table></div>' +
      '<div class="lettres"><strong>Totalité en lettres :</strong> ' + esc(nombreEnLettres(data.totalTTC)) + '</div>' +
      '<div class="signatures">' +
        '<div class="sig-box">Réceptionnaire</div>' +
        '<div class="sig-box">Livreur' + (data.livreur ? ' : ' + esc(data.livreur) : '') + '</div>' +
      '</div>' +
      '<div class="footer">' +
        '<div class="footer-col"><strong>' + esc(e.nom) + '</strong><br>' + adresseSociete + '</div>' +
        '<div class="footer-col">' + fiscSociete + '</div>' +
        '<div class="footer-col" style="text-align:right">' +
          (e.telephone ? 'Tél : ' + esc(e.telephone) + '<br>' : '') +
          (e.email ? 'Email : ' + esc(e.email) : '') +
        '</div>' +
      '</div>\n</body>\n</html>';
  }

  var CSS = [
    '* { box-sizing: border-box; margin: 0; padding: 0; }',
    '.c { text-align: center; }',
    'body { font-family: Arial, Helvetica, sans-serif; font-size: 11px; color: #222; background: #fff; padding: 28px 32px; }',
    '.header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }',
    '.logo { font-size: 26px; font-style: italic; color: #b07830; font-weight: 300; letter-spacing: 1px; }',
    '.company-info { text-align: right; font-size: 10.5px; color: #444; line-height: 1.6; }',
    '.company-info strong { font-size: 12px; color: #222; }',
    '.client-block { margin-bottom: 18px; font-size: 10.5px; line-height: 1.7; }',
    '.client-block .client-name { font-weight: bold; font-size: 12px; text-transform: uppercase; }',
    '.fiscal { color: #444; }',
    '.facture-title { font-size: 22px; font-weight: bold; color: #b07830; margin: 20px 0 14px; }',
    '.dates-row { width: 100%; border-collapse: collapse; margin-bottom: 16px; }',
    '.dates-row th { background: #f0f0f0; border: 1px solid #ccc; padding: 5px 10px; font-size: 10px; color: #666; font-weight: normal; text-align: center; }',
    '.dates-row td { border: 1px solid #ccc; padding: 5px 10px; text-align: center; font-size: 11px; }',
    '.items-table { width: 100%; border-collapse: collapse; margin-bottom: 18px; }',
    '.items-table thead tr { background: #f0f0f0; border-top: 2px solid #b07830; border-bottom: 1px solid #ccc; }',
    '.items-table th { padding: 7px 8px; text-align: left; font-size: 10.5px; color: #444; font-weight: bold; border: 1px solid #ddd; }',
    '.items-table td { padding: 6px 8px; border: 1px solid #e0e0e0; vertical-align: middle; }',
    '.items-table tbody tr:nth-child(even) { background: #fafafa; }',
    '.r { text-align: right; }',
    '.totals-wrap { display: flex; justify-content: flex-end; margin-bottom: 14px; }',
    '.totals-table { width: 340px; border-collapse: collapse; font-size: 11px; }',
    '.totals-table td { padding: 5px 10px; border: 1px solid #ddd; }',
    '.totals-table .label { color: #444; }',
    '.totals-table .amount { text-align: right; font-weight: bold; }',
    '.totals-table .row-total { background: #f5c4a0; }',
    '.totals-table .row-ttc { background: #e8935a; color: #fff; font-weight: bold; }',
    '.totals-table .mention { font-size: 9px; color: #666; font-style: italic; border: none; padding-top: 3px; text-align: right; }',
    '.lettres { font-style: italic; font-size: 10.5px; color: #333; border-top: 1px dashed #ccc; padding-top: 8px; margin-bottom: 32px; }',
    '.signatures { display: flex; justify-content: space-between; margin-bottom: 40px; }',
    '.sig-box { width: 200px; border-top: 1px solid #999; text-align: center; padding-top: 6px; font-size: 10px; color: #666; }',
    '.footer { border-top: 1.5px solid #b07830; padding-top: 10px; display: flex; justify-content: space-between; font-size: 9.5px; color: #444; line-height: 1.6; }',
    '.footer-col { width: 32%; }',
    '.footer-col strong { color: #222; font-size: 10px; }',
    '.prev-banner { border: 2px dashed #c0392b; color: #c0392b; font-weight: bold; padding: 8px 12px; margin: -4px 0 14px; font-size: 11.5px; text-transform: none; }',
    '.print-btn { position: fixed; top: 16px; right: 16px; padding: 8px 18px; background: #b07830; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; font-family: Arial, sans-serif; box-shadow: 0 2px 6px rgba(0,0,0,0.2); }',
    '.print-btn:hover { background: #8a5e22; }',
    '@media print { .print-btn { display: none; } body { padding: 10px 14px; } }'
  ].join('\n');

  // Coordonnées de la société : même source que le BL serveur et l'app mobile
  var entrepriseCache = null;
  function chargerEntreprise() {
    if (entrepriseCache) return Promise.resolve(entrepriseCache);
    return fetch('/API/system-config/', { credentials: 'same-origin', headers: { 'Accept': 'application/json' } })
      .then(function (r) { return r.ok ? r.json() : {}; })
      .catch(function () { return {}; })
      .then(function (cfg) {
        var e = (cfg && cfg.entreprise) || {};
        entrepriseCache = {
          nom: e.nom || '', adresse: e.adresse || '', telephone: e.telephone || '',
          email: e.email || '', rc: e.rc || '', nif: e.nif || '', nis: e.nis || ''
        };
        return entrepriseCache;
      });
  }

  // Ouvre le BL dans un nouvel onglet (bouton « Imprimer » en haut à droite, comme le BL serveur)
  function imprimer(data, fenetre) {
    var w = fenetre || window.open('', '_blank');
    if (!w) return null;
    w.document.open();
    w.document.write(html(data));
    w.document.close();
    return w;
  }

  window.BonLivraison = {
    html: html,
    imprimer: imprimer,
    chargerEntreprise: chargerEntreprise,
    formatDA: formatDA,
    nombreEnLettres: nombreEnLettres
  };
})(window);
