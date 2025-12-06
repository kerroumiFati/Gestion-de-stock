// Gestion des Livreurs
window.livreurs_list = window.livreurs_list || [];
window.currentLivreurId = window.currentLivreurId || null;

var livreurs = window.livreurs_list;
var currentLivreurId = window.currentLivreurId;

// Liste des entrepôts/vans
window.entrepots_list = window.entrepots_list || [];

// Fonction d'initialisation
window.initLivreursPage = function() {
    // Vérifier que les éléments nécessaires existent avant d'initialiser
    const tbody = document.getElementById('livreurs-tbody');
    if (!tbody) {
        console.log('[LIVREURS] Page elements not found, skipping initialization');
        return;
    }

    console.log('[LIVREURS] Initializing livreurs page');
    loadLivreurs();
    loadEntrepots();
    setupFormHandlers();
};

// Charger la liste des entrepôts/vans
function loadEntrepots() {
    fetch('/API/entrepots/', {
        credentials: 'same-origin',
        headers: {
            'Accept': 'application/json',
        }
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Gérer le format array ou object avec results
            const entrepots = Array.isArray(data) ? data : (data.results || []);
            window.entrepots_list = entrepots;
            populateEntrepotSelect(entrepots);
        })
        .catch(error => {
            console.error('Erreur chargement entrepôts:', error);
            // Afficher un message dans le select
            const select = document.getElementById('entrepot');
            if (select) {
                select.innerHTML = '<option value="">Erreur chargement - Reconnectez-vous</option>';
            }
        });
}

// Remplir le select des entrepôts (uniquement les vans)
function populateEntrepotSelect(entrepots) {
    const select = document.getElementById('entrepot');
    if (!select) return;

    select.innerHTML = '<option value="">Aucun van assigné</option>';

    // Filtrer pour afficher UNIQUEMENT les vans
    const vans = entrepots.filter(e => {
        const code = (e.code || '').toLowerCase();
        return code.includes('van');
    });

    vans.forEach(e => {
        const name = e.name || e.nom || 'Sans nom';
        const code = e.code || '';
        const option = document.createElement('option');
        option.value = e.id;
        option.textContent = `🚐 ${name} (${code})`;
        select.appendChild(option);
    });

    console.log('[LIVREURS] Vans chargés:', vans.length);
}

// NE PAS charger automatiquement au DOMContentLoaded car on utilise le chargement dynamique
// La page sera initialisée uniquement via fragment:loaded

// Charger les livreurs lors du chargement dynamique
document.addEventListener('fragment:loaded', function(e) {
    if (e.detail && e.detail.name === 'livreurs') {
        console.log('[LIVREURS] fragment:loaded event for livreurs');
        window.initLivreursPage();
    }
});

