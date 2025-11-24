// Gestion des Tournées
window.tournees = window.tournees || [];
window.livreurs_tournees = window.livreurs_tournees || [];
window.clients_tournees = window.clients_tournees || [];
window.warehouses_tournees = window.warehouses_tournees || [];
window.codes_prix_tournees = window.codes_prix_tournees || [];
window.currentFilter = window.currentFilter || 'all';
window.arretCounter = window.arretCounter || 0;

var tournees = window.tournees;
var livreurs = window.livreurs_tournees;
var clients = window.clients_tournees;
var warehouses = window.warehouses_tournees;
var codes_prix = window.codes_prix_tournees;
var currentFilter = window.currentFilter;
var arretCounter = window.arretCounter;

// Fonction d'initialisation
window.initTourneesPage = function() {
    // Vérifier que les éléments nécessaires existent avant d'initialiser
    const container = document.getElementById('tournees-container');
    if (!container) {
        console.log('[TOURNEES] Page elements not found, skipping initialization');
        return;
    }

    console.log('[TOURNEES] Initializing tournees page');
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
    fetch('/API/distribution/tournees/', {
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
        distance_km: apiData.distance_km || 0,
        argent_depart: apiData.argent_depart || 0,
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
        updated_at: apiData.updated_at
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
            <button class="btn-success" onclick="demarrerTournee(${tournee.id})">
                <i class="fas fa-play"></i> Démarrer
            </button>
            <button class="btn-warning" onclick="editTournee(${tournee.id})">
                <i class="fas fa-edit"></i>
            </button>
            <button class="btn-danger" onclick="annulerTournee(${tournee.id})">
                <i class="fas fa-times"></i>
            </button>
        `;
    } else if (tournee.statut === 'en_cours') {
        actions += `
            <button class="btn-success" onclick="terminerTournee(${tournee.id})">
                <i class="fas fa-check"></i> Terminer
            </button>
            <button class="btn-danger" onclick="annulerTournee(${tournee.id})">
                <i class="fas fa-times"></i> Annuler
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
    });
    event.target.classList.add('active');

    let filtered = window.tournees;
    if (status !== 'all') {
        filtered = window.tournees.filter(t => t.statut === status);
    }

    displayTournees(filtered);
}

