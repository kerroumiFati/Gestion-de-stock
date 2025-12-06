// Gestion des Tournées
window.tournees = window.tournees || [];
window.livreurs_tournees = window.livreurs_tournees || [];
window.clients_tournees = window.clients_tournees || [];
window.warehouses_tournees = window.warehouses_tournees || [];
window.codes_prix_tournees = window.codes_prix_tournees || [];
window.currentFilter = window.currentFilter || 'all';
window.arretCounter = window.arretCounter || 0;
window.userPermissions = window.userPermissions || null;

var tournees = window.tournees;
var livreurs = window.livreurs_tournees;
var clients = window.clients_tournees;
var warehouses = window.warehouses_tournees;
var codes_prix = window.codes_prix_tournees;
var currentFilter = window.currentFilter;
var arretCounter = window.arretCounter;

// ============================================
// GESTION DES PERMISSIONS
// ============================================
function hasPermission(permName) {
    // Superuser a toutes les permissions
    if (window.userPermissions && window.userPermissions.is_superuser) {
        return true;
    }
    // Vérifier si la permission est dans la liste
    if (window.userPermissions && window.userPermissions.permissions) {
        return window.userPermissions.permissions.includes(permName);
    }
    return false;
}

async function loadUserPermissions() {
    try {
        const response = await fetch('/API/my-permissions/');
        if (response.ok) {
            window.userPermissions = await response.json();
            console.log('[TOURNEES] Permissions chargées:', window.userPermissions);
        }
    } catch (error) {
        console.error('[TOURNEES] Erreur chargement permissions:', error);
    }
}

// ============================================
// CUSTOM SELECT FUNCTIONS
// ============================================
function initCustomSelect(containerId, triggerId, dropdownId, searchId, optionsId, hiddenSelectId) {
    var trigger = document.getElementById(triggerId);
    var dropdown = document.getElementById(dropdownId);
    var searchInput = searchId ? document.getElementById(searchId) : null;
    var optionsContainer = document.getElementById(optionsId);
    var hiddenSelect = document.getElementById(hiddenSelectId);

    if (!trigger || !dropdown || !optionsContainer) {
        console.warn('[TOURNEES] Custom select elements not found:', containerId);
        return;
    }

    // Supprimer anciens event listeners en clonant
    var newTrigger = trigger.cloneNode(true);
    trigger.parentNode.replaceChild(newTrigger, trigger);
    trigger = newTrigger;

    // Toggle dropdown
    trigger.addEventListener('click', function(e) {
        e.stopPropagation();
        e.preventDefault();

        var dd = document.getElementById(dropdownId);
        var isOpen = dd.classList.contains('open');

        // Fermer tous les autres dropdowns
        document.querySelectorAll('.custom-select-dropdown.open').forEach(function(d) {
            d.classList.remove('open');
        });
        document.querySelectorAll('.custom-select-trigger.open').forEach(function(t) {
            t.classList.remove('open');
        });

        if (!isOpen) {
            dd.classList.add('open');
            trigger.classList.add('open');
            var si = searchId ? document.getElementById(searchId) : null;
            if (si) {
                si.value = '';
                setTimeout(function() { si.focus(); }, 50);
                filterCustomSelectOptions(document.getElementById(optionsId), '');
            }
        } else {
            dd.classList.remove('open');
            trigger.classList.remove('open');
        }
    });

    // Search filter
    if (searchInput) {
        var newSearchInput = searchInput.cloneNode(true);
        searchInput.parentNode.replaceChild(newSearchInput, searchInput);
        searchInput = newSearchInput;

        searchInput.addEventListener('input', function() {
            filterCustomSelectOptions(document.getElementById(optionsId), this.value);
        });
        searchInput.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    }

    // Option click
    var newOptionsContainer = optionsContainer.cloneNode(true);
    optionsContainer.parentNode.replaceChild(newOptionsContainer, optionsContainer);

    newOptionsContainer.addEventListener('click', function(e) {
        e.stopPropagation();
        var option = e.target.closest('.custom-select-option');
        if (option) {
            var value = option.getAttribute('data-value') || '';
            var text = option.textContent.trim();

            // Update trigger text
            var tr = document.getElementById(triggerId);
            var selectedText = tr ? tr.querySelector('.selected-text') : null;
            if (selectedText) {
                selectedText.textContent = text;
                selectedText.classList.toggle('placeholder', value === '');
            }

            // Update hidden select
            var hs = document.getElementById(hiddenSelectId);
            if (hs) {
                hs.value = value;
            }

            // Update selected state
            newOptionsContainer.querySelectorAll('.custom-select-option').forEach(function(opt) {
                opt.classList.toggle('selected', opt.getAttribute('data-value') === value);
            });

            // Close dropdown
            var dd = document.getElementById(dropdownId);
            if (dd) dd.classList.remove('open');
            if (tr) tr.classList.remove('open');
        }
    });
}

function filterCustomSelectOptions(optionsContainer, searchText) {
    if (!optionsContainer) return;
    var options = optionsContainer.querySelectorAll('.custom-select-option');
    var search = (searchText || '').toLowerCase().trim();
    var hasVisible = false;

    options.forEach(function(opt) {
        var text = (opt.textContent || '').toLowerCase();
        var match = !search || text.indexOf(search) !== -1;
        opt.style.display = match ? '' : 'none';
        if (match) hasVisible = true;
    });

    var noResults = optionsContainer.querySelector('.custom-select-no-results');
    if (!hasVisible) {
        if (!noResults) {
            noResults = document.createElement('div');
            noResults.className = 'custom-select-no-results';
            noResults.textContent = 'Aucun résultat';
            optionsContainer.appendChild(noResults);
        }
        noResults.style.display = '';
    } else if (noResults) {
        noResults.style.display = 'none';
    }
}

function populateCustomSelectOptions(optionsId, items, valueKey, textKey, placeholder) {
    var optionsContainer = document.getElementById(optionsId);
    if (!optionsContainer) return;

    optionsContainer.innerHTML = '';

    // Add placeholder option
    var placeholderOpt = document.createElement('div');
    placeholderOpt.className = 'custom-select-option selected';
    placeholderOpt.setAttribute('data-value', '');
    placeholderOpt.textContent = placeholder || 'Sélectionner...';
    optionsContainer.appendChild(placeholderOpt);

    // Add items
    items.forEach(function(item) {
        var opt = document.createElement('div');
        opt.className = 'custom-select-option';
        opt.setAttribute('data-value', item[valueKey]);
        opt.textContent = typeof textKey === 'function' ? textKey(item) : item[textKey];
        optionsContainer.appendChild(opt);
    });
}

// Close all custom selects when clicking outside
document.addEventListener('click', function(e) {
    if (!e.target.closest('.custom-select-container')) {
        document.querySelectorAll('.custom-select-dropdown.open').forEach(function(d) {
            d.classList.remove('open');
        });
        document.querySelectorAll('.custom-select-trigger.open').forEach(function(t) {
            t.classList.remove('open');
        });
    }
});
// ============================================

// Fonction d'initialisation
window.initTourneesPage = async function() {
    // Vérifier que les éléments nécessaires existent avant d'initialiser
    const container = document.getElementById('tournees-container');
    if (!container) {
        console.log('[TOURNEES] Page elements not found, skipping initialization');
        return;
    }

    console.log('[TOURNEES] Initializing tournees page');

    // Charger les permissions utilisateur en premier
    await loadUserPermissions();

    window.arretCounter = 0;
    loadTournees();

    // Charger les livreurs et peupler le select
    loadLivreurs().then(() => {
        populateLivreursSelect();
    }).catch(err => console.error('Erreur chargement livreurs:', err));

    // Charger les clients
    loadClients().catch(err => console.error('Erreur chargement clients:', err));

    // Charger les entrepôts et peupler le select
    loadWarehouses().then(() => {
        populateWarehousesSelect();
    }).catch(err => console.error('Erreur chargement entrepôts:', err));

    // Charger les codes de prix et peupler le select
    loadCodesPrix().then(() => {
        populateCodesPrixSelect();
    }).catch(err => console.error('Erreur chargement codes de prix:', err));

    setupFormHandlers();

    // Définir la date par défaut à aujourd'hui
    const dateField = document.getElementById('date');
    if (dateField) {
        const today = new Date().toISOString().split('T')[0];
        dateField.value = today;
    }
};

// NE PAS charger automatiquement au DOMContentLoaded car on utilise le chargement dynamique
// La page sera initialisée uniquement via fragment:loaded

// Charger lors du chargement dynamique
document.addEventListener('fragment:loaded', function(e) {
    if (e.detail && e.detail.name === 'tournees') {
        console.log('[TOURNEES] fragment:loaded event for tournees');
        window.initTourneesPage();
    }
});

// Charger les tournées
function loadTournees() {
    fetch('/API/tournees/', {
        credentials: 'same-origin',
        headers: { 'Accept': 'application/json' }
    })
        .then(response => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.json();
        })
        .then(data => {
            // Gérer la pagination DRF (data.results) ou tableau direct
            let tourneesRaw = Array.isArray(data) ? data : (data.results || []);

            // Transformer les données de l'API vers le format attendu par l'interface
            window.tournees = tourneesRaw.map(t => transformTourneeData(t));

            console.log('Tournées chargées:', window.tournees.length);
            displayTournees(window.tournees);
            updateTourneesStats(window.tournees);
        })
        .catch(error => {
            console.error('Erreur:', error);
            showMessage('Erreur lors du chargement des tournées', 'error');
        });
}

// Transformer les données de l'API vers le format attendu par l'interface
function transformTourneeData(apiData) {
    const stats = apiData.statistiques || {};

    // Mapper les noms de champs de l'API vers ceux attendus par l'interface
    return {
        id: apiData.id,
        numero: apiData.numero_tournee,
        date: apiData.date_tournee,
        livreur: apiData.livreur,
        livreur_nom: apiData.livreur_nom || 'Non assigné',
        statut: apiData.statut,
        statut_display: getStatutDisplay(apiData.statut),
        heure_debut: apiData.heure_debut,
        heure_fin: apiData.heure_fin,
        heure_depart_prevue: apiData.heure_debut || '--:--',
        heure_retour_prevue: apiData.heure_fin || '--:--',
        commentaire: apiData.notes || '',
        warehouse: apiData.warehouse,
        arrets: apiData.arrets || [],
        nombre_arrets: stats.total_arrets || (apiData.arrets ? apiData.arrets.length : 0),
        arrets_livres: stats.arrets_livres || 0,
        arrets_echec: stats.arrets_echec || 0,
        arrets_en_attente: stats.arrets_en_attente || 0,
        taux_reussite: stats.taux_reussite || 0,
        ca_total: stats.ca_total || 0,
        est_cloturee: apiData.est_cloturee || false,
        created_at: apiData.created_at,
        updated_at: apiData.updated_at,
        statistiques: stats  // Passer les statistiques complètes incluant arrets_visites et arrets_restants
    };
}

