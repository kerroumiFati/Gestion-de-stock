// Application Mobile pour Livreurs
let currentTournee = null;
let allArrets = [];
let signaturePad = null;

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
        // Charger toutes les tournées et trouver celle du livreur connecté
        const response = await fetch('/API/tournees/');
        const tournees = await response.json();

        // Trouver la tournée active du livreur (statut = en_cours ou planifiee)
        // Note: Dans une vraie app, il faudrait authentifier le livreur
        // Pour l'instant, on prend la première tournée en cours ou planifiée
        currentTournee = tournees.find(t => t.statut === 'en_cours' || t.statut === 'planifiee');

        if (currentTournee) {
            displayTourneeInfo(currentTournee);
            await loadArrets(currentTournee.id);
        } else {
            showEmptyState('Aucune tournée assignée');
        }
    } catch (error) {
        console.error('Erreur chargement données:', error);
        showEmptyState('Erreur de chargement');
    }
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
