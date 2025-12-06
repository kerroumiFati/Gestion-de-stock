/**
 * Configuration Clients / Chauffeurs
 * Interface pour assigner des clients aux chauffeurs de l'application mobile
 */

// État global
let state = {
    livreurs: [],
    clients: [],
    selectedLivreur: null,
    assignedClients: [],
    searchQuery: ''
};

// API Base URL
const API_BASE = '/API';

/**
 * Initialisation de la page
 */
window.initConfigClientsChauffeursPage = function() {
    console.log('Initialisation de la page Configuration Clients/Chauffeurs');

    // Charger les données initiales
    loadLivreurs();
    loadAllClients();

    // Attacher les événements
    attachEventListeners();
};

/**
 * Attacher les événements
 */
function attachEventListeners() {
    // Recherche de clients
    const searchInput = document.getElementById('searchClient');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            state.searchQuery = e.target.value.toLowerCase();
            renderClientLists();
        });
    }
}

/**
 * Charger tous les livreurs
 */
async function loadLivreurs() {
    try {
        const response = await fetch(`${API_BASE}/distribution/livreurs/`);
        if (!response.ok) throw new Error('Erreur lors du chargement des livreurs');

        const data = await response.json();
        // Handle both paginated and non-paginated responses
        state.livreurs = data.results || data;

        renderLivreursList();
    } catch (error) {
        console.error('Erreur:', error);
        showAlert('Erreur lors du chargement des chauffeurs', 'error');
    }
}

/**
 * Charger tous les clients
 */
async function loadAllClients() {
    try {
        const response = await fetch(`${API_BASE}/clients/`);
        if (!response.ok) throw new Error('Erreur lors du chargement des clients');

        const data = await response.json();
        // Handle both paginated and non-paginated responses
        state.clients = data.results || data;
    } catch (error) {
        console.error('Erreur:', error);
        showAlert('Erreur lors du chargement des clients', 'error');
    }
}

/**
 * Afficher la liste des livreurs
 */