// Obtenir le libellé d'un statut
function getStatutDisplay(statut) {
    const statuts = {
        'planifiee': 'Planifiée',
        'en_cours': 'En cours',
        'terminee': 'Terminée',
        'annulee': 'Annulée',
        'cloturee': 'Clôturée'
    };
    return statuts[statut] || statut;
}

// Charger les livreurs
function loadLivreurs() {
    return fetch('/API/distribution/livreurs/', {
        credentials: 'same-origin',
        headers: { 'Accept': 'application/json' }
    })
        .then(response => {
            if (!response.ok) {
                console.error('Erreur HTTP livreurs:', response.status);
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Gérer la pagination DRF (data.results) ou tableau direct
            window.livreurs_tournees = Array.isArray(data) ? data : (data.results || []);
            console.log('Livreurs chargés:', window.livreurs_tournees.length);
            return window.livreurs_tournees;
        })
        .catch(error => {
            console.error('Erreur chargement livreurs:', error);
            window.livreurs_tournees = [];
            throw error;
        });
}

// Charger les clients
function loadClients() {
    return fetch('/API/clients/?page_size=1000', {
        credentials: 'same-origin',
        headers: { 'Accept': 'application/json' }
    })
        .then(response => {
            if (!response.ok) {
                console.error('Erreur HTTP clients:', response.status);
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Gérer la pagination DRF (data.results) ou tableau direct
            window.clients_tournees = Array.isArray(data) ? data : (data.results || []);
            console.log('Clients chargés:', window.clients_tournees.length);
            return window.clients_tournees;
        })
        .catch(error => {
            console.error('Erreur chargement clients:', error);
            window.clients_tournees = [];
            throw error;
        });
}

// Charger les entrepôts
function loadWarehouses() {
    return fetch('/API/entrepots/?page_size=1000', {
        credentials: 'same-origin',  // Inclure les cookies de session
        headers: {
            'Accept': 'application/json',
        }
    })
        .then(response => {
            if (!response.ok) {
                console.error('Erreur HTTP entrepôts:', response.status, response.statusText);
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            // Gérer la pagination DRF (data.results) ou tableau direct
            window.warehouses_tournees = Array.isArray(data) ? data : (data.results || []);
            console.log('Entrepôts chargés:', window.warehouses_tournees.length);
            console.log('Liste des entrepôts:', window.warehouses_tournees.map(w => `${w.code} - ${w.name}`));
            return window.warehouses_tournees;
        })
        .catch(error => {
            console.error('Erreur chargement entrepôts:', error);
            window.warehouses_tournees = [];
            throw error;
        });
}

// Charger les codes de prix
function loadCodesPrix() {
    return fetch('/API/codes-prix/?page_size=1000', {
        credentials: 'same-origin',
        headers: {
            'Accept': 'application/json',
        }
    })
        .then(response => {
            if (!response.ok) {
                console.error('Erreur HTTP codes de prix:', response.status, response.statusText);
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            // Gérer la pagination DRF (data.results) ou tableau direct
            window.codes_prix_tournees = Array.isArray(data) ? data : (data.results || []);
            // Filtrer uniquement les codes actifs
            window.codes_prix_tournees = window.codes_prix_tournees.filter(c => c.is_active);
            console.log('Codes de prix chargés:', window.codes_prix_tournees.length);
            return window.codes_prix_tournees;
        })
        .catch(error => {
            console.error('Erreur chargement codes de prix:', error);
            window.codes_prix_tournees = [];
            throw error;
        });
}

// Peupler le select des codes de prix
function populateCodesPrixSelect() {
    const select = document.getElementById('code_prix');
    if (!select) {
        console.warn('Element #code_prix not found');
        return;
    }

    select.innerHTML = '<option value="">Sélectionner le code de prix...</option>';

    if (!window.codes_prix_tournees || !Array.isArray(window.codes_prix_tournees) || window.codes_prix_tournees.length === 0) {
        console.warn('window.codes_prix_tournees is empty:', window.codes_prix_tournees);
        return;
    }

    console.log('Codes de prix à afficher:', window.codes_prix_tournees.length);

    window.codes_prix_tournees.forEach(codePrix => {
        const isDefault = codePrix.is_default ? ' (par défaut)' : '';
        const label = `${codePrix.libelle} (${codePrix.code})${isDefault}`;
        const selected = codePrix.is_default ? ' selected' : '';
        select.innerHTML += `<option value="${codePrix.id}"${selected}>${label}</option>`;
    });

    // Populate and init custom select
    populateCustomSelectOptions('codePrixOptions', window.codes_prix_tournees, 'id', function(cp) {
        var isDefault = cp.is_default ? ' (par défaut)' : '';
        return cp.libelle + ' (' + cp.code + ')' + isDefault;
    }, 'Sélectionner le code de prix...');
    initCustomSelect('customSelectCodePrix', 'codePrixTrigger', 'codePrixDropdown', null, 'codePrixOptions', 'code_prix');

    // Planning modal code prix
    populateCustomSelectOptions('planningCodePrixOptions', window.codes_prix_tournees, 'id', function(cp) {
        var isDefault = cp.is_default ? ' (par défaut)' : '';
        return cp.libelle + ' (' + cp.code + ')' + isDefault;
    }, 'Sélectionner le code de prix...');
    initCustomSelect('customSelectPlanningCodePrix', 'planningCodePrixTrigger', 'planningCodePrixDropdown', null, 'planningCodePrixOptions', 'planning-code-prix');

    // Init planning jour select
    initCustomSelect('customSelectPlanningJour', 'planningJourTrigger', 'planningJourDropdown', null, 'planningJourOptions', 'planning-jour');
}

// Afficher les tournées
function displayTournees(tourneesData) {
    const container = document.getElementById('tournees-container');

    if (!container) {
        console.warn('Element #tournees-container not found - skipping display');
        return;
    }

    if (!tourneesData || tourneesData.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 40px;">
                <i class="fas fa-inbox" style="font-size: 3rem; color: #d1d5db; margin-bottom: 15px;"></i>
                <p style="color: #6b7280;">Aucune tournée trouvée</p>
            </div>
        `;
        return;
    }

    container.innerHTML = tourneesData.map(tournee => `
        <div class="tournee-card">
            <div class="tournee-header">
                <div>
                    <div class="tournee-numero">${tournee.numero}</div>
                    <span class="badge badge-${tournee.statut}">${tournee.statut_display}</span>
                </div>
                <div>
                    ${getTourneeActions(tournee)}
                </div>
            </div>

            <div class="tournee-info">
                <div class="info-item">
                    <i class="fas fa-calendar"></i>
                    <span>${formatDate(tournee.date)}</span>
                </div>
                <div class="info-item">
                    <i class="fas fa-user"></i>
                    <span>${tournee.livreur_nom || 'Non assigné'}</span>
                </div>
                <div class="info-item">
                    <i class="fas fa-clock"></i>
                    <span>${tournee.heure_depart_prevue}</span>
                </div>
                <div class="info-item">
                    <i class="fas fa-map-marker-alt"></i>
                    <span>${tournee.nombre_arrets} arrêts</span>
                </div>
            </div>

            ${tournee.nombre_arrets > 0 ? `
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${tournee.taux_reussite}%"></div>
                </div>
                <div style="text-align: right; font-size: 0.9rem; color: #6b7280; margin-top: 5px;">
                    ${tournee.arrets_livres}/${tournee.nombre_arrets} livrés (${tournee.taux_reussite}%)
                </div>
            ` : ''}

            ${tournee.commentaire ? `
                <div style="margin-top: 10px; padding: 10px; background: #f9fafb; border-radius: 6px; font-size: 0.9rem;">
                    <i class="fas fa-comment"></i> ${tournee.commentaire}
                </div>
            ` : ''}

            <div style="margin-top: 15px;">
                <button class="btn-primary" onclick="viewTourneeDetails(${tournee.id})" style="font-size: 0.9rem;">
                    <i class="fas fa-eye"></i> Voir les détails
                </button>
            </div>
        </div>
    `).join('');
}

// Obtenir les actions pour une tournée
function getTourneeActions(tournee) {
    let actions = '';

    if (tournee.statut === 'planifiee') {
        actions += `
            <button class="btn-success" onclick="demarrerTournee(${tournee.id})" title="Démarrer la tournée">
                <i class="fas fa-play"></i> Démarrer
            </button>
            <button class="btn-primary" onclick="syncTourneeArrets(${tournee.id})" title="Synchroniser avec les clients assignés">
                <i class="fas fa-sync-alt"></i>
            </button>
            <button class="btn-warning" onclick="editTournee(${tournee.id})" title="Modifier">
                <i class="fas fa-edit"></i>
            </button>
            <button class="btn-danger" onclick="annulerTournee(${tournee.id})" title="Annuler">
                <i class="fas fa-times"></i>
            </button>
        `;
    } else if (tournee.statut === 'en_cours') {
        actions += `
            <button class="btn-primary" onclick="syncTourneeArrets(${tournee.id})" title="Synchroniser avec les clients assignés">
                <i class="fas fa-sync-alt"></i> Sync
            </button>
        `;
        // Bouton Modifier si permission accordée
        if (hasPermission('edit_tournee_en_cours')) {
            actions += `
                <button class="btn-warning" onclick="editTournee(${tournee.id})" title="Modifier la tournée en cours">
                    <i class="fas fa-edit"></i>
                </button>
            `;
        }
        actions += `
            <button class="btn-success" onclick="terminerTournee(${tournee.id})" title="Terminer la tournée">
                <i class="fas fa-check"></i> Terminer
            </button>
            <button class="btn-danger" onclick="annulerTournee(${tournee.id})" title="Annuler">
                <i class="fas fa-times"></i>
            </button>
        `;
    } else if (tournee.statut === 'terminee') {
        actions += `
            <span style="color: #10b981; font-weight: 500;">
                <i class="fas fa-check-circle"></i> Terminée
            </span>
        `;
    }

    return actions;
}

// Mettre à jour les statistiques
function updateTourneesStats(tourneesData) {
    if (!tourneesData || !Array.isArray(tourneesData)) {
        console.warn('Invalid tourneesData for updateTourneesStats');
        return;
    }

    const today = new Date().toISOString().split('T')[0];
    const tournees_today = tourneesData.filter(t => t.date === today || t.date_tournee === today);
    const en_cours = tourneesData.filter(t => t.statut === 'en_cours');

    // Calculer le taux de réussite global
    const terminees = tourneesData.filter(t => t.statut === 'terminee');
    let totalArrets = 0;
    let totalLivres = 0;
    terminees.forEach(t => {
        totalArrets += t.nombre_arrets || 0;
        totalLivres += t.arrets_livres || 0;
    });
    const tauxReussite = totalArrets > 0 ? Math.round((totalLivres / totalArrets) * 100) : 0;

    // Mise à jour des éléments avec vérification
    const updateElement = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    };

    updateElement('total-tournees', tourneesData.length);
    updateElement('tournees-today', tournees_today.length);
    updateElement('tournees-en-cours', en_cours.length);
    updateElement('taux-reussite', tauxReussite + '%');
}

// Filtrer les tournées
function filterTournees(status) {
    window.currentFilter = status;

    // Mettre à jour les onglets actifs
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
        // Activer l'onglet correspondant au statut
        if ((status === 'all' && tab.getAttribute('data-tab') === 'tournees') ||
            tab.getAttribute('data-tab') === status) {
            tab.classList.add('active');
        }
    });

    let filtered = window.tournees;
    if (status !== 'all') {
        filtered = window.tournees.filter(t => t.statut === status);
    }

    displayTournees(filtered);
}

// Voir les détails d'une tournée
function viewTourneeDetails(id) {
    fetch(`/API/tournees/${id}/`, {
        credentials: 'same-origin',
        headers: {
            'Accept': 'application/json'
        }
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(apiData => {
            // Transformer les données de l'API vers le format attendu
            const tournee = transformTourneeData(apiData);

            // Transformer les données des arrêts
            tournee.arrets = (apiData.arrets || []).map(arret => ({
                id: arret.id,
                ordre: arret.ordre_passage,
                client: arret.client,
                client_nom: arret.client_nom || 'Client inconnu',
                client_adresse: arret.client_adresse,
                heure_prevue: arret.heure_prevue || '--:--',
                statut: arret.statut || 'en_attente',
                statut_display: getStatutArretDisplay(arret.statut),
                adresse_livraison: arret.client_adresse,
                notes: arret.notes || ''
            }));

            showTourneeDetailsModal(tournee);
        })
        .catch(error => {
            console.error('Erreur lors du chargement des détails:', error);
            showMessage('Erreur lors du chargement des détails: ' + error.message, 'error');
        });
}

// Obtenir le libellé d'un statut d'arrêt
function getStatutArretDisplay(statut) {
    const statuts = {
        'en_attente': 'En attente',
        'livre': 'Livré',
        'echec': 'Échec',
        'reporte': 'Reporté'
    };
    return statuts[statut] || statut;
}

// Afficher la modal des détails
function showTourneeDetailsModal(tournee) {
    const stats = tournee.statistiques || {};

    // Récupérer les arrêts depuis statistiques ou depuis la liste d'arrêts brute
    let arretsVisites = stats.arrets_visites || [];
    let arretsRestants = stats.arrets_restants || [];

    // Si les statistiques ne contiennent pas les arrêts, les construire depuis tournee.arrets
    if (arretsVisites.length === 0 && arretsRestants.length === 0 && tournee.arrets && tournee.arrets.length > 0) {
        tournee.arrets.forEach(arret => {
            const arretData = {
                id: arret.id,
                client_nom: arret.client_nom || 'Client inconnu',
                client_prenom: arret.client_prenom || '',
                adresse: arret.adresse_livraison || arret.client_adresse || '',
                ordre: arret.ordre || arret.ordre_passage || 0,
                heure_prevue: arret.heure_prevue || '--:--',
                statut: arret.statut || 'en_attente',
                heure_arrivee: arret.heure_arrivee || null,
                nom_receptionnaire: arret.nom_receptionnaire || '',
                motif_echec: arret.motif_echec || ''
            };

            if (arret.statut === 'livre' || arret.statut === 'echec') {
                arretsVisites.push(arretData);
            } else {
                arretsRestants.push(arretData);
            }
        });
    }

    const caisse = stats.caisse;

    // Dénominations en DA (Dinar Algérien)
    const denominations = [
        { valeur: 2000, label: '2 000 DA' },
        { valeur: 1000, label: '1 000 DA' },
        { valeur: 500, label: '500 DA' },
        { valeur: 200, label: '200 DA' },
        { valeur: 100, label: '100 DA' },
        { valeur: 50, label: '50 DA' },
        { valeur: 20, label: '20 DA' },
        { valeur: 10, label: '10 DA' },
        { valeur: 5, label: '5 DA' }
    ];

    let detailBilletsHTML = '';
    if (caisse && caisse.detail_billets && Object.keys(caisse.detail_billets).length > 0) {
        detailBilletsHTML = `
            <div style="background: #f9fafb; padding: 15px; border-radius: 8px; margin-top: 15px;">
                <h4 style="margin-bottom: 10px; color: #374151;">💵 Détail des billets</h4>
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;">
                    ${denominations.map(denom => {
                        const quantite = caisse.detail_billets[denom.valeur] || 0;
                        if (quantite > 0) {
                            const sousTotal = denom.valeur * quantite;
                            return `
                                <div style="background: white; padding: 8px; border-radius: 6px; border: 1px solid #e5e7eb;">
                                    <div style="font-weight: 600; color: #8b5cf6;">${denom.label}</div>
                                    <div style="font-size: 0.9rem; color: #6b7280;">× ${quantite} = ${sousTotal.toFixed(2)} DA</div>
                                </div>
                            `;
                        }
                        return '';
                    }).filter(html => html).join('')}
                </div>
            </div>
        `;
    }

    const modalContent = `
        <div style="padding: 30px;">
            <h2 style="margin-bottom: 20px;">${tournee.numero_tournee || tournee.numero}</h2>

            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-bottom: 30px;">
                <div><strong>Date:</strong> ${formatDate(tournee.date_tournee || tournee.date)}</div>
                <div><strong>Livreur:</strong> ${tournee.livreur_nom || 'Non assigné'}</div>
                <div><strong>Départ prévu:</strong> ${tournee.heure_debut || tournee.heure_depart_prevue || '-'}</div>
                <div><strong>Retour prévu:</strong> ${tournee.heure_fin || tournee.heure_retour_prevue || '-'}</div>
                <div><strong>Statut:</strong> <span class="badge badge-${tournee.statut}">${tournee.statut_display || getStatutDisplay(tournee.statut)}</span></div>
            </div>

            ${caisse ? `
                <div style="background: #dbeafe; padding: 20px; border-radius: 10px; margin-bottom: 25px;">
                    <h3 style="margin-bottom: 15px; color: #1e40af;">💰 Rapport de Caisse</h3>
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px;">
                        <div>
                            <div style="font-size: 0.9rem; color: #3730a3;">Fonds de départ</div>
                            <div style="font-size: 1.3rem; font-weight: 700; color: #1e40af;">
                                ${parseFloat(caisse.fonds_depart || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} DA
                            </div>
                        </div>
                        <div>
                            <div style="font-size: 0.9rem; color: #3730a3;">Total encaissements</div>
                            <div style="font-size: 1.3rem; font-weight: 700; color: #059669;">
                                ${parseFloat(caisse.total_encaissements || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} DA
                            </div>
                        </div>
                        <div>
                            <div style="font-size: 0.9rem; color: #3730a3;">Espèces</div>
                            <div style="font-weight: 600;">${parseFloat(caisse.total_especes || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} DA</div>
                        </div>
                        <div>
                            <div style="font-size: 0.9rem; color: #3730a3;">Cartes</div>
                            <div style="font-weight: 600;">${parseFloat(caisse.total_cartes || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} DA</div>
                        </div>
                        <div>
                            <div style="font-size: 0.9rem; color: #3730a3;">Chèques</div>
                            <div style="font-weight: 600;">${parseFloat(caisse.total_cheques || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} DA</div>
                        </div>
                        <div>
                            <div style="font-size: 0.9rem; color: #3730a3;">À crédit</div>
                            <div style="font-weight: 600;">${parseFloat(caisse.total_credits || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} DA</div>
                        </div>
                        <div>
                            <div style="font-size: 0.9rem; color: #3730a3;">Dépenses</div>
                            <div style="font-weight: 600; color: #dc2626;">
                                ${parseFloat(caisse.total_depenses || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} DA
                            </div>
                        </div>
                        <div>
                            <div style="font-size: 0.9rem; color: #3730a3;">Solde réel</div>
                            <div style="font-size: 1.2rem; font-weight: 700; color: ${caisse.ecart < 0 ? '#dc2626' : '#059669'};">
                                ${parseFloat(caisse.solde_final_reel || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} DA
                            </div>
                        </div>
                    </div>
                    ${detailBilletsHTML}
                </div>
            ` : `
                <div style="background: #f3f4f6; padding: 15px; border-radius: 8px; margin-bottom: 25px; text-align: center; color: #6b7280;">
                    <i class="fas fa-info-circle"></i> Aucun rapport de caisse disponible
                </div>
            `}

            <div style="margin-bottom: 25px;">
                <h3 style="margin-bottom: 15px; color: #059669;">
                    ✅ Clients visités (${arretsVisites.length})
                </h3>
                ${arretsVisites.length > 0 ? arretsVisites.map(arret => `
                    <div class="arret-item">
                        <div>
                            <strong>#${arret.ordre}</strong> - ${arret.client_nom} ${arret.client_prenom || ''}
                            <div style="font-size: 0.9rem; color: #6b7280;">
                                <i class="fas fa-clock"></i> ${arret.heure_prevue || '-'}
                                ${arret.heure_arrivee ? ` → ${arret.heure_arrivee}` : ''}
                                ${arret.adresse ? `<br><i class="fas fa-map-marker-alt"></i> ${arret.adresse}` : ''}
                                ${arret.nom_receptionnaire ? `<br><i class="fas fa-user"></i> ${arret.nom_receptionnaire}` : ''}
                                ${arret.motif_echec ? `<br><i class="fas fa-exclamation-triangle"></i> ${arret.motif_echec}` : ''}
                            </div>
                        </div>
                        <span class="badge badge-${arret.statut}">${arret.statut === 'livre' ? 'Livré' : 'Échec'}</span>
                    </div>
                `).join('') : '<p style="color: #9ca3af; text-align: center; padding: 20px;">Aucun client visité</p>'}
            </div>

            <div style="margin-bottom: 25px;">
                <h3 style="margin-bottom: 15px; color: #f59e0b;">
                    ⏳ Clients restants (${arretsRestants.length})
                </h3>
                ${arretsRestants.length > 0 ? arretsRestants.map(arret => `
                    <div class="arret-item">
                        <div>
                            <strong>#${arret.ordre}</strong> - ${arret.client_nom} ${arret.client_prenom || ''}
                            <div style="font-size: 0.9rem; color: #6b7280;">
                                <i class="fas fa-clock"></i> ${arret.heure_prevue || '-'}
                                ${arret.adresse ? `<br><i class="fas fa-map-marker-alt"></i> ${arret.adresse}` : ''}
                            </div>
                        </div>
                        <span class="badge badge-en_attente">En attente</span>
                    </div>
                `).join('') : '<p style="color: #9ca3af; text-align: center; padding: 20px;">Tous les clients ont été visités</p>'}
            </div>

            <div style="margin-top: 30px; text-align: right;">
                <button class="btn-secondary" onclick="closeDetailsModal()">Fermer</button>
            </div>
        </div>
    `;

    const modal = document.createElement('div');
    modal.id = 'detailsModal';
    modal.className = 'modal';
    modal.style.display = 'block';
    modal.innerHTML = `<div class="modal-content">${modalContent}</div>`;
    document.body.appendChild(modal);

    // Fermer en cliquant en dehors
    modal.onclick = function(event) {
        if (event.target == modal) {
            closeDetailsModal();
        }
    }
}

function closeDetailsModal() {
    const modal = document.getElementById('detailsModal');
    if (modal) {
        document.body.removeChild(modal);
    }
}

// Démarrer une tournée
function demarrerTournee(id) {
    if (!confirm('Démarrer cette tournée ?')) return;

    fetch(`/API/tournees/${id}/demarrer/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(result => {
        loadTournees();
        showMessage('Tournée démarrée', 'success');
    })
    .catch(error => {
        console.error('Erreur:', error);
        showMessage('Erreur lors du démarrage', 'error');
    });
}

// Terminer une tournée
function terminerTournee(id) {
    if (!confirm('Terminer cette tournée ?')) return;

    fetch(`/API/tournees/${id}/terminer/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(result => {
        loadTournees();
        showMessage(`Tournée terminée - Taux de réussite: ${result.taux_reussite}%`, 'success');
    })
    .catch(error => {
        console.error('Erreur:', error);
        showMessage('Erreur lors de la finalisation', 'error');
    });
}

// Annuler une tournée
function annulerTournee(id) {
    if (!confirm('Annuler cette tournée ?')) return;

    fetch(`/API/tournees/${id}/`, {
        method: 'PATCH',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ statut: 'annulee' })
    })
    .then(response => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
    })
    .then(result => {
        loadTournees();
        showMessage('Tournée annulée', 'success');
    })
    .catch(error => {
        console.error('Erreur:', error);
        showMessage('Erreur lors de l\'annulation', 'error');
    });
}

// Ouvrir le modal de tournée
async function openTourneeModal(tourneeId = null) {
    const modal = document.getElementById('tourneeModal');
    const title = document.getElementById('modal-title');

    window.arretCounter = 0;
    document.getElementById('arrets-container').innerHTML = '';

    // Afficher le modal immédiatement
    modal.style.display = 'block';

    if (tourneeId) {
        title.textContent = 'Modifier la Tournée';
    } else {
        title.textContent = 'Nouvelle Tournée';
    }

    // Charger toutes les données nécessaires en parallèle
    const loadPromises = [];

    if (!window.livreurs_tournees || window.livreurs_tournees.length === 0) {
        console.log('Rechargement des livreurs...');
        loadPromises.push(loadLivreurs());
    } else {
        loadPromises.push(Promise.resolve());
    }

    if (!window.warehouses_tournees || window.warehouses_tournees.length === 0) {
        console.log('Rechargement des entrepôts...');
        loadPromises.push(loadWarehouses());
    } else {
        loadPromises.push(Promise.resolve());
    }

    if (!window.clients_tournees || window.clients_tournees.length === 0) {
        console.log('Rechargement des clients...');
        loadPromises.push(loadClients());
    } else {
        console.log('Clients déjà chargés:', window.clients_tournees.length);
        loadPromises.push(Promise.resolve());
    }

    if (!window.codes_prix_tournees || window.codes_prix_tournees.length === 0) {
        console.log('Rechargement des codes de prix...');
        loadPromises.push(loadCodesPrix());
    } else {
        loadPromises.push(Promise.resolve());
    }

    // Attendre que toutes les données soient chargées
    try {
        await Promise.all(loadPromises);
    } catch (err) {
        console.error('Erreur rechargement données:', err);
        showMessage('Erreur lors du chargement des données', 'warning');
    }

    // Peupler les selects après le chargement
    populateLivreursSelect();
    populateWarehousesSelect();
    populateCodesPrixSelect();

    if (tourneeId) {
        // Charger les données de la tournée après que les selects soient peuplés
        loadTourneeData(tourneeId);
    } else {
        document.getElementById('tournee-form').reset();
        document.getElementById('tournee-id').value = '';
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('date').value = today;
    }
}

function closeTourneeModal() {
    document.getElementById('tourneeModal').style.display = 'none';
}

// Peupler le select des livreurs
function populateLivreursSelect() {
    const select = document.getElementById('livreur');
    if (!select) {
        console.warn('Element #livreur not found');
        return;
    }

    select.innerHTML = '<option value="">Sélectionner un livreur...</option>';

    if (!window.livreurs_tournees || !Array.isArray(window.livreurs_tournees) || window.livreurs_tournees.length === 0) {
        console.warn('window.livreurs_tournees is empty, not an array, or undefined:', window.livreurs_tournees);
        return;
    }

    const livreursActifs = window.livreurs_tournees.filter(l => l.is_active && l.is_disponible);
    console.log('Livreurs actifs filtrés:', livreursActifs.length, '/', window.livreurs_tournees.length);

    if (livreursActifs.length === 0) {
        console.warn('Aucun livreur actif et disponible trouvé');
    }

    livreursActifs.forEach(livreur => {
        select.innerHTML += `<option value="${livreur.id}">${livreur.full_name} - ${livreur.vehicule_type || 'Livreur'}</option>`;
    });

    // Populate and init custom select
    populateCustomSelectOptions('livreurOptions', livreursActifs, 'id', function(l) {
        return l.full_name + ' - ' + (l.vehicule_type || 'Livreur');
    }, 'Sélectionner un livreur...');
    initCustomSelect('customSelectLivreur', 'livreurTrigger', 'livreurDropdown', 'livreurSearch', 'livreurOptions', 'livreur');

    // Planning modal livreur
    populateCustomSelectOptions('planningLivreurOptions', livreursActifs, 'id', function(l) {
        return l.full_name + ' - ' + (l.vehicule_type || 'Livreur');
    }, 'Sélectionner un livreur...');
    initCustomSelect('customSelectPlanningLivreur', 'planningLivreurTrigger', 'planningLivreurDropdown', 'planningLivreurSearch', 'planningLivreurOptions', 'planning-livreur');
}

// Peupler le select des entrepôts
function populateWarehousesSelect() {
    const select = document.getElementById('warehouse');
    if (!select) {
        console.warn('Element #warehouse not found');
        return;
    }

    select.innerHTML = '<option value="">Sélectionner...</option>';

    if (!window.warehouses_tournees || !Array.isArray(window.warehouses_tournees) || window.warehouses_tournees.length === 0) {
        console.warn('window.warehouses_tournees is empty, not an array, or undefined:', window.warehouses_tournees);
        return;
    }

    console.log('Entrepôts à afficher:', window.warehouses_tournees.length);

    window.warehouses_tournees.forEach(warehouse => {
        // Afficher le code et le nom pour mieux identifier
        const label = warehouse.code ? `${warehouse.code} - ${warehouse.name}` : warehouse.name;
        select.innerHTML += `<option value="${warehouse.id}">${label}</option>`;
    });

    // Populate and init custom select
    populateCustomSelectOptions('warehouseOptions', window.warehouses_tournees, 'id', function(w) {
        return w.code ? w.code + ' - ' + w.name : w.name;
    }, 'Sélectionner...');
    initCustomSelect('customSelectWarehouse', 'warehouseTrigger', 'warehouseDropdown', 'warehouseSearch', 'warehouseOptions', 'warehouse');
}

// Ajouter un formulaire d'arrêt
function addArretForm() {
    // Vérifier si les clients sont chargés, sinon les charger d'abord
    if (!window.clients_tournees || !Array.isArray(window.clients_tournees) || window.clients_tournees.length === 0) {
        console.warn('Clients non chargés, chargement en cours...');
        showMessage('Chargement des clients...', 'info');

        loadClients()
            .then(() => {
                console.log('Clients chargés, ajout du formulaire d\'arrêt');
                addArretFormInternal();
            })
            .catch(err => {
                console.error('Erreur lors du chargement des clients:', err);
                showMessage('Impossible de charger les clients. Veuillez réessayer.', 'error');
            });
        return;
    }

    addArretFormInternal();
}

// Fonction interne pour ajouter le formulaire d'arrêt
function addArretFormInternal(clientData = null) {
    window.arretCounter++;
    const counter = window.arretCounter;
    const container = document.getElementById('arrets-container');
    const arretDiv = document.createElement('div');
    arretDiv.className = 'arret-form-item';
    arretDiv.id = `arret-${counter}`;

    // S'assurer que les clients sont chargés
    const clientsOptions = (window.clients_tournees && Array.isArray(window.clients_tournees) && window.clients_tournees.length > 0)
        ? window.clients_tournees.map(c => `<option value="${c.id}">${c.nom || ''} ${c.prenom || ''}</option>`).join('')
        : '<option value="" disabled>Aucun client disponible</option>';

    console.log('Ajout arrêt - clients disponibles:', window.clients_tournees ? window.clients_tournees.length : 0);

    // Info client si fourni
    const clientInfo = clientData ? `
        <div style="background: #f0fdf4; padding: 10px; border-radius: 6px; margin-bottom: 15px; border-left: 4px solid #10b981;">
            <div style="font-weight: 600; color: #166534;">${clientData.client_nom || 'Client'}</div>
            ${clientData.client_adresse ? `<div style="font-size: 0.85rem; color: #4b5563;"><i class="fas fa-map-marker-alt"></i> ${clientData.client_adresse}</div>` : ''}
            ${clientData.client_telephone ? `<div style="font-size: 0.85rem; color: #4b5563;"><i class="fas fa-phone"></i> ${clientData.client_telephone}</div>` : ''}
        </div>
    ` : '';

    arretDiv.innerHTML = `
        <button type="button" class="remove-arret" onclick="removeArret(${counter})">×</button>
        <h4 style="margin-bottom: 15px;">Arrêt #${counter}</h4>
        ${clientInfo}
        <div class="form-grid">
            <div class="form-group full-width">
                <label>Client *</label>
                <div class="custom-select-container" id="customSelectArretClient${counter}">
                    <div class="custom-select-trigger" id="arretClientTrigger${counter}">
                        <span class="selected-text placeholder">Sélectionner un client...</span>
                        <i class="fas fa-chevron-down arrow"></i>
                    </div>
                    <div class="custom-select-dropdown" id="arretClientDropdown${counter}">
                        <div class="custom-select-search">
                            <input type="text" id="arretClientSearch${counter}" placeholder="Rechercher un client...">
                        </div>
                        <div class="custom-select-options" id="arretClientOptions${counter}"></div>
                    </div>
                    <div style="position:absolute;width:0;height:0;overflow:hidden;opacity:0;pointer-events:none;">
                        <select class="arret-client" id="arretClient${counter}" required data-lat="${clientData?.client_lat || ''}" data-lng="${clientData?.client_lng || ''}">
                            <option value="">Sélectionner...</option>
                            ${clientsOptions}
                        </select>
                    </div>
                </div>
            </div>
        </div>
    `;

    container.appendChild(arretDiv);

    // Initialiser le custom select pour ce nouvel arrêt
    setTimeout(function() {
        var clientsList = window.clients_tournees || [];
        populateCustomSelectOptions('arretClientOptions' + counter, clientsList, 'id', function(c) {
            return (c.nom || '') + ' ' + (c.prenom || '');
        }, 'Sélectionner un client...');
        initCustomSelect(
            'customSelectArretClient' + counter,
            'arretClientTrigger' + counter,
            'arretClientDropdown' + counter,
            'arretClientSearch' + counter,
            'arretClientOptions' + counter,
            'arretClient' + counter
        );

        // Si un client est fourni, le sélectionner automatiquement
        if (clientData && clientData.client) {
            const selectEl = document.getElementById('arretClient' + counter);
            if (selectEl) {
                selectEl.value = clientData.client;
                // Mettre à jour l'affichage du custom select
                const trigger = document.getElementById('arretClientTrigger' + counter);
                if (trigger) {
                    const textSpan = trigger.querySelector('.selected-text');
                    if (textSpan) {
                        textSpan.textContent = clientData.client_nom || 'Client';
                        textSpan.classList.remove('placeholder');
                    }
                }
            }
        }
    }, 50);
}

// Charger les clients assignés au livreur pour un jour donné
async function loadClientsAssignesJour(livreurId, date) {
    if (!livreurId || !date) return [];

    try {
        // Convertir la date en jour de la semaine (1=Lundi, 7=Dimanche)
        const dateObj = new Date(date);
        const dayOfWeek = dateObj.getDay();
        const jourSemaine = dayOfWeek === 0 ? 7 : dayOfWeek;

        console.log('[TOURNEES] Chargement clients assignés - Livreur:', livreurId, 'Date:', date, 'Jour:', jourSemaine);

        const response = await fetch(`/API/distribution/clients-livreurs-hebdo/?livreur=${livreurId}&jour_semaine=${jourSemaine}&is_active=true`);
        const data = await response.json();
        const configs = Array.isArray(data) ? data : (data.results || []);

        console.log('[TOURNEES] Clients assignés trouvés:', configs.length);
        return configs;
    } catch (error) {
        console.error('[TOURNEES] Erreur chargement clients assignés:', error);
        return [];
    }
}

// Auto-remplir les arrêts avec les clients assignés
async function autoFillArretsFromConfig() {
    const livreurId = document.getElementById('livreur').value;
    const date = document.getElementById('date').value;

    if (!livreurId || !date) {
        showMessage('Veuillez sélectionner un livreur et une date', 'warning');
        return;
    }

    // Vider les arrêts existants
    const container = document.getElementById('arrets-container');
    container.innerHTML = '<div style="text-align: center; padding: 20px;"><i class="fas fa-spinner fa-spin"></i> Chargement des clients assignés...</div>';

    // Charger les clients assignés
    const configs = await loadClientsAssignesJour(livreurId, date);

    container.innerHTML = '';
    window.arretCounter = 0;

    if (configs.length === 0) {
        container.innerHTML = `
            <div style="background: #fef3c7; padding: 15px; border-radius: 8px; text-align: center; color: #92400e;">
                <i class="fas fa-info-circle"></i> Aucun client assigné à ce livreur pour ce jour.
                <br><small>Vous pouvez ajouter des arrêts manuellement.</small>
            </div>
        `;
        return;
    }

    // Ajouter les clients comme arrêts
    configs.sort((a, b) => (a.ordre_passage || 0) - (b.ordre_passage || 0));

    for (const config of configs) {
        addArretFormInternal(config);
    }

    showMessage(`${configs.length} client(s) assigné(s) chargé(s) automatiquement`, 'success');
}

// Synchroniser les arrêts d'une tournée avec les clients assignés
async function syncTourneeArrets(tourneeId) {
    if (!tourneeId) {
        showMessage('Aucune tournée sélectionnée', 'error');
        return;
    }

    if (!confirm('Voulez-vous synchroniser les arrêts de cette tournée avec la configuration actuelle des clients assignés ?\n\nCela va mettre à jour les arrêts en fonction de la configuration "Clients / Chauffeurs".')) {
        return;
    }

    try {
        showMessage('Synchronisation en cours...', 'info');

        const response = await fetch(`/API/tournees/${tourneeId}/sync_arrets/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            credentials: 'same-origin'
        });

        const data = await response.json();

        if (response.ok) {
            const added = data.arrets_ajoutes || 0;
            const removed = data.arrets_supprimes || 0;
            const updated = data.arrets_mis_a_jour || 0;
            let message = 'Synchronisation réussie ! ';
            const parts = [];
            if (added > 0) parts.push(`${added} arrêt(s) ajouté(s)`);
            if (removed > 0) parts.push(`${removed} supprimé(s)`);
            if (updated > 0) parts.push(`${updated} adresse(s) mise(s) à jour`);
            if (parts.length === 0) parts.push('Aucun changement');
            message += parts.join(', ');
            showMessage(message, 'success');
            // Recharger les tournées pour voir les changements
            loadTournees();
        } else {
            showMessage(data.error || data.detail || 'Erreur lors de la synchronisation', 'error');
        }
    } catch (error) {
        console.error('Erreur synchronisation:', error);
        showMessage('Erreur de connexion lors de la synchronisation', 'error');
    }
}

// Synchroniser toutes les tournées en cours
async function syncAllTourneesEnCours() {
    if (!confirm('Voulez-vous synchroniser TOUTES les tournées en cours avec la configuration actuelle des clients assignés ?')) {
        return;
    }

    try {
        showMessage('Synchronisation de toutes les tournées en cours...', 'info');

        const response = await fetch('/API/tournees/sync_all_en_cours/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            credentials: 'same-origin'
        });

        const data = await response.json();

        if (response.ok) {
            showMessage(`Synchronisation terminée ! ${data.tournees_synced || 0} tournée(s) mise(s) à jour`, 'success');
            loadTournees();
        } else {
            showMessage(data.error || 'Erreur lors de la synchronisation', 'error');
        }
    } catch (error) {
        console.error('Erreur synchronisation globale:', error);
        showMessage('Erreur de connexion', 'error');
    }
}

function removeArret(id) {
    const arret = document.getElementById(`arret-${id}`);
    if (arret) {
        arret.remove();
    }
}

// Soumettre le formulaire de tournée
// Configuration des event handlers
function setupFormHandlers() {
    const form = document.getElementById('tournee-form');
    if (!form) {
        console.warn('Form #tournee-form not found - skipping handler setup');
        return;
    }

    // Éviter de configurer plusieurs fois
    if (form.dataset.handlerConfigured) {
        return;
    }
    form.dataset.handlerConfigured = 'true';

    form.addEventListener('submit', function(e) {
        e.preventDefault();

        const id = document.getElementById('tournee-id').value;
        const codePrixValue = document.getElementById('code_prix').value;
        const livreurValue = document.getElementById('livreur').value;
        const warehouseValue = document.getElementById('warehouse').value;
        const dateValue = document.getElementById('date').value;

        // Validation
        if (!livreurValue) {
            showMessage('Veuillez sélectionner un livreur', 'error');
            return;
        }

        // Si c'est une nouvelle tournée, vérifier d'abord si une existe déjà
        if (!id) {
            checkExistingTournee(livreurValue, dateValue).then(existingTournee => {
                if (existingTournee) {
                    // Une tournée existe déjà, proposer de la modifier
                    showTourneeExistsDialog(existingTournee, function() {
                        // L'utilisateur veut modifier la tournée existante
                        openTourneeModal(existingTournee.id);
                    });
                } else {
                    // Pas de tournée existante, créer une nouvelle
                    submitTourneeForm(null, dateValue, livreurValue, warehouseValue, codePrixValue);
                }
            });
        } else {
            // Modification d'une tournée existante
            submitTourneeForm(id, dateValue, livreurValue, warehouseValue, codePrixValue);
        }
    });
}

// Vérifier si une tournée existe déjà pour ce livreur et cette date
function checkExistingTournee(livreurId, date) {
    return fetch(`/API/tournees/?livreur=${livreurId}&date_tournee=${date}`, {
        credentials: 'same-origin',
        headers: { 'Accept': 'application/json' }
    })
    .then(response => response.json())
    .then(data => {
        const tournees = Array.isArray(data) ? data : (data.results || []);
        return tournees.length > 0 ? tournees[0] : null;
    })
    .catch(err => {
        console.error('[TOURNEES] Erreur vérification tournée existante:', err);
        return null;
    });
}

// Afficher le dialogue quand une tournée existe déjà
function showTourneeExistsDialog(existingTournee, onModify) {
    const livreurNom = existingTournee.livreur_nom || 'ce livreur';
    const date = existingTournee.date_tournee;
    const numero = existingTournee.numero_tournee;

    const message = `Une tournée existe déjà pour ${livreurNom} le ${formatDate(date)}:\n\n` +
        `📋 ${numero}\n` +
        `📊 Statut: ${existingTournee.statut}\n\n` +
        `Voulez-vous modifier cette tournée existante ?`;

    if (confirm(message)) {
        onModify();
    }
}

// Soumettre le formulaire de tournée
function submitTourneeForm(id, dateValue, livreurValue, warehouseValue, codePrixValue) {
    // Générer le numéro de tournée
    const dateFormatted = dateValue.replace(/-/g, '');
    const timestamp = Date.now().toString().slice(-4);
    const numeroTournee = 'T-' + dateFormatted + '-' + timestamp;

    const data = {
        date_tournee: dateValue,
        numero_tournee: numeroTournee,
        livreur: parseInt(livreurValue),
        warehouse: warehouseValue ? parseInt(warehouseValue) : null,
        code_prix: codePrixValue ? parseInt(codePrixValue) : null,
        heure_debut: document.getElementById('heure_depart_prevue').value || null,
        heure_fin: document.getElementById('heure_retour_prevue').value || null,
        notes: document.getElementById('commentaire').value || '',
        statut: 'planifiee'
    };

    // Si modification, utiliser le numéro existant
    if (id && window.currentTourneeNumero) {
        data.numero_tournee = window.currentTourneeNumero;
    }

    console.log('[TOURNEES] Données à envoyer:', data);

    const url = id ? `/API/tournees/${id}/` : '/API/tournees/';
    const method = id ? 'PUT' : 'POST';

    fetch(url, {
        method: method,
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(data)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => {
                console.error('[TOURNEES] Erreur API:', err);
                let errorMsg = 'Erreur lors de l\'enregistrement';
                if (err.non_field_errors) {
                    if (err.non_field_errors[0].includes('unique')) {
                        errorMsg = 'Une tournée existe déjà pour ce livreur à cette date';
                    } else {
                        errorMsg = err.non_field_errors[0];
                    }
                } else if (err.detail) {
                    errorMsg = err.detail;
                } else {
                    const erreurs = [];
                    for (const [field, messages] of Object.entries(err)) {
                        erreurs.push(`${field}: ${messages.join(', ')}`);
                    }
                    if (erreurs.length > 0) {
                        errorMsg = erreurs.join('\n');
                    }
                }
                throw new Error(errorMsg);
            });
        }
        return response.json();
    })
    .then(tournee => {
        // Si c'est une modification, supprimer les anciens arrêts d'abord
        const arrets = collectArrets();
        if (id && arrets.length > 0) {
            // Supprimer les anciens arrêts puis créer les nouveaux
            return deleteExistingArrets(tournee.id).then(() => createArrets(tournee.id, arrets));
        } else if (arrets.length > 0) {
            // Nouvelle tournée, créer directement les arrêts
            return createArrets(tournee.id, arrets);
        }
        return tournee;
    })
    .then(() => {
        closeTourneeModal();
        loadTournees();
        showMessage(id ? 'Tournée modifiée avec succès' : 'Tournée créée avec succès', 'success');
    })
    .catch(error => {
        console.error('Erreur:', error);
        showMessage(error.message || 'Erreur lors de l\'enregistrement', 'error');
    });
}

