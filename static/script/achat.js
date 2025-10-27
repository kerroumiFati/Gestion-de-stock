// Achats - remplir le select client simplement
(function($){
  const DEBUG = true; function dbg(...a){ if(DEBUG) try{ console.log('[Achat]', ...a);}catch(e){} }
  const API_CLIENTS = '/API/clients/';
  const API_PRODUITS = '/API/produits/';
  const API_ENTREPOTS = '/API/entrepots/';

  function asList(data){
    if(Array.isArray(data)) return data;
    if(data && Array.isArray(data.results)) return data.results;
    if(data && typeof data === 'object') return Object.values(data);
    return [];
  }

  // CSRF helpers
  function getCookie(name){
    var match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? decodeURIComponent(match[2]) : null;
  }
  function getCSRFToken(){
    return getCookie('csrftoken') || (document.querySelector('input[name="csrfmiddlewaretoken"]') && document.querySelector('input[name="csrfmiddlewaretoken"]').value) || '';
  }

  function loadClients(){
    const $sel = $('#client');
    if(!$sel.length){ dbg('loadClients: #client not found, skip'); return; }
    // garder la première option
    const first = $sel.find('option').first().clone();
    $sel.empty().append(first);

    $.ajax({ url: API_CLIENTS + '?page_size=1000', method: 'GET', dataType: 'json' })
      .done(function(data){
        const list = asList(data);
        dbg('loadClients: size =', list.length, list);
        let defaultId = null;
        list.forEach(function(c){
          const label = [c.nom, c.prenom].filter(Boolean).join(' ');
          const $opt = $('<option>').val(c.id).text(label || ('Client #' + c.id)).appendTo($sel);
          // detect a "Divers" client by name
          const nameLc = (label || '').toLowerCase();
          if(defaultId === null && (nameLc === 'divers' || nameLc === 'client divers' || nameLc.includes('divers'))){
            defaultId = c.id;
          }
        });
        if(defaultId !== null){ $sel.val(defaultId); }
      })
      .fail(function(xhr){
        dbg('loadClients: fail', xhr.status, xhr.responseText || xhr.statusText);
      });
  }

  function loadProduits(query){
    const $sel = $('#sproduit');
    if(!$sel.length){ dbg('loadProduits: #sproduit not found, skip'); return; }
    const first = $sel.find('option').first().clone();
    $sel.empty().append(first);

    let url = API_PRODUITS + '?page_size=1000';
    if(query && query.trim()){
      url = API_PRODUITS + 'search/?q=' + encodeURIComponent(query.trim());
    }

    $.ajax({ url: url, method: 'GET', dataType: 'json' })
      .done(function(data){
        const list = asList(data);
        dbg('loadProduits: size =', list.length, list);
        list.forEach(function(p){
          const label = (p.reference ? (p.reference + ' - ') : '') + (p.designation || 'Produit #' + p.id);
          $('<option>').val(p.id).text(label).appendTo($sel);
        });
        // si un seul résultat, sélectionner automatiquement
        if(list.length === 1){ $sel.val(list[0].id); }
      })
      .fail(function(xhr){ dbg('loadProduits: fail', xhr.status, xhr.responseText || xhr.statusText); });
  }

  function loadWarehouses(){
    const $sel = $('#warehouse');
    if(!$sel.length){ dbg('loadWarehouses: #warehouse not found, skip'); return; }
    const first = $sel.find('option').first().clone();
    $sel.empty().append(first);

    $.ajax({ url: API_ENTREPOTS, method: 'GET', dataType: 'json' })
      .done(function(data){
        const list = asList(data).filter(function(w){ return w.is_active !== false; });
        dbg('loadWarehouses: size =', list.length, list);
        let defaultId = null;
        list.forEach(function(w){
          const label = (w.code ? (w.code + ' - ') : '') + (w.name || ('Entrepôt #' + w.id));
          const $opt = $('<option>').val(w.id).text(label).appendTo($sel);
          if(defaultId === null) defaultId = w.id;
        });
        if(defaultId !== null){ $sel.val(defaultId); }
      })
      .fail(function(xhr){ dbg('loadWarehouses: fail', xhr.status, xhr.responseText || xhr.statusText); });
  }

  function bindProduitFilters(){
    const $ref = $('#ref');
    const $code = $('#codebar');
    const $sel = $('#sproduit');
    if(!$sel.length) return;

    // initial load
    loadProduits();

    function doSearch(){
      const q = ($ref.val()||'').toString().trim() || ($code.val()||'').toString().trim();
      loadProduits(q);
    }

    let t; function debounced(){ clearTimeout(t); t = setTimeout(doSearch, 300); }
    $ref.on('input', debounced);
    $code.on('input', debounced);
  }

  function normalizeNumberToFloat(str){
    if(str == null) return NaN; let s = (''+str).trim(); if(!s) return NaN; s = s.replace(/\s+/g,'');
    if(s.includes(',') && s.includes('.')){ s = s.replace(/\./g,''); s = s.replace(',', '.'); }
    else if(s.includes(',')){ s = s.replace(',', '.'); }
    s = s.replace(/[^0-9\.-]/g,''); const v = parseFloat(s); return isNaN(v) ? NaN : v;
  }

  function buildAchatPayload(){
    const prixStr = ($('#prix_achat').val()||'').toString();
    const prix = normalizeNumberToFloat(prixStr);
    const data = {
      date_Achat: ($('#datea').val()||'').toString().slice(0,10),
      date_expiration: ($('#dateexp').val()||'').toString().slice(0,10) || null,
      quantite: parseInt(($('#quantite').val()||'0').toString(), 10),
      prix_achat: isNaN(prix) ? 0 : prix,
      client: parseInt(($('#client').val()||'0').toString(), 10) || null,
      produit: parseInt(($('#sproduit').val()||'0').toString(), 10) || null,
      warehouse: parseInt(($('#warehouse').val()||'0').toString(), 10) || null
    };
    if(!data.client) delete data.client;
    if(!data.produit) delete data.produit;
    if(!data.warehouse) delete data.warehouse;
    if(!data.date_expiration) data.date_expiration = null; // explicit null
    return data;
  }

  function createAchat(){
    const payload = buildAchatPayload();
    if(!payload.produit){ alert('Veuillez sélectionner un produit'); return; }
    if(!payload.client){ alert('Veuillez sélectionner un client'); return; }
    if(!payload.quantite || payload.quantite <= 0){ alert('Quantité invalide'); return; }
    return $.ajax({ url:'/API/achats/', method:'POST', contentType:'application/json', headers:{ 'X-CSRFToken': getCSRFToken() }, data: JSON.stringify(payload) })
      .done(function(){
        alert('Achat ajouté');
        // refresh table
        loadAchats();
        // reset some fields (keep date and selections)
        $('#quantite').val('');
        $('#ref').val('');
        $('#codebar').val('');
      })
      .fail(function(xhr){ alert((xhr.responseJSON && (xhr.responseJSON.detail||xhr.responseJSON.error)) || 'Erreur ajout achat'); });
  }

  function fetchAchat(id){
    return $.ajax({ url: '/API/achats/' + id + '/', method: 'GET', dataType: 'json' });
  }

  function updateAchat(id){
    const payload = buildAchatPayload();
    if(!payload.quantite || payload.quantite <= 0){ alert('Quantité invalide'); return; }
    return $.ajax({ url:'/API/achats/' + id + '/', method:'PUT', contentType:'application/json', headers:{ 'X-CSRFToken': getCSRFToken() }, data: JSON.stringify(payload) })
      .done(function(){
        alert('Achat mis à jour');
        loadAchats();
        resetEditMode();
      })
      .fail(function(xhr){ alert((xhr.responseJSON && (xhr.responseJSON.detail||xhr.responseJSON.error)) || 'Erreur mise à jour achat'); });
  }

  function deleteAchat(id){
    if(!confirm('Confirmer la suppression de cet achat ?')) return;
    return $.ajax({ url:'/API/achats/' + id + '/', method:'DELETE', headers:{ 'X-CSRFToken': getCSRFToken() } })
      .done(function(){
        loadAchats();
      })
      .fail(function(xhr){ alert((xhr.responseJSON && (xhr.responseJSON.detail||xhr.responseJSON.error)) || 'Erreur suppression achat'); });
  }

  function enterEditMode(achat){
    try {
      if(achat.date_Achat) $('#datea').val((achat.date_Achat||'').toString().slice(0,10));
      if(achat.date_expiration) $('#dateexp').val((achat.date_expiration||'').toString().slice(0,10)); else $('#dateexp').val('');
      if(achat.quantite != null) $('#quantite').val(achat.quantite);
      if(achat.prix_achat != null) $('#prix_achat').val(achat.prix_achat);
      if(achat.client) $('#client').val(achat.client);
      if(achat.produit) $('#sproduit').val(achat.produit);
      updateTotalAchat();
    } catch(e) {}
    $('#id').val(achat.id);
    $('#section-achat #btn').text('Mettre à jour').attr('data-mode','edit');
  }

  function resetEditMode(){
    $('#id').val('');
    $('#section-achat #btn').text('Ajouter').attr('data-mode','add');
  }

  function renderAchats(list){
    const $tbody = $('#tachat tbody#table-content');
    if(!$tbody.length) return;
    $tbody.empty();
    if(!list || !list.length){
      $tbody.append('<tr><td colspan="7" class="text-center text-muted">Aucun achat</td></tr>');
      return;
    }
    list.forEach(function(a){
      const tr = $('<tr>');
      tr.append('<td>'+(a.id||'')+'</td>');
      tr.append('<td>'+(a.date_Achat||'')+'</td>');
      tr.append('<td>'+(a.quantite||0)+'</td>');
      var clientTxt = (a.client_nom||'') + (a.client_prenom?(' '+a.client_prenom):'');
      var prodTxt = (a.produit_reference? (a.produit_reference+' - ') : '') + (a.produit_designation||'');
      tr.append('<td>'+ (clientTxt || a.client || '') +'</td>');
      tr.append('<td>'+ (prodTxt || a.produit || '') +'</td>');
      var prix = (typeof a.prix_achat !== 'undefined') ? a.prix_achat : '';
      var total = (a.total_achat != null) ? a.total_achat : '';
      var sym = a.currency_symbol || '';
      // If we add new columns, ensure header also updated if needed
      // Append price and total columns after product if header supports it
      // For now, include in product cell suffix for backward-compatible header
      tr.append('<td>'+(prix!==''? (prix+' '+sym): '')+'</td>');
      tr.append('<td>'+(total!==''? (total+' '+sym): '')+'</td>');
      tr.append('<td><button class="btn btn-sm btn-outline-danger" data-action="delete" data-id="'+a.id+'">Supprimer</button></td>');
      tr.append('<td><button class="btn btn-sm btn-outline-primary" data-action="edit" data-id="'+a.id+'">Modifier</button></td>');
      $tbody.append(tr);
    });
  }

  function loadAchats(){
    const url = '/API/achats/?page_size=1000';
    return $.ajax({ url:url, method:'GET', dataType:'json' })
      .done(function(data){ const list = Array.isArray(data)?data:(data.results||data||[]); renderAchats(list); })
      .fail(function(xhr){ console.warn('loadAchats failed', xhr.status, xhr.responseText||xhr.statusText); });
  }

  function updateTotalAchat(){
    const qty = parseInt(($('#quantite').val()||'0').toString(), 10) || 0;
    const p = normalizeNumberToFloat($('#prix_achat').val()||'0');
    const total = (isNaN(p)?0:p) * qty;
    $('#total_achat').val(total.toFixed(2));
  }

  function init(){
    if(!document.getElementById('tachat')){ dbg('init: achats page not detected, skip'); return; }
    // Set default date to today's system date if empty
    var $date = $('#datea');
    if($date.length && (!$date.val() || $date.val()==='')){
      try {
        var tzOffset = (new Date()).getTimezoneOffset() * 60000;
        var localISODate = (new Date(Date.now() - tzOffset)).toISOString().slice(0,10);
        $date.val(localISODate);
      } catch(e) { try{ $date.val(new Date().toISOString().slice(0,10)); }catch(_){} }
    }
    // bind add/update button
    $(document).off('click', '#section-achat #btn').on('click', '#section-achat #btn', function(){
      var mode = $(this).attr('data-mode') || 'add';
      var id = $('#id').val();
      if(mode === 'edit' && id){ updateAchat(id); } else { createAchat(); }
    });
    // bind table actions (edit/delete)
    $(document).off('click', '#tachat [data-action="delete"]').on('click', '#tachat [data-action="delete"]', function(){
      var id = $(this).data('id');
      deleteAchat(id);
    });
    $(document).off('click', '#tachat [data-action="edit"]').on('click', '#tachat [data-action="edit"]', function(){
      var id = $(this).data('id');
      fetchAchat(id).done(function(data){ enterEditMode(data); });
    });
    // reactive total calc
    $(document).off('input', '#quantite, #prix_achat').on('input', '#quantite, #prix_achat', updateTotalAchat);
    loadClients();
    loadWarehouses();
    bindProduitFilters();
    loadAchats();
  }

  $(document).ready(init);
  document.addEventListener('fragment:loaded', function(e){ if(e && e.detail && e.detail.name==='achat'){ init(); } });
})(jQuery);
