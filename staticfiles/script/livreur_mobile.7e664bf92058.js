// Application Mobile pour Livreurs
let currentTournee = null;
let allArrets = [];
let signaturePad = null;
let tourneeVerrouillee = false;  // Indique si une tournée est en cours (verrouillée)

// Fonction d'initialisation
function initLivreurMobilePage() {
    // Vérifier que les éléments nécessaires existent
    const canvas = document.getElementById('signature-canvas');
    if (!canvas) {
        console.log('[LIVREUR_MOBILE] Page elements not found, skipping initialization');
        return;
    }

    console.log('[LIVREUR_MOBILE] Initializing livreur mobile page');
    initSignaturePad();
    loadLivreurData();
    setupFormHandlers();
}

// NE PAS charger automatiquement au DOMContentLoaded car on utilise le chargement dynamique
// La page sera initialisée uniquement via fragment:loaded

// Charger lors du chargement dynamique
document.addEventListener('fragment:loaded', function(e) {
    if (e.detail && e.detail.name === 'livreur_mobile') {
        console.log('[LIVREUR_MOBILE] fragment:loaded event for livreur_mobile');
        initLivreurMobilePage();
    }
});

function initSignaturePad() {
    const canvas = document.getElementById('signature-canvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;

    let drawing = false;

    canvas.addEventListener('mousedown', startDrawing);
    canvas.addEventListener('mousemove', draw);
    canvas.addEventListener('mouseup', stopDrawing);
    canvas.addEventListener('mouseout', stopDrawing);

    // Touch events pour mobile
    canvas.addEventListener('touchstart', function(e) {
        e.preventDefault();
        const touch = e.touches[0];
        const mouseEvent = new MouseEvent('mousedown', {
            clientX: touch.clientX,
            clientY: touch.clientY
        });
        canvas.dispatchEvent(mouseEvent);
    });

    canvas.addEventListener('touchmove', function(e) {
        e.preventDefault();
        const touch = e.touches[0];
        const mouseEvent = new MouseEvent('mousemove', {
            clientX: touch.clientX,
            clientY: touch.clientY
        });
        canvas.dispatchEvent(mouseEvent);
    });

    canvas.addEventListener('touchend', function(e) {
        e.preventDefault();
        const mouseEvent = new MouseEvent('mouseup', {});
        canvas.dispatchEvent(mouseEvent);
    });

    function startDrawing(e) {
        drawing = true;
        const rect = canvas.getBoundingClientRect();
        ctx.beginPath();
        ctx.moveTo(e.clientX - rect.left, e.clientY - rect.top);
    }

    function draw(e) {
        if (!drawing) return;
        const rect = canvas.getBoundingClientRect();
        ctx.lineTo(e.clientX - rect.left, e.clientY - rect.top);
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 2;
        ctx.lineCap = 'round';
        ctx.stroke();
    }

    function stopDrawing() {
        drawing = false;
    }

    signaturePad = { canvas, ctx };
}

function clearSignature() {
    if (!signaturePad) return;
    const ctx = signaturePad.ctx;
    const canvas = signaturePad.canvas;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
}

function getSignatureData() {
    if (!signaturePad) return '';
    return signaturePad.canvas.toDataURL('image/png');
}

async function loadLivreurData() {
    try {
        const joursNoms = ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'];

        // 1. D'abord vérifier s'il y a une tournée en cours (verrouillée)
        const tourneeResponse = await fetch('/API/distribution/tournees/?statut=en_cours');
        const tourneeData = await tourneeResponse.json();
        const tourneesEnCours = Array.isArray(tourneeData) ? tourneeData : (tourneeData.results || []);

        console.log('[LIVREUR_MOBILE] Tournées en cours:', tourneesEnCours.length);

        if (tourneesEnCours.length > 0) {
            // Une tournée est en cours - VERROUILLÉE
            currentTournee = tourneesEnCours[0];
            tourneeVerrouillee = true;

            // Utiliser la date de la tournée (pas la date actuelle)
            const dateTournee = new Date(currentTournee.date_tournee);
            const jourSemaineTournee = dateTournee.getDay(); // 0=Dimanche
            const jourSemaineAPI = jourSemaineTournee === 0 ? 7 : jourSemaineTournee; // 1=Lundi, 7=Dimanche
            const jourNom = joursNoms[jourSemaineTournee];

            console.log('[LIVREUR_MOBILE] Tournée verrouillée - Date:', currentTournee.date_tournee, 'Jour:', jourNom);

            // Charger les clients assignés au livreur pour le jour de la tournée
            const livreurId = currentTournee.livreur;
            const configResponse = await fetch(`/API/distribution/clients-livreurs-hebdo/?livreur=${livreurId}&jour_semaine=${jourSemaineAPI}&is_active=true`);
            const configData = await configResponse.json();
            const configs = Array.isArray(configData) ? configData : (configData.results || []);

            console.log('[LIVREUR_MOBILE] Clients pour cette tournée:', configs.length);

            // Afficher avec info de verrouillage
            displayTourneeVerrouilleeInfo(currentTournee, configs.length);
            displayClientsJourAvecActions(configs, currentTournee.id);

        } else {
            // Pas de tournée en cours - vérifier s'il y en a une planifiée ou afficher les clients du jour
            tourneeVerrouillee = false;

            const today = new Date();
            const dayOfWeek = today.getDay();
            const jourSemaine = dayOfWeek === 0 ? 7 : dayOfWeek;
            const jourNom = joursNoms[dayOfWeek];

            console.log('[LIVREUR_MOBILE] Pas de tournée en cours - Jour actuel:', jourNom);

            // Charger les clients du jour actuel
            const configResponse = await fetch(`/API/distribution/clients-livreurs-hebdo/?jour_semaine=${jourSemaine}&is_active=true`);
            const configData = await configResponse.json();
            const configs = Array.isArray(configData) ? configData : (configData.results || []);

            if (configs.length > 0) {
                displayJourInfoAvecDemarrage(jourNom, configs);
            } else {
                showEmptyState(`Aucun client assigné pour ${jourNom}`);
            }
        }
    } catch (error) {
        console.error('Erreur chargement données:', error);
        showEmptyState('Erreur de chargement');
    }
}

// Afficher les infos d'une tournée verrouillée (en cours)
function displayTourneeVerrouilleeInfo(tournee, nbClients) {
    const dateTournee = new Date(tournee.date_tournee);
    const dateStr = dateTournee.toLocaleDateString('fr-FR', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });

    document.getElementById('livreur-name').textContent = tournee.livreur_nom || 'Livreur';
    document.getElementById('tournee-status').innerHTML = '<span style="color: #f59e0b;"><i class="fas fa-lock"></i> Tournée en cours</span>';
    document.getElementById('tournee-numero').textContent = tournee.numero_tournee || '-';
    document.getElementById('tournee-date').textContent = dateStr;
    document.getElementById('tournee-heure').textContent = tournee.heure_debut || '-';
    document.getElementById('tournee-arrets').textContent = nbClients;

    document.getElementById('tournee-info').style.display = 'block';
    document.getElementById('progress-bar').style.display = 'block';
}

