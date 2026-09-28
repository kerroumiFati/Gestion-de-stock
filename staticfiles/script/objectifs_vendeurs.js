/**
 * Objectifs mensuels des vendeurs (livreurs) : saisie et suivi.
 * Deux perimetres d'objectif : entrepot / gamme (Produit.entrepot_rattachement)
 * et type de produit (categorie + sous-categories). Taux calcule cote serveur.
 */
(function () {
  'use strict';
  var API = {
    objectifs: '/API/distribution/objectifs-vendeurs/',
    livreurs: '/API/distribution/livreurs/',
    entrepots: '/API/entrepots/',
    categories: '/API/categories/'
  };
  var MOIS = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août',
              'Septembre', 'Octobre', 'Novembre', 'Décembre'];
  var state = { livreurs: [], entrepots: [], categories: [], objectifs: [], currency: 'DA' };

  var $ = function (sel) { return document.querySelector(sel); };
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function getCookie(name) {
    var m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return m ? decodeURIComponent(m.pop()) : '';
  }
  function asList(d) { return Array.isArray(d) ? d : (d && Array.isArray(d.results) ? d.results : []); }
  function money(n) {
    var v = Number(n) || 0;
    return v.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' ' + state.currency;
  }
  function showAlert(msg, level) {
    var box = $('#obj-alerts');
    if (!box) return;
    var cls = level === 'success' ? 'alert-success' : level === 'warning' ? 'alert-warning' : level === 'danger' ? 'alert-danger' : 'alert-info';
    box.innerHTML = '<div class="alert ' + cls + ' alert-dismissible fade show" role="alert">' + esc(msg) +
      '<button type="button" class="close" data-dismiss="alert"><span>&times;</span></button></div>';
    if (level === 'success') setTimeout(function () { box.innerHTML = ''; }, 4000);
  }
  function api(url, opts) {
    opts = opts || {};
    var headers = Object.assign({ 'Accept': 'application/json' }, opts.headers || {});
    if (opts.method && opts.method !== 'GET') {
      headers['Content-Type'] = 'application/json';
      headers['X-CSRFToken'] = getCookie('csrftoken');
    }
    return fetch(url, Object.assign({ credentials: 'same-origin' }, opts, { headers: headers })).then(function (r) {
      if (r.status === 204) return null;
      return r.json().catch(function () { return null; }).then(function (data) {
        if (!r.ok) { var e = new Error('HTTP ' + r.status); e.data = data; e.status = r.status; throw e; }
        return data;
      });
    });
  }
  function errorMessage(e) {
    if (e && e.data && typeof e.data === 'object') {
      var parts = [];
      Object.keys(e.data).forEach(function (k) {
        var v = e.data[k];
        parts.push((k === 'non_field_errors' || k === 'detail' ? '' : k + ' : ') + (Array.isArray(v) ? v.join(', ') : v));
      });
      if (parts.length) return parts.join(' | ');
    }
    if (e && e.status === 403) return "Action réservée aux administrateurs.";
    return (e && e.message) || 'Erreur';
  }

  // ---------------- Periode ----------------
  function periode() {
    return { annee: parseInt($('#obj-filter-annee').value, 10), mois: parseInt($('#obj-filter-mois').value, 10) };
  }
  function initPeriode() {
    var now = new Date();
    var selMois = $('#obj-filter-mois');
    selMois.innerHTML = MOIS.map(function (m, i) { return '<option value="' + (i + 1) + '">' + m + '</option>'; }).join('');
    selMois.value = String(now.getMonth() + 1);
    $('#obj-filter-annee').value = String(now.getFullYear());
  }

  // ---------------- Referentiels ----------------
  function loadReferentiels() {
    return Promise.all([
      api(API.livreurs).then(function (d) { state.livreurs = asList(d); }),
      api(API.entrepots).then(function (d) {
        state.entrepots = asList(d).filter(function (w) {
          return w.is_active !== false && !String(w.code || '').toUpperCase().startsWith('VAN');
        });
      }),
      api(API.categories).then(function (d) {
        state.categories = asList(d).filter(function (c) { return c.is_active !== false; });
        state.categories.sort(function (a, b) {
          return String(a.full_path || a.nom).localeCompare(String(b.full_path || b.nom), 'fr');
        });
      })
    ]).then(function () {
      var livOpts = state.livreurs.map(function (l) {
        return '<option value="' + l.id + '">' + esc(l.nom) + (l.matricule ? ' (' + esc(l.matricule) + ')' : '') + '</option>';
      }).join('');
      $('#obj-livreur').innerHTML = '<option value="">Choisir…</option>' + livOpts;
      $('#obj-filter-livreur').innerHTML = '<option value="">Tous les vendeurs</option>' + livOpts;
      $('#obj-entrepot').innerHTML = '<option value="">Choisir…</option>' + state.entrepots.map(function (w) {
        return '<option value="' + w.id + '">' + esc(w.code) + ' - ' + esc(w.name) + '</option>';
      }).join('');
      $('#obj-categorie').innerHTML = '<option value="">Choisir…</option>' + state.categories.map(function (c) {
        return '<option value="' + c.id + '">' + esc(c.full_path || c.nom) + '</option>';
      }).join('');
    });
  }

  // ---------------- Suivi ----------------
  function loadObjectifs() {
    var p = periode();
    if (!p.annee || !p.mois) return Promise.resolve();
    var url = API.objectifs + '?annee=' + p.annee + '&mois=' + p.mois;
    var liv = $('#obj-filter-livreur').value;
    if (liv) url += '&livreur=' + encodeURIComponent(liv);
    $('#obj-period-label').textContent = '— ' + MOIS[p.mois - 1] + ' ' + p.annee;
    return api(url).then(function (d) {
      state.objectifs = asList(d);
      renderSynthese();
      renderTable();
    }).catch(function (e) { showAlert('Chargement des objectifs impossible : ' + errorMessage(e), 'danger'); });
  }

  function renderSynthese() {
    var list = state.objectifs;
    var nb = list.length;
    var atteints = list.filter(function (o) { return o.atteint; }).length;
    var totalObj = list.reduce(function (s, o) { return s + (Number(o.montant_objectif) || 0); }, 0);
    var totalCa = list.reduce(function (s, o) { return s + (Number(o.ca_realise) || 0); }, 0);
    $('#obj-card-nb').textContent = nb;
    $('#obj-card-atteints').textContent = atteints + (nb ? ' / ' + nb : '');
    $('#obj-card-ca').textContent = money(totalCa);
    $('#obj-card-taux').textContent = totalObj > 0 ? (totalCa / totalObj * 100).toFixed(1) + ' %' : '-';
  }

  function tauxClass(t) { return t == null ? 'low' : t >= 100 ? 'ok' : t >= 60 ? 'mid' : 'low'; }

  function renderTable() {
    var tbody = $('#obj-tbody');
    var list = state.objectifs.slice();
    if (!list.length) {
      tbody.innerHTML = '<tr><td colspan="7"><div class="obj-empty"><i class="fas fa-bullseye"></i>Aucun objectif défini pour cette période.</div></td></tr>';
      return;
    }
    // Regrouper par vendeur
    var groups = {};
    list.forEach(function (o) {
      (groups[o.livreur] = groups[o.livreur] || { nom: o.livreur_nom, matricule: o.livreur_matricule, items: [] }).items.push(o);
    });
    var html = '';
    Object.keys(groups).sort(function (a, b) { return String(groups[a].nom).localeCompare(String(groups[b].nom), 'fr'); }).forEach(function (id) {
      var g = groups[id];
      var totalObj = g.items.reduce(function (s, o) { return s + (Number(o.montant_objectif) || 0); }, 0);
      var totalCa = g.items.reduce(function (s, o) { return s + (Number(o.ca_realise) || 0); }, 0);
      var tauxG = totalObj > 0 ? totalCa / totalObj * 100 : null;
      html += '<tr class="obj-vendeur-row"><td><i class="fas fa-user"></i> ' + esc(g.nom) + (g.matricule ? ' <small class="text-muted">' + esc(g.matricule) + '</small>' : '') + '</td>' +
        '<td><small class="text-muted">' + g.items.length + ' objectif' + (g.items.length > 1 ? 's' : '') + '</small></td>' +
        '<td class="num">' + money(totalObj) + '</td><td class="num">' + money(totalCa) + '</td><td class="num"></td>' +
        '<td><span class="obj-taux ' + tauxClass(tauxG) + '">' + (tauxG == null ? '-' : tauxG.toFixed(1) + ' %') + '</span> <small class="text-muted">global</small></td><td></td></tr>';
      g.items.forEach(function (o) {
        var t = o.taux_reussite;
        var width = t == null ? 0 : Math.min(100, Math.max(0, t));
        var cls = tauxClass(t);
        html += '<tr data-id="' + o.id + '">' +
          '<td></td>' +
          '<td><span class="obj-perimetre ' + esc(o.type_perimetre) + '"><i class="fas ' + (o.type_perimetre === 'entrepot' ? 'fa-warehouse' : 'fa-tags') + '"></i> ' + esc(o.perimetre_label) + '</span>' +
            (o.note ? '<div class="obj-help">' + esc(o.note) + '</div>' : '') + '</td>' +
          '<td class="num">' + money(o.montant_objectif) + '</td>' +
          '<td class="num">' + money(o.ca_realise) + '</td>' +
          '<td class="num">' + (o.atteint ? '<span class="obj-badge ok">Atteint</span>' : money(o.reste)) + '</td>' +
          '<td><div class="obj-progress"><div class="obj-progress-bar"><div class="obj-progress-fill ' + cls + '" style="width:' + width + '%"></div></div>' +
            '<span class="obj-taux ' + cls + '">' + (t == null ? '-' : t.toFixed(1) + ' %') + '</span></div></td>' +
          '<td><div class="obj-actions">' +
            '<button type="button" class="btn btn-outline-primary" data-action="edit" data-id="' + o.id + '" title="Modifier"><i class="fas fa-edit"></i></button>' +
            '<button type="button" class="btn btn-outline-danger" data-action="delete" data-id="' + o.id + '" title="Supprimer"><i class="fas fa-trash"></i></button>' +
          '</div></td></tr>';
      });
    });
    tbody.innerHTML = html;
  }

  // ---------------- Formulaire ----------------
  function togglePerimetre() {
    var t = $('#obj-type').value;
    $('#obj-entrepot-wrap').style.display = t === 'entrepot' ? '' : 'none';
    $('#obj-categorie-wrap').style.display = t === 'categorie' ? '' : 'none';
  }
  function resetForm() {
    $('#obj-id').value = '';
    $('#obj-livreur').value = '';
    $('#obj-type').value = 'entrepot';
    $('#obj-entrepot').value = '';
    $('#obj-categorie').value = '';
    $('#obj-montant').value = '';
    $('#obj-note').value = '';
    $('#obj-form-title').textContent = 'Définir un objectif';
    $('#obj-btn-cancel').style.display = 'none';
    togglePerimetre();
  }
  function fillForm(o) {
    $('#obj-id').value = o.id;
    $('#obj-livreur').value = String(o.livreur);
    $('#obj-type').value = o.type_perimetre;
    $('#obj-entrepot').value = o.entrepot ? String(o.entrepot) : '';
    $('#obj-categorie').value = o.categorie ? String(o.categorie) : '';
    $('#obj-montant').value = Number(o.montant_objectif) || '';
    $('#obj-note').value = o.note || '';
    $('#obj-form-title').textContent = 'Modifier l\'objectif de ' + (o.livreur_nom || '');
    $('#obj-btn-cancel').style.display = '';
    togglePerimetre();
    $('#obj-montant').focus();
  }
  function saveForm(ev) {
    ev.preventDefault();
    var p = periode();
    var id = $('#obj-id').value;
    var type = $('#obj-type').value;
    var payload = {
      livreur: parseInt($('#obj-livreur').value, 10) || null,
      annee: p.annee, mois: p.mois,
      type_perimetre: type,
      entrepot: type === 'entrepot' ? (parseInt($('#obj-entrepot').value, 10) || null) : null,
      categorie: type === 'categorie' ? (parseInt($('#obj-categorie').value, 10) || null) : null,
      montant_objectif: parseFloat($('#obj-montant').value) || 0,
      note: $('#obj-note').value.trim()
    };
    if (!payload.livreur) { showAlert('Choisissez un vendeur.', 'warning'); return; }
    if (type === 'entrepot' && !payload.entrepot) { showAlert("Choisissez l'entrepôt / gamme.", 'warning'); return; }
    if (type === 'categorie' && !payload.categorie) { showAlert('Choisissez le type de produit.', 'warning'); return; }
    if (!(payload.montant_objectif > 0)) { showAlert("Saisissez un objectif de CA strictement positif.", 'warning'); return; }
    var btn = $('#obj-btn-save'); btn.disabled = true;
    api(id ? API.objectifs + id + '/' : API.objectifs, { method: id ? 'PUT' : 'POST', body: JSON.stringify(payload) })
      .then(function () {
        showAlert(id ? 'Objectif mis à jour.' : 'Objectif enregistré.', 'success');
        resetForm();
        return loadObjectifs();
      })
      .catch(function (e) {
        var msg = errorMessage(e);
        if (/unique|déjà|already|existe/i.test(msg)) msg = 'Un objectif identique existe déjà pour ce vendeur, ce périmètre et ce mois. Modifiez-le dans le tableau.';
        showAlert(msg, 'danger');
      })
      .finally(function () { btn.disabled = false; });
  }
  function deleteObjectif(id) {
    var o = state.objectifs.find(function (x) { return String(x.id) === String(id); });
    if (!o) return;
    if (!window.confirm('Supprimer l\'objectif « ' + o.perimetre_label + ' » de ' + o.livreur_nom + ' ?')) return;
    api(API.objectifs + id + '/', { method: 'DELETE' })
      .then(function () { showAlert('Objectif supprimé.', 'success'); if ($('#obj-id').value === String(id)) resetForm(); return loadObjectifs(); })
      .catch(function (e) { showAlert(errorMessage(e), 'danger'); });
  }

  // Reprendre les objectifs du mois precedent (ceux qui n'existent pas encore)
  function copyPreviousMonth() {
    var p = periode();
    var prevMois = p.mois === 1 ? 12 : p.mois - 1;
    var prevAnnee = p.mois === 1 ? p.annee - 1 : p.annee;
    var liv = $('#obj-filter-livreur').value;
    var url = API.objectifs + '?annee=' + prevAnnee + '&mois=' + prevMois + (liv ? '&livreur=' + encodeURIComponent(liv) : '');
    api(url).then(function (d) {
      var prev = asList(d);
      if (!prev.length) { showAlert('Aucun objectif en ' + MOIS[prevMois - 1] + ' ' + prevAnnee + '.', 'info'); return; }
      var key = function (o) { return [o.livreur, o.type_perimetre, o.entrepot || '', o.categorie || ''].join('|'); };
      var existing = {}; state.objectifs.forEach(function (o) { existing[key(o)] = true; });
      var todo = prev.filter(function (o) { return !existing[key(o)]; });
      if (!todo.length) { showAlert('Tous les objectifs du mois précédent existent déjà pour ce mois.', 'info'); return; }
      if (!window.confirm('Créer ' + todo.length + ' objectif(s) pour ' + MOIS[p.mois - 1] + ' ' + p.annee + ' à partir de ' + MOIS[prevMois - 1] + ' ' + prevAnnee + ' ?')) return;
      return Promise.all(todo.map(function (o) {
        return api(API.objectifs, { method: 'POST', body: JSON.stringify({
          livreur: o.livreur, annee: p.annee, mois: p.mois, type_perimetre: o.type_perimetre,
          entrepot: o.entrepot, categorie: o.categorie, montant_objectif: o.montant_objectif, note: o.note || ''
        }) });
      })).then(function () { showAlert(todo.length + ' objectif(s) créé(s).', 'success'); return loadObjectifs(); });
    }).catch(function (e) { showAlert(errorMessage(e), 'danger'); });
  }

  // ---------------- Init ----------------
  function bind() {
    $('#obj-type').addEventListener('change', togglePerimetre);
    $('#obj-form').addEventListener('submit', saveForm);
    $('#obj-btn-cancel').addEventListener('click', resetForm);
    $('#obj-btn-refresh').addEventListener('click', loadObjectifs);
    $('#obj-btn-copy-prev').addEventListener('click', copyPreviousMonth);
    ['#obj-filter-mois', '#obj-filter-annee', '#obj-filter-livreur'].forEach(function (s) {
      $(s).addEventListener('change', loadObjectifs);
    });
    $('#obj-tbody').addEventListener('click', function (e) {
      var btn = e.target.closest('button[data-action]');
      if (!btn) return;
      var id = btn.getAttribute('data-id');
      if (btn.getAttribute('data-action') === 'edit') {
        var o = state.objectifs.find(function (x) { return String(x.id) === String(id); });
        if (o) { fillForm(o); window.scrollTo({ top: $('#obj-form').getBoundingClientRect().top + window.scrollY - 90, behavior: 'smooth' }); }
      } else if (btn.getAttribute('data-action') === 'delete') {
        deleteObjectif(id);
      }
    });
  }
  function init() {
    if (!$('#obj-tbody')) return;
    if ($('#obj-tbody').dataset.inited) { loadObjectifs(); return; }
    $('#obj-tbody').dataset.inited = '1';
    initPeriode();
    bind();
    resetForm();
    loadReferentiels().then(loadObjectifs).catch(function (e) { showAlert('Chargement des référentiels impossible : ' + errorMessage(e), 'danger'); });
  }
  document.addEventListener('fragment:loaded', function (e) {
    if (e && e.detail && e.detail.name === 'objectifs_vendeurs') init();
  });
  if (document.readyState !== 'loading') init(); else document.addEventListener('DOMContentLoaded', init);
})();
