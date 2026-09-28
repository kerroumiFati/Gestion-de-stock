/**
 * carton_input.js — saisie et affichage des quantités en cartons.
 *
 * Principe : le stock et toutes les quantités échangées avec l'API restent en
 * UNITÉS. Ce composant ajoute, sous un input de quantité, une aide de saisie
 * « N cartons + M unités » qui recalcule l'input en unités (et inversement).
 * Le nombre d'unités par carton vient du conditionnement du produit
 * (champ `unites_par_carton` renvoyé par /API/produits/<id>/).
 *
 * Utilisation déclarative (aucun JS à écrire dans la page) :
 *   <input id="vente_qte" type="number" data-carton-product="#vente_prod">
 *     -> le produit est lu dans le <select> #vente_prod (valeur = id produit)
 *   <input ... data-carton-product-fn="maFonction">
 *     -> window.maFonction(input) renvoie un id produit OU un objet produit
 *        contenant `unites_par_carton` (ex. produits de /API/distribution/produits/)
 *   <input ... data-carton-product=".product-select" data-carton-scope="tr">
 *     -> le sélecteur est cherché dans l'ancêtre `tr` de l'input
 *
 * API programmatique :
 *   CartonInput.scan(root)                 attache les inputs non encore traités
 *   CartonInput.refresh(inputOrSelector)   re-lit le produit et recalcule l'aide
 *   CartonInput.prime(produits)            pré-remplit le cache (liste ou objet)
 *   CartonInput.getUnitsPerCarton(id)      Promise<int>
 *   CartonInput.format(qty, upc)           "3 ct + 2 u" ('' si upc <= 1)
 *   CartonInput.formatHtml(qty, upc)       <small> prêt à insérer sous une quantité
 */
