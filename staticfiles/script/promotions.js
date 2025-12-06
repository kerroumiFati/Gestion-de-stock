/**
 * Gestion des Promotions - JavaScript
 * Interface complète de configuration des promotions avec conditionnement
 */

// Configuration et caches
const PromoConfig = {
    apiUrl: '/API/',
    cache: {
        produits: [],
        categories: [],
        conditionnements: {},
        typesPrix: []
    },
    initialized: false
};

// État du formulaire
let currentPromotion = null;
let selectedType = '';
let selectedUnit = 'unite';

// ============================================================
// INITIALISATION
// ============================================================

// Vérifier si on est sur la page promotions
function isPromotionsPage() {
    return document.getElementById('promo-form-section') !== null;
}

document.addEventListener('DOMContentLoaded', function() {
    // Ne s'exécuter que sur la page promotions
    if (isPromotionsPage() && !PromoConfig.initialized) {
        PromoConfig.initialized = true;
        initPromotions();
    }
});

async function initPromotions() {
    try {
        // Charger les données de référence
        await Promise.all([
            loadProduits(),
            loadCategories(),
            loadTypesPrix(),
            loadStats()
        ]);

        // Charger la liste des promotions
        await loadPromotions();

        // Initialiser les événements
        initEventListeners();

        // Cacher le formulaire au démarrage
        const formSection = document.getElementById('promo-form-section');
        if (formSection) formSection.style.display = 'none';

    } catch (error) {
        console.error('Erreur initialisation promotions:', error);
        showNotification('Erreur lors du chargement', 'error');
    }
}

function initEventListeners() {
    // Sélection du type de promotion
    document.querySelectorAll('.promo-type-card').forEach(card => {
        card.addEventListener('click', function() {
            selectPromoType(this.dataset.type);
        });
    });

    // Sélection de l'unité d'application
    document.querySelectorAll('.unit-option').forEach(option => {
        option.addEventListener('click', function() {
            selectUnit(this.dataset.unit);
        });
    });

    // Changement de produit
    const produitSelect = document.getElementById('promo-produit');
    if (produitSelect) {
        produitSelect.addEventListener('change', function() {
            onProductChange(this.value);
        });
    }

    // Filtres
    const filterStatut = document.getElementById('filter-statut');
    const filterType = document.getElementById('filter-type');
    if (filterStatut) filterStatut.addEventListener('change', loadPromotions);
    if (filterType) filterType.addEventListener('change', loadPromotions);

    // Prévisualisation en temps réel
    ['promo-code', 'promo-nom', 'promo-produit', 'promo-categorie'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', updatePreview);
    });
}

// ============================================================
// CHARGEMENT DES DONNÉES
// ============================================================

async function loadProduits() {
    try {
        const response = await fetch(`${PromoConfig.apiUrl}produits/`);
        if (!response.ok) throw new Error('Erreur chargement produits');
        const data = await response.json();

        // Gérer la réponse paginée ou directe
        PromoConfig.cache.produits = Array.isArray(data) ? data : (data.results || []);

        console.log('[PROMOTIONS] Produits chargés:', PromoConfig.cache.produits.length);

        const select = document.getElementById('promo-produit');
        if (!select) {
            console.error('[PROMOTIONS] Select promo-produit non trouvé');
            return;
        }

        select.innerHTML = '<option value="">-- Sélectionner un produit --</option>';

        PromoConfig.cache.produits.forEach(p => {
            const option = document.createElement('option');
            option.value = p.id;
            const prix = p.prix_formatted || (p.prixU ? p.prixU + ' DA' : 'N/A');
            option.textContent = `${p.reference || 'N/A'} - ${p.designation || 'Sans nom'} (${prix})`;
            select.appendChild(option);
        });

        console.log('[PROMOTIONS] Options produits ajoutées:', select.options.length - 1);
    } catch (error) {
        console.error('Erreur chargement produits:', error);
    }
}

