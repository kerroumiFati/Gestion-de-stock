// Vente page behaviors: load clients, currencies, and products into selects
(function($){
  const DEBUG = true; function dbg(...a){ if(DEBUG) try{ console.log('[Vente]', ...a);}catch(e){} }
  const API_CLIENTS = '/API/clients/';
  const API_PRODUITS = '/API/produits/';
  const API_CURRENCIES = '/API/currencies/';
  const API_EXCHANGE_RATES = '/API/exchange-rates/';
  const API_WAREHOUSES = '/API/entrepots/';

  // Variable globale pour stocker le symbole de devise par défaut
  let DEFAULT_CURRENCY_SYMBOL = '€'; // Valeur par défaut si non configurée
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

  function loadSystemConfig(){
    return $.ajax({ url: '/API/system-config/', method: 'GET', dataType: 'json' })
      .done(function(cfg){
        dbg('loadSystemConfig success', cfg);
        // Mettre à jour le symbole de devise par défaut
        if(cfg && cfg.default_currency_details && cfg.default_currency_details.symbol){
          DEFAULT_CURRENCY_SYMBOL = cfg.default_currency_details.symbol;
          dbg('Devise par défaut:', cfg.default_currency_details.code, DEFAULT_CURRENCY_SYMBOL);
        }
        return cfg;
      })
      .fail(function(xhr){
        dbg('loadSystemConfig fail', xhr.status, xhr.responseText || xhr.statusText);
      });
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
    $('#vente_total_ht').text(total.toFixed(2)+' '+DEFAULT_CURRENCY_SYMBOL);
    $('#vente_remise_montant').text(remiseMontant.toFixed(2)+' '+DEFAULT_CURRENCY_SYMBOL);
    $('#vente_total_ttc').text(totalTTC.toFixed(2)+' '+DEFAULT_CURRENCY_SYMBOL);
  }

    /**
   * Get the best price for a product, checking for promotional prices first
   * @param {Object} product - The product object from cache
   * @returns {number} - The best available price
   */
  function getBestPrice(product){
    if(!product) return 0;
    
    // Check if product has prix_multiples (multiple prices)
    if(product.prix_multiples && Array.isArray(product.prix_multiples) && product.prix_multiples.length > 0){
      // Filter for active and valid promotional prices
      const promoPrices = product.prix_multiples.filter(function(pm){
        return pm.is_active && pm.is_valid && 
               (pm.type_prix_code === 'PROMO' || pm.type_prix_code === 'PROMOTION' ||
                (pm.type_prix_libelle && pm.type_prix_libelle.toLowerCase().includes('promo')));
      });
      
      // If promotional prices exist, use the lowest one
      if(promoPrices.length > 0){
        const lowestPromo = Math.min.apply(null, promoPrices.map(function(pp){ return Number(pp.prix || 0); }));
        dbg('Using promotional price:', lowestPromo, 'for product', product.designation);
        return lowestPromo;
      }
      
      // Otherwise, check for any active/valid price
      const activePrices = product.prix_multiples.filter(function(pm){
        return pm.is_active && pm.is_valid;
      });
      
      if(activePrices.length > 0){
        // Use the first active price (you could also use the lowest or a specific type)
        const activePrice = Number(activePrices[0].prix || 0);
        dbg('Using active price:', activePrice, 'for product', product.designation);
        return activePrice;
      }
    }
    
    // Fall back to default prixU
    dbg('Using default price (prixU):', product.prixU, 'for product', product.designation);
    return Number(product.prixU || 0);
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
      prixU_snapshot: getBestPrice(p),
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

    // Définir le statut selon le bouton cliqué
    if(isFinal){
      payload.statut = 'completed'; // Vente finalisée directement
    } else {
      payload.statut = 'draft'; // Vente en brouillon
    }

    // Créer la vente avec le statut approprié
    $.ajax({ url:'/API/ventes/', method:'POST', contentType:'application/json', headers:{ 'X-CSRFToken': getCSRFToken() }, data: JSON.stringify(payload) })
      .done(function(resp){
        const id = resp.id; const num = resp.numero || id;
        const statusText = isFinal ? 'finalisée' : 'enregistrée en brouillon';
        $('#vente_status').text('Vente '+statusText+' (#'+num+')')
          .removeClass('text-danger').addClass('text-success');
        clearSale();
        // refresh list and stats, then switch to list tab
        loadSalesList();
        loadStats();
        $('a#liste-ventes-tab').tab('show');
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
    const $table = $('#tbl_liste_ventes');

    // Destroy DataTable if it exists
    if($.fn.dataTable && $.fn.dataTable.isDataTable($table)){
      $table.DataTable().clear().destroy();
    }

    $tbody.empty();
    const list = asList(rows);
    if(!list.length){ $tbody.append('<tr><td colspan="7" class="text-center text-muted">Aucune vente</td></tr>'); }
    else {
      list.forEach(function(v){
        const tr = $('<tr>').css('cursor', 'pointer').addClass('sale-row');
        tr.attr('data-sale-id', v.id);
        tr.append('<td>'+(v.numero || v.id)+'</td>');
        tr.append('<td>'+(v.date_vente || '').toString().replace('T',' ').slice(0,16)+'</td>');
        tr.append('<td>'+(v.client_nom || '')+' '+(v.client_prenom || '')+'</td>');
        tr.append('<td>'+ (v.statut || '') +'</td>');
        tr.append('<td>'+ (v.type_paiement || '') +'</td>');
        tr.append('<td>'+ (typeof v.total_ttc!=="undefined" ? v.total_ttc : '') +'</td>');
        var actions = '';
        if((v.statut||'') === 'draft'){
          actions += '<button class="btn btn-sm btn-success finalize-sale" data-id="'+v.id+'"><i class="fa fa-check"></i> Finaliser</button> ';
        }
        actions += '<button class="btn btn-sm btn-info view-sale-details" data-id="'+v.id+'"><i class="fa fa-eye"></i> Détails</button>';
        tr.append('<td>'+ (actions || '') +'</td>');
        $tbody.append(tr);
      });
    }

    // Reinitialize DataTable
    if($.fn.DataTable){
      try {
        $table.DataTable({
          language: {
            "sProcessing": "Traitement en cours...",
            "sSearch": "Rechercher&nbsp;:",
            "sLengthMenu": "Afficher _MENU_ &eacute;l&eacute;ments",
            "sInfo": "Affichage de l'&eacute;l&eacute;ment _START_ &agrave; _END_ sur _TOTAL_ &eacute;l&eacute;ments",
            "sInfoEmpty": "Affichage de l'&eacute;l&eacute;ment 0 &agrave; 0 sur 0 &eacute;l&eacute;ment",
            "sInfoFiltered": "(filtr&eacute; de _MAX_ &eacute;l&eacute;ments au total)",
            "sInfoPostFix": "",
            "sLoadingRecords": "Chargement en cours...",
            "sZeroRecords": "Aucun &eacute;l&eacute;ment &agrave; afficher",
            "sEmptyTable": "Aucune donn&eacute;e disponible dans le tableau",
            "oPaginate": {
              "sFirst": "Premier",
              "sPrevious": "Pr&eacute;c&eacute;dent",
              "sNext": "Suivant",
              "sLast": "Dernier"
            },
            "oAria": {
              "sSortAscending": ": activer pour trier la colonne par ordre croissant",
              "sSortDescending": ": activer pour trier la colonne par ordre d&eacute;croissant"
            },
            "select": {
              "rows": {
                "_": "%d lignes s&eacute;lectionn&eacute;es",
                "0": "Aucune ligne s&eacute;lectionn&eacute;e",
                "1": "1 ligne s&eacute;lectionn&eacute;e"
              }
            }
          },
          order: [[1, 'desc']], // Sort by date (column 1) descending
          pageLength: 25
        });
      } catch(e) {
        dbg('DataTable init failed:', e);
      }
    }
  }

  function loadSalesList(){
    $.ajax({ url:'/API/ventes/?page_size=100', method:'GET', dataType:'json' })
      .done(function(data){ SALES_LIST = asList(data); applySalesFilterAndRender(); })
      .fail(function(xhr){ dbg('loadSalesList fail', xhr.status, xhr.responseText || xhr.statusText); });
  }

  function loadStats(){
    $.ajax({ url:'/API/ventes/stats/', method:'GET', dataType:'json' })
      .done(function(data){
        dbg('loadStats success', data);
        // Nombre de ventes
        $('#stat_ventes_today').text(data.ventes_aujourd_hui || 0);
        $('#stat_ventes_week').text(data.ventes_semaine || 0);
        $('#stat_ventes_month').text(data.ventes_mois || 0);
        $('#stat_ventes_total').text(data.total_ventes || 0);

        // Chiffre d'affaires
        const formatMoney = function(val){ return (val || 0).toFixed(2) + ' ' + DEFAULT_CURRENCY_SYMBOL; };
        $('#stat_ca_today').text(formatMoney(data.ca_aujourd_hui));
        $('#stat_ca_week').text(formatMoney(data.ca_semaine));
        $('#stat_ca_month').text(formatMoney(data.ca_mois));
        $('#stat_ca_total').text(formatMoney(data.ca_total));
      })
      .fail(function(xhr){
        dbg('loadStats fail', xhr.status, xhr.responseText || xhr.statusText);
        // Afficher des 0 en cas d'erreur
        $('.card-body h4[id^="stat_"]').text('N/A');
      });
  }

  function loadSaleDetails(saleId){
    return $.ajax({ url:'/API/ventes/'+saleId+'/', method:'GET', dataType:'json' });
  }

  function showSaleDetailsModal(saleId){
    // Ouvrir la modal
    $('#saleDetailsModal').modal('show');

    // Réinitialiser le contenu avec un loader
    $('#saleDetailsContent').html('<div class="text-center py-5"><i class="fa fa-spinner fa-spin fa-3x text-muted"></i><p class="mt-3 text-muted">Chargement des détails...</p></div>');

    // Charger les détails de la vente
    loadSaleDetails(saleId)
      .done(function(sale){
        renderSaleDetailsInModal(sale);
      })
      .fail(function(xhr){
        $('#saleDetailsContent').html('<div class="alert alert-danger m-3"><i class="fa fa-exclamation-triangle"></i> Erreur de chargement: '+(xhr.responseText || xhr.statusText)+'</div>');
      });
  }

  function renderSaleDetailsInModal(sale){
    const $container = $('#saleDetailsContent');
    if(!$container.length) return;

    // Mise à jour du titre de la modal
    $('#saleDetailsModalLabel').html('<i class="fa fa-file-invoice"></i> Détails de la vente #'+(sale.numero || sale.id));

    let html = '<div class="container-fluid">';

    // En-tête avec informations principales
    html += '<div class="row mb-4">';
    html += '<div class="col-md-6">';
    html += '<div class="card border-primary mb-3">';
    html += '<div class="card-header bg-primary text-white"><i class="fa fa-info-circle"></i> Informations générales</div>';
    html += '<div class="card-body">';
    html += '<p class="mb-2"><strong><i class="fa fa-calendar"></i> Date:</strong> '+(sale.date_vente || '').toString().replace('T',' ').slice(0,16)+'</p>';
    html += '<p class="mb-2"><strong><i class="fa fa-user"></i> Client:</strong> '+(sale.client_nom || '')+' '+(sale.client_prenom || '')+'</p>';
    html += '<p class="mb-2"><strong><i class="fa fa-tag"></i> Statut:</strong> <span class="badge badge-'+(sale.statut==='completed'?'success':'warning')+'">'+(sale.statut || '')+'</span></p>';
    html += '<p class="mb-2"><strong><i class="fa fa-credit-card"></i> Paiement:</strong> '+(sale.type_paiement || '')+'</p>';
    html += '<p class="mb-0"><strong><i class="fa fa-warehouse"></i> Entrepôt:</strong> '+(sale.warehouse_name || sale.warehouse || 'N/A')+'</p>';
    html += '</div></div>';
    html += '</div>';

    html += '<div class="col-md-6">';
    html += '<div class="card border-success mb-3">';
    html += '<div class="card-header bg-success text-white"><i class="fa fa-money-bill-wave"></i> Montants</div>';
    html += '<div class="card-body">';
    html += '<p class="mb-2"><strong>Total HT:</strong> <span class="float-right">'+(sale.total_ht || 0)+' '+(sale.currency_symbol || '€')+'</span></p>';
    if(sale.remise_percent > 0){
      html += '<p class="mb-2"><strong>Remise ('+(sale.remise_percent || 0)+'%):</strong> <span class="float-right text-danger">-'+((sale.total_ht || 0) * (sale.remise_percent || 0) / 100).toFixed(2)+' '+(sale.currency_symbol || '€')+'</span></p>';
    }
    html += '<hr class="my-2">';
    html += '<h5 class="mb-0"><strong>Total TTC:</strong> <span class="float-right text-success">'+(sale.total_ttc || 0)+' '+(sale.currency_symbol || '€')+'</span></h5>';
    html += '</div></div>';
    if(sale.observations){
      html += '<div class="alert alert-info mb-0"><strong><i class="fa fa-comment"></i> Observations:</strong><br>'+(sale.observations || '')+'</div>';
    }
    html += '</div>';
    html += '</div>';

    // Tableau des produits
    html += '<div class="row">';
    html += '<div class="col-12">';
    html += '<h5 class="mb-3"><i class="fa fa-boxes"></i> Produits <span class="badge badge-secondary">'+(sale.lignes ? sale.lignes.length : 0)+'</span></h5>';

    const lignes = sale.lignes || [];
    if(lignes.length === 0){
      html += '<div class="alert alert-warning"><i class="fa fa-exclamation-triangle"></i> Aucun produit dans cette vente</div>';
    } else {
      html += '<div class="table-responsive" style="max-height: 400px; overflow-y: auto;">';
      html += '<table class="table table-sm table-bordered table-hover mb-0">';
      html += '<thead class="thead-dark" style="position: sticky; top: 0; z-index: 1;">';
      html += '<tr><th style="width: 15%;">Référence</th><th style="width: 40%;">Désignation</th><th style="width: 15%;">Prix unitaire</th><th style="width: 10%;">Quantité</th><th style="width: 20%;">Total</th></tr>';
      html += '</thead>';
      html += '<tbody>';
      lignes.forEach(function(ligne){
        const ref = ligne.produit_reference || 'N/A';
        const desig = ligne.designation || 'N/A';
        const prix = parseFloat(ligne.prixU_snapshot || 0);
        const qty = parseInt(ligne.quantite || 0, 10);
        const total = prix * qty;
        const sym = ligne.currency_symbol || sale.currency_symbol || '€';
        html += '<tr>';
        html += '<td><code>'+ref+'</code></td>';
        html += '<td>'+desig+'</td>';
        html += '<td class="text-right">'+(isNaN(prix) ? '0.00' : prix.toFixed(2))+' '+sym+'</td>';
        html += '<td class="text-center"><span class="badge badge-primary">'+qty+'</span></td>';
        html += '<td class="text-right"><strong>'+(isNaN(total) ? '0.00' : total.toFixed(2))+' '+sym+'</strong></td>';
        html += '</tr>';
      });
      html += '</tbody>';
      html += '</table>';
      html += '</div>';
    }
    html += '</div>';
    html += '</div>';
    html += '</div>';

    $container.html(html);
  }

  function init(){
    // Detect presence of vente UI
    if(!document.getElementById('vente_client') && !document.getElementById('vente_prod')){
      return; // not on vente page
    }
    LINES = []; // reset

    // Charger la configuration système en premier pour obtenir la devise
    loadSystemConfig().always(function(){
      // Une fois la devise chargée (ou en cas d'erreur), charger le reste
      loadClients();
      loadCurrencies();
      loadWarehouses();
      bindProduitFilters();
      renderLines();
      loadSalesList();
      loadStats(); // Load initial stats
    });

    // apply filter change
    $(document).off('change', '#ventes_filter').on('change', '#ventes_filter', function(){ applySalesFilterAndRender(); });

    // handle finalize click
    $(document).off('click', '.finalize-sale').on('click', '.finalize-sale', function(e){
      e.stopPropagation(); // Empêcher le clic de se propager à la ligne
      var id = $(this).data('id');
      if(!id) return;
      if(!confirm('Finaliser cette vente ?')) return;
      var $btn = $(this); $btn.prop('disabled', true).addClass('disabled');
      $.ajax({ url:'/API/ventes/'+id+'/complete/', method:'POST', headers:{ 'X-CSRFToken': getCSRFToken() } })
        .done(function(){ loadSalesList(); loadStats(); })
        .fail(function(xhr){ alert('Erreur finalisation: '+ (xhr.responseText || xhr.statusText)); })
        .always(function(){ $btn.prop('disabled', false).removeClass('disabled'); });
    });

    // handle view details click
    $(document).off('click', '.view-sale-details').on('click', '.view-sale-details', function(e){
      e.stopPropagation(); // Empêcher le clic de se propager à la ligne
      var id = $(this).data('id');
      if(!id) return;
      showSaleDetailsModal(id);
    });

    // handle sale row click
    $(document).off('click', '.sale-row').on('click', '.sale-row', function(){
      var id = $(this).data('sale-id');
      if(!id) return;
      showSaleDetailsModal(id);
    });

    // handle print button
    $(document).off('click', '#printSaleDetails').on('click', '#printSaleDetails', function(){
      window.print();
    });

    // reload list when switching to the list tab
    $(document).off('shown.bs.tab', 'a#liste-ventes-tab').on('shown.bs.tab', 'a#liste-ventes-tab', function(){ loadSalesList(); });

    // reload stats when switching to stats tab
    $(document).off('shown.bs.tab', 'a#stats-ventes-tab').on('shown.bs.tab', 'a#stats-ventes-tab', function(){ loadStats(); });

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
