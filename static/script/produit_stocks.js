/*
 * Gestion des achats → onglet « Stock par entrepôt ».
 * Recherche immédiate, filtre par entrepôt, chiffres clés (le dernier filtre les produits à
 * surveiller), jauge de niveau par ligne, correction tracée (POST /API/stocks/corriger/ :
 * mouvement de stock + journal d'audit, motif « Inventaire » par défaut).
 */
(function () {
  const $ = window.jQuery;
  const API = '/API';
  const MOTIFS = [['INV', 'Inventaire'], ['CASSE', 'Casse'], ['PERTE', 'Perte / vol'], ['CORR', 'Erreur de saisie'], ['AUTRE', 'Autre']];
  const COULEURS = ['#2563eb', '#7c3aed', '#db2777', '#ea580c', '#059669', '#0891b2', '#4f46e5', '#b45309'];

  let LIGNES = [];
  let ENTREPOTS = [];
  let ENTREPOTS_TOUS = [];
  let SEULEMENT_ALERTE = false;
  let EN_COURS = null;
  let MOTIF = 'INV';

  const cookie = (n) => { const v = `; ${document.cookie}`.split(`; ${n}=`); return v.length === 2 ? v.pop().split(';').shift() : ''; };
  const nombre = (n) => (Number(n) || 0).toLocaleString('fr-FR');
  const argent = (n) => (Number(n) || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const esc = (t) => String(t == null ? '' : t).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const norm = (t) => String(t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  const couleur = (id) => COULEURS[Math.abs(Number(id) || 0) % COULEURS.length];
  const initiale = (t) => (String(t || '?').trim()[0] || '?').toUpperCase();
  const entrepot = (id) => ENTREPOTS_TOUS.find(x => String(x.id) === String(id));

  function niveau(l) {
    const q = Number(l.quantity) || 0;
    const seuil = Math.max(1, Number(l.seuil_alerte) || 0);
    if (q <= 0) return { cle: 'epuise', libelle: 'Épuisé', coul: '#dc2626', pct: 0 };
    if (q <= seuil) return { cle: 'faible', libelle: 'Faible', coul: '#d97706', pct: Math.max(8, Math.round(q / (seuil * 3) * 100)) };
    return { cle: 'ok', libelle: 'OK', coul: '#16a34a', pct: Math.min(100, Math.round(q / (seuil * 3) * 100)) };
  }

  function cartons(l) {
    const upc = Number(l.unites_par_carton) || 1, q = Number(l.quantity) || 0;
    if (upc <= 1 || q < upc) return '';
    const ct = Math.floor(q / upc), u = q % upc;
    return `${ct} ct${u ? ` + ${u} u` : ''}`;
  }

  function filtrees() {
    const wh = $('#ps_wh').val(), texte = norm($('#ps_recherche').val()).trim(), zero = $('#ps_zero').is(':checked');
    return LIGNES.filter(l => {
      const q = Number(l.quantity) || 0;
      if (wh && String(l.warehouse) !== String(wh)) return false;
      if (SEULEMENT_ALERTE) { if (niveau(l).cle === 'ok') return false; }
      else if (!zero && q <= 0) return false;
      if (texte && !norm(`${l.produit_designation} ${l.produit_reference}`).includes(texte)) return false;
      return true;
    }).sort((a, b) => String(a.produit_designation).localeCompare(String(b.produit_designation), 'fr')
                      || (Number(b.quantity) || 0) - (Number(a.quantity) || 0));
  }

  function afficher() {
    const lignes = filtrees();
    const tbody = $('#tstock tbody').empty();
    let qte = 0, valeur = 0, alerte = 0, prec = null;
    const produits = new Set();
    // Les chiffres clés portent sur l'entrepôt choisi, sans tenir compte de la recherche
    const wh = $('#ps_wh').val();
    LIGNES.forEach(l => {
      if (wh && String(l.warehouse) !== String(wh)) return;
      const q = Number(l.quantity) || 0;
      if (q > 0) { produits.add(l.produit); qte += q; valeur += q * (Number(l.prix_unitaire) || 0); }
      if (niveau(l).cle !== 'ok') alerte++;   // stock faible ou épuisé (= ce qu'affiche un clic sur ce chiffre)
    });

    const frag = document.createDocumentFragment();
    lignes.forEach(l => {
      const q = Number(l.quantity) || 0, n = niveau(l), suite = prec === l.produit; prec = l.produit;
      const ent = entrepot(l.warehouse), off = ent && ent.is_active === false;
      const tr = document.createElement('tr');
      if (suite) tr.className = 'ps-suite';
      tr.innerHTML =
        (suite ? '<td></td>' :
          `<td><div class="ps-prod"><span class="ps-av" style="background:${couleur(l.produit)}">${esc(initiale(l.produit_designation))}</span>` +
          `<div><div class="ps-nom">${esc(l.produit_designation)}</div><div class="ps-ref">${esc(l.produit_reference || '')}</div></div></div></td>`) +
        `<td>${esc(l.warehouse_name || '')}<div class="ps-ref">${esc(l.warehouse_code || '')}${off ? ' · <span class="text-danger">inactif</span>' : ''}</div></td>` +
        `<td class="ps-num"><div class="ps-qte">${nombre(q)}</div><div class="ps-ct">${esc(cartons(l))}</div></td>` +
        `<td><div class="ps-jauge mb-1"><span style="width:${n.pct}%;background:${n.coul}"></span></div>` +
        `<span class="ps-pastille" style="color:${n.coul}">${n.libelle}</span></td>` +
        `<td class="ps-num">${argent(q * (Number(l.prix_unitaire) || 0))} <span class="text-muted small">DA</span></td>` +
        `<td class="text-right"><button type="button" class="btn btn-outline-primary ps-act" title="Corriger" aria-label="Corriger"><i class="fas fa-pen"></i></button></td>`;
      tr.querySelector('button').addEventListener('click', (e) => { e.preventDefault(); ouvrir(l); });
      frag.appendChild(tr);
    });
    tbody[0].appendChild(frag);

    $('#ps_nb').text(nombre(produits.size));
    $('#ps_qte').text(nombre(qte));
    $('#ps_valeur').text(argent(valeur));
    $('#ps_alerte').text(nombre(alerte));
    $('#ps_kpi_alerte').toggleClass('ps-actif', SEULEMENT_ALERTE);
    $('#tstock').toggle(lignes.length > 0);
    $('#ps_vide').toggle(lignes.length === 0);
  }

  function charger() {
    $('#ps_refresh').prop('disabled', true).addClass('ps-tourne');
    return $.when($.get(API + '/stocks/'), $.get(API + '/entrepots/'))
      .then(function (rs, rw) {
        LIGNES = Array.isArray(rs[0]) ? rs[0] : (rs[0] && rs[0].results) || [];
        ENTREPOTS_TOUS = Array.isArray(rw[0]) ? rw[0] : (rw[0] && rw[0].results) || [];
        ENTREPOTS = ENTREPOTS_TOUS.filter(x => x.is_active !== false);
        const choisi = $('#ps_wh').val();
        $('#ps_wh').html('<option value="">Tous les entrepôts</option>' +
          ENTREPOTS.map(x => `<option value="${x.id}">${esc(x.name || '')} · ${esc(x.code || '')}</option>`).join(''));
        if (choisi) $('#ps_wh').val(choisi);
        afficher();
      })
      .fail(function () {
        $('#tstock').hide();
        $('#ps_vide').html('<i class="fas fa-wifi text-danger"></i><span>Connexion impossible</span>').show();
      })
      .always(function () { $('#ps_refresh').prop('disabled', false).removeClass('ps-tourne'); });
  }

  // ---------- Correction ----------
  function ouvrir(l) {
    EN_COURS = l; MOTIF = 'INV';
    $('#ps_m_av').text(initiale(l.produit_designation)).css('background', couleur(l.produit));
    $('#ps_m_produit').text(l.produit_designation);
    $('#ps_m_entrepot').text(`${l.produit_reference || ''} · ${l.warehouse_name || ''}`);
    $('#ps_m_avant').text(nombre(l.quantity));
    $('#ps_m_nouvelle').val(Number(l.quantity) || 0);
    $('#ps_m_note').val('');
    $('#ps_m_erreur').hide();
    $('#ps_m_motifs').html(MOTIFS.map(([v, t]) =>
      `<button type="button" class="ps-motif${v === MOTIF ? ' ps-on' : ''}" data-motif="${v}">${esc(t)}</button>`).join(''));
    maj();
    $('#ps_modal').modal('show');
    setTimeout(() => $('#ps_m_nouvelle').trigger('focus').select(), 350);
  }

  function valeurSaisie() {
    const brut = String($('#ps_m_nouvelle').val()).trim();
    const n = Number(brut);
    return brut !== '' && Number.isInteger(n) && n >= 0 ? n : null;
  }

  function maj() {
    if (!EN_COURS) return;
    const avant = Number(EN_COURS.quantity) || 0, n = valeurSaisie();
    const d = n === null ? null : n - avant;
    $('#ps_m_apres').text(n === null ? '—' : nombre(n));
    const delta = $('#ps_m_delta');
    if (d === null || d === 0) delta.text(d === null ? '!' : '0').css({ background: '#f1f5f9', color: '#6b7280' });
    else if (d > 0) delta.text(`+${nombre(d)}`).css({ background: '#dcfce7', color: '#15803d' });
    else delta.text(`−${nombre(-d)}`).css({ background: '#fee2e2', color: '#b91c1c' });
    $('#ps_m_valider').prop('disabled', d === null || d === 0);
    $('#ps_m_erreur').hide();
  }

  function pas(sens) {
    const n = valeurSaisie();
    $('#ps_m_nouvelle').val(Math.max(0, (n === null ? Number(EN_COURS.quantity) || 0 : n) + sens));
    maj();
  }

  function valider() {
    const n = valeurSaisie();
    if (!EN_COURS || n === null || n === (Number(EN_COURS.quantity) || 0)) return;
    $('#ps_m_valider').prop('disabled', true);
    $.ajax({
      url: API + '/stocks/corriger/', method: 'POST', contentType: 'application/json',
      headers: { 'X-CSRFToken': cookie('csrftoken') },
      data: JSON.stringify({ produit: EN_COURS.produit, warehouse: EN_COURS.warehouse, nouvelle_quantite: n, motif: MOTIF, note: $('#ps_m_note').val() }),
    }).done(function (r) {
      $('#ps_modal').modal('hide');
      const d = r.delta > 0 ? `+${nombre(r.delta)}` : `−${nombre(-r.delta)}`;
      $('#ps_message').html(`<i class="fas fa-check-circle"></i> <b>${esc(r.produit)}</b> · ${esc(r.entrepot)}<br>${nombre(r.avant)} → <b>${nombre(r.apres)}</b> (${d}) · ${esc(r.motif)}`)
        .stop(true, true).fadeIn(150).delay(4500).fadeOut(400);
      charger();
    }).fail(function (x) {
      $('#ps_m_erreur').text((x.responseJSON && (x.responseJSON.detail || x.responseJSON.error)) || 'Échec de l\'enregistrement').show();
      maj();
    });
  }

  function init() {
    if (!$('#tstock').length) return;
    $(document).off('.ps');
    $(document).on('click.ps', '#ps_refresh', (e) => { e.preventDefault(); charger(); });
    $(document).on('change.ps', '#ps_wh, #ps_zero', afficher);
    $(document).on('input.ps', '#ps_recherche', afficher);
    $(document).on('click.ps', '#ps_kpi_alerte', () => { SEULEMENT_ALERTE = !SEULEMENT_ALERTE; afficher(); });
    $(document).on('input.ps', '#ps_m_nouvelle', maj);
    $(document).on('click.ps', '#ps_m_moins', () => pas(-1));
    $(document).on('click.ps', '#ps_m_plus', () => pas(1));
    $(document).on('click.ps', '#ps_m_motifs [data-motif]', function () {
      MOTIF = $(this).data('motif');
      $('#ps_m_motifs [data-motif]').removeClass('ps-on');
      $(this).addClass('ps-on');
    });
    $(document).on('click.ps', '#ps_m_valider', (e) => { e.preventDefault(); valider(); });
    $(document).on('keydown.ps', '#ps_m_nouvelle, #ps_m_note', (e) => { if (e.key === 'Enter') { e.preventDefault(); valider(); } });
    charger();
  }

  $(document).ready(init);
  document.addEventListener('fragment:loaded', (e) => { if (e && e.detail && e.detail.name === 'achat') init(); });
})();