async function loadCategories() {
    try {
        const response = await fetch(`${PromoConfig.apiUrl}categories/`);
        if (!response.ok) throw new Error('Erreur chargement catégories');
        const data = await response.json();

        // Gérer la réponse paginée ou directe
        PromoConfig.cache.categories = Array.isArray(data) ? data : (data.results || []);

        console.log('[PROMOTIONS] Catégories chargées:', PromoConfig.cache.categories.length);

        const select = document.getElementById('promo-categorie');
        if (!select) {
            console.error('[PROMOTIONS] Select promo-categorie non trouvé');
            return;
        }

        select.innerHTML = '<option value="">-- Sélectionner une catégorie --</option>';

        PromoConfig.cache.categories.forEach(c => {
            const option = document.createElement('option');
            option.value = c.id;
            option.textContent = c.full_path || c.nom || 'Sans nom';
            select.appendChild(option);
        });

        console.log('[PROMOTIONS] Options catégories ajoutées:', select.options.length - 1);
    } catch (error) {
        console.error('Erreur chargement catégories:', error);
    }
}

async function loadTypesPrix() {
    try {
        const response = await fetch(`${PromoConfig.apiUrl}types-prix/`);
        if (response.ok) {
            PromoConfig.cache.typesPrix = await response.json();
        }
    } catch (error) {
        console.error('Erreur chargement types prix:', error);
    }
}

async function loadStats() {
    try {
        const response = await fetch(`${PromoConfig.apiUrl}promotions/stats/`);
        if (!response.ok) throw new Error('Erreur chargement stats');
        const stats = await response.json();

        const elActives = document.getElementById('stat-actives');
        const elPlanifiees = document.getElementById('stat-planifiees');
        const elExpirees = document.getElementById('stat-expirees');
        const elTotal = document.getElementById('stat-total');

        if (elActives) elActives.textContent = stats.actives_actuellement || 0;
        if (elPlanifiees) elPlanifiees.textContent = stats.par_statut?.planifiee || 0;
        if (elExpirees) elExpirees.textContent = stats.par_statut?.expiree || 0;
        if (elTotal) elTotal.textContent = stats.total || 0;
    } catch (error) {
        console.error('Erreur chargement stats:', error);
    }
}

async function loadPromotions() {
    try {
        let url = `${PromoConfig.apiUrl}promotions/`;
        const params = new URLSearchParams();

        const filterStatut = document.getElementById('filter-statut');
        const filterType = document.getElementById('filter-type');

        const statut = filterStatut ? filterStatut.value : '';
        const type = filterType ? filterType.value : '';

        if (statut) params.append('statut', statut);
        if (type) params.append('type_promotion', type);

        if (params.toString()) url += '?' + params.toString();

        const response = await fetch(url);
        if (!response.ok) throw new Error('Erreur chargement promotions');
        const promotions = await response.json();

        renderPromotionsTable(promotions);
    } catch (error) {
        console.error('Erreur chargement promotions:', error);
        showNotification('Erreur lors du chargement des promotions', 'error');
    }
}

async function loadConditionnement(produitId) {
    if (PromoConfig.cache.conditionnements[produitId]) {
        return PromoConfig.cache.conditionnements[produitId];
    }

    try {
        const response = await fetch(`${PromoConfig.apiUrl}conditionnements/par_produit/?produit_id=${produitId}`);
        if (response.ok) {
            const data = await response.json();
            PromoConfig.cache.conditionnements[produitId] = data;
            return data;
        }
        return null;
    } catch (error) {
        console.error('Erreur chargement conditionnement:', error);
        return null;
    }
}

// ============================================================
// RENDU DE LA LISTE
// ============================================================