// Collecter les données des arrêts
function collectArrets() {
    const arrets = [];
    const container = document.getElementById('arrets-container');
    const arretForms = container.querySelectorAll('.arret-form-item');

    arretForms.forEach((form, index) => {
        const clientSelect = form.querySelector('.arret-client');
        const client = clientSelect ? clientSelect.value : null;

        if (client) {
            // Récupérer les coordonnées GPS du client si disponibles
            const lat = clientSelect.dataset.lat || null;
            const lng = clientSelect.dataset.lng || null;

            // Récupérer l'adresse du client depuis la liste des clients
            let adresse = '';
            if (window.clients_tournees && Array.isArray(window.clients_tournees)) {
                const clientData = window.clients_tournees.find(c => c.id == client);
                if (clientData) {
                    adresse = clientData.adresse || '';
                }
            }

            arrets.push({
                client: parseInt(client),
                ordre_passage: index + 1,
                latitude: lat,
                longitude: lng
            });
        }
    });

    return arrets;
}

// Supprimer les arrêts existants d'une tournée
async function deleteExistingArrets(tourneeId) {
    console.log('[TOURNEES] Suppression des arrêts existants pour tournée:', tourneeId);

    try {
        // Récupérer les arrêts existants
        const response = await fetch(`/API/distribution/arrets/?tournee=${tourneeId}`, {
            credentials: 'same-origin',
            headers: { 'Accept': 'application/json' }
        });

        if (!response.ok) {
            console.warn('[TOURNEES] Impossible de récupérer les arrêts existants');
            return;
        }

        const data = await response.json();
        const arrets = Array.isArray(data) ? data : (data.results || []);

        // Supprimer seulement les arrêts en attente (ne pas supprimer ceux déjà livrés)
        for (const arret of arrets) {
            if (arret.statut === 'en_attente') {
                await fetch(`/API/distribution/arrets/${arret.id}/`, {
                    method: 'DELETE',
                    credentials: 'same-origin',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                });
                console.log('[TOURNEES] Arrêt supprimé:', arret.id);
            }
        }
    } catch (error) {
        console.error('[TOURNEES] Erreur suppression arrêts:', error);
    }
}