(function(){
  'use strict';
  if(window.CartonInput){ return; }

  var API_PRODUITS = '/API/produits/';
  var cache = {};        // id produit -> unites_par_carton
  var pending = {};      // id produit -> Promise
  var ATTACHED = 'cartonInputAttached';

  // ---------- Styles (injectés une seule fois) ----------
  function injectStyles(){
    if(document.getElementById('carton-input-styles')) return;
    var css = ''
      + '.carton-helper{display:flex;flex-wrap:wrap;align-items:center;gap:4px;margin-top:6px;'
      + 'padding:6px 8px;border:1px dashed #cbd5e0;border-radius:6px;background:#f8fafc;'
      + 'font-size:.8rem;color:#4a5568;line-height:1.2}'
      + '.carton-helper[hidden]{display:none}'
      + '.carton-helper .carton-helper-icon{color:#718096;margin-right:2px}'
      + '.carton-helper input{width:58px;min-width:0;padding:3px 6px;font-size:.85rem;'
      + 'border:1px solid #cbd5e0;border-radius:4px;text-align:center;background:#fff}'
      + '.carton-helper input:focus{outline:none;border-color:#4a5568;box-shadow:0 0 0 2px rgba(74,85,104,.12)}'
      + '.carton-helper .carton-helper-upc{color:#718096;white-space:nowrap}'
      + '.carton-helper .carton-helper-total{margin-left:auto;font-weight:600;color:#2d3748;white-space:nowrap}'
      + '.carton-eq{display:block;font-size:.75rem;color:#718096;white-space:nowrap}'
      + '.carton-eq i{margin-right:3px}';
    var style = document.createElement('style');
    style.id = 'carton-input-styles';
    style.textContent = css;
    document.head.appendChild(style);
  }

  // ---------- Utilitaires ----------
  function toInt(v){ var n = parseInt(v, 10); return isFinite(n) ? n : 0; }

  function format(qty, upc){
    qty = toInt(qty); upc = toInt(upc);
    if(upc <= 1) return '';
    var sign = qty < 0 ? '-' : '';
    qty = Math.abs(qty);
    var ct = Math.floor(qty / upc), u = qty % upc;
    return sign + ct + ' ct' + (u ? ' + ' + u + ' u' : '');
  }

  function formatHtml(qty, upc){
    var txt = format(qty, upc);
    if(!txt) return '';
    return '<small class="carton-eq" title="1 carton = ' + toInt(upc) + ' unités"><i class="fas fa-box"></i>' + txt + '</small>';
  }

  function prime(list){
    if(!list) return;
    if(!Array.isArray(list)) list = [list];
    list.forEach(function(p){
      if(p && p.id != null && p.unites_par_carton != null){
        cache[p.id] = Math.max(1, toInt(p.unites_par_carton));
      }
    });
  }

  function getUnitsPerCarton(productId){
    productId = toInt(productId);
    if(!productId) return Promise.resolve(1);
    if(cache[productId] != null) return Promise.resolve(cache[productId]);
    if(pending[productId]) return pending[productId];
    pending[productId] = fetch(API_PRODUITS + productId + '/', {credentials: 'same-origin', headers: {'Accept': 'application/json'}})
      .then(function(r){ return r.ok ? r.json() : null; })
      .then(function(p){
        var upc = p && p.unites_par_carton ? Math.max(1, toInt(p.unites_par_carton)) : 1;
        cache[productId] = upc;
        delete pending[productId];
        return upc;
      })
      .catch(function(){ delete pending[productId]; return 1; });
    return pending[productId];
  }

  // Résout le produit courant d'un input : { id, upc } (upc peut être null si à charger)
  function resolveProduct(input){
    var fnName = input.getAttribute('data-carton-product-fn');
    if(fnName && typeof window[fnName] === 'function'){
      var res;
      try{ res = window[fnName](input); }catch(_){ res = null; }
      if(res && typeof res === 'object'){
        var upc = res.unites_par_carton != null ? Math.max(1, toInt(res.unites_par_carton)) : null;
        if(res.id != null && upc != null) cache[res.id] = upc;
        return {id: res.id != null ? toInt(res.id) : 0, upc: upc};
      }
      return {id: toInt(res), upc: null};
    }
    var sel = input.getAttribute('data-carton-product');
    if(!sel) return {id: 0, upc: null};
    var scopeSel = input.getAttribute('data-carton-scope');
    var scope = scopeSel ? (input.closest(scopeSel) || document) : document;
    var el = scope.querySelector(sel);
    if(!el) return {id: 0, upc: null};
    // Option avec data-upc / data-unites-par-carton (ex. select rempli avec des références)
    var opt = el.tagName === 'SELECT' ? el.options[el.selectedIndex] : null;
    if(opt && (opt.dataset.upc || opt.dataset.unitesParCarton)){
      return {id: toInt(el.value), upc: Math.max(1, toInt(opt.dataset.upc || opt.dataset.unitesParCarton))};
    }
    return {id: toInt(el.value), upc: null};
  }

  // ---------- Construction de l'aide sous l'input ----------
  function buildHelper(input){
    var helper = document.createElement('div');
    helper.className = 'carton-helper';
    helper.hidden = true;
    helper.innerHTML = ''
      + '<i class="fas fa-box carton-helper-icon" aria-hidden="true"></i>'
      + '<input type="number" min="0" step="1" class="carton-helper-ct" aria-label="Cartons" title="Cartons">'
      + '<span class="carton-helper-upc">ct × <b class="carton-helper-upc-val">1</b> u</span>'
      + '<span>+</span>'
      + '<input type="number" min="0" step="1" class="carton-helper-u" aria-label="Unités" title="Unités">'
      + '<span>u</span>'
      + '<span class="carton-helper-total"></span>';
    // Insérer juste après l'input (ou après son input-group si présent)
    var anchor = input.closest('.input-group') || input;
    anchor.insertAdjacentElement('afterend', helper);
    return helper;
  }

  function attach(input){
    if(!input || input.dataset[ATTACHED]) return;
    input.dataset[ATTACHED] = '1';
    injectStyles();

    var helper = buildHelper(input);
    var ctIn = helper.querySelector('.carton-helper-ct');
    var uIn = helper.querySelector('.carton-helper-u');
    var upcVal = helper.querySelector('.carton-helper-upc-val');
    var total = helper.querySelector('.carton-helper-total');
    var state = {upc: 1, productId: 0, syncing: false};

    function renderFromQty(){
      if(state.upc <= 1){ helper.hidden = true; return; }
      helper.hidden = false;
      var qty = toInt(input.value);
      var sign = qty < 0 ? -1 : 1;
      var a = Math.abs(qty);
      ctIn.value = sign * Math.floor(a / state.upc);
      uIn.value = a % state.upc;
      upcVal.textContent = state.upc;
      total.textContent = '= ' + qty + ' u';
    }

    function pushToQty(){
      var qty = toInt(ctIn.value) * state.upc + toInt(uIn.value);
      state.syncing = true;
      input.value = qty;
      total.textContent = '= ' + qty + ' u';
      // Prévenir les scripts de la page. Les handlers jQuery (directs ou délégués)
      // reçoivent aussi ces événements natifs : ne pas re-déclencher via jQuery,
      // sinon ils tourneraient deux fois.
      input.dispatchEvent(new Event('input', {bubbles: true}));
      input.dispatchEvent(new Event('change', {bubbles: true}));
      state.syncing = false;
    }

    function refresh(){
      var res = resolveProduct(input);
      state.productId = res.id;
      if(!res.id){ state.upc = 1; renderFromQty(); return; }
      if(res.upc != null){ state.upc = res.upc; renderFromQty(); return; }
      var wanted = res.id;
      getUnitsPerCarton(wanted).then(function(upc){
        if(state.productId !== wanted) return; // le produit a changé entre-temps
        state.upc = upc;
        renderFromQty();
      });
    }
    input._cartonRefresh = refresh;

    ctIn.addEventListener('input', pushToQty);
    uIn.addEventListener('input', function(){
      // Normaliser : 14 u pour 12/ct -> 1 ct + 2 u
      var u = toInt(uIn.value);
      if(u >= state.upc && state.upc > 1){
        ctIn.value = toInt(ctIn.value) + Math.floor(u / state.upc);
        uIn.value = u % state.upc;
      }
      pushToQty();
    });
    input.addEventListener('input', function(){ if(!state.syncing) renderFromQty(); });
    input.addEventListener('change', function(){ if(!state.syncing) renderFromQty(); });
    input.addEventListener('carton:refresh', refresh);

    // Suivre les changements de produit (jQuery pour Select2, natif sinon)
    var sel = input.getAttribute('data-carton-product');
    if(sel){
      var scopeSel = input.getAttribute('data-carton-scope');
      var scope = scopeSel ? (input.closest(scopeSel) || document) : document;
      var prodEl = scope.querySelector(sel);
      if(prodEl){
        if(window.jQuery){ window.jQuery(prodEl).on('change.cartonInput', refresh); }
        else { prodEl.addEventListener('change', refresh); }
      }
    }
    refresh();
  }

  function refreshTarget(target){
    if(typeof target === 'string') target = document.querySelector(target);
    if(target && typeof target._cartonRefresh === 'function') target._cartonRefresh();
  }

  function scan(root){
    root = root || document;
    if(!root.querySelectorAll) return;
    var nodes = root.querySelectorAll('input[data-carton-product], input[data-carton-product-fn]');
    for(var i = 0; i < nodes.length; i++){ attach(nodes[i]); }
  }

  // ---------- Auto-attachement ----------
  var scanTimer = null;
  function scheduleScan(){
    if(scanTimer) return;
    scanTimer = setTimeout(function(){ scanTimer = null; scan(document); }, 50);
  }
  function boot(){
    scan(document);
    try{
      var obs = new MutationObserver(function(muts){
        for(var i = 0; i < muts.length; i++){
          if(muts[i].addedNodes && muts[i].addedNodes.length){ scheduleScan(); return; }
        }
      });
      obs.observe(document.body, {childList: true, subtree: true});
    }catch(_){}
  }
  if(document.readyState !== 'loading') boot();
  else document.addEventListener('DOMContentLoaded', boot);
  document.addEventListener('fragment:loaded', scheduleScan);

  window.CartonInput = {
    scan: scan,
    attach: attach,
    refresh: refreshTarget,
    prime: prime,
    getUnitsPerCarton: getUnitsPerCarton,
    upcSync: function(productId){ var v = cache[toInt(productId)]; return v != null ? v : null; },
    format: format,
    formatHtml: formatHtml
  };
})();