// Charger la liste des livreurs
function loadLivreurs() {
    fetch('/API/livreurs/')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            window.livreurs_list = data;
            displayLivreurs(data);
            updateStats(data);
        })
        .catch(error => {
            console.error('Erreur chargement livreurs:', error);
            const tbody = document.getElementById('livreurs-tbody');
            if (tbody) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="7" style="text-align: center; padding: 40px; color: #ef4444;">
                            <i class="fas fa-exclamation-triangle" style="font-size: 2rem; margin-bottom: 10px;"></i><br>
                            <strong>Erreur lors du chargement des livreurs</strong><br>
                            <small>${error.message}</small><br><br>
                            <button class="btn-primary" onclick="loadLivreurs()">Réessayer</button>
                        </td>
                    </tr>
                `;
                showMessage('Erreur lors du chargement des livreurs', 'error');
            } else {
                console.warn('Element livreurs-tbody not found, skipping error display');
            }
        });
}

// Afficher les livreurs dans le tableau
function displayLivreurs(livreursData) {
    const tbody = document.getElementById('livreurs-tbody');

    if (!tbody) {
        console.warn('Element livreurs-tbody not found, skipping display');
        return;
    }

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
            <td>${livreur.tournees_actives_count || 0}</td>
            <td>
                <div class="action-buttons">
                    <button class="btn-icon btn-edit" onclick="editLivreur(${livreur.id})" title="Modifier">
                        <i class="fas fa-edit"></i>
                    </button>
                    ${livreur.has_user_account ?
                        `<button class="btn-icon" onclick="resetPassword(${livreur.id})" title="Réinitialiser mot de passe" style="background: #f59e0b; color: white;">
                            <i class="fas fa-key"></i>
                        </button>` :
                        `<button class="btn-icon" onclick="createAccount(${livreur.id})" title="Créer compte utilisateur" style="background: #10b981; color: white;">
                            <i class="fas fa-user-plus"></i>
                        </button>`
                    }
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
    const filtered = window.livreurs_list.filter(livreur =>
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
            // Charger l'entrepôt/van assigné
            const entrepotSelect = document.getElementById('entrepot');
            if (entrepotSelect) {
                entrepotSelect.value = livreur.entrepot || '';
            }
        })
        .catch(error => {
            console.error('Erreur:', error);
            showMessage('Erreur lors du chargement des données', 'error');
        });
}

// Configuration des event handlers
function setupFormHandlers() {
    const form = document.getElementById('livreur-form');
    if (!form) return;

    // Soumettre le formulaire
    form.addEventListener('submit', function(e) {
        e.preventDefault();

        const id = document.getElementById('livreur-id').value;
        const entrepotValue = document.getElementById('entrepot').value;
        const data = {
            matricule: document.getElementById('nom').value.substring(0, 10).toUpperCase(),
            nom: document.getElementById('nom').value + ' ' + document.getElementById('prenom').value,
            telephone: document.getElementById('telephone').value,
            email: document.getElementById('email').value,
            vehicule_marque: document.getElementById('vehicule_marque').value || document.getElementById('vehicule_type').value,
            vehicule_immatriculation: document.getElementById('immatriculation').value,
            statut: 'actif',
            entrepot: entrepotValue ? parseInt(entrepotValue) : null
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
            console.log('[LIVREURS] Réponse du serveur:', result);
            console.log('[LIVREURS] ID:', id);
            console.log('[LIVREURS] compte_cree:', result.compte_cree);
            console.log('[LIVREURS] username:', result.username);
            console.log('[LIVREURS] mot_de_passe_initial:', result.mot_de_passe_initial);

            closeLivreurModal();
            loadLivreurs();

            // Afficher les informations de connexion pour un nouveau livreur
            if (!id && result.compte_cree && result.username && result.mot_de_passe_initial) {
                console.log('[LIVREURS] Affichage du modal de connexion');
                showLoginInfoModal(result);
            } else {
                console.log('[LIVREURS] Affichage du message de succès standard');
                showMessage(id ? 'Livreur modifié avec succès' : 'Livreur créé avec succès', 'success');
            }
        })
        .catch(error => {
            console.error('Erreur:', error);
            showMessage('Erreur lors de l\'enregistrement', 'error');
        });
    });
}

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

// Créer un compte utilisateur pour un livreur
function createAccount(id) {
    if (!confirm('Voulez-vous créer un compte utilisateur pour ce livreur ?\n\nUn nom d\'utilisateur et un mot de passe seront générés automatiquement.')) {
        return;
    }

    fetch(`/API/livreurs/${id}/creer_compte/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (response.status === 403) {
            throw new Error('Vous devez être administrateur pour créer un compte');
        }
        return response.json();
    })
    .then(result => {
        if (result.error) {
            showMessage(result.error, 'error');
        } else {
            // Recharger la liste des livreurs pour mettre à jour l'interface
            loadLivreurs();
            // Afficher les informations de connexion dans un modal
            showAccountCreatedModal(result);
        }
    })
    .catch(error => {
        console.error('Erreur:', error);
        showMessage(error.message || 'Erreur lors de la création du compte', 'error');
    });
}