// Créer les arrêts
async function createArrets(tourneeId, arrets) {
    console.log('[TOURNEES] Création des arrêts pour tournée:', tourneeId);
    console.log('[TOURNEES] Arrêts à créer:', arrets);

    const results = [];
    for (const arret of arrets) {
        arret.tournee = tourneeId;
        console.log('[TOURNEES] Envoi arrêt:', JSON.stringify(arret));

        try {
            const response = await fetch('/API/distribution/arrets/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify(arret)
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error('[TOURNEES] Erreur création arrêt:', errorData);
            } else {
                const data = await response.json();
                console.log('[TOURNEES] Arrêt créé:', data);
                results.push(response);
            }
        } catch (error) {
            console.error('[TOURNEES] Exception création arrêt:', error);
        }
    }

    return results;
}

// Modifier une tournée
function editTournee(id) {
    openTourneeModal(id);
}

// Charger les données d'une tournée
function loadTourneeData(id) {
    // S'assurer que les clients sont chargés avant de charger les données de la tournée
    const ensureClientsLoaded = (!window.clients_tournees || window.clients_tournees.length === 0)
        ? loadClients()
        : Promise.resolve();

    ensureClientsLoaded
        .then(() => fetch(`/API/tournees/${id}/`))
        .then(response => {
            if (!response.ok) {
                throw new Error('Erreur HTTP: ' + response.status);
            }
            return response.json();
        })
        .then(tournee => {
            console.log('[TOURNEES] Données chargées:', tournee);
            console.log('[TOURNEES] Champs: date_tournee=' + tournee.date_tournee + ', livreur=' + tournee.livreur);

            document.getElementById('tournee-id').value = tournee.id;

            // Utiliser les noms de champs corrects du serializer TourneeMobile
            var dateInput = document.getElementById('date');
            if (dateInput) {
                dateInput.value = tournee.date_tournee || '';
                console.log('[TOURNEES] Date définie:', dateInput.value);
            }

            // Fonction helper pour mettre à jour un custom select trigger
            function updateCustomSelectTrigger(triggerId, text) {
                var trigger = document.getElementById(triggerId);
                if (trigger) {
                    var span = trigger.querySelector('.selected-text');
                    if (span) {
                        span.textContent = text;
                        span.classList.remove('placeholder');
                    } else {
                        trigger.innerHTML = '<span class="selected-text">' + text + '</span><i class="fas fa-chevron-down arrow"></i>';
                    }
                }
            }

            // Mettre à jour le select livreur et son custom select
            var livreurSelect = document.getElementById('livreur');
            if (livreurSelect && tournee.livreur) {
                // Vérifier si l'option existe déjà dans le select
                var optionExists = Array.from(livreurSelect.options).some(opt => opt.value == tournee.livreur);
                if (!optionExists && tournee.livreur_nom) {
                    // Ajouter l'option si elle n'existe pas (livreur non disponible mais assigné)
                    var newOption = document.createElement('option');
                    newOption.value = tournee.livreur;
                    newOption.textContent = tournee.livreur_nom + ' (assigné)';
                    livreurSelect.appendChild(newOption);
                }
                livreurSelect.value = tournee.livreur;
                var selectedOption = livreurSelect.options[livreurSelect.selectedIndex];
                if (selectedOption && selectedOption.value) {
                    updateCustomSelectTrigger('livreurTrigger', selectedOption.text);
                }
                console.log('[TOURNEES] Livreur défini:', livreurSelect.value);
            }

            // Note: TourneeMobile n'a pas de champ warehouse, ignorer

            // Formater l'heure pour le champ input (HH:mm seulement)
            function formatTimeForInput(timeStr) {
                if (!timeStr) return '';
                // Prendre seulement HH:mm (les 5 premiers caractères)
                return timeStr.substring(0, 5);
            }

            // TourneeMobile utilise heure_debut et heure_fin
            var heureDepart = document.getElementById('heure_depart_prevue');
            var heureRetour = document.getElementById('heure_retour_prevue');
            if (heureDepart) {
                heureDepart.value = formatTimeForInput(tournee.heure_debut);
                console.log('[TOURNEES] Heure départ définie:', heureDepart.value);
            }
            if (heureRetour) {
                heureRetour.value = formatTimeForInput(tournee.heure_fin);
                console.log('[TOURNEES] Heure retour définie:', heureRetour.value);
            }

            // Stocker le numero_tournee pour la modification
            window.currentTourneeNumero = tournee.numero_tournee;

            // TourneeMobile utilise 'notes' au lieu de 'commentaire'
            var commentaireInput = document.getElementById('commentaire');
            if (commentaireInput) {
                commentaireInput.value = tournee.notes || '';
            }

            // Code prix si présent
            var codePrixSelect = document.getElementById('code_prix');
            if (codePrixSelect && tournee.code_prix) {
                // Vérifier si l'option existe déjà dans le select
                var optionExists = Array.from(codePrixSelect.options).some(opt => opt.value == tournee.code_prix);
                if (!optionExists && (tournee.code_prix_libelle || tournee.code_prix_code)) {
                    // Ajouter l'option si elle n'existe pas
                    var newOption = document.createElement('option');
                    newOption.value = tournee.code_prix;
                    newOption.textContent = tournee.code_prix_libelle + ' (' + tournee.code_prix_code + ')';
                    codePrixSelect.appendChild(newOption);
                }
                codePrixSelect.value = tournee.code_prix;
                var selectedOption = codePrixSelect.options[codePrixSelect.selectedIndex];
                if (selectedOption && selectedOption.value) {
                    updateCustomSelectTrigger('codePrixTrigger', selectedOption.text);
                }
                console.log('[TOURNEES] Code prix défini:', codePrixSelect.value);
            }

            // Charger les arrêts existants si disponibles
            if (tournee.arrets && tournee.arrets.length > 0) {
                console.log('[TOURNEES] Chargement de', tournee.arrets.length, 'arrêts');

                // S'assurer que les clients sont chargés avant d'ajouter les arrêts
                const loadClientsPromise = (!window.clients_tournees || window.clients_tournees.length === 0)
                    ? loadClients()
                    : Promise.resolve();

                loadClientsPromise.then(function() {
                    tournee.arrets.forEach(function(arret, index) {
                        console.log('[TOURNEES] Ajout arrêt:', arret.client, arret.client_nom);
                        addArretFormInternal();
                        var lastArret = document.getElementById('arret-' + window.arretCounter);
                        if (lastArret) {
                            var clientSelect = lastArret.querySelector('.arret-client');
                            if (clientSelect) {
                                // Vérifier si l'option existe, sinon l'ajouter
                                var optionExists = Array.from(clientSelect.options).some(function(opt) {
                                    return opt.value == arret.client;
                                });
                                if (!optionExists && arret.client_nom) {
                                    var newOption = document.createElement('option');
                                    newOption.value = arret.client;
                                    newOption.textContent = arret.client_nom;
                                    clientSelect.appendChild(newOption);
                                }
                                clientSelect.value = arret.client;
                                console.log('[TOURNEES] Client défini pour arrêt:', clientSelect.value);
                            }
                            var heureInput = lastArret.querySelector('.arret-heure');
                            if (heureInput && arret.heure_prevue) {
                                heureInput.value = arret.heure_prevue.substring(0, 5);
                            }

                            // Afficher le statut de l'arrêt si livré ou en échec
                            if (arret.statut && arret.statut !== 'en_attente') {
                                var statusBadge = document.createElement('span');
                                statusBadge.className = 'badge ' + (arret.statut === 'livre' ? 'badge-success' : 'badge-danger');
                                statusBadge.style.cssText = 'margin-left: 10px; padding: 4px 8px; border-radius: 4px; font-size: 0.8em;';
                                statusBadge.textContent = arret.statut === 'livre' ? 'Livré' : (arret.statut === 'echec' ? 'Échec' : arret.statut);
                                var header = lastArret.querySelector('.arret-header') || lastArret.firstChild;
                                if (header) header.appendChild(statusBadge);
                            }
                        }
                    });
                    console.log('[TOURNEES] Tous les arrêts ont été chargés');
                }).catch(function(err) {
                    console.error('[TOURNEES] Erreur chargement clients pour arrêts:', err);
                });
            }

            console.log('[TOURNEES] Données appliquées au formulaire');
        })
        .catch(error => {
            console.error('[TOURNEES] Erreur chargement:', error);
            showMessage('Erreur lors du chargement des données', 'error');
        });
}

