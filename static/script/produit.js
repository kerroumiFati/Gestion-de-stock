/* Rovo Dev: Gestion Produits - inclut Prix U */
(function(){
  if(window.__rovodev_produit_loaded){ return; }
  window.__rovodev_produit_loaded = true;
  let __rovodev_inited = false;
  const api = {
    produits: '/API/produits/',
    categories: '/API/categories/',
    fournisseurs: '/API/fournisseurs/'
  };
  let __cacheProduits = [];

  const el = sel => document.querySelector(sel);
  function toFixed2(n){
    const v = Number(n||0);
    return isFinite(v) ? v.toFixed(2) : '0.00';
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

  async function loadFournisseurs(){
    try{
      console.log('[Produit] Chargement des fournisseurs...');
      const data = await fetchJSON(api.fournisseurs);
      const sel = el('#fournisseur');
      if(!sel){
        console.warn('[Produit] Element #fournisseur non trouvé');
        return;
      }
      const fournisseurs = Array.isArray(data) ? data : (data.results || []);
      console.log(`[Produit] ${fournisseurs.length} fournisseurs chargés`);
      sel.innerHTML = '<option value="">Sélectionner un fournisseur</option>' +
        fournisseurs.map(f=>`<option value="${f.id}">${f.libelle}</option>`).join('');
    }catch(e){
      console.error('[Produit] Erreur chargement fournisseurs:', e);
      showAlert('Erreur de chargement des fournisseurs', 'warning');
    }
  }

  async function loadProduits(){
    try{
      const data = await fetchJSON(api.produits);
      __cacheProduits = Array.isArray(data) ? data : [];
      const tbody = el('#tproduit tbody#table-content') || el('#tproduit tbody');
      if(!tbody) return;
      tbody.innerHTML = __cacheProduits.map(p=>{
        return `<tr data-id="${p.id}">
          <td>${p.id}</td>
          <td>${p.reference||''}</td>
          <td>${p.code_barre||''}</td>
          <td>${p.designation||''}</td>
          <td>${p.categorie_nom||''}</td>
          <td>${p.prixU!=null? toFixed2(p.prixU): ''} ${p.currency_symbol||''}</td>
          <td>${p.fournisseur_nom||''}</td>
          <td><button class="btn btn-sm btn-outline-danger act-del">Supprimer</button></td>
          <td><button class="btn btn-sm btn-outline-primary act-edit">Modifier</button></td>
        </tr>`;
      }).join('');
    }catch(e){ console.warn('produits load failed', e); }
  }

  function collectForm(){
    const id = el('#id') && el('#id').value ? Number(el('#id').value) : null;
    const payload = {
      reference: el('#reference')?.value?.trim(),
      code_barre: el('#code_barre')?.value?.trim(),
      designation: el('#designation')?.value?.trim(),
      categorie: el('#categorie')?.value ? Number(el('#categorie').value) : null,
      fournisseur: el('#fournisseur')?.value ? Number(el('#fournisseur').value) : null,
      prixU: el('#prixU')?.value ? Number(el('#prixU').value) : 0,
      quantite: el('#quantite')?.value ? Number(el('#quantite').value) : 0,
    };
    return {id, payload};
  }

  async function createOrUpdate(){
    const {id, payload} = collectForm();
    // Validation stricte: vérifier que les champs ne sont pas vides/null/undefined
    if(!payload.reference || !payload.designation || payload.categorie == null || payload.fournisseur == null || !payload.code_barre || payload.quantite == null){
      showAlert('Veuillez remplir les champs obligatoires (référence, code-barres, désignation, catégorie, fournisseur, quantité)', 'warning');
      return;
    }
    // Vérification unicité côté client pour éviter une erreur 400 inutile
    const refExists = __cacheProduits.some(p => (p.reference||'').toLowerCase() === (payload.reference||'').toLowerCase());
    const cbExists = __cacheProduits.some(p => (p.code_barre||'').toLowerCase() === (payload.code_barre||'').toLowerCase());
    if(!id && (refExists || cbExists)){
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
      showAlert(id? 'Produit mis à jour' : 'Produit créé', 'success');
      clearForm();
      await loadProduits();
    }catch(e){
      console.error('save produit failed', e);
      showAlert('Erreur lors de l\'enregistrement du produit', 'danger');
    }
  }

  function clearForm(){
    ['#id','#reference','#code_barre','#designation','#prixU','#quantite'].forEach(s=>{ const n=el(s); if(n) n.value=''; });
    if(el('#categorie')) el('#categorie').value='';
    if(el('#fournisseur')) el('#fournisseur').value='';
  }

  function showAlert(msg, level){
    const box = el('#product-alerts');
    if(!box) return;
    box.innerHTML = `<div class="alert alert-${level||'info'}">${msg}</div>`;
    setTimeout(()=>{ box.innerHTML=''; }, 3000);
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
          if(el('#fournisseur')) el('#fournisseur').value = p.fournisseur||'';
          if(el('#prixU')) el('#prixU').value = p.prixU!=null? Number(p.prixU): '';
          if(el('#quantite')) el('#quantite').value = p.quantite!=null? Number(p.quantite): '';
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
      loadFournisseurs(),
      loadProduits()
    ]).then(() => {
      console.log('[Produit] Toutes les données chargées avec succès');
    }).catch(err => {
      console.error('[Produit] Erreur lors du chargement initial:', err);
    });

    bindTableActions();
    const btn = el('#btn');
    if(btn){ btn.addEventListener('click', createOrUpdate); }

    // Bouton Check - vérifier les produits avec quantité faible
    const btnRisk = el('#btnrisk');
    if(btnRisk){
      btnRisk.addEventListener('click', async () => {
        const riskValue = el('#risk')?.value ? Number(el('#risk').value) : 0;
        if(riskValue <= 0){
          showAlert('Veuillez entrer un seuil de risque valide', 'warning');
          return;
        }

        // Filtrer les produits dont la quantité est inférieure au seuil
        const lowStockProducts = __cacheProduits.filter(p => (p.quantite || 0) <= riskValue);

        if(lowStockProducts.length === 0){
          showAlert(`Aucun produit avec quantité ≤ ${riskValue}`, 'info');
        } else {
          showAlert(`${lowStockProducts.length} produit(s) avec quantité ≤ ${riskValue}`, 'warning');
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