// Réinitialiser le mot de passe d'un livreur
function resetPassword(id) {
    if (!confirm('Voulez-vous réinitialiser le mot de passe de ce livreur ?\n\nLe nouveau mot de passe sera généré avec le format : username + jour + mois')) {
        return;
    }

    fetch(`/API/livreurs/${id}/reinitialiser_mot_de_passe/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (response.status === 403) {
            throw new Error('Vous devez être administrateur pour réinitialiser un mot de passe');
        }
        if (response.status === 400) {
            return response.json().then(data => {
                throw new Error(data.error || 'Ce livreur n\'a pas de compte utilisateur. Créez d\'abord un compte.');
            });
        }
        return response.json();
    })
    .then(result => {
        if (result.error) {
            showMessage(result.error, 'error');
        } else {
            // Afficher le nouveau mot de passe dans un modal
            showPasswordResetModal(result);
        }
    })
    .catch(error => {
        console.error('Erreur:', error);
        showMessage(error.message || 'Erreur lors de la réinitialisation du mot de passe', 'error');
    });
}

// Modal pour afficher le nouveau mot de passe après réinitialisation
function showPasswordResetModal(data) {
    const modal = document.createElement('div');
    modal.id = 'passwordResetModal';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
    `;

    modal.innerHTML = `
        <div style="background: white; padding: 30px; border-radius: 12px; max-width: 500px; width: 90%; box-shadow: 0 20px 60px rgba(0,0,0,0.3);">
            <div style="text-align: center; margin-bottom: 20px;">
                <div style="width: 60px; height: 60px; background: #f59e0b; border-radius: 50%; margin: 0 auto 15px; display: flex; align-items: center; justify-content: center;">
                    <i class="fas fa-key" style="color: white; font-size: 24px;"></i>
                </div>
                <h2 style="margin: 0 0 10px 0; color: #1f2937;">Mot de passe réinitialisé</h2>
                <p style="color: #6b7280; margin: 0;">Le mot de passe a été réinitialisé avec succès</p>
            </div>

            <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                <div style="margin-bottom: 15px;">
                    <label style="display: block; font-size: 0.85rem; color: #6b7280; margin-bottom: 5px;">Nom d'utilisateur</label>
                    <div style="background: white; padding: 12px; border-radius: 6px; font-family: monospace; font-size: 1.1rem; color: #1f2937; border: 2px solid #e5e7eb;">
                        <strong>${data.username}</strong>
                    </div>
                </div>

                <div style="margin-bottom: 10px;">
                    <label style="display: block; font-size: 0.85rem; color: #6b7280; margin-bottom: 5px;">Nouveau mot de passe</label>
                    <div style="background: white; padding: 12px; border-radius: 6px; font-family: monospace; font-size: 1.1rem; color: #1f2937; border: 2px solid #e5e7eb; display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: #10b981; font-weight: 600;">${data.nouveau_mot_de_passe}</span>
                        <button onclick="copyToClipboard('${data.nouveau_mot_de_passe}', 'password')" style="background: #8b5cf6; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-size: 0.85rem;">
                            <i class="fas fa-copy"></i> Copier
                        </button>
                    </div>
                </div>
            </div>

            <div style="background: #fef3c7; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #f59e0b;">
                <p style="margin: 0; color: #92400e; font-size: 0.85rem;">
                    <i class="fas fa-info-circle"></i> Format : <code style="background: white; padding: 2px 6px; border-radius: 3px;">username + jour + mois (JJMM)</code>
                </p>
            </div>

            <div style="text-align: center;">
                <button onclick="closePasswordResetModal()" style="background: #8b5cf6; color: white; border: none; padding: 12px 30px; border-radius: 8px; cursor: pointer; font-size: 1rem; font-weight: 600;">
                    Fermer
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
}

// Fonction pour fermer la modal de réinitialisation de mot de passe
window.closePasswordResetModal = function() {
    const modal = document.getElementById('passwordResetModal');
    if (modal) {
        modal.remove();
    }
}

// Modal pour afficher les informations après création de compte
function showAccountCreatedModal(data) {
    const modal = document.createElement('div');
    modal.id = 'accountCreatedModal';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
    `;

    modal.innerHTML = `
        <div style="background: white; padding: 30px; border-radius: 12px; max-width: 500px; width: 90%; box-shadow: 0 20px 60px rgba(0,0,0,0.3);">
            <div style="text-align: center; margin-bottom: 20px;">
                <div style="width: 60px; height: 60px; background: #10b981; border-radius: 50%; margin: 0 auto 15px; display: flex; align-items: center; justify-content: center;">
                    <i class="fas fa-user-check" style="color: white; font-size: 24px;"></i>
                </div>
                <h2 style="margin: 0 0 10px 0; color: #1f2937;">Compte créé avec succès</h2>
                <p style="color: #6b7280; margin: 0;">Le compte utilisateur a été créé pour ce livreur</p>
            </div>

            <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                <div style="margin-bottom: 15px;">
                    <label style="display: block; font-size: 0.85rem; color: #6b7280; margin-bottom: 5px;">Nom d'utilisateur</label>
                    <div style="background: white; padding: 12px; border-radius: 6px; font-family: monospace; font-size: 1.1rem; color: #1f2937; border: 2px solid #e5e7eb; display: flex; justify-content: space-between; align-items: center;">
                        <strong>${data.username}</strong>
                        <button onclick="copyToClipboard('${data.username}', 'username')" style="background: #8b5cf6; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-size: 0.85rem;">
                            <i class="fas fa-copy"></i> Copier
                        </button>
                    </div>
                </div>

                <div style="margin-bottom: 10px;">
                    <label style="display: block; font-size: 0.85rem; color: #6b7280; margin-bottom: 5px;">Mot de passe</label>
                    <div style="background: white; padding: 12px; border-radius: 6px; font-family: monospace; font-size: 1.1rem; color: #1f2937; border: 2px solid #e5e7eb; display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: #10b981; font-weight: 600;">${data.mot_de_passe}</span>
                        <button onclick="copyToClipboard('${data.mot_de_passe}', 'password')" style="background: #8b5cf6; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-size: 0.85rem;">
                            <i class="fas fa-copy"></i> Copier
                        </button>
                    </div>
                </div>
            </div>

            <div style="background: #fef3c7; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #f59e0b;">
                <p style="margin: 0 0 10px 0; color: #92400e; font-size: 0.9rem;">
                    <i class="fas fa-exclamation-triangle"></i> <strong>Important :</strong>
                    Notez ces informations maintenant ! Le mot de passe ne sera plus affiché.
                </p>
                <p style="margin: 0; color: #92400e; font-size: 0.85rem;">
                    <i class="fas fa-info-circle"></i> Format : <code style="background: white; padding: 2px 6px; border-radius: 3px;">username + jour + mois (JJMM)</code>
                </p>
            </div>

            <div style="text-align: center;">
                <button onclick="closeAccountCreatedModal()" style="background: #10b981; color: white; border: none; padding: 12px 30px; border-radius: 8px; cursor: pointer; font-size: 1rem; font-weight: 600;">
                    J'ai noté les informations
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
}

// Fonction pour fermer la modal de création de compte
window.closeAccountCreatedModal = function() {
    const modal = document.getElementById('accountCreatedModal');
    if (modal) {
        modal.remove();
    }
}

// Fermer le modal en cliquant en dehors
window.onclick = function(event) {
    const livreurModal = document.getElementById('livreurModal');
    const passwordResetModal = document.getElementById('passwordResetModal');
    const loginInfoModal = document.getElementById('loginInfoModal');
    const accountCreatedModal = document.getElementById('accountCreatedModal');

    if (event.target == livreurModal) {
        closeLivreurModal();
    }

    if (event.target == passwordResetModal) {
        closePasswordResetModal();
    }

    if (event.target == loginInfoModal) {
        closeLoginInfoModal();
    }

    if (event.target == accountCreatedModal) {
        closeAccountCreatedModal();
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

// Afficher modal avec les informations de connexion
function showLoginInfoModal(livreurData) {
    const modal = document.createElement('div');
    modal.id = 'loginInfoModal';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
    `;

    modal.innerHTML = `
        <div style="background: white; padding: 30px; border-radius: 12px; max-width: 500px; width: 90%; box-shadow: 0 20px 60px rgba(0,0,0,0.3);">
            <div style="text-align: center; margin-bottom: 20px;">
                <div style="width: 60px; height: 60px; background: #10b981; border-radius: 50%; margin: 0 auto 15px; display: flex; align-items: center; justify-content: center;">
                    <i class="fas fa-check" style="color: white; font-size: 24px;"></i>
                </div>
                <h2 style="margin: 0 0 10px 0; color: #1f2937;">Livreur créé avec succès !</h2>
                <p style="color: #6b7280; margin: 0;">Le compte d'accès a été créé automatiquement</p>
            </div>

            <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                <h3 style="margin: 0 0 15px 0; font-size: 1rem; color: #1f2937;">
                    <i class="fas fa-key"></i> Informations de connexion
                </h3>

                <div style="margin-bottom: 15px;">
                    <label style="display: block; font-size: 0.85rem; color: #6b7280; margin-bottom: 5px;">Nom d'utilisateur</label>
                    <div style="background: white; padding: 12px; border-radius: 6px; font-family: monospace; font-size: 1.1rem; color: #1f2937; border: 2px solid #e5e7eb; display: flex; justify-content: space-between; align-items: center;">
                        <span id="username-display">${livreurData.username}</span>
                        <button onclick="copyToClipboard('${livreurData.username}', 'username')" style="background: #8b5cf6; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-size: 0.85rem;">
                            <i class="fas fa-copy"></i> Copier
                        </button>
                    </div>
                </div>

                <div style="margin-bottom: 10px;">
                    <label style="display: block; font-size: 0.85rem; color: #6b7280; margin-bottom: 5px;">Mot de passe</label>
                    <div style="background: white; padding: 12px; border-radius: 6px; font-family: monospace; font-size: 1.1rem; color: #1f2937; border: 2px solid #e5e7eb; display: flex; justify-content: space-between; align-items: center;">
                        <span id="password-display">${livreurData.mot_de_passe_initial}</span>
                        <button onclick="copyToClipboard('${livreurData.mot_de_passe_initial}', 'password')" style="background: #8b5cf6; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-size: 0.85rem;">
                            <i class="fas fa-copy"></i> Copier
                        </button>
                    </div>
                </div>
            </div>

            <div style="background: #fef3c7; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #f59e0b;">
                <p style="margin: 0 0 10px 0; color: #92400e; font-size: 0.9rem;">
                    <i class="fas fa-exclamation-triangle"></i> <strong>Important :</strong>
                    Notez ces informations maintenant ! Le mot de passe ne sera plus affiché après la fermeture de cette fenêtre.
                </p>
                <p style="margin: 0; color: #92400e; font-size: 0.85rem; padding-left: 20px;">
                    <i class="fas fa-info-circle"></i> Le mot de passe est généré automatiquement avec le format : <br>
                    <code style="background: white; padding: 2px 6px; border-radius: 3px; font-weight: 600;">nom_utilisateur + jour + mois</code>
                    <br><small>Exemple : LIV001 créé le 13/11 → LIV0011311</small>
                </p>
            </div>

            <div style="text-align: center;">
                <button onclick="closeLoginInfoModal()" style="background: #8b5cf6; color: white; border: none; padding: 12px 30px; border-radius: 8px; cursor: pointer; font-size: 1rem; font-weight: 600;">
                    J'ai noté les informations
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
}

// Fonction pour fermer la modal des informations de connexion
window.closeLoginInfoModal = function() {
    const modal = document.getElementById('loginInfoModal');
    if (modal) {
        modal.remove();
    }
}

// Copier dans le presse-papier
function copyToClipboard(text, type) {
    navigator.clipboard.writeText(text).then(() => {
        showMessage(type === 'username' ? 'Nom d\'utilisateur copié' : 'Mot de passe copié', 'success');
    }).catch(err => {
        console.error('Erreur copie:', err);
        showMessage('Erreur lors de la copie', 'error');
    });
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