// Fermer le modal en cliquant en dehors
window.onclick = function(event) {
    const modal = document.getElementById('tourneeModal');
    if (event.target == modal) {
        closeTourneeModal();
    }
}

// Fonction pour formater la date
function formatDate(dateStr) {
    if (!dateStr) {
        console.warn('[TOURNEES] formatDate: dateStr est vide ou undefined');
        return 'Date non définie';
    }

    try {
        const date = new Date(dateStr);

        // Vérifier si la date est valide
        if (isNaN(date.getTime())) {
            console.warn('[TOURNEES] formatDate: Date invalide:', dateStr);
            return dateStr; // Retourner la chaîne originale
        }

        return date.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' });
    } catch (error) {
        console.error('[TOURNEES] formatDate: Erreur:', error, 'dateStr:', dateStr);
        return dateStr || 'Date invalide';
    }
}

// Fonction pour afficher les messages
function showMessage(message, type) {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 25px;
        border-radius: 8px;
        color: white;
        font-weight: 500;
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
    `;

    if (type === 'success') {
        notification.style.background = '#10b981';
    } else if (type === 'error') {
        notification.style.background = '#ef4444';
    } else {
        notification.style.background = '#3b82f6';
    }

    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}

// Fonction pour obtenir le cookie CSRF
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// ============================================
// FONCTIONS PLANNING HEBDOMADAIRE
// ============================================

// Variables globales pour le planning
let allPlannings = [];
let planningsMap = {}; // Map[livreurId][jourSemaine] = planning

// Fonction pour basculer entre les onglets
function switchTab(tabName) {
    // Mettre à jour les onglets actifs
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });

    const activeTab = document.querySelector(`.tab[data-tab="${tabName}"]`);
    if (activeTab) {
        activeTab.classList.add('active');
    }

    // Cacher toutes les sections
    document.getElementById('tournees-section').style.display = 'none';
    document.getElementById('planning-section').style.display = 'none';
    const configSection = document.getElementById('config-clients-section');
    if (configSection) {
        configSection.style.display = 'none';
    }

    // Afficher la bonne section
    if (tabName === 'planning') {
        document.getElementById('planning-section').style.display = 'block';
        loadPlanningsHebdo();
    } else if (tabName === 'config-clients') {
        if (configSection) {
            configSection.style.display = 'block';
            // Charger les données nécessaires pour la configuration
            Promise.all([
                (!window.livreurs_tournees || window.livreurs_tournees.length === 0) ? loadLivreurs() : Promise.resolve(),
                (!window.clients_tournees || window.clients_tournees.length === 0) ? loadClients() : Promise.resolve()
            ]).then(() => {
                // Mettre à jour les variables locales après le chargement
                livreurs = window.livreurs_tournees;
                clients = window.clients_tournees;
                loadConfigClientsLivreurs();
            }).catch(err => {
                console.error('Erreur lors du chargement des données:', err);
                showMessage('Erreur lors du chargement des données', 'error');
            });
        }
    } else {
        document.getElementById('tournees-section').style.display = 'block';
        if (tabName === 'tournees') {
            filterTournees('all');
        } else {
            filterTournees(tabName);
        }
    }
}

// Charger les plannings hebdomadaires
async function loadPlanningsHebdo() {
    try {
        const livreurFilter = document.getElementById('filter-livreur-planning').value;
        let url = '/API/distribution/plannings-hebdo/';
        if (livreurFilter) {
            url += `?livreur=${livreurFilter}`;
        }

        const response = await fetch(url);
        if (!response.ok) throw new Error('Erreur lors du chargement des plannings');

        allPlannings = await response.json();
        displayPlanningsTable();
    } catch (error) {
        console.error('Erreur:', error);
        showMessage('Erreur lors du chargement des plannings', 'error');
    }
}

// Afficher la table des plannings
function displayPlanningsTable() {
    const tbody = document.getElementById('planning-table-body');

    // Créer un map des plannings par livreur et jour
    planningsMap = {};
    allPlannings.forEach(planning => {
        if (!planningsMap[planning.livreur]) {
            planningsMap[planning.livreur] = {};
        }
        planningsMap[planning.livreur][planning.jour_semaine] = planning;
    });

    // Obtenir la liste unique des livreurs
    const livreursIds = Object.keys(planningsMap);

    if (livreursIds.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; padding: 40px; color: #6b7280;">
                    Aucun planning configuré. Cliquez sur "Nouveau Planning" pour commencer.
                </td>
            </tr>
        `;
        return;
    }

    // Générer les lignes du tableau
    let html = '';
    livreursIds.forEach(livreurId => {
        const firstPlanning = Object.values(planningsMap[livreurId])[0];
        html += `<tr style="border-bottom: 1px solid #e5e7eb;">`;
        html += `<td style="padding: 12px; font-weight: 500;">${firstPlanning.livreur_nom}</td>`;

        // Pour chaque jour de la semaine (1-7)
        for (let jour = 1; jour <= 7; jour++) {
            const planning = planningsMap[livreurId][jour];
            if (planning) {
                const statusIcon = planning.is_active ? '✅' : '❌';
                const codePrix = planning.code_prix_code || 'Aucun';
                html += `
                    <td style="padding: 12px; text-align: center; background: ${planning.is_active ? '#f0fdf4' : '#fef2f2'};">
                        <div style="font-size: 1.2rem;">${statusIcon}</div>
                        <small style="color: #6b7280; display: block; margin-top: 4px;">${codePrix}</small>
                        <div style="margin-top: 8px;">
                            <button class="btn-sm btn-primary" onclick="editPlanning(${planning.id})" style="padding: 4px 8px; font-size: 0.75rem; margin-right: 4px;">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn-sm btn-danger" onclick="deletePlanning(${planning.id})" style="padding: 4px 8px; font-size: 0.75rem;">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </td>
                `;
            } else {
                html += `
                    <td style="padding: 12px; text-align: center; background: #f9fafb;">
                        <button class="btn-sm btn-success" onclick="openPlanningModal(${livreurId}, ${jour})" style="padding: 4px 8px; font-size: 0.75rem;">
                            <i class="fas fa-plus"></i>
                        </button>
                    </td>
                `;
            }
        }
        html += `</tr>`;
    });

    tbody.innerHTML = html;
}

