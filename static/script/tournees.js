// Gestion des Tournées
let tournees = [];
let livreurs = [];
let clients = [];
let warehouses = [];
let currentFilter = 'all';
let arretCounter = 0;

// Charger les données au démarrage
document.addEventListener('DOMContentLoaded', function() {
    loadTournees();
    loadLivreurs();
    loadClients();
    loadWarehouses();

    // Définir la date par défaut à aujourd'hui
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('date').value = today;
});

// Charger les tournées
function loadTournees() {
    fetch('/API/tournees/')
        .then(response => response.json())
        .then(data => {
            tournees = data;
            displayTournees(data);
            updateStats(data);
        })
        .catch(error => {
            console.error('Erreur:', error);
            showMessage('Erreur lors du chargement des tournées', 'error');
        });
}

// Charger les livreurs
function loadLivreurs() {
    fetch('/API/livreurs/')
        .then(response => response.json())
        .then(data => {
            livreurs = data;
            populateLivreursSelect();
        })
        .catch(error => console.error('Erreur:', error));
}

// Charger les clients
function loadClients() {
    fetch('/API/clients/?page_size=1000')
        .then(response => response.json())
        .then(data => {
            clients = data;
        })
        .catch(error => console.error('Erreur:', error));
}

// Charger les entrepôts
function loadWarehouses() {
    fetch('/API/entrepots/')
        .then(response => response.json())
        .then(data => {
            warehouses = data;
            populateWarehousesSelect();
        })
        .catch(error => console.error('Erreur:', error));
}

// Afficher les tournées
function displayTournees(tourneesData) {
    const container = document.getElementById('tournees-container');

    if (tourneesData.length === 0) {
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
function updateStats(tourneesData) {
    const today = new Date().toISOString().split('T')[0];
    const tournees_today = tourneesData.filter(t => t.date === today);
    const en_cours = tourneesData.filter(t => t.statut === 'en_cours');

    // Calculer le taux de réussite global
    const terminees = tourneesData.filter(t => t.statut === 'terminee');
    let totalArrets = 0;
    let totalLivres = 0;
    terminees.forEach(t => {
        totalArrets += t.nombre_arrets;
        totalLivres += t.arrets_livres;
    });
    const tauxReussite = totalArrets > 0 ? Math.round((totalLivres / totalArrets) * 100) : 0;

    document.getElementById('total-tournees').textContent = tourneesData.length;
    document.getElementById('tournees-today').textContent = tournees_today.length;
    document.getElementById('tournees-en-cours').textContent = en_cours.length;
    document.getElementById('taux-reussite').textContent = tauxReussite + '%';
}

// Filtrer les tournées
function filterTournees(status) {
    currentFilter = status;

    // Mettre à jour les onglets actifs
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });
    event.target.classList.add('active');

    let filtered = tournees;
    if (status !== 'all') {
        filtered = tournees.filter(t => t.statut === status);
    }

    displayTournees(filtered);
}

// Voir les détails d'une tournée
function viewTourneeDetails(id) {
    fetch(`/API/tournees/${id}/`)
        .then(response => response.json())
        .then(tournee => {
            showTourneeDetailsModal(tournee);
        })
        .catch(error => {
            console.error('Erreur:', error);
            showMessage('Erreur lors du chargement des détails', 'error');
        });
}