function renderPromotionsTable(promotions) {
    const tbody = document.getElementById('promo-table-body');
    const noMessage = document.getElementById('no-promo-message');

    if (!tbody) return;

    if (!promotions || promotions.length === 0) {
        tbody.innerHTML = '';
        if (noMessage) noMessage.style.display = 'block';
        return;
    }

    if (noMessage) noMessage.style.display = 'none';

    tbody.innerHTML = promotions.map(p => `
        <tr>
            <td><strong>${escapeHtml(p.code)}</strong></td>
            <td>${escapeHtml(p.nom)}</td>
            <td><span class="type-badge">${escapeHtml(p.type_promotion_display || p.type_promotion)}</span></td>
            <td>${escapeHtml(p.produit_designation || p.categorie_nom || '-')}</td>
            <td class="promo-summary">${escapeHtml(p.resume || '-')}</td>
            <td>
                <small>
                    ${formatDate(p.date_debut)}<br>
                    au ${formatDate(p.date_fin)}
                </small>
            </td>
            <td>
                <span class="status-badge ${p.statut}">${escapeHtml(p.statut_display || p.statut)}</span>
            </td>
            <td>
                ${p.usage_actuel || 0}${p.usage_maximum ? '/' + p.usage_maximum : ''}
            </td>
            <td>
                <button class="action-btn-promo edit" onclick="editPromotion(${p.id})" title="Modifier">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="action-btn-promo duplicate" onclick="duplicatePromotion(${p.id})" title="Dupliquer">
                    <i class="fas fa-copy"></i>
                </button>
                ${p.statut === 'brouillon' ? `
                    <button class="action-btn-promo btn-promo-success" onclick="activatePromotion(${p.id})" title="Activer" style="background: #d1fae5; color: #059669;">
                        <i class="fas fa-check"></i>
                    </button>
                ` : ''}
                ${p.statut === 'active' ? `
                    <button class="action-btn-promo" onclick="suspendPromotion(${p.id})" title="Suspendre" style="background: #fef3c7; color: #d97706;">
                        <i class="fas fa-pause"></i>
                    </button>
                ` : ''}
                <button class="action-btn-promo delete" onclick="deletePromotion(${p.id})" title="Supprimer">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

// ============================================================
// GESTION DU FORMULAIRE
// ============================================================

function showNewPromoForm() {
    currentPromotion = null;
    document.getElementById('promo-id').value = '';
    document.getElementById('form-title').textContent = 'Nouvelle Promotion';
    resetForm();
    document.getElementById('promo-form-section').style.display = 'block';
    document.getElementById('promo-form-section').scrollIntoView({ behavior: 'smooth' });
}

function resetForm() {
    document.getElementById('promo-form').reset();
    document.getElementById('promo-id').value = '';

    // Reset type selection
    document.querySelectorAll('.promo-type-card').forEach(c => c.classList.remove('selected'));
    selectedType = '';
    document.getElementById('promo-type').value = '';
    document.getElementById('type-config-container').innerHTML = '';

    // Reset unit selection
    document.querySelectorAll('.unit-option').forEach(o => o.classList.remove('selected'));
    document.querySelector('.unit-option[data-unit="unite"]').classList.add('selected');
    selectedUnit = 'unite';
    document.getElementById('promo-unite-application').value = 'unite';

    // Reset conditionnement display
    document.getElementById('conditionnement-display').style.display = 'none';

    // Reset preview
    document.getElementById('promo-preview').style.display = 'none';

    // Set default dates
    const now = new Date();
    const nextMonth = new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000);
    document.getElementById('promo-date-debut').value = formatDateTimeLocal(now);
    document.getElementById('promo-date-fin').value = formatDateTimeLocal(nextMonth);
}

function cancelForm() {
    document.getElementById('promo-form-section').style.display = 'none';
    resetForm();
}

async function editPromotion(id) {
    try {
        const response = await fetch(`${PromoConfig.apiUrl}promotions/${id}/`);
        if (!response.ok) throw new Error('Erreur chargement promotion');
        const promo = await response.json();

        currentPromotion = promo;
        document.getElementById('form-title').textContent = 'Modifier la promotion';
        document.getElementById('promo-id').value = promo.id;

        // Remplir le formulaire
        document.getElementById('promo-code').value = promo.code || '';
        document.getElementById('promo-nom').value = promo.nom || '';
        document.getElementById('promo-description').value = promo.description || '';
        document.getElementById('promo-priorite').value = promo.priorite || 0;

        // Type de promotion
        selectPromoType(promo.type_promotion);

        // Remplir les valeurs selon le type
        setTimeout(() => {
            if (promo.valeur_pourcentage) {
                const el = document.getElementById('config-pourcentage');
                if (el) el.value = promo.valeur_pourcentage;
            }
            if (promo.valeur_fixe) {
                const el = document.getElementById('config-valeur-fixe');
                if (el) el.value = promo.valeur_fixe;
            }
            if (promo.prix_special) {
                const el = document.getElementById('config-prix-special');
                if (el) el.value = promo.prix_special;
            }
            if (promo.quantite_achat) {
                const el = document.getElementById('config-qte-achat');
                if (el) el.value = promo.quantite_achat;
            }
            if (promo.quantite_offerte) {
                const el = document.getElementById('config-qte-offerte');
                if (el) el.value = promo.quantite_offerte;
            }
        }, 100);

        // Produit/Catégorie
        document.getElementById('promo-produit').value = promo.produit || '';
        document.getElementById('promo-categorie').value = promo.categorie || '';

        if (promo.produit) {
            onProductChange(promo.produit);
        }

        // Unité d'application
        selectUnit(promo.unite_application || 'unite');

        // Dates
        if (promo.date_debut) {
            document.getElementById('promo-date-debut').value = promo.date_debut.slice(0, 16);
        }
        if (promo.date_fin) {
            document.getElementById('promo-date-fin').value = promo.date_fin.slice(0, 16);
        }

        // Conditions
        document.getElementById('promo-qte-min').value = promo.quantite_minimum || 1;
        document.getElementById('promo-qte-max').value = promo.quantite_maximum || '';
        document.getElementById('promo-usage-max').value = promo.usage_maximum || '';
        document.getElementById('promo-usage-client').value = promo.usage_par_client || '';
        document.getElementById('promo-carton-complet').checked = promo.carton_complet_requis || false;
        document.getElementById('promo-cumulable').checked = promo.est_cumulable || false;

        // Afficher le formulaire
        document.getElementById('promo-form-section').style.display = 'block';
        document.getElementById('promo-form-section').scrollIntoView({ behavior: 'smooth' });

    } catch (error) {
        console.error('Erreur modification:', error);
        showNotification('Erreur lors du chargement de la promotion', 'error');
    }
}

// ============================================================
// SÉLECTION TYPE DE PROMOTION
// ============================================================

function selectPromoType(type) {
    // Mettre à jour l'UI
    document.querySelectorAll('.promo-type-card').forEach(c => {
        c.classList.toggle('selected', c.dataset.type === type);
    });

    selectedType = type;
    document.getElementById('promo-type').value = type;

    // Générer la configuration spécifique
    renderTypeConfig(type);

    // Mettre à jour l'aperçu
    updatePreview();
}

function renderTypeConfig(type) {
    const container = document.getElementById('type-config-container');

    switch (type) {
        case 'pourcentage':
            container.innerHTML = `
                <div class="row">
                    <div class="col-md-6">
                        <label class="form-label-promo">Pourcentage de réduction <span class="required">*</span></label>
                        <div class="input-group">
                            <input type="number" class="form-control-promo" id="config-pourcentage"
                                   min="0" max="100" step="0.01" placeholder="Ex: 10" onchange="updatePreview()">
                            <span class="input-group-text">%</span>
                        </div>
                    </div>
                </div>
            `;
            break;

        case 'valeur_fixe':
            container.innerHTML = `
                <div class="row">
                    <div class="col-md-6">
                        <label class="form-label-promo">Montant de la réduction <span class="required">*</span></label>
                        <div class="input-group">
                            <input type="number" class="form-control-promo" id="config-valeur-fixe"
                                   min="0" step="0.01" placeholder="Ex: 2.00" onchange="updatePreview()">
                            <span class="input-group-text">DA</span>
                        </div>
                    </div>
                </div>
            `;
            break;

        case 'prix_special':
            container.innerHTML = `
                <div class="row">
                    <div class="col-md-6">
                        <label class="form-label-promo">Prix spécial <span class="required">*</span></label>
                        <div class="input-group">
                            <input type="number" class="form-control-promo" id="config-prix-special"
                                   min="0" step="0.01" placeholder="Ex: 9.99" onchange="updatePreview()">
                            <span class="input-group-text">DA</span>
                        </div>
                    </div>
                </div>
            `;
            break;

        case 'achetez_x_payez_y':
            container.innerHTML = `
                <div class="row">
                    <div class="col-md-4">
                        <label class="form-label-promo">Achetez <span class="required">*</span></label>
                        <input type="number" class="form-control-promo" id="config-qte-achat"
                               min="1" placeholder="Ex: 3" onchange="updatePreview()">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label-promo">Payez <span class="required">*</span></label>
                        <input type="number" class="form-control-promo" id="config-qte-offerte"
                               min="1" placeholder="Ex: 2" onchange="updatePreview()">
                    </div>
                    <div class="col-md-4 d-flex align-items-end">
                        <p class="text-muted mb-2"><i class="fas fa-info-circle"></i> Ex: Achetez 3, payez 2</p>
                    </div>
                </div>
            `;
            break;

        case 'achetez_x_offert_y':
            container.innerHTML = `
                <div class="row">
                    <div class="col-md-4">
                        <label class="form-label-promo">Achetez <span class="required">*</span></label>
                        <input type="number" class="form-control-promo" id="config-qte-achat"
                               min="1" placeholder="Ex: 2" onchange="updatePreview()">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label-promo">Offert(s) <span class="required">*</span></label>
                        <input type="number" class="form-control-promo" id="config-qte-offerte"
                               min="1" placeholder="Ex: 1" onchange="updatePreview()">
                    </div>
                    <div class="col-md-4 d-flex align-items-end">
                        <p class="text-muted mb-2"><i class="fas fa-info-circle"></i> Ex: 2 achetés = 1 offert</p>
                    </div>
                </div>
            `;
            break;

        case 'demunerisation':
            container.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle"></i>
                    Le prix de démunération sera appliqué pour la vente à l'unité depuis un carton ouvert.
                    Configurez le prix dans le conditionnement du produit.
                </div>
            `;
            break;

        default:
            container.innerHTML = '';
    }
}