// Ouvrir le modal de planning
function openPlanningModal(livreurId = null, jourSemaine = null) {
    document.getElementById('planningModal').style.display = 'block';
    document.getElementById('planning-form').reset();
    document.getElementById('planning-id').value = '';
    document.getElementById('planning-modal-title').textContent = 'Nouveau Planning Hebdomadaire';

    // Pré-remplir si livreur et jour fournis
    if (livreurId) {
        document.getElementById('planning-livreur').value = livreurId;
    }
    if (jourSemaine) {
        document.getElementById('planning-jour').value = jourSemaine;
    }

    // Charger les livreurs si pas encore fait
    loadLivreursForPlanning();
    // Charger les codes prix
    loadCodesPrixForPlanning();
}

// Fermer le modal de planning
function closePlanningModal() {
    document.getElementById('planningModal').style.display = 'none';
}

// Charger les livreurs pour le planning
async function loadLivreursForPlanning() {
    try {
        const response = await fetch('/API/distribution/livreurs/');
        const livreurs = await response.json();

        const select = document.getElementById('planning-livreur');
        const filterSelect = document.getElementById('filter-livreur-planning');

        // Remplir les deux selects
        [select, filterSelect].forEach(sel => {
            const currentValue = sel.value;
            sel.innerHTML = '<option value="">Sélectionner un livreur...</option>';
            livreurs.forEach(livreur => {
                const option = document.createElement('option');
                option.value = livreur.id;
                option.textContent = livreur.nom;
                sel.appendChild(option);
            });
            if (currentValue) sel.value = currentValue;
        });
    } catch (error) {
        console.error('Erreur lors du chargement des livreurs:', error);
    }
}

