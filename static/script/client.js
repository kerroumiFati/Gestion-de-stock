// Page Clients : liste, recherche, ajout / modification / suppression — interface simplifiée
(function($){
  const API_BASE = '/API/clients/';
  const API_SECTEURS = '/API/secteurs/';
  const API_TYPES_PRIX = '/API/types-prix/';
  const AVATAR_COLORS = ['#2563eb', '#16a34a', '#d97706', '#dc2626', '#7c3aed', '#0891b2', '#db2777', '#4b5563'];

  let allClients = [];
  let currentFilter = 'all';
  let pendingDeleteId = null;

  // ---------- Outils ----------
  function getCookie(name){
    const m = document.cookie.split('; ').find(r => r.startsWith(name + '='));
    return m ? decodeURIComponent(m.split('=')[1]) : null;
  }
  function getCSRFToken(){
    let t = getCookie('csrftoken');
    if(!t){ const el = document.querySelector('input[name="csrfmiddlewaretoken"]'); if(el) t = el.value; }
    return t;
  }
  $.ajaxSetup({
    beforeSend: function(xhr, settings){
      if(!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type)){
        const t = getCSRFToken(); if(t) xhr.setRequestHeader('X-CSRFToken', t);
      }
    }
  });

  function esc(v){
    return String(v == null ? '' : v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }
  function asList(data){
    if(Array.isArray(data)) return data;
    if(data && Array.isArray(data.results)) return data.results;
    return [];
  }
  function money(n){
    return Number(n || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' DA';
  }
  function normalize(s){
    return String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  }
  function fullName(c){ return ((c.nom || '') + ' ' + (c.prenom || '')).trim() || 'Client sans nom'; }

  function toast(message, type){
    type = type || 'success';
    const icon = type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle';
    const $t = $(`<div class="cp-toast ${type}"><i class="fa ${icon}"></i><div>${esc(message)}</div></div>`);
    $('#cpToasts').append($t);
    setTimeout(() => $t.fadeOut(300, () => $t.remove()), type === 'success' ? 3500 : 6000);
  }

  // Le solde : négatif = le client doit de l'argent, positif = il a payé d'avance
  function balanceHtml(solde){
    const v = parseFloat(solde || 0);
    if(v < 0) return `<span class="cp-balance debt"><i class="fa fa-arrow-down"></i> Doit ${money(-v)}</span>`;
    if(v > 0) return `<span class="cp-balance credit"><i class="fa fa-arrow-up"></i> Avance ${money(v)}</span>`;
    return `<span class="cp-balance ok"><i class="fa fa-check"></i> À jour</span>`;
  }

  // ---------- Listes déroulantes ----------
  function loadSecteurs(){
    return $.getJSON(API_SECTEURS + '?is_active=true').done(function(data){
      const $s = $('#secteur');
      $s.find('option:not(:first)').remove();
      asList(data).forEach(s => $s.append(`<option value="${s.id}">${esc(s.nom)}${s.code ? ' (' + esc(s.code) + ')' : ''}</option>`));
    });
  }
  function loadTypesPrix(){
    return $.getJSON(API_TYPES_PRIX + '?is_active=true').done(function(data){
      const $s = $('#type_prix');
      $s.find('option:not(:first)').remove();
      asList(data).forEach(tp => $s.append(`<option value="${tp.id}">${esc(tp.libelle || tp.code)}</option>`));
    });
  }

  // ---------- Liste des clients ----------
  function loadClients(){
    return $.getJSON(API_BASE + '?page_size=1000')
      .done(function(data){
        allClients = asList(data);
        renderStats();
        renderTable();
      })
      .fail(function(){
        $('#table-content').html(`<tr><td colspan="6" class="cp-empty"><i class="fa fa-wifi"></i>
          <h5>Impossible de charger les clients</h5>
          <p>Vérifiez votre connexion internet puis <a href="#" class="cp-reload">cliquez ici pour réessayer</a>.</p></td></tr>`);
      });
  }

  function renderStats(){
    const debtors = allClients.filter(c => parseFloat(c.solde || 0) < 0);
    const totalDebt = debtors.reduce((s, c) => s - parseFloat(c.solde || 0), 0);
    $('#statTotal').text(allClients.length);
    $('#statDebt').text(debtors.length);
    $('#statDebtTotal').text(money(totalDebt));
  }

  function renderTable(){
    const $body = $('#table-content');
    const q = normalize($('#searchFilter').val()).trim();
    const qDigits = q.replace(/\D/g, '');

    let list = allClients.filter(c => {
      if(currentFilter === 'debt' && !(parseFloat(c.solde || 0) < 0)) return false;
      if(!q) return true;
      const text = normalize([c.nom, c.prenom, c.prenom + ' ' + c.nom, c.email, c.adresse, c.secteur_nom, c.telephone].join(' '));
      if(text.includes(q)) return true;
      // Recherche de téléphone sans tenir compte des espaces / tirets
      return qDigits.length >= 3 && String(c.telephone || '').replace(/\D/g, '').includes(qDigits);
    });
    list.sort((a, b) => fullName(a).localeCompare(fullName(b), 'fr'));

    const n = list.length;
    $('#countText').text(n + (n > 1 ? ' clients affichés' : ' client affiché'));

    if(!allClients.length){
      $body.html(`<tr><td colspan="6" class="cp-empty"><i class="fa fa-user-friends"></i>
        <h5>Vous n'avez encore aucun client</h5>
        <p>Cliquez sur le bouton vert pour ajouter votre premier client.</p>
        <button type="button" class="cp-btn-big cp-btn-green mt-2 cp-open-new"><i class="fa fa-user-plus"></i> Nouveau client</button></td></tr>`);
      return;
    }
    if(!n){
      $body.html(`<tr><td colspan="6" class="cp-empty"><i class="fa fa-search"></i>
        <h5>Aucun client trouvé</h5>
        <p>Vérifiez l'orthographe ou <a href="#" class="cp-clear-search">effacez la recherche</a>.</p></td></tr>`);
      return;
    }

    $body.html(list.map(c => {
      const color = AVATAR_COLORS[(c.id || 0) % AVATAR_COLORS.length];
      const initials = (String(c.nom || '?').charAt(0) + String(c.prenom || '').charAt(0)).toUpperCase();
      const secteur = c.secteur_nom
        ? `<span class="badge" style="background:${esc(c.secteur_couleur || '#6b7280')};color:#fff;font-weight:500;">${esc(c.secteur_nom)}</span>` : '';
      const tel = c.telephone
        ? `<a class="cp-phone" href="tel:${esc(String(c.telephone).replace(/\s/g, ''))}"><i class="fa fa-phone-alt"></i> ${esc(c.telephone)}</a>`
        : '<span class="text-muted">—</span>';
      return `<tr data-id="${c.id}">
        <td><div class="cp-client">
          <div class="cp-avatar" style="background:${color};">${esc(initials)}</div>
          <div><div class="cp-client-name">${esc(fullName(c))}</div>${secteur}</div>
        </div></td>
        <td>${tel}</td>
        <td class="cp-hide-mobile">${esc(c.adresse) || '<span class="text-muted">—</span>'}</td>
        <td class="cp-hide-mobile">${c.type_prix_libelle || c.type_prix_code ? esc(c.type_prix_libelle || c.type_prix_code) : '<span class="text-muted">Normal</span>'}</td>
        <td>${balanceHtml(c.solde)}</td>
        <td><div class="cp-actions">
          <button type="button" class="cp-act edit btn-edit" data-id="${c.id}"><i class="fa fa-pen"></i> Modifier</button>
          <button type="button" class="cp-act btn-historique" data-id="${c.id}"><i class="fa fa-history"></i> Paiements</button>
          <button type="button" class="cp-act del btn-delete" data-id="${c.id}" title="Supprimer"><i class="fa fa-trash"></i></button>
        </div></td>
      </tr>`;
    }).join(''));
  }

  // ---------- Formulaire ----------
  function setSelect($sel, value){
    $sel.val(value == null ? '' : String(value)).trigger('change');
  }

  function clearErrors(){
    $('#clientForm .cp-input').removeClass('is-invalid');
    $('#clientForm .cp-error').removeClass('show').text('');
  }
  function fieldError(field, message){
    $('#' + field).addClass('is-invalid');
    $(`#clientForm .cp-error[data-for="${field}"]`).text(message).addClass('show');
  }

  function setSolde(value){
    const v = parseFloat(value || 0);
    $('#solde').val(v || '');
    $('#soldeType').val(v < 0 ? '-1' : (v > 0 ? '1' : '0'));
    $('#soldeMontant').val(v ? Math.abs(v) : '');
    $('#soldeAmountGroup').toggle(v !== 0);
  }
  function computeSolde(){
    const sign = parseInt($('#soldeType').val(), 10) || 0;
    const amount = Math.abs(parseFloat($('#soldeMontant').val()) || 0);
    return sign * amount;
  }

  function updateMapLink(){
    const lat = $('#lat').val(), lng = $('#lng').val();
    if(lat && lng) $('#linkSeeMap').attr('href', `https://www.google.com/maps?q=${encodeURIComponent(lat)},${encodeURIComponent(lng)}`).show();
    else $('#linkSeeMap').hide();
  }

  function resetForm(){
    $('#clientForm')[0] && $('#clientForm')[0].reset();
    $('#id').val('');
    setSelect($('#secteur'), '');
    setSelect($('#type_prix'), '');
    setSolde(0);
    updateMapLink();
    clearErrors();
    $('#moreInfo').collapse('hide');
  }

  function openForm(client){
    resetForm();
    const isEdit = !!client;
    $('#formTitle').text(isEdit ? 'Modifier : ' + fullName(client) : 'Nouveau client');
    $('#formIcon').attr('class', isEdit ? 'fa fa-user-edit text-primary' : 'fa fa-user-plus text-success');
    $('#btnClient span').text(isEdit ? 'Enregistrer les modifications' : 'Enregistrer le client');

    if(isEdit){
      $('#id').val(client.id);
      ['nom', 'prenom', 'email', 'telephone', 'adresse', 'lat', 'lng', 'nif', 'nis', 'ai', 'rc'].forEach(f => $('#' + f).val(client[f] == null ? '' : client[f]));
      setSelect($('#secteur'), client.secteur);
      setSelect($('#type_prix'), client.type_prix);
      setSolde(client.solde);
      updateMapLink();
      // Ouvrir la partie « plus d'informations » si elle contient déjà quelque chose
      if(client.lat || client.lng || client.nif || client.nis || client.ai || client.rc || parseFloat(client.solde || 0)){
        $('#moreInfo').collapse('show');
      }
    }

    $('#clientFormCard').slideDown(200, function(){
      const top = $('#clientFormCard').offset().top - 90;
      $('html, body').animate({ scrollTop: top }, 250);
      $('#nom').trigger('focus');
    });
  }

  function closeForm(){
    $('#clientFormCard').slideUp(200);
    resetForm();
  }

  function payloadFromForm(){
    const val = id => ($('#' + id).val() || '').trim();
    const secteur = $('#secteur').val(), typePrix = $('#type_prix').val();
    const lat = val('lat'), lng = val('lng');
    const solde = computeSolde();
    $('#solde').val(solde || '');
    return {
      nom: val('nom'), prenom: val('prenom'), email: val('email'),
      telephone: val('telephone'), adresse: val('adresse'),
      secteur: secteur ? parseInt(secteur, 10) : null,
      type_prix: typePrix ? parseInt(typePrix, 10) : null,
      lat: lat ? parseFloat(lat) : null, lng: lng ? parseFloat(lng) : null,
      nif: val('nif'), nis: val('nis'), ai: val('ai'), rc: val('rc'),
      solde: solde
    };
  }

  function validate(d){
    clearErrors();
    let firstBad = null;
    const need = (field, msg) => { fieldError(field, msg); firstBad = firstBad || field; };
    if(!d.nom) need('nom', 'Écrivez le nom du client.');
    if(!d.prenom) need('prenom', 'Écrivez le prénom du client.');
    if(!d.telephone) need('telephone', 'Écrivez le numéro de téléphone.');
    else if(d.telephone.replace(/\D/g, '').length < 8) need('telephone', 'Ce numéro semble trop court. Vérifiez-le.');
    if(!d.adresse) need('adresse', "Écrivez l'adresse du client.");
    if(d.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(d.email)) need('email', "Cette adresse email n'est pas valide (exemple : nom@exemple.dz). Vous pouvez aussi la laisser vide.");
    if(firstBad){
      $('#' + firstBad).trigger('focus');
      toast('Il manque des informations : regardez les cases en rouge.', 'error');
      return false;
    }
    return true;
  }

  function showServerErrors(xhr, fallback){
    const j = xhr.responseJSON;
    let shown = false;
    if(j && typeof j === 'object'){
      Object.keys(j).forEach(k => {
        const msg = Array.isArray(j[k]) ? j[k][0] : j[k];
        if($(`#clientForm .cp-error[data-for="${k}"]`).length){ fieldError(k, msg); shown = true; }
      });
      if(!shown && (j.detail || j.error)){ toast(j.detail || j.error, 'error'); return; }
    }
    toast(shown ? 'Corrigez les cases en rouge puis réessayez.' : fallback, 'error');
  }

  function saveClient(){
    const data = payloadFromForm();
    if(!validate(data)) return;
    const id = $('#id').val();
    const $btn = $('#btnClient').prop('disabled', true);
    const oldHtml = $btn.html();
    $btn.html('<i class="fa fa-spinner fa-spin"></i> <span>Enregistrement…</span>');

    $.ajax({
      url: id ? API_BASE + id + '/' : API_BASE,
      method: id ? 'PATCH' : 'POST',
      contentType: 'application/json',
      data: JSON.stringify(data)
    })
      .done(function(resp){
        const name = fullName(resp && resp.nom ? resp : data);
        toast(id ? `Les informations de ${name} ont été enregistrées.` : `Le client ${name} a été ajouté.`);
        closeForm();
        loadClients().done(function(){
          const newId = (resp && resp.id) || id;
          const $row = $(`#table-content tr[data-id="${newId}"]`);
          if($row.length){
            $row.addClass('cp-flash');
            const box = $row.closest('.table-responsive');
            box.scrollTop(box.scrollTop() + $row.position().top - 60);
          }
        });
      })
      .fail(function(xhr){
        showServerErrors(xhr, id ? "Les modifications n'ont pas pu être enregistrées. Réessayez." : "Le client n'a pas pu être ajouté. Réessayez.");
      })
      .always(function(){ $btn.prop('disabled', false).html(oldHtml); });
  }

  function editClient(id){
    $.getJSON(API_BASE + id + '/')
      .done(openForm)
      .fail(() => toast('Impossible d\'ouvrir ce client. Réessayez.', 'error'));
  }

  // ---------- Suppression ----------
  function askDelete(id){
    const c = allClients.find(x => String(x.id) === String(id));
    pendingDeleteId = id;
    $('#deleteClientName').text(c ? fullName(c) : '');
    $('#deleteClientModal').modal('show');
  }
  function confirmDelete(){
    if(!pendingDeleteId) return;
    const id = pendingDeleteId;
    const c = allClients.find(x => String(x.id) === String(id));
    $.ajax({ url: API_BASE + id + '/', method: 'DELETE' })
      .done(function(){
        $('#deleteClientModal').modal('hide');
        toast(`Le client ${c ? fullName(c) : ''} a été supprimé.`);
        if(String($('#id').val()) === String(id)) closeForm();
        loadClients();
      })
      .fail(function(xhr){
        $('#deleteClientModal').modal('hide');
        const j = xhr.responseJSON;
        toast((j && (j.detail || j.error)) || 'Ce client ne peut pas être supprimé, probablement parce qu\'il a déjà des ventes ou des commandes.', 'error');
      })
      .always(() => { pendingDeleteId = null; });
  }

  // ---------- Historique des paiements ----------
  function showHistorique(clientId){
    $('#historique-client-info').hide();
    $('#historique-content').html('<div class="text-center py-4"><i class="fa fa-spinner fa-spin fa-2x"></i><p class="mt-2">Chargement…</p></div>');
    $('#historiqueModal').modal('show');

    $.getJSON(API_BASE + clientId + '/historique_paiements/')
      .done(function(data){
        $('#historique-client-nom').text(data.client_nom || '');
        $('#historique-solde-actuel').html('Situation actuelle : ' + balanceHtml(data.solde_actuel));
        $('#historique-client-info').show();

        const list = data.paiements || [];
        if(!list.length){
          $('#historique-content').html('<div class="alert alert-light text-center border"><i class="fa fa-info-circle"></i> Aucun paiement enregistré pour ce client.</div>');
          return;
        }
        $('#historique-content').html(`<div class="table-responsive"><table class="table table-hover">
          <thead><tr><th>Date</th><th>Montant payé</th><th>Moyen</th><th>Situation après</th><th>Par</th><th>Note</th></tr></thead>
          <tbody>${list.map(p => `<tr>
            <td><small>${esc(new Date(p.date_paiement).toLocaleString('fr-FR'))}</small></td>
            <td class="text-success"><strong>+ ${money(p.montant)}</strong></td>
            <td><span class="badge badge-info">${esc(p.mode_paiement_display || '')}</span></td>
            <td>${balanceHtml(p.solde_apres)}</td>
            <td><small>${esc(p.enregistre_par || '—')}</small></td>
            <td><small>${esc(p.notes || '—')}</small></td>
          </tr>`).join('')}</tbody></table></div>`);
      })
      .fail(function(){
        $('#historique-content').html('<div class="alert alert-danger">Impossible de charger les paiements. Réessayez.</div>');
      });
  }

  // ---------- Position GPS ----------
  function useMyPosition(){
    if(!navigator.geolocation){ toast('Votre appareil ne permet pas de donner la position.', 'error'); return; }
    const $b = $('#btnMyPosition').prop('disabled', true);
    const old = $b.html();
    $b.html('<i class="fa fa-spinner fa-spin"></i> Recherche de la position…');
    navigator.geolocation.getCurrentPosition(function(pos){
      $('#lat').val(pos.coords.latitude.toFixed(7));
      $('#lng').val(pos.coords.longitude.toFixed(7));
      updateMapLink();
      toast('Position enregistrée dans le formulaire.');
      $b.prop('disabled', false).html(old);
    }, function(){
      toast('Position introuvable. Autorisez la localisation dans le navigateur puis réessayez.', 'error');
      $b.prop('disabled', false).html(old);
    }, { enableHighAccuracy: true, timeout: 15000 });
  }

  // ---------- Événements ----------
  function bind(){
    const ns = '.clientPage';
    $(document).off(ns);
    // Anciens gestionnaires d'une version précédente de la page encore en mémoire
    $(document)
      .off('click', '#btnClient')
      .off('click', '#table-content .btn-delete')
      .off('click', '#table-content .btn-edit')
      .off('click', '#table-content .btn-historique');
    $(document)
      .on('click' + ns, '#btnNouveauClient, .cp-open-new', () => openForm(null))
      .on('click' + ns, '#btnCancelForm', closeForm)
      .on('click' + ns, '#btnClient', saveClient)
      .on('keydown' + ns, '#clientForm input', function(e){ if(e.key === 'Enter'){ e.preventDefault(); saveClient(); } })
      .on('input' + ns, '#clientForm .cp-input', function(){
        $(this).removeClass('is-invalid');
        $(`#clientForm .cp-error[data-for="${this.id}"]`).removeClass('show');
      })
      .on('click' + ns, '#table-content .btn-edit', function(){ editClient($(this).data('id')); })
      .on('click' + ns, '#table-content .btn-delete', function(){ askDelete($(this).data('id')); })
      .on('click' + ns, '#table-content .btn-historique', function(){ showHistorique($(this).data('id')); })
      .on('click' + ns, '#btnConfirmDelete', confirmDelete)
      .on('input' + ns, '#searchFilter', renderTable)
      .on('click' + ns, '.cp-clear-search', function(e){ e.preventDefault(); $('#searchFilter').val('').trigger('focus'); setFilter('all'); })
      .on('click' + ns, '.cp-reload', function(e){ e.preventDefault(); loadClients(); })
      .on('click' + ns, '#clientsPage .cp-stat', function(){ setFilter($(this).data('filter')); })
      .on('change' + ns, '#soldeType', function(){
        const show = $(this).val() !== '0';
        $('#soldeAmountGroup').toggle(show);
        if(show) $('#soldeMontant').trigger('focus'); else $('#soldeMontant').val('');
      })
      .on('input' + ns, '#lat, #lng', updateMapLink)
      .on('click' + ns, '#btnMyPosition', useMyPosition);
  }

  function setFilter(f){
    currentFilter = f || 'all';
    $('#clientsPage .cp-stat').removeClass('active');
    $(`#clientsPage .cp-stat[data-filter="${currentFilter}"]`).first().addClass('active');
    renderTable();
  }

  function init(){
    if(!document.getElementById('clientsPage')) return;
    currentFilter = 'all';
    allClients = [];
    bind();
    loadSecteurs();
    loadTypesPrix();
    loadClients();
  }

  window.ClientPage = { init: init };
  // Compatibilité : ancien bouton « Réinitialiser »
  window.resetForm = resetForm;

  // Premier chargement ; les visites suivantes appellent ClientPage.init() depuis client.html
  $(init);
})(jQuery);