// ============================================================
// SÉLECTION UNITÉ D'APPLICATION
// ============================================================

function selectUnit(unit) {
    document.querySelectorAll('.unit-option').forEach(o => {
        o.classList.toggle('selected', o.dataset.unit === unit);
    });

    selectedUnit = unit;
    document.getElementById('promo-unite-application').value = unit;

    updatePreview();
}

// ============================================================
// CHANGEMENT DE PRODUIT
// ============================================================

async function onProductChange(produitId) {
    const condDisplay = document.getElementById('conditionnement-display');

    if (!produitId) {
        condDisplay.style.display = 'none';
        return;
    }

    // Trouver le produit
    const produit = PromoConfig.cache.produits.find(p => p.id == produitId);
    if (!produit) return;

    document.getElementById('cond-prix-unite').textContent = `${produit.prixU || 0} DA`;

    // Charger le conditionnement
    const cond = await loadConditionnement(produitId);

    if (cond) {
        document.getElementById('cond-unites-carton').textContent = cond.unites_par_carton || '-';
        document.getElementById('cond-prix-carton').textContent = cond.prix_carton_calcule ? `${cond.prix_carton_calcule} DA` : '-';
        document.getElementById('cond-cartons-colis').textContent = cond.cartons_par_colis || '-';
        condDisplay.style.display = 'block';
    } else {
        document.getElementById('cond-unites-carton').textContent = '-';
        document.getElementById('cond-prix-carton').textContent = '-';
        document.getElementById('cond-cartons-colis').textContent = '-';
        condDisplay.style.display = 'block';
    }

    updatePreview();
}