// Afficher la modal des détails
function showTourneeDetailsModal(tournee) {
    const modalContent = `
        <div style="padding: 30px;">
            <h2 style="margin-bottom: 20px;">${tournee.numero}</h2>

            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-bottom: 30px;">
                <div><strong>Date:</strong> ${formatDate(tournee.date)}</div>
                <div><strong>Livreur:</strong> ${tournee.livreur_nom || 'Non assigné'}</div>
                <div><strong>Départ prévu:</strong> ${tournee.heure_depart_prevue}</div>
                <div><strong>Retour prévu:</strong> ${tournee.heure_retour_prevue || '-'}</div>
                <div><strong>Statut:</strong> <span class="badge badge-${tournee.statut}">${tournee.statut_display}</span></div>
                <div><strong>Distance:</strong> ${tournee.distance_km || '-'} km</div>
            </div>

            <h3 style="margin-bottom: 15px;">Arrêts de livraison (${tournee.arrets.length})</h3>
            ${tournee.arrets.map((arret, index) => `
                <div class="arret-item">
                    <div>
                        <strong>#${arret.ordre}</strong> - ${arret.client_nom}
                        <div style="font-size: 0.9rem; color: #6b7280;">
                            <i class="fas fa-clock"></i> ${arret.heure_prevue}
                            ${arret.adresse_livraison ? `<br><i class="fas fa-map-marker-alt"></i> ${arret.adresse_livraison}` : ''}
                        </div>
                    </div>
                    <span class="badge badge-${arret.statut}">${arret.statut_display}</span>
                </div>
            `).join('')}

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

    fetch(`/API/tournees/${id}/annuler/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
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

    arretCounter = 0;
    document.getElementById('arrets-container').innerHTML = '';

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
    select.innerHTML = '<option value="">Sélectionner un livreur...</option>';

    livreurs.filter(l => l.is_active && l.is_disponible).forEach(livreur => {
        select.innerHTML += `<option value="${livreur.id}">${livreur.full_name} - ${livreur.vehicule_type || 'Livreur'}</option>`;
    });
}

// Peupler le select des entrepôts
function populateWarehousesSelect() {
    const select = document.getElementById('warehouse');
    select.innerHTML = '<option value="">Sélectionner...</option>';

    warehouses.forEach(warehouse => {
        select.innerHTML += `<option value="${warehouse.id}">${warehouse.nom}</option>`;
    });
}

// Ajouter un formulaire d'arrêt
function addArretForm() {
    arretCounter++;
    const container = document.getElementById('arrets-container');
    const arretDiv = document.createElement('div');
    arretDiv.className = 'arret-form-item';
    arretDiv.id = `arret-${arretCounter}`;

    arretDiv.innerHTML = `
        <button type="button" class="remove-arret" onclick="removeArret(${arretCounter})">×</button>
        <h4 style="margin-bottom: 15px;">Arrêt #${arretCounter}</h4>
        <div class="form-grid">
            <div class="form-group">
                <label>Client *</label>
                <select class="arret-client" required>
                    <option value="">Sélectionner...</option>
                    ${clients.map(c => `<option value="${c.id}">${c.nom} ${c.prenom}</option>`).join('')}
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
document.getElementById('tournee-form').addEventListener('submit', function(e) {
    e.preventDefault();

    const id = document.getElementById('tournee-id').value;
    const data = {
        date: document.getElementById('date').value,
        livreur: document.getElementById('livreur').value,
        warehouse: document.getElementById('warehouse').value || null,
        heure_depart_prevue: document.getElementById('heure_depart_prevue').value,
        heure_retour_prevue: document.getElementById('heure_retour_prevue').value || null,
        distance_km: document.getElementById('distance_km').value || null,
        commentaire: document.getElementById('commentaire').value
    };

    const url = id ? `/API/tournees/${id}/` : '/API/tournees/';
    const method = id ? 'PUT' : 'POST';

    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
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
        return fetch('/API/arrets-livraison/', {
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
    fetch(`/API/tournees/${id}/`)
        .then(response => response.json())
        .then(tournee => {
            document.getElementById('tournee-id').value = tournee.id;
            document.getElementById('date').value = tournee.date;
            document.getElementById('livreur').value = tournee.livreur || '';
            document.getElementById('warehouse').value = tournee.warehouse || '';
            document.getElementById('heure_depart_prevue').value = tournee.heure_depart_prevue;
            document.getElementById('heure_retour_prevue').value = tournee.heure_retour_prevue || '';
            document.getElementById('distance_km').value = tournee.distance_km || '';
            document.getElementById('commentaire').value = tournee.commentaire || '';

            // Charger les arrêts existants
            tournee.arrets.forEach((arret, index) => {
                addArretForm();
                const lastArret = document.getElementById(`arret-${arretCounter}`);
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