// Afficher les clients avec possibilité de démarrer une tournée
function displayJourInfoAvecDemarrage(jourNom, configs) {
    const today = new Date();
    const dateStr = today.toLocaleDateString('fr-FR', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });

    document.getElementById('livreur-name').textContent = 'Mes clients du jour';
    document.getElementById('tournee-status').textContent = jourNom;
    document.getElementById('tournee-numero').textContent = '-';
    document.getElementById('tournee-date').textContent = dateStr;
    document.getElementById('tournee-heure').textContent = '-';
    document.getElementById('tournee-arrets').textContent = configs.length;

    document.getElementById('tournee-info').style.display = 'block';
    document.getElementById('progress-bar').style.display = 'none';

    // Afficher les clients avec bouton démarrer
    displayClientsAvecBoutonDemarrer(configs);
}

// Afficher les clients avec bouton pour démarrer la tournée
function displayClientsAvecBoutonDemarrer(configs) {
    const container = document.getElementById('arrets-container');

    if (configs.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-inbox"></i>
                <p>Aucun client assigné pour aujourd'hui</p>
            </div>
        `;
        return;
    }

    // Bouton pour démarrer la tournée
    let html = `
        <div style="background: linear-gradient(135deg, #10b981, #059669); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; text-align: center;">
            <h4 style="margin: 0 0 10px 0;"><i class="fas fa-play-circle"></i> Prêt à démarrer ?</h4>
            <p style="margin: 0 0 15px 0; opacity: 0.9;">${configs.length} client(s) à visiter aujourd'hui</p>
            <button onclick="demarrerTournee()" class="btn" style="background: white; color: #059669; padding: 12px 30px; font-weight: bold; border-radius: 8px;">
                <i class="fas fa-rocket"></i> Démarrer la tournée
            </button>
        </div>
    `;

    // Liste des clients (preview)
    configs.sort((a, b) => (a.ordre_passage || 0) - (b.ordre_passage || 0));

    html += configs.map((config, index) => `
        <div class="arret-card" style="opacity: 0.7;">
            <div class="arret-header" style="background: #9ca3af;">
                <span class="arret-number">Client #${index + 1}</span>
                <span class="badge badge-en_attente">En attente</span>
            </div>
            <div class="arret-body">
                <div class="client-name">${config.client_nom || 'Client'}</div>
                ${config.client_adresse ? `
                    <div class="arret-detail">
                        <i class="fas fa-map-marker-alt"></i>
                        <span>${config.client_adresse}</span>
                    </div>
                ` : ''}
            </div>
        </div>
    `).join('');

    container.innerHTML = html;
}

// Démarrer une nouvelle tournée
async function demarrerTournee() {
    if (!confirm('Voulez-vous démarrer la tournée maintenant ?')) return;

    try {
        const today = new Date();
        const dateStr = today.toISOString().split('T')[0]; // Format YYYY-MM-DD
        const heureDebut = today.toTimeString().split(' ')[0]; // Format HH:MM:SS

        // Créer une nouvelle tournée
        const response = await fetch('/API/distribution/tournees/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                date_tournee: dateStr,
                statut: 'en_cours',
                heure_debut: heureDebut
            })
        });

        if (response.ok) {
            const tournee = await response.json();
            currentTournee = tournee;
            tourneeVerrouillee = true;
            showNotification('Tournée démarrée !', 'success');

            // Recharger les données
            await loadLivreurData();
        } else {
            const error = await response.json();
            showNotification(error.error || error.detail || 'Erreur lors du démarrage', 'error');
        }
    } catch (error) {
        console.error('Erreur démarrage tournée:', error);
        showNotification('Erreur de connexion', 'error');
    }
}

// Terminer la tournée en cours
async function terminerTournee() {
    if (!currentTournee) return;

    if (!confirm('Voulez-vous terminer cette tournée ?')) return;

    try {
        const heureFin = new Date().toTimeString().split(' ')[0];

        const response = await fetch(`/API/distribution/tournees/${currentTournee.id}/`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                statut: 'terminee',
                heure_fin: heureFin
            })
        });

        if (response.ok) {
            tourneeVerrouillee = false;
            currentTournee = null;
            showNotification('Tournée terminée !', 'success');

            // Recharger les données
            await loadLivreurData();
        } else {
            const error = await response.json();
            showNotification(error.error || 'Erreur lors de la terminaison', 'error');
        }
    } catch (error) {
        console.error('Erreur terminaison tournée:', error);
        showNotification('Erreur de connexion', 'error');
    }
}

// Afficher les clients pour une tournée en cours (avec actions)
function displayClientsJourAvecActions(configs, tourneeId) {
    const container = document.getElementById('arrets-container');

    if (configs.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-inbox"></i>
                <p>Aucun client pour cette tournée</p>
            </div>
        `;
        return;
    }

    // Bouton pour terminer la tournée
    let html = `
        <div style="background: linear-gradient(135deg, #ef4444, #dc2626); color: white; padding: 15px; border-radius: 10px; margin-bottom: 20px; text-align: center;">
            <button onclick="terminerTournee()" class="btn" style="background: white; color: #dc2626; padding: 10px 25px; font-weight: bold; border-radius: 8px;">
                <i class="fas fa-flag-checkered"></i> Terminer la tournée
            </button>
        </div>
    `;

    // Trier par ordre de passage
    configs.sort((a, b) => (a.ordre_passage || 0) - (b.ordre_passage || 0));

    html += configs.map((config, index) => `
        <div class="arret-card">
            <div class="arret-header">
                <span class="arret-number">Client #${index + 1}</span>
                <span class="badge badge-en_attente">À visiter</span>
            </div>
            <div class="arret-body">
                <div class="client-name">${config.client_nom || 'Client'}</div>

                ${config.client_adresse ? `
                    <div class="arret-detail">
                        <i class="fas fa-map-marker-alt"></i>
                        <span>${config.client_adresse}</span>
                    </div>
                ` : ''}

                ${config.client_telephone ? `
                    <div class="arret-detail">
                        <i class="fas fa-phone"></i>
                        <span>${config.client_telephone}</span>
                    </div>
                ` : ''}

                ${config.notes ? `
                    <div class="arret-detail">
                        <i class="fas fa-info-circle"></i>
                        <span>${config.notes}</span>
                    </div>
                ` : ''}

                <div class="btn-group">
                    ${config.client_adresse ? `
                        <button class="btn btn-navigate" onclick="navigateToAddress('${encodeURIComponent(config.client_adresse)}')">
                            <i class="fas fa-directions"></i> Naviguer
                        </button>
                    ` : ''}
                    ${config.client_telephone ? `
                        <button class="btn btn-success" onclick="callClient('${config.client_telephone}')" style="grid-column: auto;">
                            <i class="fas fa-phone"></i> Appeler
                        </button>
                    ` : ''}
                </div>
            </div>
        </div>
    `).join('');

    container.innerHTML = html;
}

