// Dashboard de Distribution
let chartsInstances = {};

// Fonction d'initialisation
function initDistributionDashboard() {
    // Vérifier que les éléments nécessaires existent
    const dateToField = document.getElementById('date-to');
    const dateFromField = document.getElementById('date-from');

    if (!dateToField || !dateFromField) {
        console.log('[DISTRIBUTION] Page elements not found, skipping initialization');
        return;
    }

    console.log('[DISTRIBUTION] Initializing distribution dashboard');

    // Initialiser les dates par défaut
    const today = new Date();
    const thirtyDaysAgo = new Date(today.getTime() - (30 * 24 * 60 * 60 * 1000));

    dateToField.value = today.toISOString().split('T')[0];
    dateFromField.value = thirtyDaysAgo.toISOString().split('T')[0];

    loadDashboardData();
}

// NE PAS charger automatiquement au DOMContentLoaded car on utilise le chargement dynamique
// La page sera initialisée uniquement via fragment:loaded

// Charger lors du chargement dynamique
document.addEventListener('fragment:loaded', function(e) {
    if (e.detail && e.detail.name === 'distribution_dashboard') {
        console.log('[DISTRIBUTION] fragment:loaded event for distribution_dashboard');
        initDistributionDashboard();
    }
});

function loadDashboardData() {
    const period = document.getElementById('period-filter').value;
    const dateFrom = document.getElementById('date-from').value;
    const dateTo = document.getElementById('date-to').value;

    console.log('[DISTRIBUTION] Loading dashboard data from API endpoints...');

    // Charger toutes les données depuis les endpoints de distribution
    Promise.all([
        fetch('/API/distribution/tournees/', { credentials: 'same-origin' }).then(r => {
            if (!r.ok) throw new Error('Erreur tournees: ' + r.status);
            return r.json();
        }),
        fetch('/API/distribution/arrets/', { credentials: 'same-origin' }).then(r => {
            if (!r.ok) throw new Error('Erreur arrets: ' + r.status);
            return r.json();
        }),
        fetch('/API/distribution/livreurs/', { credentials: 'same-origin' }).then(r => {
            if (!r.ok) throw new Error('Erreur livreurs: ' + r.status);
            return r.json();
        })
    ])
        .then(([tournees, arrets, livreurs]) => {
        console.log('[DISTRIBUTION] Data loaded:', {
            tournees: tournees.length,
            arrets: arrets.length,
            livreurs: livreurs.length
        });
        
        // Filtrer par période
        const filteredTournees = filterByPeriod(tournees, period, dateFrom, dateTo);
        const filteredArrets = arrets.filter(a => {
            return filteredTournees.some(t => t.id === (a.tournee || a.tournee_id));
        });

        console.log('[DISTRIBUTION] Filtered data:', {
            tournees: filteredTournees.length,
            arrets: filteredArrets.length
        });

        updateMainStats(filteredTournees, filteredArrets);
        createTourneesChart(filteredTournees);
        createLivraisonsChart(filteredArrets);
        createLivreursChart(filteredTournees, livreurs);
        displayTopPerformers(livreurs, filteredTournees);
    })
    .catch(error => {
        console.error('[DISTRIBUTION] Error loading data:', error);
        // Afficher un message d'erreur à l'utilisateur
        document.getElementById('total-tournees').textContent = 'Erreur';
        document.getElementById('top-performers').innerHTML = `
            <div style="text-align: center; padding: 20px; color: #ef4444;">
                <i class="fas fa-exclamation-triangle"></i> 
                <p>Erreur lors du chargement des données</p>
                <small>${error.message}</small>
            </div>
        `;
    });
}

function filterByPeriod(tournees, period, dateFrom, dateTo) {
    if (dateFrom && dateTo) {
        return tournees.filter(t => t.date_tournee >= dateFrom && t.date_tournee <= dateTo);
    }

    const days = parseInt(period);
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - days);
    const cutoff = cutoffDate.toISOString().split('T')[0];

    return tournees.filter(t => t.date_tournee >= cutoff);
}

function updateMainStats(tournees, arrets) {
    // Total tournées
    document.getElementById('total-tournees').textContent = tournees.length;

    // Total livraisons
    const totalLivraisons = arrets.length;
    document.getElementById('total-livraisons').textContent = totalLivraisons;

    // Taux de réussite
    const livraisons_reussies = arrets.filter(a => a.statut === 'livre').length;
    const tauxReussite = totalLivraisons > 0 ? Math.round((livraisons_reussies / totalLivraisons) * 100) : 0;
    document.getElementById('taux-reussite').textContent = tauxReussite + '%';

    // Distance totale
    const distanceTotale = tournees.reduce((sum, t) => sum + (parseFloat(t.distance_km) || 0), 0);
    document.getElementById('distance-totale').textContent = Math.round(distanceTotale);
}