// ============================================================
// APERÇU EN TEMPS RÉEL
// ============================================================

function updatePreview() {
    const preview = document.getElementById('promo-preview');
    const produitId = document.getElementById('promo-produit').value;

    if (!selectedType || !produitId) {
        preview.style.display = 'none';
        return;
    }

    const produit = PromoConfig.cache.produits.find(p => p.id == produitId);
    if (!produit) {
        preview.style.display = 'none';
        return;
    }

    let prixOriginal = parseFloat(produit.prixU) || 0;
    let prixPromo = prixOriginal;

    // Calculer selon le type
    switch (selectedType) {
        case 'pourcentage':
            const pourcent = parseFloat(document.getElementById('config-pourcentage')?.value) || 0;
            prixPromo = prixOriginal * (1 - pourcent / 100);
            break;

        case 'valeur_fixe':
            const reduction = parseFloat(document.getElementById('config-valeur-fixe')?.value) || 0;
            prixPromo = Math.max(0, prixOriginal - reduction);
            break;

        case 'prix_special':
            prixPromo = parseFloat(document.getElementById('config-prix-special')?.value) || prixOriginal;
            break;
    }

    // Afficher l'aperçu
    document.getElementById('preview-prix-original').textContent = `${prixOriginal.toFixed(2)} DA`;
    document.getElementById('preview-prix-promo').textContent = `${prixPromo.toFixed(2)} DA`;

    const economie = prixOriginal - prixPromo;
    const pourcentEconomie = prixOriginal > 0 ? (economie / prixOriginal * 100) : 0;
    document.getElementById('preview-economie').textContent =
        `${economie.toFixed(2)} DA (${pourcentEconomie.toFixed(0)}%)`;

    preview.style.display = 'block';
}

// ============================================================
// SAUVEGARDE
// ============================================================

