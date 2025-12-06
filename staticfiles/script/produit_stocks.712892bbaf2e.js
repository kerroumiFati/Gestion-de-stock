(function(){
  const apiBase = '/API';
  const $ = window.jQuery;
  let PRODUCTS = []; // cached product list
  let PRODUCT_MAP = {}; // id -> product

  function getCookie(name){
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  }
  function ajaxJSON(opts){
    const csrftoken = getCookie('csrftoken');
    opts.headers = opts.headers || {};
    if (csrftoken) opts.headers['X-CSRFToken'] = csrftoken;
    opts.contentType = opts.contentType || 'application/json';
    return $.ajax(opts);
  }

  function loadProducts(){
    // Load first page for dropdown, we'll lazy-fetch any missing products as needed
    return $.get(apiBase + '/produits/').then(function(items){
      const list = Array.isArray(items) ? items : (items && items.results ? items.results : []);
      PRODUCTS = list;
      PRODUCT_MAP = {};
      list.forEach(function(p){ PRODUCT_MAP[String(p.id)] = p; });
      const opts = ['<option value="">Sélectionner un produit</option>'];
      list.forEach(p => opts.push(`<option value="${p.id}">${p.reference || ''} - ${p.designation || ''}</option>`));
      $('#ps_prod').html(opts.join(''));
    });
  }

  function ensureProductInMap(prodId){
    const key = String(prodId);
    if(PRODUCT_MAP[key]) return $.Deferred().resolve(PRODUCT_MAP[key]).promise();
    return $.get(apiBase + '/produits/' + prodId + '/').then(function(p){
      PRODUCT_MAP[key] = p; return p;
    }).catch(function(){ return null; });
  }

  function loadWarehouses(){
    return $.get(apiBase + '/entrepots/').then(function(items){
      const list = Array.isArray(items) ? items : (items && items.results ? items.results : []);
      return list;
    });
  }

  function renderTotals(rows){
    // When filtering by product, compute value; else show only total qty rows count
    const prodId = $('#ps_prod').val();
    const whId = $('#ps_wh').val();
    let sumQty = 0;
    rows.forEach(function(r){
      if(whId && String(r.warehouse) !== String(whId)) return;
      sumQty += parseFloat(r.quantity || 0);
    });
    const fmt = (v) => (isFinite(v) ? Number(v).toFixed(2) : '-');
    if(prodId){
      const p = PRODUCT_MAP[String(prodId)] || {};
      const unit = parseFloat(p.prixU || p.prixu || 0) || 0;
      const total = unit * sumQty;
      $('#ps_totals').text('Produit sélectionné | Prix unitaire: ' + fmt(unit) + ' | Quantité totale: ' + fmt(sumQty) + ' | Valeur totale: ' + fmt(total));
    } else {
      $('#ps_totals').text('Quantité totale (toutes lignes affichées): ' + fmt(sumQty));
    }
  }

  function loadStocks(){
    const prod = $('#ps_prod').val();
    const whSelected = $('#ps_wh').val();
    const params = {};
    if (prod) params.produit = prod;
    if (whSelected) params.warehouse = whSelected;
    return $.get(apiBase + '/stocks/', params).then(function(rows){
      rows = Array.isArray(rows) ? rows : (rows && rows.results ? rows.results : []);
      return loadWarehouses().then(function(warehouses){
        const whMap = {}; warehouses.forEach(function(w){ whMap[String(w.id)] = w; });
        const tbody = $('#tstock tbody');
        tbody.empty();
        if (prod){
          const p = PRODUCT_MAP[String(prod)] || {};
          const unit = parseFloat(p.prixU || p.prixu || 0) || 0;
          const byWh = {}; rows.forEach(function(r){ byWh[String(r.warehouse)] = r; });
          warehouses.forEach(function(w){
            if (whSelected && String(whSelected) !== String(w.id)) return;
            const existing = byWh[String(w.id)];
            const qty = existing ? (parseFloat(existing.quantity || 0) || 0) : 0;

            // Ne pas afficher les lignes avec quantité 0
            if (qty <= 0) return;

            const value = isFinite(unit*qty) ? (unit*qty).toFixed(2) : '-';
            const tr = $('<tr>');
            const prodLabel = (p.reference || '') + ' - ' + (p.designation || '');
            tr.append($('<td>').text(prodLabel));
            tr.append($('<td>').text(`${w.code || ''} - ${w.name || ''}`));
            tr.append($('<td>').text(qty));
            tr.append($('<td>').text(value));
            const input = $('<input type="number" class="form-control form-control-sm" />').val(qty);
            tr.append($('<td>').append(input));
            const btn = $('<button type="button" class="btn btn-sm btn-outline-secondary">Edit</button>');
            btn.on('click', function(e){
              e.preventDefault();
              e.stopPropagation();
              const newQty = parseInt(input.val()||'0', 10);
              const payload = JSON.stringify({ produit: parseInt(prod,10), warehouse: w.id, quantity: newQty });
              if (existing){
                ajaxJSON({ url: apiBase + '/stocks/' + existing.id + '/', method:'PATCH', data: JSON.stringify({quantity:newQty}) })
                  .then(function(){ loadStocks(); })
                  .catch(function(xhr){ alert((xhr.responseJSON && (xhr.responseJSON.detail || xhr.responseJSON.error)) || 'Erreur mise à jour'); });
              } else {
                ajaxJSON({ url: apiBase + '/stocks/', method:'POST', data: payload })
                  .then(function(){ loadStocks(); })
                  .catch(function(xhr){ alert((xhr.responseJSON && (xhr.responseJSON.detail || xhr.responseJSON.error)) || 'Erreur création'); });
              }
            });
            tr.append($('<td>').append(btn));
            tbody.append(tr);
          });
        } else {
          // No product filter: show existing rows from API as-is
          rows.forEach(function(r){
            const qty = parseFloat(r.quantity || 0) || 0;

            // Ne pas afficher les lignes avec quantité 0
            if (qty <= 0) return;

            const w = whMap[String(r.warehouse)] || {};
            const p = PRODUCT_MAP[String(r.produit)] || {};
            const unit = parseFloat(p.prixU || p.prixu || 0) || 0;
            const value = isFinite(unit*qty) ? (unit*qty).toFixed(2) : '-';
            const tr = $('<tr>');
            const prodLabel = (p.reference || '') + ' - ' + (p.designation || '');
            tr.append($('<td>').text(prodLabel));
            tr.append($('<td>').text(`${w.code || ''} - ${w.name || ''}`));
            tr.append($('<td>').text(qty));
            tr.append($('<td>').text(value));
            const input = $('<input type="number" class="form-control form-control-sm" />').val(qty);
            tr.append($('<td>').append(input));
            const btn = $('<button type="button" class="btn btn-sm btn-outline-secondary">Edit</button>');
            btn.on('click', function(e){
              e.preventDefault();
              e.stopPropagation();
              const newQty = parseInt(input.val()||'0', 10);
              ajaxJSON({ url: apiBase + '/stocks/' + r.id + '/', method:'PATCH', data: JSON.stringify({quantity:newQty}) })
                .then(function(){ loadStocks(); })
                .catch(function(xhr){ alert((xhr.responseJSON && (xhr.responseJSON.detail || xhr.responseJSON.error)) || 'Erreur mise à jour'); });
            });
            tr.append($('<td>').append(btn));
            tbody.append(tr);
          });
        }
        renderTotals(rows);
      });
    });
  }

  function populateWarehouseSelect(){
    return loadWarehouses().then(function(warehouses){
      const opts = ['<option value="">Tous les entrepôts</option>'];
      warehouses.forEach(function(w){ opts.push(`<option value="${w.id}">${w.code || ''} - ${w.name || ''}</option>`); });
      $('#ps_wh').html(opts.join(''));
    });
  }

  function init(){
    if (!$('#tstock').length) return;
    $.when(loadProducts(), populateWarehouseSelect()).then(loadStocks);
    $(document).off('click', '#ps_refresh').on('click', '#ps_refresh', function(e){ e.preventDefault(); loadStocks(); });
    $('#ps_prod').on('change', loadStocks);
    $(document).on('change', '#ps_wh', loadStocks);
    // Load everything by default (no filters)
    setTimeout(loadStocks, 0);
  }

  $(document).ready(init);
})();