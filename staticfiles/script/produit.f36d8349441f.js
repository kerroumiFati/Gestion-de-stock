/* Rovo Dev: Gestion Produits - inclut Prix U - v2024.11.24 */
(function(){
  if(window.__rovodev_produit_loaded){ return; }
  window.__rovodev_produit_loaded = true;
  let __rovodev_inited = false;
  const apiBase = '/API';
  const api = {
    produits: '/API/produits/',
    categories: '/API/categories/'
  };
  let __cacheProduits = [];
  let __cacheTypesPrix = [];
  let __cachePrixProduits = [];

  const el = sel => document.querySelector(sel);
  function toFixed2(n){
    const v = Number(n||0);
    return isFinite(v) ? v.toFixed(2) : '0.00';
  }

  function asList(data){
    if(Array.isArray(data)) return data;
    if(data && Array.isArray(data.results)) return data.results;
    if(data && typeof data === 'object') return Object.values(data);
    return [];
  }

  function getCookie(name){
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
  }

  async function fetchJSON(url, opts){
    const options = Object.assign({
      credentials: 'same-origin',
      headers: {}
    }, opts||{});
    options.headers = Object.assign({}, options.headers);
    const method = (options.method||'GET').toUpperCase();
    if(method !== 'GET' && method !== 'HEAD' && method !== 'OPTIONS'){
      const csrftoken = getCookie('csrftoken');
      if(csrftoken){ options.headers['X-CSRFToken'] = csrftoken; }
      options.headers['X-Requested-With'] = 'XMLHttpRequest';
      if(!options.headers['Content-Type']){
        options.headers['Content-Type'] = 'application/json';
      }
    }
    const res = await fetch(url, options);
    const text = await res.text();
    let data = null;
    try{ data = text? JSON.parse(text): null; }catch(_){ data = text; }
    if(!res.ok){
      const err = new Error('HTTP '+res.status);
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  }

  async function loadCategories(){
    try{
      console.log('[Produit] Chargement des catégories...');
      const data = await fetchJSON(api.categories);
      const sel = el('#categorie');
      if(!sel){
        console.warn('[Produit] Element #categorie non trouvé');
        return;
      }
      // Filtrer les catégories actives uniquement
      const activeCategories = Array.isArray(data) ? data.filter(c => c.is_active !== false) : data;
      console.log(`[Produit] ${activeCategories.length} catégories actives chargées`);
      sel.innerHTML = '<option value="">Sélectionner une catégorie</option>' +
        activeCategories.map(c=>`<option value="${c.id}">${c.nom}</option>`).join('');
    }catch(e){
      console.error('[Produit] Erreur chargement catégories:', e);
      showAlert('Erreur de chargement des catégories', 'warning');
    }
  }


  async function loadProduits(){
    try{
      const data = await fetchJSON(api.produits);
      __cacheProduits = Array.isArray(data) ? data : [];
      console.log('[Produit] loadProduits: nombre produits:', __cacheProduits.length);
      renderProduitsWithPrices();
    }catch(e){ console.warn('produits load failed', e); }
  }

  function renderProduitsWithPrices(){
    const tbody = el('#tproduit tbody#table-content') || el('#tproduit tbody');
    console.log('[Produit] renderProduitsWithPrices: tbody trouvé?', !!tbody);
    if(!tbody){
      console.warn('[Produit] tbody #table-content introuvable!');
      return;
    }

    const selectedPriceType = $('#display_price_type').val();
    console.log('[Produit] Type de prix sélectionné:', selectedPriceType);

    tbody.innerHTML = __cacheProduits.map(p=>{
      let prixDisplay = p.prixU;
      let priceLabel = '';

      // Si un type de prix est sélectionné, chercher le prix correspondant
      if(selectedPriceType){
        const prixMultiple = __cachePrixProduits.find(pm =>
          String(pm.produit) === String(p.id) &&
          String(pm.type_prix) === String(selectedPriceType) &&
          pm.is_active
        );
        if(prixMultiple){
          prixDisplay = prixMultiple.prix;
          priceLabel = `<small class="text-muted">(${prixMultiple.type_prix_code})</small>`;
        } else {
          priceLabel = `<small class="text-muted">(défaut)</small>`;
        }
      }

      return `<tr data-id="${p.id}">
        <td>${p.id}</td>
        <td>${p.reference||''}</td>
        <td>${p.code_barre||''}</td>
        <td>${p.designation||''}</td>
        <td>${p.categorie_nom||''}</td>
        <td>${prixDisplay!=null? toFixed2(prixDisplay): ''} ${p.currency_symbol||''} ${priceLabel}</td>
        <td class="text-center">
          <button class="btn btn-sm action-btn-product btn-edit act-edit" title="Modifier">
            <i class="fas fa-edit"></i> Modifier
          </button>
          <button class="btn btn-sm action-btn-product btn-delete act-del ml-1" title="Supprimer">
            <i class="fas fa-trash"></i> Supprimer
          </button>
        </td>
      </tr>`;
    }).join('');
  }

  function collectForm(){
    const id = el('#id') && el('#id').value ? Number(el('#id').value) : null;
    const payload = {
      reference: el('#reference')?.value?.trim(),
      code_barre: el('#code_barre')?.value?.trim(),
      designation: el('#designation')?.value?.trim(),
      categorie: el('#categorie')?.value ? Number(el('#categorie').value) : null,
      prixU: el('#prixU')?.value ? Number(el('#prixU').value) : 0,
    };
    return {id, payload};
  }

  async function createOrUpdate(){
    const {id, payload} = collectForm();
    // Validation stricte: vérifier que les champs ne sont pas vides/null/undefined
    if(!payload.reference || !payload.designation || payload.categorie == null || !payload.code_barre){
      showAlert('Veuillez remplir les champs obligatoires (référence, code-barres, désignation, catégorie)', 'warning');
      return;
    }
    // Vérification unicité côté client pour éviter une erreur 400 inutile
    // Exclure le produit en cours de modification lors de la vérification
    const refExists = __cacheProduits.some(p => p.id !== id && (p.reference||'').toLowerCase() === (payload.reference||'').toLowerCase());
    const cbExists = __cacheProduits.some(p => p.id !== id && (p.code_barre||'').toLowerCase() === (payload.code_barre||'').toLowerCase());
    if(refExists || cbExists){
      const fields = [refExists? 'référence':'' , cbExists? 'code-barres':'' ].filter(Boolean).join(' et ');
      showAlert('Un produit avec la même ' + fields + ' existe déjà. Merci de choisir une autre valeur.', 'warning');
      return;
    }
    try{
      const opts = {
        method: id? 'PUT':'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      };
      const url = id? api.produits + id + '/' : api.produits;
      await fetchJSON(url, opts);
      showAlert(id? 'Produit mis à jour avec succès' : 'Produit créé avec succès', 'success');
      clearForm();
      await loadProduits();
    }catch(e){
      console.error('save produit failed', e);

      // Afficher le message d'erreur exact du serveur
      let errorMsg = 'Erreur lors de l\'enregistrement du produit';

      if(e.data && typeof e.data === 'object'){
        // Extraire les messages d'erreur du serveur
        const errors = [];
        for(const [field, messages] of Object.entries(e.data)){
          if(Array.isArray(messages)){
            errors.push(`${field}: ${messages.join(', ')}`);
          } else {
            errors.push(`${field}: ${messages}`);
          }
        }
        if(errors.length > 0){
          errorMsg = errors.join(' | ');
        }
      } else if(e.data && typeof e.data === 'string'){
        errorMsg = e.data;
      }

      showAlert(errorMsg, 'danger');
    }
  }

  function clearForm(){
    ['#id','#reference','#code_barre','#designation','#prixU'].forEach(s=>{ const n=el(s); if(n) n.value=''; });
    if(el('#categorie')) el('#categorie').value='';
  }

  function showAlert(msg, level){
    const box = el('#product-alerts');
    if(!box) return;
    const alertClass = level === 'success' ? 'alert-success' : level === 'warning' ? 'alert-warning' : level === 'danger' ? 'alert-danger' : 'alert-info';
    const icon = level === 'success' ? 'check-circle' : level === 'warning' ? 'exclamation-triangle' : level === 'danger' ? 'times-circle' : 'info-circle';
    box.innerHTML = `<div class="alert ${alertClass} alert-dismissible fade show" role="alert">
      <i class="fa fa-${icon}"></i> ${msg}
      <button type="button" class="close" data-dismiss="alert" aria-label="Close">
        <span aria-hidden="true">&times;</span>
      </button>
    </div>`;
    setTimeout(()=>{ box.innerHTML=''; }, 5000);
  }

  function bindTableActions(){
    const table = el('#tproduit');
    if(!table) return;
    table.addEventListener('click', async (e)=>{
      const tr = e.target.closest('tr');
      if(!tr) return;
      const id = Number(tr.getAttribute('data-id'));
      if(e.target.classList.contains('act-del')){
        if(!confirm('Supprimer ce produit ?')) return;
        try{
          await fetchJSON(api.produits + id + '/', { method:'DELETE' });
          showAlert('Produit supprimé', 'success');
          await loadProduits();
        }catch(err){ showAlert('Suppression échouée', 'danger'); }
      }else if(e.target.classList.contains('act-edit')){
        try{
          const p = await fetchJSON(api.produits + id + '/');
          if(el('#id')) el('#id').value = p.id;
          if(el('#reference')) el('#reference').value = p.reference||'';
          if(el('#code_barre')) el('#code_barre').value = p.code_barre||'';
          if(el('#designation')) el('#designation').value = p.designation||'';
          if(el('#categorie')) el('#categorie').value = p.categorie||'';
          if(el('#prixU')) el('#prixU').value = p.prixU!=null? Number(p.prixU): '';
        }catch(err){ showAlert('Chargement produit échoué', 'danger'); }
      }
    });
  }

  function init(){
    if(__rovodev_inited){
      console.log('[Produit] Déjà initialisé, skip');
      return; // avoid re-entry
    }
    if(!el('#tproduit')){
      console.log('[Produit] Table #tproduit non trouvée, attente...');
      return; // not on this page yet
    }
    console.log('[Produit] Initialisation...');
    __rovodev_inited = true;

    // Charger les données en parallèle
    Promise.all([
      loadCategories(),
      loadProduits()
    ]).then(() => {
      console.log('[Produit] Toutes les données chargées avec succès');
      // Remplir les selects de prix maintenant que les produits sont chargés
      fillPrixProduitsSelects();
    }).catch(err => {
      console.error('[Produit] Erreur lors du chargement initial:', err);
    });

    // Charger les prix multiples
    loadTypesPrix();
    loadPrixProduits();
    loadAllPrixProduits();

    bindTableActions();
    const btn = el('#btn');
    if(btn){ btn.addEventListener('click', createOrUpdate); }

    // Event handler pour changer le type de prix affiché
    $(document).off('change', '#display_price_type').on('change', '#display_price_type', function(){
      console.log('[Produit] Changement de type de prix affiché');
      renderProduitsWithPrices();
    });

    // Event handlers pour la gestion des prix multiples
    console.log('[Produit] Attachement des event handlers pour prix multiples');
    $(document).off('click', '#btn_add_type_prix').on('click', '#btn_add_type_prix', function(e){
      e.preventDefault();
      console.log('[Produit] Bouton type prix cliqué');
      addTypePrix();
    });
    $(document).off('click', '[data-action="delete-type-prix"]').on('click', '[data-action="delete-type-prix"]', function(e){
      e.preventDefault();
      deleteTypePrix($(this).data('id'));
    });
    $(document).off('click', '[data-action="toggle-default"]').on('click', '[data-action="toggle-default"]', function(e){
      e.preventDefault();
      setDefaultTypePrix($(this).data('id'));
    });
    $(document).off('click', '#btn_add_prix_prod').on('click', '#btn_add_prix_prod', function(e){
      e.preventDefault();
      addPrixProduit();
    });
    $(document).off('click', '[data-action="delete-prix-prod"]').on('click', '[data-action="delete-prix-prod"]', function(e){
      e.preventDefault();
      deletePrixProduit($(this).data('id'));
    });
    $(document).off('change', '#prix_prod_filter').on('change', '#prix_prod_filter', function(){
      loadPrixProduits();
    });

    // Bouton Check - vérifier les produits avec stock faible
    const btnRisk = el('#btnrisk');
    if(btnRisk){
      btnRisk.addEventListener('click', async () => {
        const riskValue = el('#risk')?.value ? Number(el('#risk').value) : 0;
        if(riskValue <= 0){
          showAlert('Veuillez entrer un seuil de risque valide', 'warning');
          return;
        }

        // Filtrer les produits dont le stock est inférieur au seuil
        const lowStockProducts = __cacheProduits.filter(p => (p.stock || 0) <= riskValue);

        if(lowStockProducts.length === 0){
          showAlert(`Aucun produit avec stock ≤ ${riskValue}`, 'info');
        } else {
          showAlert(`${lowStockProducts.length} produit(s) avec stock ≤ ${riskValue}`, 'warning');
        }
      });
    }

    // Bouton Refresh - recharger les données
    const btnRef = el('#btnref');
    if(btnRef){
      btnRef.addEventListener('click', async () => {
        showAlert('Actualisation des données...', 'info');
        await loadProduits();
        showAlert('Données actualisées avec succès', 'success');
      });
    }
  }

  /******************************************
   * GESTION DES PRIX MULTIPLES
   ******************************************/

  // Fonction helper pour CSRF Token
  function getCSRFToken(){
    const cookieValue = document.cookie
      .split('; ')
      .find(row => row.startsWith('csrftoken='));
    return cookieValue ? cookieValue.split('=')[1] : '';
  }

  // Types de Prix
  function loadTypesPrix(){
    $.ajax({ url: apiBase + '/types-prix/?page_size=1000', method: 'GET', dataType: 'json' })
      .done(function(data){
        const list = asList(data);
        __cacheTypesPrix = list;
        renderTypesPrix(list);
        fillTypesPrixSelects(list);
        fillDisplayPriceTypeSelect(list);
      })
      .fail(function(xhr){ console.warn('Erreur chargement types prix', xhr); });
  }

  function fillDisplayPriceTypeSelect(list){
    const $sel = $('#display_price_type');
    if(!$sel.length) return;

    const opts = ['<option value="">Prix de base (prixU)</option>'];
    list.forEach(function(t){
      if(t.is_active){
        opts.push('<option value="'+t.id+'">'+t.libelle+' ('+t.code+')</option>');
      }
    });
    $sel.html(opts.join(''));
  }

  function loadAllPrixProduits(){
    $.ajax({ url: apiBase + '/prix-produits/?page_size=10000', method: 'GET', dataType: 'json' })
      .done(function(data){
        __cachePrixProduits = asList(data);
        console.log('[Produit] Prix produits chargés:', __cachePrixProduits.length);
        // Recharger l'affichage des produits avec les prix
        renderProduitsWithPrices();
      })
      .fail(function(xhr){ console.warn('Erreur chargement prix produits', xhr); });
  }

  function renderTypesPrix(list){
    const $tbody = $('#types_prix_body');
    if(!$tbody.length) return;
    $tbody.empty();
    if(!list || !list.length){
      $tbody.append('<tr><td colspan="7" class="text-center text-muted">Aucun type de prix défini</td></tr>');
      return;
    }
    list.forEach(function(t){
      const tr = $('<tr>');
      tr.append('<td><strong>'+t.code+'</strong></td>');
      tr.append('<td>'+t.libelle+'</td>');
      tr.append('<td>'+t.ordre+'</td>');
      tr.append('<td>'+(t.is_default ? '<span class="badge badge-success">Oui</span>' : 'Non')+'</td>');
      tr.append('<td>'+(t.is_active ? '<span class="badge badge-success">Actif</span>' : '<span class="badge badge-secondary">Inactif</span>')+'</td>');
      tr.append('<td><span class="badge badge-primary">'+(t.nombre_prix || 0)+'</span></td>');
      const actions = '<button type="button" class="btn btn-sm btn-edit" data-action="toggle-default" data-id="'+t.id+'">Définir par défaut</button> ' +
                     '<button type="button" class="btn btn-sm btn-delete" data-action="delete-type-prix" data-id="'+t.id+'">Supprimer</button>';
      tr.append('<td>'+actions+'</td>');
      $tbody.append(tr);
    });
  }

  function fillTypesPrixSelects(list){
    const $sel = $('#prix_prod_type');
    if(!$sel.length) return;
    const first = $sel.find('option').first().clone();
    $sel.empty().append(first);
    list.forEach(function(t){
      if(t.is_active){
        $('<option>').val(t.id).text(t.libelle + ' (' + t.code + ')').appendTo($sel);
      }
    });
  }

  function addTypePrix(){
    console.log('[Produit] addTypePrix appelé');
    const code = ($('#type_prix_code').val() || '').trim().toUpperCase();
    const libelle = ($('#type_prix_libelle').val() || '').trim();
    const ordre = parseInt($('#type_prix_ordre').val() || '0', 10);

    console.log('[Produit] Données:', { code, libelle, ordre });

    if(!code){ alert('Code requis'); return; }
    if(!libelle){ alert('Libellé requis'); return; }

    const data = { code, libelle, ordre };

    $.ajax({ url: apiBase + '/types-prix/', method: 'POST', contentType: 'application/json',
             headers: { 'X-CSRFToken': getCSRFToken() }, data: JSON.stringify(data) })
      .done(function(resp){
        console.log('[Produit] Type prix ajouté:', resp);
        $('#type_prix_code').val('');
        $('#type_prix_libelle').val('');
        $('#type_prix_ordre').val('0');
        loadTypesPrix(); // Recharge les types et met à jour le select d'affichage
        showAlert('Type de prix ajouté avec succès', 'success');
      })
      .fail(function(xhr){
        console.error('[Produit] Erreur ajout type prix:', xhr);
        const msg = (xhr.responseJSON && (xhr.responseJSON.detail || xhr.responseJSON.error)) || 'Erreur ajout type prix';
        showAlert(msg, 'danger');
      });
  }

  function deleteTypePrix(id){
    if(!confirm('Supprimer ce type de prix ? Les prix associés seront également supprimés.')) return;
    $.ajax({ url: apiBase + '/types-prix/' + id + '/', method: 'DELETE', headers: { 'X-CSRFToken': getCSRFToken() } })
      .done(function(){
        loadTypesPrix();
        loadPrixProduits();
        showAlert('Type de prix supprimé', 'success');
      })
      .fail(function(xhr){
        const msg = (xhr.responseJSON && (xhr.responseJSON.detail || xhr.responseJSON.error)) || 'Erreur suppression';
        showAlert(msg, 'danger');
      });
  }

  function setDefaultTypePrix(id){
    $.ajax({ url: apiBase + '/types-prix/' + id + '/', method: 'PATCH', contentType: 'application/json',
             headers: { 'X-CSRFToken': getCSRFToken() }, data: JSON.stringify({ is_default: true }) })
      .done(function(){
        loadTypesPrix();
        showAlert('Type de prix défini par défaut', 'success');
      })
      .fail(function(xhr){
        const msg = (xhr.responseJSON && (xhr.responseJSON.detail || xhr.responseJSON.error)) || 'Erreur mise à jour';
        showAlert(msg, 'danger');
      });
  }

  // Prix Produits
  function loadPrixProduits(produitFilter){
    const params = {};
    const filter = produitFilter || $('#prix_prod_filter').val();
    if(filter) params.produit = filter;

    $.ajax({ url: apiBase + '/prix-produits/', method: 'GET', dataType: 'json', data: params })
      .done(function(data){
        const list = asList(data);
        renderPrixProduits(list);
      })
      .fail(function(xhr){ console.warn('Erreur chargement prix produits', xhr); });
  }

  function renderPrixProduits(list){
    const $tbody = $('#prix_produits_body');
    if(!$tbody.length) return;
    $tbody.empty();
    if(!list || !list.length){
      $tbody.append('<tr><td colspan="7" class="text-center text-muted">Aucun prix défini</td></tr>');
      return;
    }
    list.forEach(function(p){
      const tr = $('<tr>');
      tr.append('<td><code>'+p.produit_reference+'</code> - '+p.produit_designation+'</td>');
      tr.append('<td><strong>'+p.type_prix_libelle+'</strong> ('+p.type_prix_code+')</td>');
      // Utiliser le currency_symbol du produit, ou fallback vers €
      tr.append('<td class="text-right"><strong>'+p.prix+'</strong> '+(p.currency_symbol || '€')+'</td>');
      tr.append('<td class="text-center">'+p.quantite_min+'</td>');
      let validite = 'Permanent';
      if(p.date_debut || p.date_fin){
        validite = (p.date_debut || '...') + ' → ' + (p.date_fin || '...');
      }
      tr.append('<td>'+validite+'</td>');
      const statusBadge = p.is_valid ? '<span class="badge badge-success">Valide</span>' : '<span class="badge badge-warning">Expiré</span>';
      tr.append('<td>'+statusBadge+'</td>');
      const actions = '<button type="button" class="btn btn-sm btn-delete" data-action="delete-prix-prod" data-id="'+p.id+'">Supprimer</button>';
      tr.append('<td>'+actions+'</td>');
      $tbody.append(tr);
    });
  }

  function fillPrixProduitsSelects(){
    // Remplir les selects de produits pour la gestion des prix en utilisant le cache
    const $selProduit = $('#prix_prod_produit');
    const $selFilter = $('#prix_prod_filter');

    if(!$selProduit.length && !$selFilter.length) return;

    const list = __cacheProduits || [];
    const opts = ['<option value="">Sélectionner un produit</option>'];
    const optsFilter = ['<option value="">Tous les produits</option>'];

    list.forEach(function(prod){
      const label = (prod.reference || '') + ' - ' + (prod.designation || '');
      opts.push('<option value="'+prod.id+'">'+label+'</option>');
      optsFilter.push('<option value="'+prod.id+'">'+label+'</option>');
    });

    if($selProduit.length) $selProduit.html(opts.join(''));
    if($selFilter.length) $selFilter.html(optsFilter.join(''));

    console.log('[Produit] Selects de prix remplis avec', list.length, 'produits');
  }

  function addPrixProduit(){
    const produit = parseInt($('#prix_prod_produit').val() || '0', 10);
    const type_prix = parseInt($('#prix_prod_type').val() || '0', 10);
    const prix = parseFloat($('#prix_prod_prix').val() || '0');
    const quantite_min = parseInt($('#prix_prod_qte_min').val() || '1', 10);
    const date_debut = $('#prix_prod_date_debut').val() || null;
    const date_fin = $('#prix_prod_date_fin').val() || null;

    if(!produit){ alert('Veuillez sélectionner un produit'); return; }
    if(!type_prix){ alert('Veuillez sélectionner un type de prix'); return; }
    if(!prix || prix <= 0){ alert('Prix invalide'); return; }

    const data = { produit, type_prix, prix, quantite_min, date_debut, date_fin };

    $.ajax({ url: apiBase + '/prix-produits/', method: 'POST', contentType: 'application/json',
             headers: { 'X-CSRFToken': getCSRFToken() }, data: JSON.stringify(data) })
      .done(function(){
        $('#prix_prod_produit').val('');
        $('#prix_prod_type').val('');
        $('#prix_prod_prix').val('');
        $('#prix_prod_qte_min').val('1');
        $('#prix_prod_date_debut').val('');
        $('#prix_prod_date_fin').val('');
        loadPrixProduits();
        loadAllPrixProduits(); // Recharge tous les prix pour mettre à jour l'affichage
        showAlert('Prix produit ajouté avec succès', 'success');
      })
      .fail(function(xhr){
        const msg = (xhr.responseJSON && (xhr.responseJSON.detail || xhr.responseJSON.error)) || 'Erreur ajout prix';
        showAlert(msg, 'danger');
      });
  }

  function deletePrixProduit(id){
    if(!confirm('Supprimer ce prix ?')) return;
    $.ajax({ url: apiBase + '/prix-produits/' + id + '/', method: 'DELETE', headers: { 'X-CSRFToken': getCSRFToken() } })
      .done(function(){
        loadPrixProduits();
        loadAllPrixProduits(); // Recharge tous les prix pour mettre à jour l'affichage
        showAlert('Prix supprimé', 'success');
      })
      .fail(function(xhr){
        const msg = (xhr.responseJSON && (xhr.responseJSON.detail || xhr.responseJSON.error)) || 'Erreur suppression';
        showAlert(msg, 'danger');
      });
  }

  // Initialize when the produit fragment is loaded via redirect.js
  document.addEventListener('fragment:loaded', function(e){
    try{
      if(e && e.detail && e.detail.name === 'produit'){ init(); }
    }catch(_){}
  });
  // Also fallback to DOMContentLoaded in case the page is opened directly
  if(document.readyState !== 'loading') { init(); }
  else { document.addEventListener('DOMContentLoaded', init); }
})();