function createTourneesChart(tournees) {
    // Grouper par date
    const groupedByDate = {};
    tournees.forEach(t => {
        const date = new Date(t.date_tournee).toLocaleDateString('fr-FR');
        groupedByDate[date] = (groupedByDate[date] || 0) + 1;
    });

    const labels = Object.keys(groupedByDate).sort();
    const data = labels.map(label => groupedByDate[label]);

    const ctx = document.getElementById('tournees-chart');
    if (chartsInstances.tournees) {
        chartsInstances.tournees.destroy();
    }

    chartsInstances.tournees = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Nombre de tournées',
                data: data,
                borderColor: '#8b5cf6',
                backgroundColor: 'rgba(139, 92, 246, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

function createLivraisonsChart(arrets) {
    // Compter par statut
    const statutsMap = {
        'en_attente': 'En attente',
        'livre': 'Livré',
        'echec': 'Échec',
        'reporte': 'Reporté'
    };
    
    const statuts = {};
    arrets.forEach(a => {
        const label = statutsMap[a.statut] || a.statut;
        statuts[label] = (statuts[label] || 0) + 1;
    });

    const ctx = document.getElementById('livraisons-chart');
    if (chartsInstances.livraisons) {
        chartsInstances.livraisons.destroy();
    }

    chartsInstances.livraisons = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(statuts),
            datasets: [{
                data: Object.values(statuts),
                backgroundColor: [
                    '#10b981',  // Livré
                    '#f59e0b',  // En cours
                    '#ef4444',  // Échec
                    '#6b7280',  // En attente
                    '#3b82f6'   // Reporté
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

function createLivreursChart(tournees, livreurs) {
    // Compter les tournées par livreur
    const livreurStats = {};

    tournees.forEach(t => {
        if (t.livreur_nom) {
            if (!livreurStats[t.livreur_nom]) {
                livreurStats[t.livreur_nom] = {
                    total: 0,
                    terminees: 0
                };
            }
            livreurStats[t.livreur_nom].total++;
            if (t.statut === 'terminee') {
                livreurStats[t.livreur_nom].terminees++;
            }
        }
    });

    const labels = Object.keys(livreurStats);
    const data = labels.map(label => livreurStats[label].total);

    const ctx = document.getElementById('livreurs-chart');
    if (chartsInstances.livreurs) {
        chartsInstances.livreurs.destroy();
    }

    chartsInstances.livreurs = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Nombre de tournées',
                data: data,
                backgroundColor: '#8b5cf6',
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

function displayTopPerformers(livreurs, tournees) {
    // Calculer les performances
    const performances = livreurs.map(livreur => {
        const tourneesLivreur = tournees.filter(t => t.livreur === livreur.id);
        const terminees = tourneesLivreur.filter(t => t.est_cloturee || t.statut === 'terminee');

        let totalArrets = 0;
        let totalLivres = 0;
        terminees.forEach(t => {
            // Utiliser les statistiques si disponibles
            if (t.statistiques) {
                totalArrets += t.statistiques.total_arrets || 0;
                totalLivres += t.statistiques.arrets_livres || 0;
            } else {
                // Fallback sur les anciens champs
                totalArrets += t.nombre_arrets || 0;
                totalLivres += t.arrets_livres || 0;
            }
        });

        const tauxReussite = totalArrets > 0 ? Math.round((totalLivres / totalArrets) * 100) : 0;

        return {
            ...livreur,
            nb_tournees: tourneesLivreur.length,
            taux_reussite: tauxReussite,
            total_livraisons: totalLivres
        };
    });

    // Trier par taux de réussite et nombre de tournées
    performances.sort((a, b) => {
        if (b.taux_reussite !== a.taux_reussite) {
            return b.taux_reussite - a.taux_reussite;
        }
        return b.nb_tournees - a.nb_tournees;
    });

    // Afficher le top 5
    const top5 = performances.slice(0, 5).filter(p => p.nb_tournees > 0);

    const container = document.getElementById('top-performers');

    if (top5.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 20px; color: #9ca3af;">
                Aucune donnée disponible pour cette période
            </div>
        `;
        return;
    }

    container.innerHTML = top5.map((perf, index) => {
        const initials = ((perf.nom || "?")[0] + (perf.prenom || perf.nom || "?")[0]).toUpperCase();
        const badgeClass = perf.taux_reussite >= 90 ? 'badge-success' :
                          perf.taux_reussite >= 70 ? 'badge-warning' : 'badge-danger';

        return `
            <div class="performance-item">
                <div class="livreur-info">
                    <div class="livreur-avatar">${initials}</div>
                    <div class="livreur-details">
                        <h4>${perf.full_name}</h4>
                        <p>${perf.nb_tournees} tournées - ${perf.total_livraisons} livraisons</p>
                    </div>
                </div>
                <div class="performance-stats">
                    <div class="value">${perf.taux_reussite}%</div>
                    <div class="label">
                        <span class="badge ${badgeClass}">Taux de réussite</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}
