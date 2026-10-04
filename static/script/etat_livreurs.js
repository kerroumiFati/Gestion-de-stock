/**
 * etat_livreurs.js — page « État des livreurs ».
 * Données : GET /API/distribution/etat-livreurs/ (calcul dans API/etat_livreurs.py).
 */
(function () {
  'use strict';

  var API = '/API/distribution/etat-livreurs/';
  var state = { data: null, filtreEtat: '', ouverts: {} };
  var ICONES = { ecart: 'exclamation-circle', a_controler: 'clock', net: 'check-circle', aucune: 'minus-circle' };

  function $(s) { return document.querySelector(s); }
  function esc(v) {
    return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function money(n) {
    return (Number(n) || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' DA';
  }
  function signedMoney(n) {
    n = Number(n) || 0;
    if (n === 0) return '<span class="el-zero">0,00 DA</span>';
    return '<span class="' + (n < 0 ? 'el-neg' : 'el-pos') + '">' + (n > 0 ? '+' : '−') + money(Math.abs(n)) + '</span>';
  }
  function dateFr(iso) {
    if (!iso) return '–';
    var p = iso.split('-');
    return p[2] + '/' + p[1] + '/' + p[0];
  }
  function iso(d) {
    var m = d.getMonth() + 1, j = d.getDate();
    return d.getFullYear() + '-' + (m < 10 ? '0' : '') + m + '-' + (j < 10 ? '0' : '') + j;
  }
  function badge(etat, libelle) {
    return '<span class="el-badge ' + etat + '"><i class="fas fa-' + ICONES[etat] + '"></i> ' + esc(libelle) + '</span>';
  }
  function showAlert(msg, type) {
    var box = $('#el-alerts');
    if (box) box.innerHTML = msg ? '<div class="alert alert-' + (type || 'info') + '">' + esc(msg) + '</div>' : '';
  }

  // ---------------------------------------------------------------- période
  function setPeriode(q) {
    var fin = new Date(), debut = new Date();
    if (q === 'mois') debut = new Date(fin.getFullYear(), fin.getMonth(), 1);
    else debut.setDate(fin.getDate() - (parseInt(q, 10) - 1));
    $('#el-debut').value = iso(debut);
    $('#el-fin').value = iso(fin);
    document.querySelectorAll('#el-quick button').forEach(function (b) {
      b.classList.toggle('active', b.getAttribute('data-q') === String(q));
    });
  }

  // ---------------------------------------------------------------- chargement
  function load() {
    var url = API + '?date_debut=' + encodeURIComponent($('#el-debut').value) + '&date_fin=' + encodeURIComponent($('#el-fin').value);
    $('#el-tbody').innerHTML = '<tr><td colspan="8" class="el-empty">Chargement…</td></tr>';
    showAlert('');
    return fetch(url, { credentials: 'same-origin', headers: { 'Accept': 'application/json' } })
      .then(function (r) {
        return r.json().then(function (j) {
          if (!r.ok) throw new Error(j.error || j.detail || ('Erreur ' + r.status));
          return j;
        });
      })
      .then(function (data) {
        state.data = data;
        fillLivreurs(data.livreurs);
        render();
      })
      .catch(function (e) {
        $('#el-tbody').innerHTML = '<tr><td colspan="8" class="el-empty">—</td></tr>';
        showAlert('Chargement impossible : ' + e.message, 'danger');
      });
  }

  function fillLivreurs(livreurs) {
    var sel = $('#el-livreur'), courant = sel.value;
    sel.innerHTML = '<option value="">Tous les livreurs</option>' + livreurs.map(function (l) {
      return '<option value="' + l.livreur_id + '">' + esc(l.nom) + ' (' + esc(l.matricule) + ')</option>';
    }).join('');
    sel.value = courant;
  }

  // ---------------------------------------------------------------- affichage
  function render() {
    var d = state.data;
    if (!d) return;
    $('#el-n-ecart').textContent = d.synthese.ecart;
    $('#el-n-controle').textContent = d.synthese.a_controler;
    $('#el-n-net').textContent = d.synthese.net;
    $('#el-manquant').textContent = money(d.synthese.manquant_total);
    $('#el-tol').textContent = d.tolerance;
    document.querySelectorAll('.el-card[data-filtre]').forEach(function (c) {
      c.classList.toggle('selected', c.getAttribute('data-filtre') === state.filtreEtat);
    });

    var livreurId = $('#el-livreur').value;
    var voirSans = $('#el-sans') && $('#el-sans').checked;
    var rows = d.livreurs.filter(function (l) {
      if (l.etat === 'aucune' && !voirSans && !livreurId) return false;
      return (!state.filtreEtat || l.etat === state.filtreEtat) && (!livreurId || String(l.livreur_id) === livreurId);
    });
    var nbSans = d.livreurs.filter(function (l) { return l.etat === 'aucune'; }).length;
    if ($('#el-sans-n')) $('#el-sans-n').textContent = nbSans;
    if (!rows.length) {
      var aucuneTournee = !d.livreurs.some(function (l) { return l.nb_tournees > 0; });
      $('#el-tbody').innerHTML = '<tr><td colspan="8" class="el-empty">' + (aucuneTournee
        ? 'Aucune tournée terminée sur cette période. Élargissez les dates.'
        : 'Aucun livreur pour ce filtre.') + '</td></tr>';
      return;
    }
    $('#el-tbody').innerHTML = rows.map(function (l) {
      var ouvert = !!state.ouverts[l.livreur_id];
      var html = '<tr class="el-row">' +
        '<td><div class="el-name">' + esc(l.nom) + '<small>' + esc(l.matricule) + '</small></div></td>' +
        '<td>' + badge(l.etat, l.etat_libelle) + '</td>' +
        '<td class="num" data-label="Tournées">' + l.nb_tournees + '</td>' +
        '<td class="num hide-sm" data-label="Manquant">' + (l.manquant ? '<span class="el-neg">' + money(l.manquant) + '</span>' : '<span class="el-zero">–</span>') + '</td>' +
        '<td class="num hide-sm" data-label="Excédent">' + (l.excedent ? '<span class="el-pos">' + money(l.excedent) + '</span>' : '<span class="el-zero">–</span>') + '</td>' +
        '<td class="num" data-label="Écart net">' + signedMoney(l.ecart_net) + '</td>' +
        '<td class="hide-sm" data-label="Dernière tournée">' + dateFr(l.derniere_tournee) + '</td>' +
        '<td class="num el-cell-btn">' + (l.nb_tournees
          ? '<button type="button" class="el-btn-detail' + (ouvert ? ' open' : '') + '" data-id="' + l.livreur_id + '">' +
            '<i class="fas fa-' + (ouvert ? 'chevron-up' : 'search') + '"></i> ' + (ouvert ? 'Masquer' : 'Voir le détail') + '</button>'
          : '') + '</td></tr>';
      if (ouvert) html += '<tr class="el-detail-row"><td colspan="8">' + detailHtml(l) + '</td></tr>';
      return html;
    }).join('');
  }

  function billetsHtml(b) {
    var keys = Object.keys(b || {}).filter(function (k) { return Number(b[k]) > 0; })
      .sort(function (a, c) { return Number(c) - Number(a); });
    if (!keys.length) return '';
    return '<div class="el-billets"><i class="fas fa-money-bill-wave"></i> Billets rendus : ' +
      keys.map(function (k) { return b[k] + ' × ' + Number(k).toLocaleString('fr-FR'); }).join(' · ') + '</div>';
  }

  function detailHtml(l) {
    var lignes = l.tournees.map(function (t) {
      var r = t.rapport;
      var etatLib = { ecart: 'Écart', a_controler: 'À contrôler', net: 'Net' }[t.etat];
      var tete = '<td class="nowrap"><b>' + dateFr(t.date) + '</b><div class="el-motif">' + esc(t.numero) + '</div></td>' +
        '<td>' + badge(t.etat, etatLib) + '</td>';
      if (!r) {
        return '<tr>' + tete + '<td colspan="6" class="el-motif">' + esc(t.motif) + '</td></tr>';
      }
      var infos = [];
      infos.push('Rapport ' + esc(r.statut_libelle.toLowerCase()) + (r.valide_par ? ' par ' + esc(r.valide_par) : ''));
      if (t.etat === 'a_controler' && t.motif) infos.push(esc(t.motif));
      var billets = billetsHtml(r.detail_billets);
      var sous = '<div class="el-motif">' + infos.join(' · ') + '</div>' +
        (r.justification ? '<div class="el-justif"><i class="fas fa-comment"></i> <b>Justification :</b> ' + esc(r.justification) + '</div>' : '') +
        billets;
      return '<tr class="el-t">' + tete +
        '<td class="num" data-label="Fonds de départ">' + money(r.fonds_depart) + '</td>' +
        '<td class="num" data-label="+ Espèces">' + money(r.total_especes) + '</td>' +
        '<td class="num" data-label="− Dépenses">' + money(r.total_depenses) + '</td>' +
        '<td class="num" data-label="= Attendu"><b>' + money(r.solde_theorique) + '</b></td>' +
        '<td class="num" data-label="Rapporté"><b>' + money(r.solde_reel) + '</b></td>' +
        '<td class="num" data-label="Écart">' + signedMoney(r.ecart) + '</td></tr>' +
        '<tr class="el-sous"><td></td><td colspan="7">' + sous + '</td></tr>';
    }).join('');
    return '<div class="el-detail">' +
      '<h6><i class="fas fa-list"></i> Détail par tournée — ' + esc(l.nom) + '</h6>' +
      '<div class="table-responsive"><table class="el-table el-table-detail"><thead><tr>' +
      '<th>Tournée</th><th>État</th><th class="num">Fonds de départ</th><th class="num">+ Espèces</th>' +
      '<th class="num">− Dépenses</th><th class="num">= Attendu</th><th class="num">Rapporté</th><th class="num">Écart</th>' +
      '</tr></thead><tbody>' + lignes + '</tbody></table></div>' +
      '<div class="el-calc"><b>Attendu</b> = fonds de départ + espèces encaissées − dépenses. <b>Écart</b> = rapporté − attendu ' +
      '(négatif : manquant, positif : excédent). Les paiements par carte, chèque ou à crédit ne sont pas de l’argent à rapporter.</div>' +
      '</div>';
  }

  // ---------------------------------------------------------------- événements
  function bind() {
    $('#el-refresh').addEventListener('click', load);
    $('#el-debut').addEventListener('change', function () { clearQuick(); load(); });
    $('#el-fin').addEventListener('change', function () { clearQuick(); load(); });
    $('#el-livreur').addEventListener('change', render);
    $('#el-sans').addEventListener('change', render);
    document.querySelectorAll('#el-quick button').forEach(function (b) {
      b.addEventListener('click', function () { setPeriode(b.getAttribute('data-q')); load(); });
    });
    document.querySelectorAll('.el-card[data-filtre]').forEach(function (c) {
      c.addEventListener('click', function () {
        var f = c.getAttribute('data-filtre');
        state.filtreEtat = state.filtreEtat === f ? '' : f;
        render();
      });
    });
    $('#el-tbody').addEventListener('click', function (e) {
      var b = e.target.closest('.el-btn-detail');
      if (!b) return;
      var id = b.getAttribute('data-id');
      state.ouverts[id] = !state.ouverts[id];
      render();
    });
  }
  function clearQuick() {
    document.querySelectorAll('#el-quick button').forEach(function (b) { b.classList.remove('active'); });
  }

  function init() {
    if (!$('#el-tbody')) return;
    if ($('#el-tbody').dataset.inited) { load(); return; }
    $('#el-tbody').dataset.inited = '1';
    setPeriode('30');
    bind();
    load();
  }
  document.addEventListener('fragment:loaded', function (e) {
    if (e && e.detail && e.detail.name === 'etat_livreurs') init();
  });
  if (document.readyState !== 'loading') init(); else document.addEventListener('DOMContentLoaded', init);
})();