async function savePromotion(statut) {
    // Validation
    const code = document.getElementById('promo-code').value.trim();
    const nom = document.getElementById('promo-nom').value.trim();
    const type = document.getElementById('promo-type').value;
    const produit = document.getElementById('promo-produit').value;
    const categorie = document.getElementById('promo-categorie').value;
    const dateDebut = document.getElementById('promo-date-debut').value;
    const dateFin = document.getElementById('promo-date-fin').value;

    if (!code) {
        showNotification('Le code de la promotion est requis', 'error');
        return;
    }
    if (!nom) {
        showNotification('Le nom de la promotion est requis', 'error');
        return;
    }
    if (!type) {
        showNotification('Veuillez sélectionner un type de promotion', 'error');
        return;
    }
    if (!produit && !categorie) {
        showNotification('Veuillez sélectionner un produit ou une catégorie', 'error');
        return;
    }
    if (!dateDebut || !dateFin) {
        showNotification('Les dates de validité sont requises', 'error');
        return;
    }

    // Construire l'objet promotion
    const data = {
        code: code,
        nom: nom,
        description: document.getElementById('promo-description').value || '',
        type_promotion: type,
        unite_application: document.getElementById('promo-unite-application').value,
        date_debut: dateDebut,
        date_fin: dateFin,
        quantite_minimum: parseInt(document.getElementById('promo-qte-min').value) || 1,
        carton_complet_requis: document.getElementById('promo-carton-complet').checked,
        est_cumulable: document.getElementById('promo-cumulable').checked,
        priorite: parseInt(document.getElementById('promo-priorite').value) || 0,
        statut: statut
    };

    // Produit ou catégorie
    if (produit) data.produit = parseInt(produit);
    if (categorie) data.categorie = parseInt(categorie);

    // Quantité maximum (optionnel)
    const qteMax = document.getElementById('promo-qte-max').value;
    if (qteMax) data.quantite_maximum = parseInt(qteMax);

    // Usage maximum (optionnel)
    const usageMax = document.getElementById('promo-usage-max').value;
    if (usageMax) data.usage_maximum = parseInt(usageMax);

    // Usage par client (optionnel)
    const usageClient = document.getElementById('promo-usage-client').value;
    if (usageClient) data.usage_par_client = parseInt(usageClient);

    // Valeurs selon le type
    switch (type) {
        case 'pourcentage':
            data.valeur_pourcentage = parseFloat(document.getElementById('config-pourcentage')?.value) || 0;
            break;
        case 'valeur_fixe':
            data.valeur_fixe = parseFloat(document.getElementById('config-valeur-fixe')?.value) || 0;
            break;
        case 'prix_special':
            data.prix_special = parseFloat(document.getElementById('config-prix-special')?.value) || 0;
            break;
        case 'achetez_x_payez_y':
        case 'achetez_x_offert_y':
            data.quantite_achat = parseInt(document.getElementById('config-qte-achat')?.value) || 0;
            data.quantite_offerte = parseInt(document.getElementById('config-qte-offerte')?.value) || 0;
            break;
    }

    try {
        const promoId = document.getElementById('promo-id').value;
        let url = `${PromoConfig.apiUrl}promotions/`;
        let method = 'POST';

        if (promoId) {
            url += `${promoId}/`;
            method = 'PUT';
        }

        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(JSON.stringify(errorData));
        }

        showNotification(
            promoId ? 'Promotion mise à jour avec succès' : 'Promotion créée avec succès',
            'success'
        );

        cancelForm();

        // Attendre le rechargement de la liste et des stats
        await loadPromotions();
        await loadStats();

    } catch (error) {
        console.error('Erreur sauvegarde:', error);
        showNotification('Erreur lors de la sauvegarde: ' + error.message, 'error');
    }
}

// ============================================================
// ACTIONS SUR LES PROMOTIONS
// ============================================================

async function activatePromotion(id) {
    if (!confirm('Activer cette promotion ?')) return;

    try {
        const response = await fetch(`${PromoConfig.apiUrl}promotions/${id}/activer/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        });

        if (!response.ok) throw new Error('Erreur activation');

        showNotification('Promotion activée', 'success');
        await loadPromotions();
        await loadStats();
    } catch (error) {
        showNotification('Erreur lors de l\'activation', 'error');
    }
}

async function suspendPromotion(id) {
    if (!confirm('Suspendre cette promotion ?')) return;

    try {
        const response = await fetch(`${PromoConfig.apiUrl}promotions/${id}/suspendre/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        });

        if (!response.ok) throw new Error('Erreur suspension');

        showNotification('Promotion suspendue', 'success');
        await loadPromotions();
        await loadStats();
    } catch (error) {
        showNotification('Erreur lors de la suspension', 'error');
    }
}

