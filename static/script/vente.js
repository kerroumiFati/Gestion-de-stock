// Vente page behaviors: load clients, currencies, and products into selects
(function($){
  const DEBUG = true; function dbg(...a){ if(DEBUG) try{ console.log('[Vente]', ...a);}catch(e){} }
  const API_CLIENTS = '/API/clients/';
  const API_PRODUITS = '/API/produits/';
  const API_CURRENCIES = '/API/currencies/';
  const API_EXCHANGE_RATES = '/API/exchange-rates/';
  const API_WAREHOUSES = '/API/entrepots/';
  const API_TYPES_PRIX = '/API/types-prix/';
  const API_CODES_PRIX = '/API/codes-prix/';
  const API_PROMOTIONS = '/API/promotions/';

  // Variable globale pour stocker le symbole de devise par défaut
  let DEFAULT_CURRENCY_SYMBOL = 'DA'; // Valeur par défaut si non configurée
  // Variable globale pour stocker le CodePrix par défaut
  let DEFAULT_CODE_PRIX = null;
  // Variable globale pour stocker tous les clients avec reste à payer
  let allClientsReste = [];
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

  function refreshSelect2($sel){
    // Appeler la fonction globale d'initialisation Select2
    if(window.initVenteSelect2){
      var currentVal = $sel.val();
      window.initVenteSelect2('#' + $sel.attr('id'));
      if(currentVal) $sel.val(currentVal).trigger('change');
    }
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
        refreshSelect2($sel);
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
            if(exists){ $sel.val(String(dw)); refreshSelect2($sel); return; }
          }
          // Fallback: keep previous heuristic if no config or not found
          const defByCode = list.find(function(w){ return (w.code||'').toUpperCase().startsWith('DEF'); });
          if(defByCode){ $sel.val(defByCode.id); }
          refreshSelect2($sel);
        }).fail(function(){
          // If config not accessible, fallback to DEF* heuristic
          const defByCode = list.find(function(w){ return (w.code||'').toUpperCase().startsWith('DEF'); });
          if(defByCode){ $sel.val(defByCode.id); }
          refreshSelect2($sel);
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

  function loadTypesPrix(){
    $.ajax({ url: API_TYPES_PRIX + '?page_size=1000', method: 'GET', dataType: 'json' })
      .done(function(data){
        const list = asList(data);
        fillTypePrixSelect(list);
      })
      .fail(function(xhr){ dbg('loadTypesPrix fail', xhr.status, xhr.responseText || xhr.statusText); });
  }

  function loadCodesPrix(){
    return $.ajax({ url: API_CODES_PRIX + '?page_size=1000', method: 'GET', dataType: 'json' })
      .done(function(data){
        const list = asList(data);
        // Trouver le CodePrix par défaut (is_default=true)
        const defaultCode = list.find(function(c){ return c.is_default && c.is_active; });
        if(defaultCode){
          DEFAULT_CODE_PRIX = defaultCode;
          dbg('CodePrix par défaut chargé:', defaultCode.code, '(id:', defaultCode.id, ')');
        } else {
          // Fallback: prendre le premier actif
          const firstActive = list.find(function(c){ return c.is_active; });
          if(firstActive){
            DEFAULT_CODE_PRIX = firstActive;
            dbg('CodePrix fallback (premier actif):', firstActive.code);
          }
        }
      })
      .fail(function(xhr){ dbg('loadCodesPrix fail', xhr.status, xhr.responseText || xhr.statusText); });
  }

  function fillTypePrixSelect(list){
    const $sel = $('#vente_type_prix');
    if(!$sel.length) return;
    $sel.empty();
    // Ajouter les options
    list.forEach(function(t){
      if(t.is_active){
        const opt = $('<option>').val(t.id).text(t.libelle + ' (' + t.code + ')');
        // Définir DETAIL comme défaut
        if(t.code === 'DETAIL' || t.is_default){
          opt.prop('selected', true);
        }
        $sel.append(opt);
      }
    });
    // Si aucune option sélectionnée, sélectionner la première
    if($sel.find('option:selected').length === 0 && $sel.find('option').length > 0){
      $sel.find('option').first().prop('selected', true);
    }
    dbg('Types de prix chargés:', list.length);
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
        refreshSelect2($sel);
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

  // Cache des promotions applicables par produit
  const PROMOTIONS_CACHE = {};

  // Fonction pour charger les promotions applicables à un produit
  function loadPromotionsForProduct(produitId){
    const url = API_PROMOTIONS + 'applicables/?produit_id=' + produitId;
    dbg('Loading promotions from:', url);
    return $.ajax({
      url: url,
      method: 'GET',
      dataType: 'json'
    }).done(function(data){
      dbg('Promotions API response for product', produitId, ':', data);
      PROMOTIONS_CACHE[produitId] = asList(data);
      dbg('Promotions chargées pour produit', produitId, ':', PROMOTIONS_CACHE[produitId]);
      if(PROMOTIONS_CACHE[produitId].length === 0){
        dbg('WARNING: No promotions found for product', produitId);
      }
    }).fail(function(xhr){
      dbg('loadPromotionsForProduct FAILED for product', produitId, 'status:', xhr.status, 'response:', xhr.responseText);
      PROMOTIONS_CACHE[produitId] = [];
    });
  }

  // Fonction pour calculer le prix avec promotion
  function calculatePriceWithPromotion(produitId, quantite, prixOriginal){
    // Récupérer le type_prix sélectionné
    const typePrixId = parseInt($('#vente_type_prix').val() || '0', 10) || null;

    return $.ajax({
      url: API_PROMOTIONS + 'calculer_prix/',
      method: 'POST',
      contentType: 'application/json',
      headers: { 'X-CSRFToken': getCSRFToken() },
      data: JSON.stringify({
        produit_id: produitId,
        quantite: quantite,
        type_prix_id: typePrixId  // Envoyer le type de prix sélectionné
      }),
      dataType: 'json'
    });
  }

  // Afficher les promotions disponibles pour un produit sélectionné
  function displayAvailablePromotions(produitId){
    const $promoContainer = $('#promo_info');
    if(!$promoContainer.length) return;

    const promos = PROMOTIONS_CACHE[produitId] || [];
    if(promos.length === 0){
      $promoContainer.hide().empty();
      return;
    }

    let html = '<div class="alert alert-success mb-2 py-2"><small><i class="fa fa-tag"></i> <strong>Promotions disponibles:</strong><br>';
    promos.forEach(function(p){
      let desc = p.nom + ' (' + (p.type_promotion_display || p.type_promotion) + ')';
      if(p.valeur_pourcentage) desc += ' -' + p.valeur_pourcentage + '%';
      if(p.valeur_fixe) desc += ' -' + p.valeur_fixe + ' DA';
      if(p.prix_special) desc += ' Prix: ' + p.prix_special + ' DA';
      html += '<span class="badge badge-success mr-1">' + desc + '</span>';
    });
    html += '</small></div>';
    $promoContainer.html(html).show();
  }

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
        const price = Number(l.prixU_snapshot || p.prixU || 0) || 0;
        const qty = Number(l.quantite || 0) || 0;
        const total = price * qty;
        const sym = (p.currency_symbol || (p.currency && p.currency.symbol)) || 'DA';
        const prixOriginal = Number(l.prix_original || 0) || 0;
        const remisePromo = Number(l.remise_promo || 0) || 0;
        const tr = $('<tr>');
        tr.append('<td>'+ref+'</td>');

        // Désignation avec badge promo si applicable
        let designationHtml = designation;
        if(l.promotion_code){
          designationHtml += ' <span class="badge badge-success" title="'+(l.promotion_nom || '')+'"><i class="fa fa-tag"></i> '+l.promotion_code+'</span>';
          if(l.quantite_offerte > 0){
            designationHtml += ' <span class="badge badge-info">+'+l.quantite_offerte+' offert(s)</span>';
          }
        }
        tr.append('<td>'+designationHtml+'</td>');

        // Prix avec indication de promo
        let prixHtml = price.toFixed(2)+' '+sym;
        if(l.promotion && prixOriginal > 0 && prixOriginal > price){
          prixHtml = '<del class="text-muted">'+prixOriginal.toFixed(2)+'</del> <span class="text-success">'+price.toFixed(2)+'</span> '+sym;
        }
        tr.append('<td class="text-right">'+prixHtml+'</td>');

        tr.append('<td class="text-center">'+qty+'</td>');

        // Total avec économie
        let totalHtml = '<strong>'+(total.toFixed(2))+' '+sym+'</strong>';
        if(remisePromo > 0){
          totalHtml += '<br><small class="text-success">Économie: -'+remisePromo.toFixed(2)+' '+sym+'</small>';
        }
        tr.append('<td class="text-right">'+totalHtml+'</td>');

        tr.append('<td class="text-center"><button class="btn btn-sm btn-outline-danger" data-action="rm" data-idx="'+idx+'"><i class="fa fa-trash"></i></button></td>');
        $tbody.append(tr);
      });
    }
    // Mettre à jour le compteur de panier
    updateCartCount();
    recalcTotals();
  }

  function updateCartCount(){
    const count = LINES.length;
    const $badge = $('#cart_count');
    if($badge.length){
      $badge.text(count);
      // Animation visuelle lors du changement
      $badge.addClass('animate-pulse');
      setTimeout(function(){ $badge.removeClass('animate-pulse'); }, 500);
    }
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
   * Récupère le prix selon le CodePrix par défaut et le TypePrix sélectionné
   * Logique: CodePrix par défaut + TypePrix sélectionné → PrixProduit → fallback prixU
   * @param {Object} product - Le produit
   * @param {number} typePrixId - L'ID du type de prix (optionnel, sinon utilise le select)
   * @returns {number} - Le prix correspondant
   */
  function getBestPrice(product, typePrixId){
    if(!product) return 0;

    // Récupérer le type de prix sélectionné si non fourni
    if(!typePrixId){
      typePrixId = parseInt($('#vente_type_prix').val() || '0', 10);
    }

    // Check if product has prix_multiples (multiple prices)
    if(product.prix_multiples && Array.isArray(product.prix_multiples) && product.prix_multiples.length > 0){

      // 1. Chercher le prix pour CodePrix par défaut + TypePrix sélectionné
      if(DEFAULT_CODE_PRIX && typePrixId){
        const matchingPrice = product.prix_multiples.find(function(pm){
          return pm.is_active &&
                 pm.code_prix === DEFAULT_CODE_PRIX.id &&
                 pm.type_prix === typePrixId;
        });

        if(matchingPrice){
          dbg('Using price for code_prix', DEFAULT_CODE_PRIX.code, '+ type_prix', typePrixId, ':', matchingPrice.prix, 'for product', product.designation);
          return Number(matchingPrice.prix || 0);
        }
      }

      // 2. Chercher le prix pour CodePrix par défaut + n'importe quel TypePrix
      if(DEFAULT_CODE_PRIX){
        const priceForDefaultCode = product.prix_multiples.find(function(pm){
          return pm.is_active && pm.code_prix === DEFAULT_CODE_PRIX.id;
        });

        if(priceForDefaultCode){
          dbg('Using price for default code_prix', DEFAULT_CODE_PRIX.code, ':', priceForDefaultCode.prix, 'for product', product.designation);
          return Number(priceForDefaultCode.prix || 0);
        }
      }

      // 3. Chercher le prix pour TypePrix sélectionné (sans filtre CodePrix)
      if(typePrixId){
        const matchingTypePrice = product.prix_multiples.find(function(pm){
          return pm.is_active && pm.type_prix === typePrixId;
        });

        if(matchingTypePrice){
          dbg('Using price for type_prix', typePrixId, ':', matchingTypePrice.prix, 'for product', product.designation);
          return Number(matchingTypePrice.prix || 0);
        }
      }

      // 4. Chercher le prix DETAIL par défaut
      const detailPrice = product.prix_multiples.find(function(pm){
        return pm.is_active && pm.type_prix_code === 'DETAIL';
      });

      if(detailPrice){
        dbg('Using DETAIL price:', detailPrice.prix, 'for product', product.designation);
        return Number(detailPrice.prix || 0);
      }

      // 5. Prendre le premier prix actif
      const activePrice = product.prix_multiples.find(function(pm){
        return pm.is_active;
      });

      if(activePrice){
        dbg('Using first active price:', activePrice.prix, 'for product', product.designation);
        return Number(activePrice.prix || 0);
      }
    }

    // 6. Fall back to default prixU
    dbg('Using default price (prixU):', product.prixU, 'for product', product.designation);
    return Number(product.prixU || 0) || 0;
  }

  function addCurrentProductLine(){
    const prodId = parseInt($('#vente_prod').val()||'0', 10);
    const qty = parseInt($('#vente_qte').val()||'0', 10);
    if(!prodId){ alert('Veuillez choisir un produit'); return; }
    if(!qty || qty <= 0){ alert('Quantité invalide'); return; }
    const p = PRODUCTS_CACHE[prodId];
    if(!p){ alert('Produit introuvable en cache, réessayez.'); return; }

    // Vérifier si le produit existe déjà dans le panier
    const existingIndex = LINES.findIndex(function(l){ return l.produit === prodId; });

    if(existingIndex !== -1){
      // Produit déjà dans le panier - mettre à jour la quantité
      const existingLine = LINES[existingIndex];
      const newQty = existingLine.quantite + qty;
      const prixOriginal = Number(existingLine.prix_original || existingLine.prixU_snapshot || 0) || 0;

      // Recalculer la promotion avec la nouvelle quantité
      calculatePriceWithPromotion(prodId, newQty, prixOriginal)
        .done(function(result){
          dbg('Mise à jour quantité, résultat promo:', result);

          // S'assurer que les valeurs sont des nombres
          const prixTotalAvecPromo = Number(result.prix_total_avec_promo || 0) || (prixOriginal * newQty);
          const economieMontant = Number(result.economie_montant || 0) || 0;

          existingLine.quantite = newQty;
          existingLine.promotion = result.promotion ? result.promotion.id : null;
          existingLine.promotion_code = result.promotion ? result.promotion.code : null;
          existingLine.promotion_nom = result.promotion ? (result.promotion.nom || '') : null;
          existingLine.remise_promo = economieMontant;
          existingLine.quantite_offerte = result.quantite_offerte || 0;

          if(result.promotion && prixTotalAvecPromo > 0){
            existingLine.prixU_snapshot = prixTotalAvecPromo / newQty;
            existingLine.prix_avec_promo = prixTotalAvecPromo / newQty;
          } else {
            existingLine.prixU_snapshot = prixOriginal;
          }

          $('#vente_qte').val('1');
          $('#promo_info').hide().empty();
          renderLines();
        })
        .fail(function(){
          // En cas d'erreur, juste mettre à jour la quantité
          existingLine.quantite = newQty;
          $('#vente_qte').val('1');
          renderLines();
        });
    } else {
      // Nouveau produit - ajouter une nouvelle ligne
      const prixOriginal = getBestPrice(p) || 0;

      calculatePriceWithPromotion(prodId, qty, prixOriginal)
        .done(function(result){
          dbg('Résultat calcul promo:', result);

          // S'assurer que les valeurs sont des nombres
          const prixTotalAvecPromo = Number(result.prix_total_avec_promo || 0) || (prixOriginal * qty);
          const economieMontant = Number(result.economie_montant || 0) || 0;

          const line = {
            produit: prodId,
            designation: p.designation || '',
            quantite: qty,
            prixU_snapshot: prixOriginal,
            currency: p.currency || null,
            promotion: result.promotion ? result.promotion.id : null,
            promotion_code: result.promotion ? result.promotion.code : null,
            promotion_nom: result.promotion ? (result.promotion.nom || '') : null,
            prix_original: prixOriginal,
            prix_avec_promo: prixTotalAvecPromo / qty,
            remise_promo: economieMontant,
            quantite_offerte: result.quantite_offerte || 0
          };

          if(result.promotion && prixTotalAvecPromo > 0){
            line.prixU_snapshot = prixTotalAvecPromo / qty;
          }

          LINES.push(line);
          $('#vente_qte').val('1');
          $('#promo_info').hide().empty();
          renderLines();
        })
        .fail(function(){
          const line = {
            produit: prodId,
            designation: p.designation || '',
            quantite: qty,
            prixU_snapshot: prixOriginal,
            currency: p.currency || null
          };
          LINES.push(line);
          $('#vente_qte').val('1');
          renderLines();
        });
    }
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
      lignes: LINES.map(function(l){
        return {
          produit: l.produit,
          designation: l.designation,
          quantite: l.quantite,
          prixU_snapshot: l.prixU_snapshot,
          currency: l.currency || undefined,
          // Champs promotion
          promotion: l.promotion || undefined,
          prix_original: l.prix_original || undefined,
          remise_promo: l.remise_promo || 0,
          quantite_offerte: l.quantite_offerte || 0
        };
      })
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
    dbg('Creating sale with payload:', payload);
    $.ajax({ url:'/API/ventes/', method:'POST', contentType:'application/json', headers:{ 'X-CSRFToken': getCSRFToken() }, data: JSON.stringify(payload) })
      .done(function(resp){
        dbg('Sale created successfully:', resp);
        const id = resp.id; const num = resp.numero || id;
        const statusText = isFinal ? 'finalisée' : 'enregistrée en brouillon';
        $('#vente_status').text('Vente '+statusText+' (#'+num+')')
          .removeClass('text-danger').addClass('text-success');
        clearSale();
        // refresh list and stats, then switch to list tab
        dbg('Reloading sales list after creation...');
        loadSalesList();
        loadStats();
        $('a#liste-ventes-tab').tab('show');
      })
      .fail(function(xhr){
        dbg('Sale creation FAILED:', xhr.status, xhr.responseJSON || xhr.responseText);
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
    dbg('applySalesFilterAndRender: status filter =', status);
    const rows = Array.isArray(SALES_LIST) ? SALES_LIST : [];
    dbg('applySalesFilterAndRender: total rows =', rows.length);
    const filtered = status==='all' ? rows : rows.filter(function(v){ return (v.statut||'') === status; });
    dbg('applySalesFilterAndRender: filtered rows =', filtered.length);
    renderSalesList(filtered);
  }

  function renderSalesList(rows){
    dbg('renderSalesList called with rows:', rows);
    const $tbody = $('#liste_ventes_body');
    if(!$tbody.length){
      dbg('renderSalesList: tbody not found!');
      return;
    }
    const $table = $('#tbl_liste_ventes');

    // Destroy DataTable if it exists
    if($.fn.dataTable && $.fn.dataTable.isDataTable($table)){
      $table.DataTable().clear().destroy();
      dbg('renderSalesList: DataTable destroyed');
    }

    $tbody.empty();
    const list = asList(rows);
    dbg('renderSalesList: list length =', list.length);
    if(!list.length){
      dbg('renderSalesList: No sales to display');
      $tbody.append('<tr><td colspan="8" class="text-center text-muted">Aucune vente</td></tr>');
    }
    else {
      dbg('renderSalesList: Starting to render', list.length, 'rows');
      list.forEach(function(v, idx){
        try {
          const tr = $('<tr>').css('cursor', 'pointer').addClass('sale-row');
          const isMobile = v.source === 'mobile';
          tr.attr('data-sale-id', v.id);
          tr.attr('data-source', v.source || 'web');

          // Numéro avec badge source
          let numeroHtml = (v.numero || v.id);
          if(isMobile){
            numeroHtml += ' <span class="badge badge-info" title="Vente effectuée depuis l\'application mobile"><i class="fa fa-mobile"></i></span>';
          }
          tr.append('<td>'+numeroHtml+'</td>');
          tr.append('<td>'+(v.date_vente || '').toString().replace('T',' ').slice(0,16)+'</td>');
          tr.append('<td>'+(v.client_nom || '')+' '+(v.client_prenom || '')+'</td>');

          // Statut avec couleur
          let statutHtml = v.statut || '';
          if(v.statut === 'completed') statutHtml = '<span class="badge badge-success">Terminée</span>';
          else if(v.statut === 'draft') statutHtml = '<span class="badge badge-warning">Brouillon</span>';
          else if(v.statut === 'synced') statutHtml = '<span class="badge badge-info">Synchronisée</span>';
          else if(v.statut === 'canceled') statutHtml = '<span class="badge badge-danger">Annulée</span>';
          tr.append('<td>'+ statutHtml +'</td>');

          const totalTtc = parseFloat(v.total_ttc) || 0;
          const montantPaye = parseFloat(v.montant_paye) || 0;
          const reste = typeof v.reste_a_payer !== "undefined" ? parseFloat(v.reste_a_payer) : totalTtc;
          tr.append('<td>'+ totalTtc.toFixed(2) +' DA</td>');
          tr.append('<td>'+ montantPaye.toFixed(2) +' DA</td>');
          const resteClass = reste <= 0 ? 'text-success' : (reste < totalTtc ? 'text-warning' : 'text-danger');
          tr.append('<td class="'+resteClass+'"><strong>'+ reste.toFixed(2) +' DA</strong></td>');

          var actions = '';
          if(!isMobile){
            // Actions pour ventes web seulement
            if((v.statut||'') === 'draft'){
              actions += '<button class="btn btn-sm btn-success finalize-sale" data-id="'+v.id+'"><i class="fa fa-check"></i> Finaliser</button> ';
            }
            actions += '<button class="btn btn-sm btn-info view-sale-details" data-id="'+v.id+'"><i class="fa fa-eye"></i> Détails</button> ';
            if(reste > 0) {
              actions += '<button class="btn btn-sm btn-primary add-payment" data-id="'+v.id+'" data-reste="'+reste+'"><i class="fa fa-money"></i> Payer</button>';
            }
          } else {
            // Actions pour ventes mobiles
            actions += '<button class="btn btn-sm btn-info view-sale-details" data-id="'+v.id+'"><i class="fa fa-eye"></i> Détails</button> ';
            if(v.tournee){
              actions += '<span class="badge badge-secondary ml-1"><i class="fa fa-truck"></i> '+v.tournee+'</span> ';
            }
          }
          tr.append('<td>'+ (actions || '') +'</td>');
          $tbody.append(tr);
          if(idx === 0) dbg('renderSalesList: First row appended successfully');
        } catch(e) {
          dbg('renderSalesList: Error rendering row', idx, e);
        }
      });
      dbg('renderSalesList: Finished rendering. tbody children count:', $tbody.children().length);
    }

    // Only initialize DataTable if the tab is visible and table exists with proper structure
    const $tabPane = $table.closest('.tab-pane');
    const isTabVisible = $tabPane.length === 0 || ($tabPane.hasClass('active') && $tabPane.hasClass('show'));

    // Check if table has proper structure (thead exists)
    const hasProperStructure = $table.find('thead').length > 0;

    if($.fn.DataTable && isTabVisible && hasProperStructure){
      try {
        dbg('renderSalesList: Initializing DataTable (tab is visible)...');
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
        dbg('renderSalesList: DataTable initialized successfully');
      } catch(e) {
        dbg('DataTable init failed:', e);
      }
    } else if(!isTabVisible) {
      dbg('renderSalesList: Skipping DataTable init (tab not visible yet)');
    } else if(!hasProperStructure) {
      dbg('renderSalesList: Table missing proper structure (thead)');
    } else {
      dbg('renderSalesList: $.fn.DataTable not available!');
    }
  }

  function loadSalesList(){
    // Utiliser l'endpoint all_sales qui combine ventes web + mobiles
    $.ajax({ url:'/API/ventes/all_sales/', method:'GET', dataType:'json' })
      .done(function(data){
        dbg('loadSalesList data received:', data);
        SALES_LIST = asList(data);
        dbg('SALES_LIST after asList:', SALES_LIST, 'length:', SALES_LIST.length);
        applySalesFilterAndRender();
      })
      .fail(function(xhr){
        dbg('loadSalesList fail', xhr.status, xhr.responseText || xhr.statusText);
        // Fallback to regular endpoint if all_sales fails
        $.ajax({ url:'/API/ventes/?page_size=100', method:'GET', dataType:'json' })
          .done(function(data){
            dbg('loadSalesList fallback data received:', data);
            SALES_LIST = asList(data);
            applySalesFilterAndRender();
          })
          .fail(function(xhr2){ dbg('loadSalesList fallback also failed', xhr2.status); });
      });
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

    // Charger les clients avec reste à payer
    loadClientsAvecReste();
  }

  function loadClientsAvecReste(){
    const $tbody = $('#clients_reste_body');
    if(!$tbody.length) return;

    $.ajax({ url:'/API/ventes/clients_avec_reste/', method:'GET', dataType:'json' })
      .done(function(data){
        dbg('loadClientsAvecReste success', data);
        allClientsReste = data || []; // Stocker tous les clients
        renderClientsAvecReste(data);
      })
      .fail(function(xhr){
        dbg('loadClientsAvecReste fail', xhr.status, xhr.responseText || xhr.statusText);
        $tbody.html('<tr><td colspan="6" class="text-center text-danger py-4"><i class="fa fa-exclamation-triangle"></i> Erreur de chargement</td></tr>');
      });
  }

  function renderClientsAvecReste(clients){
    const $tbody = $('#clients_reste_body');
    if(!$tbody.length) return;

    $tbody.empty();

    if(!clients || clients.length === 0){
      $tbody.html('<tr><td colspan="6" class="text-center text-success py-4"><i class="fa fa-check-circle"></i> Aucun client avec reste à payer</td></tr>');
      $('#clients_reste_count').text('0');
      $('#total_ttc_global').text('0.00 ' + DEFAULT_CURRENCY_SYMBOL);
      $('#total_paye_global').text('0.00 ' + DEFAULT_CURRENCY_SYMBOL);
      $('#total_reste_global').text('0.00 ' + DEFAULT_CURRENCY_SYMBOL);
      return;
    }

    let totalTTC = 0;
    let totalPaye = 0;
    let totalReste = 0;

    clients.forEach(function(c){
      const nom = ((c.client_nom || '') + ' ' + (c.client_prenom || '')).trim() || 'Client #' + c.client_id;
      const tel = c.telephone || '-';
      const nbVentes = c.nombre_ventes || 0;
      const ttc = parseFloat(c.total_ttc) || 0;
      const paye = parseFloat(c.total_paye) || 0;
      const reste = parseFloat(c.reste_a_payer) || 0;

      totalTTC += ttc;
      totalPaye += paye;
      totalReste += reste;

      const tr = $('<tr>');
      tr.append('<td><strong>' + nom + '</strong></td>');
      tr.append('<td>' + tel + '</td>');
      tr.append('<td class="text-center"><span class="badge badge-secondary">' + nbVentes + '</span></td>');
      tr.append('<td class="text-right">' + ttc.toFixed(2) + ' ' + DEFAULT_CURRENCY_SYMBOL + '</td>');
      tr.append('<td class="text-right text-success">' + paye.toFixed(2) + ' ' + DEFAULT_CURRENCY_SYMBOL + '</td>');
      tr.append('<td class="text-right text-danger"><strong>' + reste.toFixed(2) + ' ' + DEFAULT_CURRENCY_SYMBOL + '</strong></td>');
      $tbody.append(tr);
    });

    // Mettre à jour le compteur et les totaux
    $('#clients_reste_count').text(clients.length);
    $('#total_ttc_global').text(totalTTC.toFixed(2) + ' ' + DEFAULT_CURRENCY_SYMBOL);
    $('#total_paye_global').text(totalPaye.toFixed(2) + ' ' + DEFAULT_CURRENCY_SYMBOL);
    $('#total_reste_global').text(totalReste.toFixed(2) + ' ' + DEFAULT_CURRENCY_SYMBOL);
  }

  function filterClientsReste(searchTerm){
    searchTerm = (searchTerm || '').toLowerCase().trim();

    if(!searchTerm){
      renderClientsAvecReste(allClientsReste);
      return;
    }

    const filtered = allClientsReste.filter(function(client){
      const nom = ((client.client_nom || '') + ' ' + (client.client_prenom || '')).toLowerCase();
      const tel = (client.telephone || '').toLowerCase();
      return nom.indexOf(searchTerm) !== -1 || tel.indexOf(searchTerm) !== -1;
    });

    renderClientsAvecReste(filtered);
  }

  function loadSaleDetails(saleId){
    // Vérifier si c'est une vente mobile
    if(String(saleId).startsWith('mobile_')){
      const mobileId = saleId.replace('mobile_', '');
      return $.ajax({ url:'/API/distribution/ventes/'+mobileId+'/', method:'GET', dataType:'json' });
    }
    return $.ajax({ url:'/API/ventes/'+saleId+'/', method:'GET', dataType:'json' });
  }

  function showSaleDetailsModal(saleId){
    // Ouvrir la modal
    $('#saleDetailsModal').modal('show');

    // Réinitialiser le contenu avec un loader
    $('#saleDetailsContent').html('<div class="text-center py-5"><i class="fa fa-spinner fa-spin fa-3x text-muted"></i><p class="mt-3 text-muted">Chargement des détails...</p></div>');

    // Vérifier si c'est une vente mobile
    const isMobile = String(saleId).startsWith('mobile_');

    // Charger les détails de la vente
    loadSaleDetails(saleId)
      .done(function(sale){
        if(isMobile){
          renderMobileSaleDetailsInModal(sale);
        } else {
          renderSaleDetailsInModal(sale);
        }
      })
      .fail(function(xhr){
        $('#saleDetailsContent').html('<div class="alert alert-danger m-3"><i class="fa fa-exclamation-triangle"></i> Erreur de chargement: '+(xhr.responseText || xhr.statusText)+'</div>');
      });
  }

  function renderMobileSaleDetailsInModal(sale){
    const $container = $('#saleDetailsContent');
    if(!$container.length) return;

    // Mise à jour du titre de la modal
    $('#saleDetailsModalLabel').html('<i class="fa fa-mobile"></i> Vente Mobile #'+(sale.numero_vente || sale.id));

    let html = '<div class="container-fluid">';

    // Badge source mobile
    html += '<div class="alert alert-info mb-3"><i class="fa fa-mobile"></i> <strong>Vente effectuée depuis l\'application mobile</strong></div>';

    // En-tête avec informations principales
    html += '<div class="row mb-4">';
    html += '<div class="col-md-6">';
    html += '<div class="card border-primary mb-3">';
    html += '<div class="card-header bg-primary text-white"><i class="fa fa-info-circle"></i> Informations générales</div>';
    html += '<div class="card-body">';
    html += '<p class="mb-2"><strong><i class="fa fa-calendar"></i> Date:</strong> '+(sale.date_vente || '').toString().replace('T',' ').slice(0,16)+'</p>';
    html += '<p class="mb-2"><strong><i class="fa fa-user"></i> Client:</strong> '+(sale.client_nom || '')+'</p>';
    if(sale.tournee){
      html += '<p class="mb-2"><strong><i class="fa fa-truck"></i> Tournée:</strong> '+(sale.tournee_numero || sale.tournee)+'</p>';
    }
    const statutVente = sale.est_synchronise ? 'Synchronisée' : 'En attente';
    html += '<p class="mb-2"><strong><i class="fa fa-sync"></i> Statut:</strong> <span class="badge badge-'+(sale.est_synchronise?'success':'warning')+'">'+statutVente+'</span></p>';
    html += '<p class="mb-0"><strong><i class="fa fa-credit-card"></i> Paiement:</strong> '+(sale.type_paiement || '')+'</p>';
    html += '</div></div>';
    html += '</div>';

    html += '<div class="col-md-6">';
    html += '<div class="card border-success mb-3">';
    html += '<div class="card-header bg-success text-white"><i class="fa fa-money-bill-wave"></i> Montants</div>';
    html += '<div class="card-body">';
    html += '<p class="mb-2"><strong>Montant HT:</strong> <span class="float-right">'+(sale.montant_ht || 0)+' DA</span></p>';
    html += '<p class="mb-2"><strong>TVA:</strong> <span class="float-right">'+(sale.montant_tva || 0)+' DA</span></p>';
    html += '<hr class="my-2">';
    html += '<h5 class="mb-0"><strong>Total TTC:</strong> <span class="float-right text-success">'+(sale.montant_total || 0)+' DA</span></h5>';
    html += '</div></div>';

    // Section Paiement
    const totalTtc = parseFloat(sale.montant_total) || 0;
    const montantPaye = parseFloat(sale.montant_paye) || 0;
    const resteAPayer = totalTtc - montantPaye;
    const isPaye = resteAPayer <= 0;

    let statutPaiement = isPaye ? 'PAYÉ' : 'NON PAYÉ';
    let badgeClass = isPaye ? 'success' : 'danger';

    html += '<div class="card border-'+badgeClass+' mb-3">';
    html += '<div class="card-header bg-'+badgeClass+' text-white"><i class="fa fa-wallet"></i> État du paiement</div>';
    html += '<div class="card-body">';
    html += '<p class="mb-2"><strong>Montant payé:</strong> <span class="float-right text-success">'+(montantPaye.toFixed(2))+' DA</span></p>';
    if(sale.montant_rendu > 0){
      html += '<p class="mb-2"><strong>Monnaie rendue:</strong> <span class="float-right">'+(sale.montant_rendu || 0)+' DA</span></p>';
    }
    html += '<hr class="my-2">';
    html += '<p class="mb-0"><strong>Statut:</strong> <span class="badge badge-'+badgeClass+'">'+statutPaiement+'</span></p>';
    html += '</div></div>';

    if(sale.notes){
      html += '<div class="alert alert-secondary mb-0"><strong><i class="fa fa-comment"></i> Notes:</strong><br>'+(sale.notes || '')+'</div>';
    }
    html += '</div>';
    html += '</div>';

    // Tableau des produits
    html += '<div class="row">';
    html += '<div class="col-12">';
    html += '<h5 class="mb-3"><i class="fa fa-boxes"></i> Produits</h5>';

    const lignes = sale.lignes || [];
    if(lignes.length === 0){
      html += '<div class="alert alert-warning"><i class="fa fa-exclamation-triangle"></i> Aucun produit dans cette vente</div>';
    } else {
      html += '<div class="table-responsive">';
      html += '<table class="table table-sm table-bordered table-hover mb-0">';
      html += '<thead class="thead-dark">';
      html += '<tr><th>Produit</th><th>Prix unitaire</th><th>Quantité</th><th>Total</th></tr>';
      html += '</thead>';
      html += '<tbody>';
      lignes.forEach(function(ligne){
        const desig = ligne.produit_designation || ligne.designation || 'Produit';
        const prix = parseFloat(ligne.prix_unitaire || 0);
        const qty = parseInt(ligne.quantite || 0, 10);
        const total = parseFloat(ligne.montant_total || prix * qty);

        html += '<tr>';
        html += '<td>'+desig+'</td>';
        html += '<td class="text-right">'+(prix.toFixed(2))+' DA</td>';
        html += '<td class="text-center"><span class="badge badge-primary">'+qty+'</span></td>';
        html += '<td class="text-right"><strong>'+(total.toFixed(2))+' DA</strong></td>';
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
    const statutVente = sale.statut === 'completed' ? 'Finalisée' : (sale.statut === 'draft' ? 'Brouillon' : sale.statut);
    html += '<p class="mb-2"><strong><i class="fa fa-file-alt"></i> Statut de la vente:</strong> <span class="badge badge-'+(sale.statut==='completed'?'success':'warning')+'">'+statutVente+'</span></p>';
    html += '<p class="mb-2"><strong><i class="fa fa-credit-card"></i> Mode de paiement:</strong> '+(sale.type_paiement_display || sale.type_paiement || '')+'</p>';
    html += '<p class="mb-0"><strong><i class="fa fa-warehouse"></i> Entrepôt:</strong> '+(sale.warehouse_name || sale.warehouse || 'N/A')+'</p>';
    html += '</div></div>';
    html += '</div>';

    html += '<div class="col-md-6">';
    html += '<div class="card border-success mb-3">';
    html += '<div class="card-header bg-success text-white"><i class="fa fa-money-bill-wave"></i> Montants</div>';
    html += '<div class="card-body">';
    html += '<p class="mb-2"><strong>Total HT:</strong> <span class="float-right">'+(sale.total_ht || 0)+' '+(sale.currency_symbol || 'DA')+'</span></p>';
    if(sale.remise_percent > 0){
      html += '<p class="mb-2"><strong>Remise ('+(sale.remise_percent || 0)+'%):</strong> <span class="float-right text-danger">-'+((sale.total_ht || 0) * (sale.remise_percent || 0) / 100).toFixed(2)+' '+(sale.currency_symbol || 'DA')+'</span></p>';
    }
    html += '<hr class="my-2">';
    html += '<h5 class="mb-0"><strong>Total TTC:</strong> <span class="float-right text-success">'+(sale.total_ttc || 0)+' '+(sale.currency_symbol || 'DA')+'</span></h5>';
    html += '</div></div>';

    // Section Paiement
    const totalTtc = parseFloat(sale.total_ttc) || 0;
    const montantPaye = parseFloat(sale.montant_paye) || 0;
    // Si reste_a_payer n'est pas défini, calculer : total - payé
    const resteAPayer = (typeof sale.reste_a_payer !== 'undefined') ? parseFloat(sale.reste_a_payer) : (totalTtc - montantPaye);
    const isPaye = resteAPayer <= 0;
    const isPartiel = montantPaye > 0 && resteAPayer > 0;

    // Déterminer le statut et les couleurs
    let statutPaiement = 'NON PAYÉ';
    let badgeClass = 'danger';
    let borderClass = 'danger';
    if(isPaye) {
      statutPaiement = 'PAYÉ';
      badgeClass = 'success';
      borderClass = 'success';
    } else if(isPartiel) {
      statutPaiement = 'PARTIELLEMENT PAYÉ';
      badgeClass = 'warning';
      borderClass = 'warning';
    }

    html += '<div class="card border-'+borderClass+' mb-3">';
    html += '<div class="card-header bg-'+borderClass+' text-white"><i class="fa fa-wallet"></i> État du paiement</div>';
    html += '<div class="card-body">';
    html += '<p class="mb-2"><strong>Montant payé:</strong> <span class="float-right text-success">'+(montantPaye.toFixed(2))+' '+(sale.currency_symbol || 'DA')+'</span></p>';
    html += '<p class="mb-2"><strong>Reste à payer:</strong> <span class="float-right '+(isPaye ? 'text-success' : 'text-danger')+'"><strong>'+(resteAPayer.toFixed(2))+' '+(sale.currency_symbol || 'DA')+'</strong></span></p>';
    html += '<hr class="my-2">';
    html += '<p class="mb-0"><strong>Statut paiement:</strong> <span class="badge badge-'+badgeClass+'">'+statutPaiement+'</span></p>';
    if(!isPaye) {
      html += '<button class="btn btn-primary btn-block mt-3 add-payment" data-id="'+sale.id+'" data-reste="'+resteAPayer+'"><i class="fa fa-money"></i> Ajouter un paiement</button>';
    }
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
        let desig = ligne.designation || 'N/A';
        const prix = parseFloat(ligne.prixU_snapshot || 0);
        const qty = parseInt(ligne.quantite || 0, 10);
        const total = prix * qty;
        const sym = ligne.currency_symbol || sale.currency_symbol || 'DA';

        // Ajouter badge promotion si applicable
        if(ligne.promotion_code || ligne.promotion){
          desig += ' <span class="badge badge-success"><i class="fa fa-tag"></i> '+(ligne.promotion_code || 'Promo')+'</span>';
          if(ligne.quantite_offerte > 0){
            desig += ' <span class="badge badge-info">+'+ligne.quantite_offerte+' offert(s)</span>';
          }
        }

        // Prix avec indication de promo
        let prixHtml = (isNaN(prix) ? '0.00' : prix.toFixed(2))+' '+sym;
        const prixOriginal = parseFloat(ligne.prix_original || 0);
        if(ligne.promotion && prixOriginal > 0 && prixOriginal > prix){
          prixHtml = '<del class="text-muted">'+(prixOriginal.toFixed(2))+'</del> <span class="text-success">'+(prix.toFixed(2))+'</span> '+sym;
        }

        // Total avec économie
        let totalHtml = '<strong>'+(isNaN(total) ? '0.00' : total.toFixed(2))+' '+sym+'</strong>';
        const remisePromo = parseFloat(ligne.remise_promo || 0);
        if(remisePromo > 0){
          totalHtml += '<br><small class="text-success">Économie: -'+remisePromo.toFixed(2)+' '+sym+'</small>';
        }

        html += '<tr>';
        html += '<td><code>'+ref+'</code></td>';
        html += '<td>'+desig+'</td>';
        html += '<td class="text-right">'+prixHtml+'</td>';
        html += '<td class="text-center"><span class="badge badge-primary">'+qty+'</span></td>';
        html += '<td class="text-right">'+totalHtml+'</td>';
        html += '</tr>';
      });
      html += '</tbody>';
      html += '</table>';
      html += '</div>';
    }
    html += '</div>';
    html += '</div>';

    // Section Historique des paiements
    const paiements = sale.paiements || [];
    if(paiements.length > 0) {
      html += '<div class="row mt-4">';
      html += '<div class="col-12">';
      html += '<h5 class="mb-3"><i class="fa fa-history"></i> Historique des paiements <span class="badge badge-info">'+paiements.length+'</span></h5>';
      html += '<div class="table-responsive">';
      html += '<table class="table table-sm table-bordered table-hover">';
      html += '<thead class="thead-light">';
      html += '<tr><th>Date</th><th>Montant</th><th>Moyen</th><th>Référence</th><th>Notes</th><th>Par</th></tr>';
      html += '</thead>';
      html += '<tbody>';
      paiements.forEach(function(p){
        const date = (p.date_paiement || '').toString().replace('T',' ').slice(0,16);
        const montant = parseFloat(p.montant || 0).toFixed(2);
        const moyen = p.moyen_paiement_display || p.moyen_paiement || '';
        const ref = p.reference || '-';
        const notes = p.notes || '-';
        const user = p.created_by_username || 'N/A';
        html += '<tr>';
        html += '<td><small>'+date+'</small></td>';
        html += '<td class="text-right"><strong class="text-success">'+montant+' '+(sale.currency_symbol || 'DA')+'</strong></td>';
        html += '<td>'+moyen+'</td>';
        html += '<td><small>'+ref+'</small></td>';
        html += '<td><small>'+notes+'</small></td>';
        html += '<td><small>'+user+'</small></td>';
        html += '</tr>';
      });
      html += '</tbody>';
      html += '</table>';
      html += '</div>';
      html += '</div>';
      html += '</div>';
    }

    html += '</div>';

    $container.html(html);
  }

  // ==================== GESTION DES PAIEMENTS ====================
  function openAddPaymentModal(venteId, reste) {
    // Récupérer les informations de la vente
    const vente = SALES_LIST.find(v => v.id == venteId);
    if(!vente) {
      alert('Vente introuvable');
      return;
    }

    $('#payment_vente_id').val(venteId);
    $('#payment_vente_numero').val(vente.numero || venteId);
    $('#payment_reste').val(reste.toFixed(2) + ' DA');
    $('#payment_montant').val(reste.toFixed(2));
    $('#payment_moyen').val('cash');
    $('#payment_reference').val('');
    $('#payment_notes').val('');

    $('#addPaymentModal').modal('show');
  }

  function savePayment() {
    const venteId = $('#payment_vente_id').val();
    const montant = parseFloat($('#payment_montant').val());
    const moyen = $('#payment_moyen').val();
    const reference = $('#payment_reference').val();
    const notes = $('#payment_notes').val();

    if(!montant || montant <= 0) {
      alert('Veuillez saisir un montant valide');
      return;
    }

    const data = {
      vente: venteId,
      montant: montant,
      moyen_paiement: moyen,
      reference: reference,
      notes: notes
    };

    $.ajax({
      url: '/API/paiements-vente/',
      method: 'POST',
      contentType: 'application/json',
      headers: { 'X-CSRFToken': getCSRFToken() },
      data: JSON.stringify(data),
      dataType: 'json'
    }).done(function(response){
      dbg('[Payment] Saved:', response);
      $('#addPaymentModal').modal('hide');
      alert('Paiement enregistré avec succès!');
      loadSalesList(); // Rafraîchir la liste

      // Si la modal de détails est ouverte, la rafraîchir aussi
      if($('#saleDetailsModal').hasClass('show')) {
        showSaleDetailsModal(venteId);
      }
    }).fail(function(xhr){
      dbg('[Payment] Save failed:', xhr.status, xhr.responseText);
      alert('Erreur lors de l\'enregistrement du paiement: ' + (xhr.responseJSON?.detail || xhr.statusText));
    });
  }

  // Fonction pour afficher l'horloge en temps réel
  function updateClock(){
    const now = new Date();

    // Format de la date: JJ/MM/AAAA
    const day = String(now.getDate()).padStart(2, '0');
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const year = now.getFullYear();
    const dateStr = day + '/' + month + '/' + year;

    // Format de l'heure: HH:MM:SS
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    const timeStr = hours + ':' + minutes + ':' + seconds;

    // Mettre à jour les éléments
    const $date = $('#current_date');
    const $time = $('#current_time');
    if($date.length) $date.text(dateStr);
    if($time.length) $time.text(timeStr);
  }

  function startClock(){
    // Mettre à jour immédiatement
    updateClock();
    // Mettre à jour toutes les secondes
    setInterval(updateClock, 1000);
  }

  function init(){
    // Detect presence of vente UI
    if(!document.getElementById('vente_client') && !document.getElementById('vente_prod')){
      return; // not on vente page
    }
    LINES = []; // reset

    // Démarrer l'horloge
    startClock();

    // Charger la configuration système en premier pour obtenir la devise
    loadSystemConfig().always(function(){
      // Charger le CodePrix par défaut EN PREMIER (nécessaire pour la résolution des prix)
      loadCodesPrix().always(function(){
        // Une fois le CodePrix chargé, charger le reste
        loadClients();
        loadCurrencies();
        loadTypesPrix();
        loadWarehouses();
        bindProduitFilters(); // Ceci charge les produits
        renderLines();
        // Ne pas charger loadSalesList ici, seulement quand l'onglet est visible
        // loadStats() ne pose pas de problème car il n'initialise pas de DataTable
        loadStats(); // Load initial stats
        dbg('Initialisation terminée. DEFAULT_CODE_PRIX:', DEFAULT_CODE_PRIX);
      });
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

    // Charger les promotions quand un produit est sélectionné
    $(document).off('change', '#vente_prod').on('change', '#vente_prod', function(){
      const prodId = parseInt($(this).val() || '0', 10);
      if(prodId > 0){
        loadPromotionsForProduct(prodId).done(function(){
          displayAvailablePromotions(prodId);
        });
      } else {
        $('#promo_info').hide().empty();
      }
    });
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

    // payment buttons
    $(document).off('click', '.add-payment').on('click', '.add-payment', function(e){
      e.stopPropagation();
      const venteId = $(this).data('id');
      const reste = parseFloat($(this).data('reste'));
      openAddPaymentModal(venteId, reste);
    });
    $(document).off('click', '#savePaymentBtn').on('click', '#savePaymentBtn', function(e){ e.preventDefault(); savePayment(); });

    // Écouteur pour le champ de recherche des clients avec reste à payer
    $(document).off('input', '#search_clients_reste').on('input', '#search_clients_reste', function(){
      filterClientsReste($(this).val());
    });

    // when opening the Devises tab, refresh lists
    $('a[data-toggle="tab"][href="#devises"]').on('shown.bs.tab', function(){ loadCurrencies(); loadRates(); });
  }

  $(document).ready(init);
  document.addEventListener('fragment:loaded', function(e){ if(e && e.detail && e.detail.name==='vente'){ init(); } });
})(jQuery);