function renderLivreursList() {
    const container = document.getElementById('livreurList');

    // Vérifier que l'élément existe
    if (!container) {
        console.warn('Element livreurList not found');
        return;
    }

    if (state.livreurs.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-truck"></i>
                <p>Aucun chauffeur disponible</p>
            </div>
        `;
        return;
    }

    container.innerHTML = state.livreurs.map(livreur => `
        <div class="livreur-item ${state.selectedLivreur?.id === livreur.id ? 'active' : ''}"
             onclick="selectLivreur(${livreur.id})">
            <i class="fas fa-user-circle"></i>
            <div class="livreur-info">
                <div class="livreur-name">${livreur.nom}</div>
                <div class="livreur-matricule">${livreur.matricule}</div>
            </div>
        </div>
    `).join('');
}

/**
 * Sélectionner un livreur
 */
window.selectLivreur = async function selectLivreur(livreurId) {
    const livreur = state.livreurs.find(l => l.id === livreurId);
    if (!livreur) return;

    state.selectedLivreur = livreur;
    renderLivreursList();

    // Afficher la section de gestion des clients
    document.getElementById('noLivreurSelected').style.display = 'none';
    document.getElementById('clientsManagement').style.display = 'block';
    document.getElementById('selectedLivreurName').textContent =
        `${livreur.nom} (${livreur.matricule})`;

    // Charger les clients assignés à ce livreur
    await loadLivreurClients(livreurId);

    // Afficher les listes de clients
    renderClientLists();
}

/**
 * Charger les clients assignés à un livreur
 */
async function loadLivreurClients(livreurId) {
    try {
        const response = await fetch(`${API_BASE}/distribution/livreurs/${livreurId}/clients_assignes/`);
        if (!response.ok) throw new Error('Erreur lors du chargement des clients assignés');

        const data = await response.json();
        state.assignedClients = data.clients || [];
    } catch (error) {
        console.error('Erreur:', error);
        showAlert('Erreur lors du chargement des clients assignés', 'error');
        state.assignedClients = [];
    }
}

/**
 * Charger tous les clients assignés (à tous les livreurs)
 */
async function loadAllAssignedClients() {
    try {
        const clientsAssignes = new Set();

        // Parcourir tous les livreurs pour récupérer leurs clients assignés
        for (const livreur of state.livreurs) {
            const response = await fetch(`${API_BASE}/distribution/livreurs/${livreur.id}/clients_assignes/`);
            if (response.ok) {
                const data = await response.json();
                const clients = data.clients || [];
                clients.forEach(client => clientsAssignes.add(client.id));
            }
        }

        return clientsAssignes;
    } catch (error) {
        console.error('Erreur:', error);
        return new Set();
    }
}

/**
 * Afficher les listes de clients
 */
async function renderClientLists() {
    if (!state.selectedLivreur) return;

    // Charger tous les clients assignés à tous les livreurs
    const allAssignedClientIds = await loadAllAssignedClients();

    // Filtrer les clients selon la recherche
    const filteredClients = state.clients.filter(client => {
        const searchText = `${client.nom} ${client.prenom} ${client.email} ${client.telephone}`.toLowerCase();
        return searchText.includes(state.searchQuery);
    });

    // Séparer les clients assignés au livreur actuel et disponibles
    const assignedIds = state.assignedClients.map(c => c.id);

    // Les clients disponibles sont ceux qui ne sont assignés à AUCUN livreur
    // OU qui sont assignés au livreur actuellement sélectionné
    const availableClients = filteredClients.filter(c => {
        const isAssignedToCurrent = assignedIds.includes(c.id);
        const isAssignedToOther = allAssignedClientIds.has(c.id) && !isAssignedToCurrent;
        return !isAssignedToOther; // Exclure ceux assignés à d'autres chauffeurs
    }).filter(c => !assignedIds.includes(c.id)); // Et exclure ceux déjà dans la liste assignée

    const assignedClients = filteredClients.filter(c => assignedIds.includes(c.id));

    // Afficher les clients disponibles
    renderClientList('availableClientsList', availableClients, 'available');
    const availableCount = document.getElementById('availableCount');
    if (availableCount) availableCount.textContent = availableClients.length;

    // Afficher les clients assignés
    renderClientList('assignedClientsList', assignedClients, 'assigned');
    const assignedCount = document.getElementById('assignedCount');
    if (assignedCount) assignedCount.textContent = assignedClients.length;
}

/**
 * Afficher une liste de clients
 */
function renderClientList(containerId, clients, type) {
    const container = document.getElementById(containerId);

    // Vérifier que l'élément existe
    if (!container) {
        console.warn(`Element ${containerId} not found`);
        return;
    }

    if (clients.length === 0) {
        const emptyMessage = type === 'available'
            ? 'Aucun client disponible'
            : 'Aucun client assigné';
        const emptyIcon = type === 'available'
            ? 'fa-user-friends'
            : 'fa-user-check';

        container.innerHTML = `
            <div class="empty-state">
                <i class="fas ${emptyIcon}"></i>
                <p>${emptyMessage}</p>
            </div>
        `;
        return;
    }

    container.innerHTML = clients.map(client => `
        <div class="client-item">
            <div class="client-info">
                <i class="fas fa-user"></i>
                <div>
                    <div class="client-name">${client.nom} ${client.prenom}</div>
                    <div class="client-details">
                        ${client.telephone ? `<i class="fas fa-phone"></i> ${client.telephone}` : ''}
                        ${client.email ? ` | <i class="fas fa-envelope"></i> ${client.email}` : ''}
                    </div>
                </div>
            </div>
            <div class="client-actions">
                ${type === 'available'
                    ? `<button class="btn-icon btn-add" onclick="assignClient(${client.id})" title="Assigner">
                        <i class="fas fa-plus"></i>
                       </button>`
                    : `<button class="btn-icon btn-remove" onclick="unassignClient(${client.id})" title="Retirer">
                        <i class="fas fa-minus"></i>
                       </button>`
                }
            </div>
        </div>
    `).join('');
}

/**
 * Assigner un client à un livreur
 */
window.assignClient = async function assignClient(clientId) {
    if (!state.selectedLivreur) return;

    try {
        const response = await fetch(
            `${API_BASE}/distribution/livreurs/${state.selectedLivreur.id}/ajouter_client/`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ client_id: clientId })
            }
        );

        if (!response.ok) throw new Error('Erreur lors de l\'assignation');

        const data = await response.json();

        // Recharger les clients assignés
        await loadLivreurClients(state.selectedLivreur.id);
        await renderClientLists();

        showAlert(data.message || 'Client assigné avec succès', 'success');
    } catch (error) {
        console.error('Erreur:', error);
        showAlert('Erreur lors de l\'assignation du client', 'error');
    }
}

/**
 * Retirer un client d'un livreur
 */
window.unassignClient = async function unassignClient(clientId) {
    if (!state.selectedLivreur) return;

    try {
        const response = await fetch(
            `${API_BASE}/distribution/livreurs/${state.selectedLivreur.id}/retirer_client/`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ client_id: clientId })
            }
        );

        if (!response.ok) throw new Error('Erreur lors du retrait');

        const data = await response.json();

        // Recharger les clients assignés
        await loadLivreurClients(state.selectedLivreur.id);
        await renderClientLists();

        showAlert(data.message || 'Client retiré avec succès', 'success');
    } catch (error) {
        console.error('Erreur:', error);
        showAlert('Erreur lors du retrait du client', 'error');
    }
}

/**
 * Afficher une alerte
 */
function showAlert(message, type = 'success') {
    const container = document.getElementById('alert-container');

    // Vérifier que l'élément existe
    if (!container) {
        console.warn('Element alert-container not found');
        return;
    }

    const alertClass = type === 'success' ? 'alert-success' : 'alert-error';
    const icon = type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle';

    const alertHtml = `
        <div class="alert ${alertClass}">
            <i class="fas ${icon}"></i>
            <span>${message}</span>
        </div>
    `;

    container.innerHTML = alertHtml;

    // Masquer l'alerte après 3 secondes
    setTimeout(() => {
        if (container) {
            container.innerHTML = '';
        }
    }, 3000);
}

/**
 * Obtenir le cookie CSRF
 */
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

// Auto-initialisation - seulement si les éléments de la page existent
function safeInit() {
    // Vérifier si on est sur la bonne page en cherchant un élément spécifique
    const livreursContainer = document.getElementById('livreurList');
    const clientsContainer = document.getElementById('clientsManagement');

    if (livreursContainer || clientsContainer) {
        console.log('Page config clients/chauffeurs détectée, initialisation...');
        window.initConfigClientsChauffeursPage();
    } else {
        console.log('Page config clients/chauffeurs non détectée, initialisation annulée');
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', safeInit);
} else {
    safeInit();
}
