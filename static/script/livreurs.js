// Gestion des Livreurs
let livreurs = [];
let currentLivreurId = null;

// Charger les livreurs au démarrage
document.addEventListener('DOMContentLoaded', function() {
    loadLivreurs();
});

// Charger la liste des livreurs
function loadLivreurs() {
    fetch('/API/livreurs/')
        .then(response => response.json())
        .then(data => {
            livreurs = data;
            displayLivreurs(data);
            updateStats(data);
        })
        .catch(error => {
            console.error('Erreur:', error);
            showMessage('Erreur lors du chargement des livreurs', 'error');
        });
}

// Afficher les livreurs dans le tableau
function displayLivreurs(livreursData) {
    const tbody = document.getElementById('livreurs-tbody');

    if (livreursData.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; padding: 40px;">
                    <i class="fas fa-inbox"></i><br>
                    Aucun livreur trouvé
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = livreursData.map(livreur => `
        <tr>
            <td><strong>${livreur.full_name}</strong></td>
            <td>${livreur.telephone}</td>
            <td>${livreur.vehicule_type || '-'}</td>
            <td>${livreur.immatriculation || '-'}</td>
            <td>
                ${livreur.is_disponible ?
                    '<span class="badge badge-success"><i class="fas fa-check-circle"></i> Disponible</span>' :
                    '<span class="badge badge-warning"><i class="fas fa-truck"></i> En tournée</span>'}
                ${!livreur.is_active ? '<span class="badge badge-danger">Inactif</span>' : ''}
            </td>
            <td>${livreur.nombre_tournees || 0}</td>
            <td>
                <div class="action-buttons">
                    <button class="btn-icon btn-edit" onclick="editLivreur(${livreur.id})" title="Modifier">
                        <i class="fas fa-edit"></i>
                    </button>
                    ${livreur.is_disponible ?
                        `<button class="btn-icon btn-toggle" onclick="toggleDisponibilite(${livreur.id}, false)" title="Marquer indisponible">
                            <i class="fas fa-ban"></i>
                        </button>` :
                        `<button class="btn-icon btn-toggle" onclick="toggleDisponibilite(${livreur.id}, true)" title="Marquer disponible">
                            <i class="fas fa-check"></i>
                        </button>`
                    }
                    <button class="btn-icon btn-delete" onclick="deleteLivreur(${livreur.id})" title="Supprimer">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

// Mettre à jour les statistiques
function updateStats(livreursData) {
    const total = livreursData.length;
    const disponibles = livreursData.filter(l => l.is_disponible && l.is_active).length;
    const enTournee = livreursData.filter(l => !l.is_disponible && l.is_active).length;

    document.getElementById('total-livreurs').textContent = total;
    document.getElementById('livreurs-disponibles').textContent = disponibles;
    document.getElementById('livreurs-en-tournee').textContent = enTournee;
}

// Filtrer les livreurs
function filterLivreurs() {
    const search = document.getElementById('search-livreur').value.toLowerCase();
    const filtered = livreurs.filter(livreur =>
        livreur.full_name.toLowerCase().includes(search) ||
        livreur.telephone.includes(search) ||
        (livreur.vehicule_type && livreur.vehicule_type.toLowerCase().includes(search)) ||
        (livreur.immatriculation && livreur.immatriculation.toLowerCase().includes(search))
    );
    displayLivreurs(filtered);
}

// Ouvrir le modal
function openLivreurModal(livreurId = null) {
    currentLivreurId = livreurId;
    const modal = document.getElementById('livreurModal');
    const title = document.getElementById('modal-title');

    if (livreurId) {
        title.textContent = 'Modifier le Livreur';
        loadLivreurData(livreurId);
    } else {
        title.textContent = 'Nouveau Livreur';
        document.getElementById('livreur-form').reset();
        document.getElementById('livreur-id').value = '';
    }

    modal.style.display = 'block';
}

// Fermer le modal
function closeLivreurModal() {
    document.getElementById('livreurModal').style.display = 'none';
    currentLivreurId = null;
}

// Charger les données d'un livreur
function loadLivreurData(id) {
    fetch(`/API/livreurs/${id}/`)
        .then(response => response.json())
        .then(livreur => {
            document.getElementById('livreur-id').value = livreur.id;
            document.getElementById('nom').value = livreur.nom;
            document.getElementById('prenom').value = livreur.prenom;
            document.getElementById('telephone').value = livreur.telephone;
            document.getElementById('email').value = livreur.email || '';
            document.getElementById('adresse').value = livreur.adresse || '';
            document.getElementById('vehicule_type').value = livreur.vehicule_type || '';
            document.getElementById('vehicule_marque').value = livreur.vehicule_marque || '';
            document.getElementById('immatriculation').value = livreur.immatriculation || '';
            document.getElementById('capacite_charge').value = livreur.capacite_charge || '';
            document.getElementById('numero_permis').value = livreur.numero_permis || '';
            document.getElementById('date_expiration_permis').value = livreur.date_expiration_permis || '';
        })
        .catch(error => {
            console.error('Erreur:', error);
            showMessage('Erreur lors du chargement des données', 'error');
        });
}

// Soumettre le formulaire
document.getElementById('livreur-form').addEventListener('submit', function(e) {
    e.preventDefault();

    const id = document.getElementById('livreur-id').value;
    const data = {
        nom: document.getElementById('nom').value,
        prenom: document.getElementById('prenom').value,
        telephone: document.getElementById('telephone').value,
        email: document.getElementById('email').value,
        adresse: document.getElementById('adresse').value,
        vehicule_type: document.getElementById('vehicule_type').value,
        vehicule_marque: document.getElementById('vehicule_marque').value,
        immatriculation: document.getElementById('immatriculation').value,
        capacite_charge: document.getElementById('capacite_charge').value || null,
        numero_permis: document.getElementById('numero_permis').value,
        date_expiration_permis: document.getElementById('date_expiration_permis').value || null,
        is_active: true,
        is_disponible: true
    };

    const url = id ? `/API/livreurs/${id}/` : '/API/livreurs/';
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
    .then(result => {
        closeLivreurModal();
        loadLivreurs();
        showMessage(id ? 'Livreur modifié avec succès' : 'Livreur créé avec succès', 'success');
    })
    .catch(error => {
        console.error('Erreur:', error);
        showMessage('Erreur lors de l\'enregistrement', 'error');
    });
});

// Modifier un livreur
function editLivreur(id) {
    openLivreurModal(id);
}

// Supprimer un livreur
function deleteLivreur(id) {
    if (!confirm('Êtes-vous sûr de vouloir supprimer ce livreur ?')) {
        return;
    }

    fetch(`/API/livreurs/${id}/`, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => {
        if (response.ok) {
            loadLivreurs();
            showMessage('Livreur supprimé avec succès', 'success');
        } else {
            throw new Error('Erreur lors de la suppression');
        }
    })
    .catch(error => {
        console.error('Erreur:', error);
        showMessage('Erreur lors de la suppression', 'error');
    });
}

// Basculer la disponibilité
function toggleDisponibilite(id, disponible) {
    const action = disponible ? 'marquer_disponible' : 'marquer_indisponible';

    fetch(`/API/livreurs/${id}/${action}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(result => {
        loadLivreurs();
        showMessage(disponible ? 'Livreur marqué disponible' : 'Livreur marqué indisponible', 'success');
    })
    .catch(error => {
        console.error('Erreur:', error);
        showMessage('Erreur lors de la mise à jour', 'error');
    });
}

// Fermer le modal en cliquant en dehors
window.onclick = function(event) {
    const modal = document.getElementById('livreurModal');
    if (event.target == modal) {
        closeLivreurModal();
    }
}

// Fonction pour afficher les messages
function showMessage(message, type) {
    // Créer un élément de notification
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

    // Supprimer après 3 secondes
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

// Ajouter les animations CSS
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
