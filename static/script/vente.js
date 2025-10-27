// Vente page behaviors: load clients, currencies, and products into selects
(function($){
  const DEBUG = true; function dbg(...a){ if(DEBUG) try{ console.log('[Vente]', ...a);}catch(e){} }
  const API_CLIENTS = '/API/clients/';
  const API_PRODUITS = '/API/produits/';
  const API_CURRENCIES = '/API/currencies/';
  const API_EXCHANGE_RATES = '/API/exchange-rates/';
  const API_WAREHOUSES = '/API/entrepots/';
  function asListSafe(data){
    if (Array.isArray(data)) return data;
    if (data && Array.isArray(data.results)) return data.results;
    if (data && data.results && typeof data.results === 'object') return Object.values(data.results);
    return [];
  }

  function asList(data){
    if(Array.isArray(data)) return data;
    if(data && Array.isArray(data.results)) return data.results;
    if(data && typeof data === 'object') return Object.values(data);
    return [];
  }

  function fillSelect($sel, items, map){
    if(!$sel.length) return;
    const first = $sel.find('option').first().clone();
    $sel.empty().append(first);
    items.forEach(function(item){
      const {value, text} = map(item);
      $('<option>').val(value).text(text).appendTo($sel);
    });
  }

  function loadClients(){
    const $sel = $('#vente_client');
    if(!$sel.length){ return; }
    $.ajax({ url: API_CLIENTS + '?page_size=1000', method: 'GET', dataType: 'json' })
      .done(function(data){
        const list = asList(data);
        fillSelect($sel, list, function(c){
          const label = [c.nom, c.prenom].filter(Boolean).join(' ');
          return { value: c.id, text: label || ('Client #' + c.id) };
        });
        // optional: preselect Divers if present
        let diversId = null;
        list.forEach(function(c){
          const label = [c.nom, c.prenom].filter(Boolean).join(' ').toLowerCase();
          if(diversId === null && (label === 'divers' || label.includes('divers'))){ diversId = c.id; }
        });
        if(diversId) { $sel.val(diversId); }
      })
      .fail(function(xhr){ dbg('loadClients fail', xhr.status, xhr.responseText || xhr.statusText); });
  }

  function renderCurrenciesTable(list){
    const $tbody = $('#currencies_body'); if(!$tbody.length) return;
    $tbody.empty();
    if(!list.length){ $tbody.append('<tr><td colspan="5" class="text-center text-muted">Aucune devise</td></tr>'); return; }
    list.forEach(function(c){
      const tr = $('<tr>');
      tr.append('<td>'+ (c.code||'') +'</td>');
      tr.append('<td>'+ (c.name||'') +'</td>');
      tr.append('<td>'+ (c.symbol||'') +'</td>');
      tr.append('<td>'+ (c.is_default ? '<span class="badge badge-success">Oui</span>' : 'Non') +'</td>');
      tr.append('<td><!-- actions placeholder --></td>');
      $tbody.append(tr);
    });
  }

  function fillCurrencySelects(list){
    const sels = ['#vente_currency','#rate_from_currency','#rate_to_currency','#convert_from','#convert_to'];
    sels.forEach(function(sel){
      const $s = $(sel); if(!$s.length) return;
      const first = $s.find('option').first().clone(); $s.empty().append(first);
      fillSelect($s, list, function(cur){
        const text = cur.code + (cur.symbol ? (' ('+cur.symbol+')') : '');
        return { value: cur.id, text: text };
      });
    });
    // Prefer DZD for sales currency if present, otherwise fall back to system default
    const dzd = list.find(c => (c.code||'').toUpperCase() === 'DZD');
    if(dzd){ $('#vente_currency').val(dzd.id); }
    else {
      const def = list.find(c => c.is_default);
      if(def){ $('#vente_currency').val(def.id); }
    }
  }

  function loadWarehouses(){
    const $sel = $('#vente_warehouse'); if(!$sel.length) return;
    $.ajax({ url: API_WAREHOUSES + '?page_size=1000', method: 'GET', dataType: 'json' })
      .done(function(data){
        const list = asListSafe(data).filter(function(w){ return w && w.is_active !== false; });
        fillSelect($sel, list, function(w){ return { value: w.id, text: (w.code||'') + ' - ' + (w.name||'') }; });
        // Preselect from system default warehouse when available
        $.getJSON('/API/system-config/').done(function(cfg){
          const dw = cfg && (cfg[0] || cfg).default_warehouse;
          if(dw){
            const exists = list.some(function(w){ return String(w.id) === String(dw); });
            if(exists){ $sel.val(String(dw)); return; }
          }
          // Fallback: keep previous heuristic if no config or not found
          const defByCode = list.find(function(w){ return (w.code||'').toUpperCase().startsWith('DEF'); });
          if(defByCode){ $sel.val(defByCode.id); }
        }).fail(function(){
          // If config not accessible, fallback to DEF* heuristic
          const defByCode = list.find(function(w){ return (w.code||'').toUpperCase().startsWith('DEF'); });
          if(defByCode){ $sel.val(defByCode.id); }
        });
        if(list.length === 0){ console.warn('Aucun entrepôt chargé'); }
      })
      .fail(function(xhr){ dbg('loadWarehouses fail', xhr.status, xhr.responseText || xhr.statusText); });
  }

  function loadCurrencies(){
    $.ajax({ url: API_CURRENCIES + '?page_size=1000', method: 'GET', dataType: 'json' })
      .done(function(data){
        const list = asList(data);
        renderCurrenciesTable(list);
        fillCurrencySelects(list);
      })
      .fail(function(xhr){ dbg('loadCurrencies fail', xhr.status, xhr.responseText || xhr.statusText); });
  }

  function addCurrency(){
    const code = ($('#currency_code').val()||'').trim().toUpperCase();
    const name = ($('#currency_name').val()||'').trim();
    const symbol = ($('#currency_symbol').val()||'').trim();
    if(!code || code.length!==3){ alert('Code devise invalide (3 lettres)'); return; }
    if(!name){ alert('Nom requis'); return; }
    if(!symbol){ alert('Symbole requis'); return; }
    $.ajax({ url: API_CURRENCIES, method:'POST', contentType:'application/json', headers:{ 'X-CSRFToken': getCSRFToken() }, data: JSON.stringify({ code, name, symbol }) })
      .done(function(){ $('#currency_code').val(''); $('#currency_name').val(''); $('#currency_symbol').val(''); loadCurrencies(); })
      .fail(function(xhr){ alert(((xhr.responseJSON||{}).detail || (xhr.responseJSON||{}).error || xhr.statusText || 'Erreur ajout devise')); });
  }

  function renderRates(list){
    const $tbody = $('#rates_body'); if(!$tbody.length) return;
    $tbody.empty();
    if(!list.length){ $tbody.append('<tr><td colspan="5" class="text-center text-muted">Aucun taux</td></tr>'); return; }
    list.forEach(function(r){
      const tr = $('<tr>');
      tr.append('<td>'+ (r.from_currency_code || r.from_currency) +'</td>');
      tr.append('<td>'+ (r.to_currency_code || r.to_currency) +'</td>');
      tr.append('<td>'+ (r.rate) +'</td>');
      tr.append('<td>'+ (r.date || '') +'</td>');
      tr.append('<td><!-- actions placeholder --></td>');
      $tbody.append(tr);
    });
  }

  function loadRates(){
    $.ajax({ url: API_EXCHANGE_RATES + '?page_size=1000', method:'GET', dataType:'json' })
      .done(function(data){ const list = asList(data); renderRates(list); })
      .fail(function(xhr){ dbg('loadRates fail', xhr.status, xhr.responseText || xhr.statusText); });
  }

  function normalizeNumberToFloat(str){
    if(str == null) return NaN;
    let s = (''+str).trim();
    if(!s) return NaN;
    // Remove spaces
    s = s.replace(/\s+/g,'');
    // If both ',' and '.' present, assume '.' are thousands separators and ',' is decimal (fr-FR style)
    if(s.includes(',') && s.includes('.')){
      s = s.replace(/\./g,'');
      s = s.replace(',', '.');
    } else if(s.includes(',')){
      // Only comma: treat as decimal separator
      s = s.replace(',', '.');
    }
    // Now, ensure only valid numeric format remains
    // Strip any non numeric except leading '-' and single '.'
    s = s.replace(/[^0-9\.-]/g,'');
    const v = parseFloat(s);
    return isNaN(v) ? NaN : v;
  }

  function addRate(){
    const from_currency = parseInt($('#rate_from_currency').val()||'0',10) || null;
    const to_currency = parseInt($('#rate_to_currency').val()||'0',10) || null;
    const rateStr = $('#rate_value').val();
    const rate = normalizeNumberToFloat(rateStr);
    if(!from_currency || !to_currency || !rate || rate<=0){ alert('Veuillez remplir tous les champs du taux (ex: 270,000 ou 270.000)'); return; }
    $.ajax({ url: API_EXCHANGE_RATES, method:'POST', contentType:'application/json', headers:{ 'X-CSRFToken': getCSRFToken() }, data: JSON.stringify({ from_currency, to_currency, rate }) })
      .done(function(){ $('#rate_value').val(''); loadRates(); })
      .fail(function(xhr){ alert(((xhr.responseJSON||{}).detail || (xhr.responseJSON||{}).error || xhr.statusText || 'Erreur ajout taux')); });
  }

  function convertAmount(){
    const amount = parseFloat($('#convert_amount').val()||'0');
    const from_id = parseInt($('#convert_from').val()||'0',10) || null;
    const to_id = parseInt($('#convert_to').val()||'0',10) || null;
    if(!amount || amount<=0 || !from_id || !to_id){ return; }
    // Simple client-side conversion using latest rate list currently loaded (not perfect but helpful)
    // Fallback: display hint if not possible
    const $out = $('#convert_result');
    // Since we don't have an API for conversion, prompt user to use stats or existing logic
    $out.text('Conversion approximative: utilisez le taux correspondant dans la liste.').show();
  }

  function loadProduits(query){
    const $sel = $('#vente_prod');
    if(!$sel.length){ return; }
    const first = $sel.find('option').first().clone();
    $sel.empty().append(first);

    let url = API_PRODUITS + '?page_size=1000';
    const q = (query||'').trim();
    if(q){ url = API_PRODUITS + 'search/?q=' + encodeURIComponent(q); }

    $.ajax({ url: url, method: 'GET', dataType: 'json' })
      .done(function(data){
        const list = asList(data);
        fillSelect($sel, list, function(p){
          const text = (p.reference ? (p.reference + ' - ') : '') + (p.designation || ('Produit #' + p.id));
          return { value: p.id, text: text };
        });
        if(list.length === 1){ $sel.val(list[0].id); }
      })
      .fail(function(xhr){ dbg('loadProduits fail', xhr.status, xhr.responseText || xhr.statusText); });
  }

  function bindProduitFilters(){
    const $ref = $('#vente_ref');
    const $cb = $('#vente_cb');
    const $sel = $('#vente_prod');
    if(!$sel.length) return;

    function doSearch(){
      const q = ($ref.val()||'').toString().trim() || ($cb.val()||'').toString().trim();
      loadProduits(q);
    }
    let t; function debounced(){ clearTimeout(t); t = setTimeout(doSearch, 300); }
    $ref.on('input', debounced);
    $cb.on('input', debounced);

    // initial load without filters
    loadProduits('');
  }

  // Cache produits par id pour récupérer prix et devise
  const PRODUCTS_CACHE = {};

  function getCSRFToken(){
    var m = document.cookie.match(/(^| )csrftoken=([^;]+)/); return m ? decodeURIComponent(m[2]) : '';
  }

  // Panier de lignes (avant envoi)
  let LINES = [];

  function renderLines(){
    const $tbody = $('#vente_body'); if(!$tbody.length) return;
    $tbody.empty();
    if(!LINES.length){
      $tbody.append('<tr><td colspan="6" class="text-center text-muted">Aucune ligne</td></tr>');
    } else {
      LINES.forEach(function(l, idx){
        const p = PRODUCTS_CACHE[l.produit] || {};
        const ref = p.reference || '';
        const designation = l.designation || p.designation || ('Produit #'+l.produit);
        const price = Number(l.prixU_snapshot || p.prixU || 0);
        const qty = Number(l.quantite || 0);
        const total = price * qty;
        const sym = (p.currency_symbol || p.currency && p.currency.symbol) || '';
        const tr = $('<tr>');
        tr.append('<td>'+ref+'</td>');
        tr.append('<td>'+designation+'</td>');
        tr.append('<td>'+price.toFixed(2)+' '+sym+'</td>');
        tr.append('<td>'+qty+'</td>');
        tr.append('<td>'+(total.toFixed(2))+' '+sym+'</td>');
        tr.append('<td><button class="btn btn-sm btn-outline-danger" data-action="rm" data-idx="'+idx+'">Supprimer</button></td>');
        $tbody.append(tr);
      });
    }
    recalcTotals();
  }

  function recalcTotals(){
    let total = 0;
    LINES.forEach(function(l){
      const p = PRODUCTS_CACHE[l.produit] || {}; const price = Number(l.prixU_snapshot || p.prixU || 0); const qty = Number(l.quantite||0); total += price*qty;
    });
    const remisePct = parseFloat(($('#vente_remise').val()||'0')) || 0;
    const remiseMontant = total * (remisePct/100);
    const totalTTC = total - remiseMontant;
    $('#vente_total_ht').text(total.toFixed(2)+' €');
    $('#vente_remise_montant').text(remiseMontant.toFixed(2)+' €');
    $('#vente_total_ttc').text(totalTTC.toFixed(2)+' €');
  }

  function addCurrentProductLine(){
    const prodId = parseInt($('#vente_prod').val()||'0', 10);
    const qty = parseInt($('#vente_qte').val()||'0', 10);
    if(!prodId){ alert('Veuillez choisir un produit'); return; }
    if(!qty || qty <= 0){ alert('Quantité invalide'); return; }
    const p = PRODUCTS_CACHE[prodId];
    if(!p){ alert('Produit introuvable en cache, réessayez.'); return; }
    const line = {
      produit: prodId,
      designation: p.designation || '',
      quantite: qty,
      prixU_snapshot: p.prixU,
      currency: p.currency || null
    };
    LINES.push(line);
    // reset input qty only
    $('#vente_qte').val('1');
    renderLines();
  }

  function removeLine(idx){
    if(idx<0 || idx>=LINES.length) return; LINES.splice(idx,1); renderLines();
  }

  function buildSalePayload(){
    const client = parseInt($('#vente_client').val()||'0', 10) || null;
    if(!client){ alert('Veuillez choisir un client'); return null; }
    const warehouse = parseInt($('#vente_warehouse').val()||'0', 10) || null;
    if(!warehouse){ alert("Veuillez sélectionner l'entrepôt de sortie"); return null; }
    if(LINES.length === 0){ alert('Ajoutez au moins une ligne'); return null; }
    const currency = parseInt($('#vente_currency').val()||'0', 10) || null;
    const remise = normalizeNumberToFloat($('#vente_remise').val()||'0');
    const payload = {
      numero: ($('#vente_num').val()||'').trim() || undefined,
      client: client,
      type_paiement: ($('#vente_paiement').val()||'cash'),
      warehouse: warehouse,
      currency: currency || undefined,
      remise_percent: isNaN(remise) ? 0 : remise,
      observations: ($('#vente_obs').val()||'').trim(),
      lignes: LINES.map(function(l){ return { produit: l.produit, designation: l.designation, quantite: l.quantite, prixU_snapshot: l.prixU_snapshot, currency: l.currency || undefined }; })
    };
    return payload;
  }

  function clearSale(){
    LINES = [];
    renderLines();
    $('#vente_client').val('');
    $('#vente_currency').val('');
    $('#vente_paiement').val('cash');
    $('#vente_remise').val('0');
    $('#vente_num').val('');
    $('#vente_obs').val('');
    $('#vente_prod').val('');
    $('#vente_qte').val('1');
    $('#vente_status').text('');
  }

  function saveSale(isFinal){
    const payload = buildSalePayload(); if(!payload) return;
    // Ensure types for nested lines
    payload.lignes = payload.lignes.map(function(l){ return {
      produit: parseInt(l.produit,10),
      designation: l.designation,
      quantite: parseInt(l.quantite,10),
      prixU_snapshot: l.prixU_snapshot,
      currency: l.currency ? parseInt(l.currency,10) : undefined
    };});
    // Create sale as draft
    $.ajax({ url:'/API/ventes/', method:'POST', contentType:'application/json', headers:{ 'X-CSRFToken': getCSRFToken() }, data: JSON.stringify(payload) })
      .done(function(resp){
        const id = resp.id; const num = resp.numero || id;
        function afterAll(){
          $('#vente_status').text('Vente enregistrée (#'+num+')'+(isFinal?' et finalisée':''))
            .removeClass('text-danger').addClass('text-success');
          clearSale();
          // refresh list and switch to list tab
          loadSalesList();
          $('a#liste-ventes-tab').tab('show');
        }
        if(isFinal && id){
          $.ajax({ url:'/API/ventes/'+id+'/complete/', method:'POST', headers:{ 'X-CSRFToken': getCSRFToken() } })
            .done(function(){ afterAll(); })
            .fail(function(xhr){
              console.warn('Complete sale error', xhr);
              // Still refresh and show list with draft status
              afterAll();
            });
        } else {
          afterAll();
        }
      })
      .fail(function(xhr){
        let msg = 'Bad Request';
        if(xhr.responseJSON){
          if(typeof xhr.responseJSON === 'string') msg = xhr.responseJSON;
          else if(xhr.responseJSON.detail) msg = xhr.responseJSON.detail;
          else msg = JSON.stringify(xhr.responseJSON);
        } else if(xhr.responseText){ msg = xhr.responseText; }
        $('#vente_status').text('Erreur: '+msg).removeClass('text-success').addClass('text-danger');
        console.warn('Vente POST error', xhr);
      });
  }

  function loadProduits(query){
    const $sel = $('#vente_prod');
    if(!$sel.length){ return; }
    const first = $sel.find('option').first().clone();
    $sel.empty().append(first);

    let url = API_PRODUITS + '?page_size=1000';
    const q = (query||'').trim();
    if(q){ url = API_PRODUITS + 'search/?q=' + encodeURIComponent(q); }

    $.ajax({ url: url, method: 'GET', dataType: 'json' })
      .done(function(data){
        const list = asList(data);
        list.forEach(function(p){
          PRODUCTS_CACHE[p.id] = p; // cache complet
        });
        fillSelect($sel, list, function(p){
          const text = (p.reference ? (p.reference + ' - ') : '') + (p.designation || ('Produit #' + p.id));
          return { value: p.id, text: text };
        });
        if(list.length === 1){ $sel.val(list[0].id); }
      })
      .fail(function(xhr){ dbg('loadProduits fail', xhr.status, xhr.responseText || xhr.statusText); });
  }

  let SALES_LIST = [];

  function getSelectedStatusFilter(){
    const v = ($('#ventes_filter').val()||'all');
    return v === 'draft' || v === 'completed' ? v : 'all';
  }

  function applySalesFilterAndRender(){
    const status = getSelectedStatusFilter();
    const rows = Array.isArray(SALES_LIST) ? SALES_LIST : [];
    const filtered = status==='all' ? rows : rows.filter(function(v){ return (v.statut||'') === status; });
    renderSalesList(filtered);
  }

  function renderSalesList(rows){
    const $tbody = $('#liste_ventes_body'); if(!$tbody.length) return;
    $tbody.empty();
    const list = asList(rows);
    if(!list.length){ $tbody.append('<tr><td colspan="7" class="text-center text-muted">Aucune vente</td></tr>'); return; }
    list.forEach(function(v){
      const tr = $('<tr>');
      tr.append('<td>'+(v.numero || v.id)+'</td>');
      tr.append('<td>'+(v.date_vente || '').toString().replace('T',' ').slice(0,16)+'</td>');
      tr.append('<td>'+(v.client_nom || '')+' '+(v.client_prenom || '')+'</td>');
      tr.append('<td>'+ (v.statut || '') +'</td>');
      tr.append('<td>'+ (v.type_paiement || '') +'</td>');
      tr.append('<td>'+ (typeof v.total_ttc!=="undefined" ? v.total_ttc : '') +'</td>');
      var actions = '';
      if((v.statut||'') === 'draft'){
        actions += '<button class="btn btn-sm btn-success finalize-sale" data-id="'+v.id+'"><i class="fa fa-check"></i> Finaliser</button>';
      }
      tr.append('<td>'+ (actions || '') +'</td>');
      $tbody.append(tr);
    });
  }

  function loadSalesList(){
    $.ajax({ url:'/API/ventes/?page_size=100', method:'GET', dataType:'json' })
      .done(function(data){ SALES_LIST = asList(data); applySalesFilterAndRender(); })
      .fail(function(xhr){ dbg('loadSalesList fail', xhr.status, xhr.responseText || xhr.statusText); });
  }

  function init(){
    // Detect presence of vente UI
    if(!document.getElementById('vente_client') && !document.getElementById('vente_prod')){
      return; // not on vente page
    }
    LINES = []; // reset
    loadClients();
    loadCurrencies();
    loadWarehouses();
    bindProduitFilters();
    renderLines();
    loadSalesList();

    // apply filter change
    $(document).off('change', '#ventes_filter').on('change', '#ventes_filter', function(){ applySalesFilterAndRender(); });

    // apply filter change
    $(document).off('change', '#ventes_filter').on('change', '#ventes_filter', function(){ applySalesFilterAndRender(); });

    // handle finalize click
    $(document).off('click', '.finalize-sale').on('click', '.finalize-sale', function(){
      var id = $(this).data('id');
      if(!id) return;
      if(!confirm('Finaliser cette vente ?')) return;
      var $btn = $(this); $btn.prop('disabled', true).addClass('disabled');
      $.ajax({ url:'/API/ventes/'+id+'/complete/', method:'POST', headers:{ 'X-CSRFToken': getCSRFToken() } })
        .done(function(){ loadSalesList(); })
        .fail(function(xhr){ alert('Erreur finalisation: '+ (xhr.responseText || xhr.statusText)); })
        .always(function(){ $btn.prop('disabled', false).removeClass('disabled'); });
    });

    // reload list when switching to the list tab
    $(document).off('shown.bs.tab', 'a#liste-ventes-tab').on('shown.bs.tab', 'a#liste-ventes-tab', function(){ loadSalesList(); });

    // bind add line
    $(document).off('click', '#vente_add_line').on('click', '#vente_add_line', function(e){ e.preventDefault(); addCurrentProductLine(); });
    // remove line
    $(document).off('click', '#vente_body [data-action="rm"]').on('click', '#vente_body [data-action="rm"]', function(){ var idx = parseInt($(this).data('idx'),10); removeLine(idx); });
    // recalc on remise change
    $(document).off('input', '#vente_remise').on('input', '#vente_remise', recalcTotals);
    // save draft
    $(document).off('click', '#vente_save_draft').on('click', '#vente_save_draft', function(e){ e.preventDefault(); saveSale(false); });
    // complete sale (same as draft for now due to API contract)
    $(document).off('click', '#vente_complete').on('click', '#vente_complete', function(e){ e.preventDefault(); saveSale(true); });
    // clear
    $(document).off('click', '#vente_clear').on('click', '#vente_clear', function(e){ e.preventDefault(); clearSale(); });
    // currency and rates buttons
    $(document).off('click', '#add_currency').on('click', '#add_currency', function(e){ e.preventDefault(); addCurrency(); });
    $(document).off('click', '#add_rate').on('click', '#add_rate', function(e){ e.preventDefault(); addRate(); });
    $(document).off('click', '#convert_btn').on('click', '#convert_btn', function(e){ e.preventDefault(); convertAmount(); });

    // when opening the Devises tab, refresh lists
    $('a[data-toggle="tab"][href="#devises"]').on('shown.bs.tab', function(){ loadCurrencies(); loadRates(); });
  }

  $(document).ready(init);
  document.addEventListener('fragment:loaded', function(e){ if(e && e.detail && e.detail.name==='vente'){ init(); } });
})(jQuery);