function callClient(telephone) {
    window.location.href = 'tel:' + telephone;
}

function displayTourneeInfo(tournee) {
    document.getElementById('livreur-name').textContent = tournee.livreur_nom || 'Livreur';
    document.getElementById('tournee-status').textContent = getStatusText(tournee.statut);
    document.getElementById('tournee-numero').textContent = tournee.numero;
    document.getElementById('tournee-date').textContent = formatDate(tournee.date);
    document.getElementById('tournee-heure').textContent = tournee.heure_depart_prevue;
    document.getElementById('tournee-arrets').textContent = tournee.nombre_arrets || 0;

    document.getElementById('tournee-info').style.display = 'block';
    document.getElementById('progress-bar').style.display = 'block';
}

async function loadArrets(tourneeId) {
    try {
        const response = await fetch(`/API/arrets-livraison/?tournee=${tourneeId}`);
        allArrets = await response.json();
        displayArrets(allArrets);
        updateProgress();
    } catch (error) {
        console.error('Erreur chargement arrêts:', error);
    }
}

function displayArrets(arrets) {
    const container = document.getElementById('arrets-container');

    if (arrets.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-inbox"></i>
                <p>Aucun arrêt dans cette tournée</p>
            </div>
        `;
        return;
    }

    // Trier par ordre
    arrets.sort((a, b) => a.ordre - b.ordre);

    container.innerHTML = arrets.map(arret => `
        <div class="arret-card">
            <div class="arret-header">
                <span class="arret-number">Arrêt #${arret.ordre}</span>
                <span class="badge badge-${arret.statut}">${arret.statut_display}</span>
            </div>
            <div class="arret-body">
                <div class="client-name">${arret.client_nom}</div>

                <div class="arret-detail">
                    <i class="fas fa-map-marker-alt"></i>
                    <span>${arret.adresse_livraison}</span>
                </div>

                <div class="arret-detail">
                    <i class="fas fa-clock"></i>
                    <span>Heure prévue: ${arret.heure_prevue || 'Non définie'}</span>
                </div>

                ${arret.instructions ? `
                    <div class="arret-detail">
                        <i class="fas fa-info-circle"></i>
                        <span>${arret.instructions}</span>
                    </div>
                ` : ''}

                ${arret.statut === 'en_attente' || arret.statut === 'en_cours' ? `
                    <div class="btn-group">
                        <button class="btn btn-navigate" onclick="navigateToAddress('${encodeURIComponent(arret.adresse_livraison)}')">
                            <i class="fas fa-directions"></i> Naviguer
                        </button>
                        <button class="btn btn-success" onclick="openLivraisonModal(${arret.id})">
                            <i class="fas fa-check"></i> Livré
                        </button>
                        <button class="btn btn-danger" onclick="openEchecModal(${arret.id})">
                            <i class="fas fa-times"></i> Échec
                        </button>
                    </div>
                ` : ''}

                ${arret.statut === 'livre' ? `
                    <div class="arret-detail" style="color: #10b981; font-weight: 600;">
                        <i class="fas fa-check-circle"></i>
                        <span>Livré à ${arret.heure_livraison_reelle || 'N/A'}</span>
                    </div>
                    ${arret.nom_recepteur ? `
                        <div class="arret-detail">
                            <i class="fas fa-user"></i>
                            <span>Reçu par: ${arret.nom_recepteur}</span>
                        </div>
                    ` : ''}
                ` : ''}

                ${arret.statut === 'echec' ? `
                    <div class="arret-detail" style="color: #ef4444; font-weight: 600;">
                        <i class="fas fa-exclamation-circle"></i>
                        <span>Échec: ${arret.raison_echec || 'Non spécifiée'}</span>
                    </div>
                ` : ''}
            </div>
        </div>
    `).join('');
}

function navigateToAddress(address) {
    const decodedAddress = decodeURIComponent(address);
    // Ouvrir Google Maps ou l'application de navigation par défaut
    const mapsUrl = `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(decodedAddress)}`;
    window.open(mapsUrl, '_blank');
}

function openLivraisonModal(arretId) {
    document.getElementById('arret-id').value = arretId;
    document.getElementById('nom-recepteur').value = '';
    document.getElementById('commentaire').value = '';
    clearSignature();
    document.getElementById('livraisonModal').style.display = 'block';
}

function closeLivraisonModal() {
    document.getElementById('livraisonModal').style.display = 'none';
}

function openEchecModal(arretId) {
    document.getElementById('echec-arret-id').value = arretId;
    document.getElementById('raison-echec').value = '';
    document.getElementById('echec-commentaire').value = '';
    document.getElementById('echecModal').style.display = 'block';
}

function closeEchecModal() {
    document.getElementById('echecModal').style.display = 'none';
}

function setupFormHandlers() {
    // Form livraison
    document.getElementById('livraison-form').addEventListener('submit', async function(e) {
        e.preventDefault();

        const arretId = document.getElementById('arret-id').value;
        const nomRecepteur = document.getElementById('nom-recepteur').value;
        const commentaire = document.getElementById('commentaire').value;
        const signature = getSignatureData();

        try {
            const response = await fetch(`/API/arrets-livraison/${arretId}/marquer_livre/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    nom_recepteur: nomRecepteur,
                    commentaire: commentaire,
                    signature_client: signature,
                    heure_livraison_reelle: new Date().toTimeString().split(' ')[0]
                })
            });

            if (response.ok) {
                closeLivraisonModal();
                await loadArrets(currentTournee.id);
                showNotification('Livraison confirmée avec succès', 'success');
            } else {
                const error = await response.json();
                showNotification(error.error || 'Erreur lors de la confirmation', 'error');
            }
        } catch (error) {
            console.error('Erreur:', error);
            showNotification('Erreur de connexion', 'error');
        }
    });

    // Form échec
    document.getElementById('echec-form').addEventListener('submit', async function(e) {
        e.preventDefault();

        const arretId = document.getElementById('echec-arret-id').value;
        const raisonEchec = document.getElementById('raison-echec').value;
        const commentaire = document.getElementById('echec-commentaire').value;

        try {
            const response = await fetch(`/API/arrets-livraison/${arretId}/marquer_echec/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    raison_echec: raisonEchec,
                    commentaire_echec: commentaire
                })
            });

            if (response.ok) {
                closeEchecModal();
                await loadArrets(currentTournee.id);
                showNotification('Échec enregistré', 'warning');
            } else {
                const error = await response.json();
                showNotification(error.error || 'Erreur lors de l\'enregistrement', 'error');
            }
        } catch (error) {
            console.error('Erreur:', error);
            showNotification('Erreur de connexion', 'error');
        }
    });
}

function updateProgress() {
    if (!currentTournee || allArrets.length === 0) return;

    const livres = allArrets.filter(a => a.statut === 'livre').length;
    const total = allArrets.length;
    const percentage = Math.round((livres / total) * 100);

    document.getElementById('progress-fill').style.width = percentage + '%';
}

function showActiveTournee() {
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    event.target.closest('.nav-btn').classList.add('active');
    loadLivreurData();
}

function showHistory() {
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    event.target.closest('.nav-btn').classList.add('active');
    // TODO: Implémenter l'historique des tournées terminées
    showEmptyState('Historique non disponible pour le moment');
}

function showEmptyState(message) {
    const container = document.getElementById('arrets-container');
    container.innerHTML = `
        <div class="empty-state">
            <i class="fas fa-inbox"></i>
            <p>${message}</p>
        </div>
    `;
    document.getElementById('tournee-info').style.display = 'none';
    document.getElementById('progress-bar').style.display = 'none';
}

function showNotification(message, type = 'info') {
    // Créer une notification toast simple
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#f59e0b'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
    `;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('fr-FR', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

function getStatusText(statut) {
    const statuts = {
        'planifiee': 'Planifiée',
        'en_cours': 'En cours',
        'terminee': 'Terminée',
        'annulee': 'Annulée'
    };
    return statuts[statut] || statut;
}

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
