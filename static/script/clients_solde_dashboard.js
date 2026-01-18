console.log('[CLIENTS SOLDE DASHBOARD] JavaScript loaded');

// Global variables for charts
let evolutionChart = null;
let modesChart = null;
let dashboardInitialized = false;

// API endpoint
const API_ENDPOINT = '/API/clients/dashboard_stats/';

// Initialize dashboard
function initDashboard() {
    if (dashboardInitialized) {
        console.log('[CLIENTS SOLDE DASHBOARD] Dashboard already initialized, skipping');
        return;
    }

    console.log('[CLIENTS SOLDE DASHBOARD] Initializing dashboard');
    dashboardInitialized = true;
    loadDashboardData();

    // Attach refresh button handler
    const refreshBtn = document.getElementById('refresh-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            loadDashboardData();
        });
    }
}

// Load dashboard data from API
function loadDashboardData() {
    console.log('[CLIENTS SOLDE DASHBOARD] Loading data from API');
    showLoading();

    fetch(API_ENDPOINT, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        console.log('[CLIENTS SOLDE DASHBOARD] Data received:', data);
        console.log('[CLIENTS SOLDE DASHBOARD] Stats globales:', data.stats_globales);
        console.log('[CLIENTS SOLDE DASHBOARD] Top dettes:', data.top_dettes);
        console.log('[CLIENTS SOLDE DASHBOARD] Top credits:', data.top_credits);
        console.log('[CLIENTS SOLDE DASHBOARD] Paiements recents:', data.paiements_recents);
        console.log('[CLIENTS SOLDE DASHBOARD] Evolution paiements:', data.evolution_paiements);
        console.log('[CLIENTS SOLDE DASHBOARD] Modes paiement:', data.modes_paiement);

        updateStatistics(data.stats_globales);
        updateTopDettes(data.top_dettes);
        updateTopCredits(data.top_credits);
        updatePaiementsRecents(data.paiements_recents);
        updateEvolutionChart(data.evolution_paiements);
        updateModesChart(data.modes_paiement);
        hideLoading();
    })
    .catch(error => {
        console.error('[CLIENTS SOLDE DASHBOARD] Error loading data:', error);
        hideLoading();
        alert('Erreur lors du chargement des données du dashboard');
    });
}

// Update statistics cards
function updateStatistics(stats) {
    document.getElementById('stat-total-clients').textContent = stats.total_clients || 0;

    const totalCredits = parseFloat(stats.total_credits || 0);
    document.getElementById('stat-total-credits').textContent = formatCurrency(totalCredits);

    const totalDettes = parseFloat(stats.total_dettes || 0);
    document.getElementById('stat-total-dettes').textContent = formatCurrency(Math.abs(totalDettes));

    const soldeGlobal = parseFloat(stats.solde_global || 0);
    const soldeElement = document.getElementById('stat-solde-global');
    soldeElement.textContent = formatCurrency(soldeGlobal);
    soldeElement.className = 'stat-value ' + (soldeGlobal >= 0 ? 'text-success' : 'text-danger');

    document.getElementById('stat-ventes-credit').textContent = stats.ventes_credit || 0;

    const totalResteAPayer = parseFloat(stats.total_reste_a_payer || 0);
    document.getElementById('stat-reste-a-payer').textContent = formatCurrency(totalResteAPayer);
}

// Update top dettes table
function updateTopDettes(dettes) {
    console.log('[CLIENTS SOLDE DASHBOARD] Updating top dettes, count:', dettes ? dettes.length : 0);
    const tbody = document.getElementById('top-dettes-body');
    if (!tbody) {
        console.error('[CLIENTS SOLDE DASHBOARD] top-dettes-body element not found');
        return;
    }
    tbody.innerHTML = '';

    if (!dettes || dettes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="empty-state"><i class="fas fa-check-circle"></i><div>Aucune dette en cours</div></td></tr>';
        return;
    }

    dettes.forEach(client => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${client.nom} ${client.prenom}</strong></td>
            <td>${client.telephone || '-'}</td>
            <td class="text-danger"><strong>${formatCurrency(Math.abs(parseFloat(client.solde)))}</strong></td>
        `;
        tbody.appendChild(tr);
    });
}

// Update top credits table
function updateTopCredits(credits) {
    console.log('[CLIENTS SOLDE DASHBOARD] Updating top credits, count:', credits ? credits.length : 0);
    const tbody = document.getElementById('top-credits-body');
    if (!tbody) {
        console.error('[CLIENTS SOLDE DASHBOARD] top-credits-body element not found');
        return;
    }
    tbody.innerHTML = '';

    if (!credits || credits.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="empty-state"><i class="fas fa-info-circle"></i><div>Aucun crédit accordé</div></td></tr>';
        return;
    }

    credits.forEach(client => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${client.nom} ${client.prenom}</strong></td>
            <td>${client.telephone || '-'}</td>
            <td class="text-success"><strong>${formatCurrency(parseFloat(client.solde))}</strong></td>
        `;
        tbody.appendChild(tr);
    });
}