// Voir les détails d'une tournée
function viewTourneeDetails(id) {
    fetch(`/API/distribution/tournees/${id}/`, {
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
    const arretsVisites = stats.arrets_visites || [];
    const arretsRestants = stats.arrets_restants || [];
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
                <div><strong>Distance:</strong> ${tournee.distance_km || '-'} km</div>
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

    fetch(`/API/distribution/tournees/${id}/demarrer/`, {
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

    fetch(`/API/distribution/tournees/${id}/terminer/`, {
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

    fetch(`/API/distribution/tournees/${id}/`, {
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
function openTourneeModal(tourneeId = null) {
    const modal = document.getElementById('tourneeModal');
    const title = document.getElementById('modal-title');

    window.arretCounter = 0;
    document.getElementById('arrets-container').innerHTML = '';

    // Recharger les données si nécessaire avant de peupler les selects
    if (!window.livreurs_tournees || window.livreurs_tournees.length === 0) {
        console.log('Rechargement des livreurs...');
        loadLivreurs().then(() => {
            populateLivreursSelect();
        });
    } else {
        populateLivreursSelect();
    }

    if (!window.warehouses_tournees || window.warehouses_tournees.length === 0) {
        console.log('Rechargement des entrepôts...');
        loadWarehouses().then(() => {
            populateWarehousesSelect();
        });
    } else {
        populateWarehousesSelect();
    }

    // Recharger les clients si nécessaire
    if (!window.clients_tournees || window.clients_tournees.length === 0) {
        console.log('Rechargement des clients...');
        loadClients().catch(err => {
            console.error('Erreur rechargement clients:', err);
            showMessage('Erreur lors du chargement des clients', 'warning');
        });
    } else {
        console.log('Clients déjà chargés:', window.clients_tournees.length);
    }

    if (tourneeId) {
        title.textContent = 'Modifier la Tournée';
        loadTourneeData(tourneeId);
    } else {
        title.textContent = 'Nouvelle Tournée';
        document.getElementById('tournee-form').reset();
        document.getElementById('tournee-id').value = '';
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('date').value = today;
    }

    modal.style.display = 'block';
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
function addArretFormInternal() {
    window.arretCounter++;
    const container = document.getElementById('arrets-container');
    const arretDiv = document.createElement('div');
    arretDiv.className = 'arret-form-item';
    arretDiv.id = `arret-${window.arretCounter}`;

    // S'assurer que les clients sont chargés
    const clientsOptions = (window.clients_tournees && Array.isArray(window.clients_tournees) && window.clients_tournees.length > 0)
        ? window.clients_tournees.map(c => `<option value="${c.id}">${c.nom || ''} ${c.prenom || ''}</option>`).join('')
        : '<option value="" disabled>Aucun client disponible</option>';

    console.log('Ajout arrêt - clients disponibles:', window.clients_tournees ? window.clients_tournees.length : 0);

    arretDiv.innerHTML = `
        <button type="button" class="remove-arret" onclick="removeArret(${window.arretCounter})">×</button>
        <h4 style="margin-bottom: 15px;">Arrêt #${window.arretCounter}</h4>
        <div class="form-grid">
            <div class="form-group">
                <label>Client *</label>
                <select class="arret-client" required>
                    <option value="">Sélectionner...</option>
                    ${clientsOptions}
                </select>
            </div>
            <div class="form-group">
                <label>Heure prévue *</label>
                <input type="time" class="arret-heure" required>
            </div>
            <div class="form-group full-width">
                <label>Adresse de livraison *</label>
                <input type="text" class="arret-adresse" required>
            </div>
        </div>
    `;

    container.appendChild(arretDiv);
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
        const data = {
            date_tournee: document.getElementById('date').value,
            livreur: document.getElementById('livreur').value,
            warehouse: document.getElementById('warehouse').value || null,
            code_prix: codePrixValue ? parseInt(codePrixValue) : null,
            heure_depart_prevue: document.getElementById('heure_depart_prevue').value,
            heure_retour_prevue: document.getElementById('heure_retour_prevue').value || null,
            distance_km: document.getElementById('distance_km').value || null,
            argent_depart: parseFloat(document.getElementById('argent_depart').value) || 0,
            commentaire: document.getElementById('commentaire').value || '',
            numero_tournee: 'T-' + new Date().getTime(),
            statut: 'planifiee'
        };

        const url = id ? `/API/distribution/tournees/${id}/` : '/API/distribution/tournees/';
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
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.json();
        })
        .then(tournee => {
            // Créer les arrêts
            const arrets = collectArrets();
            if (arrets.length > 0) {
                return createArrets(tournee.id, arrets);
            }
            return tournee;
        })
        .then(() => {
            closeTourneeModal();
            loadTournees();
            showMessage('Tournée enregistrée avec succès', 'success');
        })
        .catch(error => {
            console.error('Erreur:', error);
            showMessage('Erreur lors de l\'enregistrement', 'error');
        });
    });
}

// Collecter les données des arrêts
function collectArrets() {
    const arrets = [];
    const container = document.getElementById('arrets-container');
    const arretForms = container.querySelectorAll('.arret-form-item');

    arretForms.forEach((form, index) => {
        const client = form.querySelector('.arret-client').value;
        const heure = form.querySelector('.arret-heure').value;
        const adresse = form.querySelector('.arret-adresse').value;

        if (client && heure && adresse) {
            arrets.push({
                client: client,
                heure_prevue: heure,
                adresse_livraison: adresse,
                ordre: index + 1
            });
        }
    });

    return arrets;
}

// Créer les arrêts
async function createArrets(tourneeId, arrets) {
    const promises = arrets.map(arret => {
        arret.tournee = tourneeId;
        return fetch('/API/distribution/arrets/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(arret)
        });
    });

    return Promise.all(promises);
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
        .then(response => response.json())
        .then(tournee => {
            document.getElementById('tournee-id').value = tournee.id;
            document.getElementById('date').value = tournee.date;
            document.getElementById('livreur').value = tournee.livreur || '';
            document.getElementById('warehouse').value = tournee.warehouse || '';
            document.getElementById('heure_depart_prevue').value = tournee.heure_depart_prevue;
            document.getElementById('heure_retour_prevue').value = tournee.heure_retour_prevue || '';
            document.getElementById('distance_km').value = tournee.distance_km || '';
            document.getElementById('argent_depart').value = tournee.argent_depart || 0;
            document.getElementById('commentaire').value = tournee.commentaire || '';

            // Charger les arrêts existants (clients déjà chargés à ce stade)
            tournee.arrets.forEach((arret, index) => {
                addArretFormInternal(); // Utiliser la version interne pour éviter de recharger les clients
                const lastArret = document.getElementById(`arret-${window.arretCounter}`);
                lastArret.querySelector('.arret-client').value = arret.client;
                lastArret.querySelector('.arret-heure').value = arret.heure_prevue;
                lastArret.querySelector('.arret-adresse').value = arret.adresse_livraison;
            });
        })
        .catch(error => {
            console.error('Erreur:', error);
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
    const date = new Date(dateStr);
    return date.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' });
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