async function duplicatePromotion(id) {
    if (!confirm('Dupliquer cette promotion ?')) return;

    try {
        const response = await fetch(`${PromoConfig.apiUrl}promotions/${id}/dupliquer/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        });

        if (!response.ok) throw new Error('Erreur duplication');

        const newPromo = await response.json();
        showNotification('Promotion dupliquée', 'success');
        await loadPromotions();

        // Ouvrir la nouvelle promotion en édition
        editPromotion(newPromo.id);
    } catch (error) {
        showNotification('Erreur lors de la duplication', 'error');
    }
}

async function deletePromotion(id) {
    if (!confirm('Êtes-vous sûr de vouloir supprimer cette promotion ?')) return;

    try {
        const response = await fetch(`${PromoConfig.apiUrl}promotions/${id}/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        });

        if (!response.ok) throw new Error('Erreur suppression');

        showNotification('Promotion supprimée', 'success');
        await loadPromotions();
        await loadStats();
    } catch (error) {
        showNotification('Erreur lors de la suppression', 'error');
    }
}

// ============================================================
// SIMULATION
// ============================================================

let currentSimulationPromoId = null;

function openSimulationModal(promoId) {
    currentSimulationPromoId = promoId;
    document.getElementById('sim-quantite').value = 1;
    document.getElementById('simulation-result').style.display = 'none';

    const modal = new bootstrap.Modal(document.getElementById('simulationModal'));
    modal.show();
}

async function runSimulation() {
    if (!currentSimulationPromoId) return;

    const produitId = document.getElementById('promo-produit').value;
    if (!produitId) {
        showNotification('Sélectionnez un produit pour la simulation', 'warning');
        return;
    }

    const data = {
        promotion_id: currentSimulationPromoId,
        produit_id: parseInt(produitId),
        quantite: parseInt(document.getElementById('sim-quantite').value) || 1,
        type_conditionnement: document.getElementById('sim-conditionnement').value
    };

    try {
        const response = await fetch(`${PromoConfig.apiUrl}promotions/simuler/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) throw new Error('Erreur simulation');

        const result = await response.json();
        renderSimulationResult(result);
    } catch (error) {
        showNotification('Erreur lors de la simulation', 'error');
    }
}

function renderSimulationResult(result) {
    const container = document.getElementById('simulation-result');

    container.innerHTML = `
        <div class="promo-preview">
            <h6 class="mb-3"><i class="fas fa-calculator"></i> Résultat de la simulation</h6>
            <div class="price-comparison">
                <div class="price-box original">
                    <label>Prix original</label>
                    <div class="amount">${result.prix_total_sans_promotion.toFixed(2)} DA</div>
                </div>
                <div class="price-arrow"><i class="fas fa-arrow-right"></i></div>
                <div class="price-box promo">
                    <label>Prix avec promo</label>
                    <div class="amount">${result.prix_total_avec_promotion.toFixed(2)} DA</div>
                </div>
            </div>
            <div class="text-center mt-3">
                <div class="savings-badge">
                    <i class="fas fa-piggy-bank"></i>
                    Économie: ${result.economie_montant.toFixed(2)} DA (${result.economie_pourcentage.toFixed(1)}%)
                </div>
            </div>
            ${result.offre_speciale.quantite_gratuite > 0 ? `
                <div class="alert alert-success mt-3">
                    <i class="fas fa-gift"></i>
                    <strong>${result.offre_speciale.quantite_gratuite}</strong> unité(s) gratuite(s) !
                    <br>
                    Total: ${result.offre_speciale.quantite_totale} unités pour le prix de ${result.offre_speciale.quantite_a_payer}
                </div>
            ` : ''}
        </div>
    `;

    container.style.display = 'block';
}

// ============================================================
// UTILITAIRES
// ============================================================

function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value
        || document.cookie.split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1] || '';
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString('fr-FR');
    } catch {
        return dateStr;
    }
}

function formatDateTimeLocal(date) {
    const pad = n => n.toString().padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function showNotification(message, type = 'info') {
    // Utiliser le système de notification existant si disponible
    if (typeof Toastify !== 'undefined') {
        Toastify({
            text: message,
            duration: 3000,
            gravity: "top",
            position: "right",
            backgroundColor: type === 'error' ? '#ef4444' : type === 'success' ? '#10b981' : '#3b82f6'
        }).showToast();
    } else {
        // Fallback simple
        alert(message);
    }
}