// Update paiements recents table
function updatePaiementsRecents(paiements) {
    console.log('[CLIENTS SOLDE DASHBOARD] Updating paiements recents, count:', paiements ? paiements.length : 0);
    const tbody = document.getElementById('paiements-recents-body');
    if (!tbody) {
        console.error('[CLIENTS SOLDE DASHBOARD] paiements-recents-body element not found');
        return;
    }
    tbody.innerHTML = '';

    if (!paiements || paiements.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty-state"><i class="fas fa-inbox"></i><div>Aucun paiement récent</div></td></tr>';
        return;
    }

    paiements.forEach(paiement => {
        const date = new Date(paiement.date_paiement);
        const dateStr = date.toLocaleDateString('fr-FR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });

        const soldeApres = parseFloat(paiement.solde_apres);
        const soldeClass = soldeApres >= 0 ? 'text-success' : 'text-danger';

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${dateStr}</td>
            <td><strong>${paiement.client_nom}</strong></td>
            <td class="text-success"><strong>+${formatCurrency(parseFloat(paiement.montant))}</strong></td>
            <td><span class="badge badge-info">${paiement.mode_paiement}</span></td>
            <td class="${soldeClass}"><strong>${soldeApres >= 0 ? '+' : ''}${formatCurrency(soldeApres)}</strong></td>
        `;
        tbody.appendChild(tr);
    });
}

// Update evolution chart
function updateEvolutionChart(data) {
    const ctx = document.getElementById('evolution-chart').getContext('2d');

    // Destroy existing chart if any
    if (evolutionChart) {
        evolutionChart.destroy();
    }

    const labels = data.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' });
    });

    const values = data.map(d => parseFloat(d.montant));

    evolutionChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Montant des paiements (DA)',
                data: values,
                borderColor: '#8b5cf6',
                backgroundColor: 'rgba(139, 92, 246, 0.1)',
                tension: 0.4,
                fill: true,
                pointRadius: 5,
                pointHoverRadius: 7,
                pointBackgroundColor: '#8b5cf6',
                pointBorderColor: '#fff',
                pointBorderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return 'Paiements: ' + formatCurrency(context.parsed.y);
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return formatCurrency(value);
                        }
                    }
                }
            }
        }
    });
}

// Update modes de paiement chart
function updateModesChart(data) {
    const ctx = document.getElementById('modes-chart').getContext('2d');

    // Destroy existing chart if any
    if (modesChart) {
        modesChart.destroy();
    }

    if (data.length === 0) {
        ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
        ctx.font = '16px Arial';
        ctx.fillStyle = '#6b7280';
        ctx.textAlign = 'center';
        ctx.fillText('Aucun paiement récent', ctx.canvas.width / 2, ctx.canvas.height / 2);
        return;
    }

    const labels = data.map(d => d.mode_display);
    const values = data.map(d => parseFloat(d.total));

    const colors = [
        'rgba(139, 92, 246, 0.8)',
        'rgba(16, 185, 129, 0.8)',
        'rgba(59, 130, 246, 0.8)',
        'rgba(245, 158, 11, 0.8)',
        'rgba(239, 68, 68, 0.8)'
    ];

    modesChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderColor: '#fff',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return label + ': ' + formatCurrency(value) + ' (' + percentage + '%)';
                        }
                    }
                }
            }
        }
    });
}

// Format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('fr-DZ', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount) + ' DA';
}

// Show loading overlay
function showLoading() {
    document.getElementById('loading-overlay').style.display = 'flex';
}

// Hide loading overlay
function hideLoading() {
    document.getElementById('loading-overlay').style.display = 'none';
}

// Get CSRF token from cookies
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

// Listen for fragment:loaded event
document.addEventListener('fragment:loaded', function(e) {
    if (e.detail && e.detail.name === 'clients_solde_dashboard') {
        console.log('[CLIENTS SOLDE DASHBOARD] Fragment loaded event received, initializing');
        initDashboard();
    }
});

// Also initialize if the page is already loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        console.log('[CLIENTS SOLDE DASHBOARD] DOMContentLoaded, checking if we should initialize');
        const mainContent = document.getElementById('main-content');
        if (mainContent && mainContent.querySelector('.page-title')) {
            const titleText = mainContent.querySelector('.page-title span');
            if (titleText && titleText.textContent.includes('Dashboard Soldes Clients')) {
                initDashboard();
            }
        }
    });
} else {
    console.log('[CLIENTS SOLDE DASHBOARD] Document already loaded, checking if we should initialize');
    const mainContent = document.getElementById('main-content');
    if (mainContent && mainContent.querySelector('.page-title')) {
        const titleText = mainContent.querySelector('.page-title span');
        if (titleText && titleText.textContent.includes('Dashboard Soldes Clients')) {
            initDashboard();
        }
    }
}