// Charger les codes prix
async function loadCodesPrixForPlanning() {
    try {
        const response = await fetch('/API/codes-prix/');
        const codesPrix = await response.json();

        const select = document.getElementById('planning-code-prix');
        select.innerHTML = '<option value="">Aucun (optionnel)</option>';
        codesPrix.forEach(code => {
            const option = document.createElement('option');
            option.value = code.id;
            option.textContent = `${code.code} - ${code.libelle}`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Erreur lors du chargement des codes prix:', error);
    }
}

// Enregistrer le planning
document.addEventListener('DOMContentLoaded', function() {
    const planningForm = document.getElementById('planning-form');
    if (planningForm) {
        planningForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const planningId = document.getElementById('planning-id').value;
            const data = {
                livreur: parseInt(document.getElementById('planning-livreur').value),
                jour_semaine: parseInt(document.getElementById('planning-jour').value),
                code_prix: document.getElementById('planning-code-prix').value || null,
                is_active: document.getElementById('planning-actif').checked,
                date_debut: document.getElementById('planning-date-debut').value || null,
                date_fin: document.getElementById('planning-date-fin').value || null,
                notes: document.getElementById('planning-notes').value || ''
            };

            try {
                const url = planningId
                    ? `/API/distribution/plannings-hebdo/${planningId}/`
                    : '/API/distribution/plannings-hebdo/';

                const method = planningId ? 'PUT' : 'POST';

                const response = await fetch(url, {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify(data)
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(JSON.stringify(errorData));
                }

                showMessage('Planning enregistré avec succès!', 'success');
                closePlanningModal();
                loadPlanningsHebdo();
            } catch (error) {
                console.error('Erreur:', error);
                showMessage('Erreur lors de l\'enregistrement du planning', 'error');
            }
        });
    }
});

// Éditer un planning
async function editPlanning(planningId) {
    try {
        const response = await fetch(`/API/distribution/plannings-hebdo/${planningId}/`);
        const planning = await response.json();

        document.getElementById('planning-id').value = planning.id;
        document.getElementById('planning-livreur').value = planning.livreur;
        document.getElementById('planning-jour').value = planning.jour_semaine;
        document.getElementById('planning-code-prix').value = planning.code_prix || '';
        document.getElementById('planning-actif').checked = planning.is_active;
        document.getElementById('planning-date-debut').value = planning.date_debut || '';
        document.getElementById('planning-date-fin').value = planning.date_fin || '';
        document.getElementById('planning-notes').value = planning.notes || '';

        document.getElementById('planning-modal-title').textContent = 'Modifier Planning Hebdomadaire';
        document.getElementById('planningModal').style.display = 'block';

        loadLivreursForPlanning();
        loadCodesPrixForPlanning();
    } catch (error) {
        console.error('Erreur:', error);
        showMessage('Erreur lors du chargement du planning', 'error');
    }
}

// Supprimer un planning
async function deletePlanning(planningId) {
    if (!confirm('Êtes-vous sûr de vouloir supprimer ce planning?')) {
        return;
    }

    try {
        const response = await fetch(`/API/distribution/plannings-hebdo/${planningId}/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });

        if (!response.ok) throw new Error('Erreur lors de la suppression');

        showMessage('Planning supprimé avec succès!', 'success');
        loadPlanningsHebdo();
    } catch (error) {
        console.error('Erreur:', error);
        showMessage('Erreur lors de la suppression du planning', 'error');
    }
}

// Générer les tournées de la semaine
async function genererSemaine() {
    // Obtenir le lundi de la semaine courante
    const today = new Date();
    const dayOfWeek = today.getDay(); // 0 = dimanche, 1 = lundi, ...
    const diff = dayOfWeek === 0 ? -6 : 1 - dayOfWeek; // Ajuster pour obtenir le lundi
    const monday = new Date(today);
    monday.setDate(today.getDate() + diff);

    const dateDebut = monday.toISOString().split('T')[0];

    if (!confirm(`Générer les tournées pour la semaine du ${formatDate(dateDebut)}?`)) {
        return;
    }

    try {
        const response = await fetch('/API/distribution/plannings-hebdo/generer_semaine/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ date_debut: dateDebut })
        });

        if (!response.ok) throw new Error('Erreur lors de la génération');

        const result = await response.json();
        showMessage(result.message || 'Tournées générées avec succès!', 'success');

        // Revenir à l'onglet des tournées pour voir le résultat
        switchTab('tournees');
    } catch (error) {
        console.error('Erreur:', error);
        showMessage('Erreur lors de la génération des tournées', 'error');
    }
}

// ============================================
// FONCTIONS CONFIGURATION CLIENTS/LIVREURS
// ============================================

// Variables globales pour la configuration
let allConfigs = [];

// Charger les configurations client/livreur
async function loadConfigClientsLivreurs() {
    try {
        const livreurFilter = document.getElementById('filter-livreur-config').value;
        const jourFilter = document.getElementById('filter-jour-config').value;

        let url = '/API/distribution/clients-livreurs-hebdo/';
        const params = [];
        if (livreurFilter) params.push(`livreur=${livreurFilter}`);
        if (jourFilter) params.push(`jour_semaine=${jourFilter}`);
        if (params.length > 0) url += '?' + params.join('&');

        const response = await fetch(url);
        if (!response.ok) throw new Error('Erreur lors du chargement des configurations');

        allConfigs = await response.json();
        displayConfigTable();

        // Peupler le filtre livreur si vide
        if (document.getElementById('filter-livreur-config').options.length <= 1) {
            populateConfigLivreurFilter();
        }
    } catch (error) {
        console.error('Erreur:', error);
        document.getElementById('config-table-body').innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; padding: 20px; color: #ef4444;">
                    <i class="fas fa-exclamation-triangle"></i> ${error.message}
                </td>
            </tr>`;
    }
}

// Afficher la table de configuration
function displayConfigTable() {
    const tbody = document.getElementById('config-table-body');

    if (allConfigs.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; padding: 40px; color: #6b7280;">
                    <i class="fas fa-info-circle"></i> Aucune configuration trouvée
                </td>
            </tr>`;
        return;
    }

    const joursNoms = {
        1: 'Lundi', 2: 'Mardi', 3: 'Mercredi', 4: 'Jeudi',
        5: 'Vendredi', 6: 'Samedi', 7: 'Dimanche'
    };

    tbody.innerHTML = allConfigs.map(config => `
        <tr style="border-bottom: 1px solid #e5e7eb;">
            <td style="padding: 12px;">
                <strong>${config.client_nom || 'N/A'}</strong>
                ${config.client_telephone ? `<br><small style="color: #6b7280;">${config.client_telephone}</small>` : ''}
            </td>
            <td style="padding: 12px;">
                <strong>${config.livreur_nom || 'N/A'}</strong>
            </td>
            <td style="padding: 12px; text-align: center;">
                <span style="background: #e0e7ff; color: #3730a3; padding: 4px 12px; border-radius: 12px; font-weight: 500;">
                    ${joursNoms[config.jour_semaine] || config.jour_semaine}
                </span>
            </td>
            <td style="padding: 12px; text-align: center;">
                ${config.ordre_passage ? `<strong>#${config.ordre_passage}</strong>` : '-'}
            </td>
            <td style="padding: 12px; text-align: center;">
                ${config.is_active ?
                    '<span style="color: #10b981; font-weight: 500;">✓ Actif</span>' :
                    '<span style="color: #ef4444; font-weight: 500;">✗ Inactif</span>'}
            </td>
            <td style="padding: 12px; text-align: center;">
                <button onclick="editConfig(${config.id})" style="background: none; border: none; color: #3b82f6; cursor: pointer; margin-right: 10px;" title="Modifier">
                    <i class="fas fa-edit"></i>
                </button>
                <button onclick="deleteConfig(${config.id})" style="background: none; border: none; color: #ef4444; cursor: pointer;" title="Supprimer">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

// Peupler le filtre livreur de la configuration
function populateConfigLivreurFilter() {
    const select = document.getElementById('filter-livreur-config');
    const selectModal = document.getElementById('config-livreur');

    // Utiliser les variables window pour garantir les données à jour
    const livreursData = window.livreurs_tournees || livreurs || [];

    if (livreursData && livreursData.length > 0) {
        // Filtre
        if (select) {
            select.innerHTML = '<option value="">Tous les livreurs</option>' +
                livreursData.map(l => `<option value="${l.id}">${l.nom}</option>`).join('');
        }

        // Modal
        if (selectModal) {
            selectModal.innerHTML = '<option value="">Sélectionner un livreur...</option>' +
                livreursData.map(l => `<option value="${l.id}">${l.nom}</option>`).join('');
        }
    } else {
        console.warn('Aucun livreur disponible pour les selects');
        if (select) {
            select.innerHTML = '<option value="">Aucun livreur disponible</option>';
        }
        if (selectModal) {
            selectModal.innerHTML = '<option value="">Aucun livreur disponible</option>';
        }
    }
}

// Ouvrir le modal de configuration
async function openConfigModal(configId = null) {
    const modal = document.getElementById('configModal');
    const title = document.getElementById('config-modal-title');
    const form = document.getElementById('config-form');

    form.reset();
    document.getElementById('config-id').value = '';
    document.getElementById('config-actif').checked = true;

    // S'assurer que les données sont chargées
    try {
        // Charger les livreurs si pas encore chargés
        if (!window.livreurs_tournees || window.livreurs_tournees.length === 0) {
            await loadLivreurs();
        }

        // Charger les clients si pas encore chargés
        if (!window.clients_tournees || window.clients_tournees.length === 0) {
            await loadClients();
        }

        // Mettre à jour les variables locales après le chargement
        livreurs = window.livreurs_tournees;
        clients = window.clients_tournees;

        console.log('Clients chargés pour modal:', clients.length);
        console.log('Livreurs chargés pour modal:', livreurs.length);

        // Peupler les selects
        populateConfigLivreurFilter();

        // Peupler le select des clients
        const clientSelect = document.getElementById('config-client');
        if (clients && clients.length > 0) {
            clientSelect.innerHTML = '<option value="">Sélectionner un client...</option>' +
                clients.map(c => `<option value="${c.id}">${c.nom}</option>`).join('');
        } else {
            console.warn('Aucun client disponible pour le select');
            clientSelect.innerHTML = '<option value="">Aucun client disponible</option>';
        }

        if (configId) {
            // Mode édition
            title.textContent = 'Modifier Configuration';
            const config = allConfigs.find(c => c.id === configId);
            if (config) {
                document.getElementById('config-id').value = config.id;
                document.getElementById('config-client').value = config.client;
                document.getElementById('config-livreur').value = config.livreur;
                document.getElementById('config-jour').value = config.jour_semaine;
                document.getElementById('config-ordre').value = config.ordre_passage || '';
                document.getElementById('config-actif').checked = config.is_active;
            }
        } else {
            // Mode création
            title.textContent = 'Nouvelle Configuration Client/Livreur';
        }

        modal.style.display = 'block';
    } catch (error) {
        console.error('Erreur lors du chargement des données:', error);
        showMessage('Erreur lors du chargement des données. Veuillez réessayer.', 'error');
    }
}

// Fermer le modal de configuration
function closeConfigModal() {
    document.getElementById('configModal').style.display = 'none';
}

// Éditer une configuration
function editConfig(configId) {
    openConfigModal(configId);
}

// Supprimer une configuration
async function deleteConfig(configId) {
    if (!confirm('Êtes-vous sûr de vouloir désactiver cette configuration ?')) {
        return;
    }

    try {
        const response = await fetch(`/API/distribution/clients-livreurs-hebdo/${configId}/`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ is_active: false })
        });

        if (!response.ok) throw new Error('Erreur lors de la suppression');

        showMessage('Configuration désactivée avec succès!', 'success');
        loadConfigClientsLivreurs();
    } catch (error) {
        console.error('Erreur:', error);
        showMessage('Erreur lors de la suppression', 'error');
    }
}

// Sauvegarder la configuration
async function saveConfig(event) {
    event.preventDefault();

    const configId = document.getElementById('config-id').value;
    const data = {
        client: parseInt(document.getElementById('config-client').value),
        livreur: parseInt(document.getElementById('config-livreur').value),
        jour_semaine: parseInt(document.getElementById('config-jour').value),
        ordre_passage: document.getElementById('config-ordre').value ?
            parseInt(document.getElementById('config-ordre').value) : null,
        is_active: document.getElementById('config-actif').checked
    };

    try {
        let url = '/API/distribution/clients-livreurs-hebdo/';
        let method = 'POST';

        if (configId) {
            url += `${configId}/`;
            method = 'PUT';
        }

        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const errorData = await response.json();
            console.error('Erreur serveur:', errorData);

            // Extraire les messages d'erreur
            let errorMessage = 'Erreur lors de la sauvegarde: ';
            if (errorData.detail) {
                errorMessage += errorData.detail;
            } else if (typeof errorData === 'object') {
                // Afficher toutes les erreurs de validation
                const errors = [];
                for (const [field, messages] of Object.entries(errorData)) {
                    if (Array.isArray(messages)) {
                        errors.push(`${field}: ${messages.join(', ')}`);
                    } else {
                        errors.push(`${field}: ${messages}`);
                    }
                }
                errorMessage += errors.join('; ');
            } else {
                errorMessage += errorData;
            }

            throw new Error(errorMessage);
        }

        showMessage(configId ? 'Configuration modifiée avec succès!' : 'Configuration créée avec succès!', 'success');
        closeConfigModal();
        loadConfigClientsLivreurs();
    } catch (error) {
        console.error('Erreur:', error);
        showMessage(error.message, 'error');
    }
}

// Configurer le gestionnaire de formulaire de configuration
document.addEventListener('fragment:loaded', function(e) {
    if (e.detail.name === 'tournees') {
        const configForm = document.getElementById('config-form');
        if (configForm) {
            configForm.removeEventListener('submit', saveConfig);
            configForm.addEventListener('submit', saveConfig);
        }
    }
});
