// Main JavaScript for page navigation and content loading

// Show specific content section
function show(section) {
    const mainContent = document.getElementById('main-content');
    
    // Add loading state
    mainContent.innerHTML = '<div class="text-center py-5"><div class="spinner-border" role="status"><span class="sr-only">Loading...</span></div></div>';
    
    // Simulate loading different sections
    setTimeout(() => {
        switch(section) {
            case 'produit':
                loadProductSection();
                break;
            case 'client':
                loadClientSection();
                break;
            case 'fournisseur':
                loadSupplierSection();
                break;
            case 'achat':
                loadPurchaseSection();
                break;
            case 'vente':
                loadSalesSection();
                break;
            case 'categorie':
                loadCategorySection();
                break;
            case 'statistiques':
                loadStatsSection();
                break;
            case 'facture':
                loadInvoiceSection();
                break;
            case 'inventaire':
                loadInventorySection();
                break;
            case 'mouvements':
                loadMovementsSection();
                break;
            default:
                loadDashboard();
        }
    }, 500);
}

function loadProductSection() {
    document.getElementById('main-content').innerHTML = `
        <div class="page-header">
            <h1><i class="zmdi zmdi-shopping-cart"></i> Gestion des Produits</h1>
        </div>
        <div class="row">
            <div class="col-md-12">
                <div class="card">
                    <div class="card-header">
                        <h5>Liste des Produits</h5>
                    </div>
                    <div class="card-body">
                        <button class="btn btn-primary mb-3" onclick="showAddProductModal()">
                            <i class="zmdi zmdi-plus"></i> Ajouter un Produit
                        </button>
                        <div class="table-responsive">
                            <table class="table table-striped">
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>Nom</th>
                                        <th>Catégorie</th>
                                        <th>Prix</th>
                                        <th>Stock</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td>1</td>
                                        <td>Produit Example</td>
                                        <td>Électronique</td>
                                        <td>150.00 €</td>
                                        <td><span class="status-badge in-stock">25</span></td>
                                        <td>
                                            <div class="action-buttons">
                                                <button class="btn btn-sm btn-info">Voir</button>
                                                <button class="btn btn-sm btn-warning">Modifier</button>
                                                <button class="btn btn-sm btn-danger">Supprimer</button>
                                            </div>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function loadStatsSection() {
    document.getElementById('main-content').innerHTML = `
        <div class="page-header">
            <h1><i class="zmdi zmdi-chart"></i> Statistiques</h1>
        </div>
        <div class="stats-grid">
            <div class="stats-card">
                <div class="stats-icon"><i class="zmdi zmdi-shopping-cart"></i></div>
                <div class="stats-number">150</div>
                <div class="stats-label">Produits Total</div>
            </div>
            <div class="stats-card">
                <div class="stats-icon"><i class="zmdi zmdi-accounts"></i></div>
                <div class="stats-number">45</div>
                <div class="stats-label">Clients</div>
            </div>
            <div class="stats-card">
                <div class="stats-icon"><i class="zmdi zmdi-money"></i></div>
                <div class="stats-number">12,450€</div>
                <div class="stats-label">Ventes du Mois</div>
            </div>
            <div class="stats-card">
                <div class="stats-icon"><i class="zmdi zmdi-trending-up"></i></div>
                <div class="stats-number">+15%</div>
                <div class="stats-label">Croissance</div>
            </div>
        </div>
        <div class="row">
            <div class="col-md-12">
                <div class="card">
                    <div class="card-header">
                        <h5>Graphique des Ventes</h5>
                    </div>
                    <div class="card-body">
                        <canvas id="salesChart" width="400" height="200"></canvas>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function loadClientSection() {
    document.getElementById('main-content').innerHTML = `
        <div class="page-header">
            <h1><i class="zmdi zmdi-accounts"></i> Gestion des Clients</h1>
        </div>
        <div class="row">
            <div class="col-md-12">
                <div class="card">
                    <div class="card-header">
                        <h5>Liste des Clients</h5>
                    </div>
                    <div class="card-body">
                        <button class="btn btn-primary mb-3">
                            <i class="zmdi zmdi-plus"></i> Ajouter un Client
                        </button>
                        <div class="table-responsive">
                            <table class="table table-striped">
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>Nom</th>
                                        <th>Email</th>
                                        <th>Téléphone</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td colspan="5" class="text-center">Aucun client trouvé</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Load default sections for other menu items
function loadSupplierSection() {
    document.getElementById('main-content').innerHTML = `
        <div class="page-header">
            <h1><i class="zmdi zmdi-truck"></i> Gestion des Fournisseurs</h1>
        </div>
        <div class="alert alert-info">Section Fournisseurs en cours de développement...</div>
    `;
}

function loadPurchaseSection() {
    document.getElementById('main-content').innerHTML = `
        <div class="page-header">
            <h1><i class="zmdi zmdi-shopping-basket"></i> Gestion des Achats</h1>
        </div>
        <div class="alert alert-info">Section Achats en cours de développement...</div>
    `;
}

function loadSalesSection() {
    document.getElementById('main-content').innerHTML = `
        <div class="page-header">
            <h1><i class="zmdi zmdi-money"></i> Gestion des Ventes</h1>
        </div>
        <div class="alert alert-info">Section Ventes en cours de développement...</div>
    `;
}

function loadCategorySection() {
    document.getElementById('main-content').innerHTML = `
        <div class="page-header">
            <h1><i class="zmdi zmdi-view-list"></i> Gestion des Catégories</h1>
        </div>
        <div class="alert alert-info">Section Catégories en cours de développement...</div>
    `;
}

function loadInvoiceSection() {
    document.getElementById('main-content').innerHTML = `
        <div class="page-header">
            <h1><i class="zmdi zmdi-file-text"></i> Gestion des Factures</h1>
        </div>
        <div class="alert alert-info">Section Factures en cours de développement...</div>
    `;
}

function loadInventorySection() {
    document.getElementById('main-content').innerHTML = `
        <div class="page-header">
            <h1><i class="zmdi zmdi-check-circle"></i> Gestion de l'Inventaire</h1>
        </div>
        <div class="alert alert-info">Section Inventaire en cours de développement...</div>
    `;
}

function loadMovementsSection() {
    document.getElementById('main-content').innerHTML = `
        <div class="page-header">
            <h1><i class="zmdi zmdi-swap-vertical"></i> Mouvements de Stock</h1>
        </div>
        <div class="alert alert-info">Section Mouvements en cours de développement...</div>
    `;
}

function loadDashboard() {
    loadStatsSection(); // Default to stats dashboard
}

// Sidebar toggle functionality
document.addEventListener('DOMContentLoaded', function() {
    const showSidebarBtn = document.getElementById('show-sidebar');
    const closeSidebarBtn = document.getElementById('close-sidebar');
    const pageWrapper = document.querySelector('.page-wrapper');
    
    if (showSidebarBtn) {
        showSidebarBtn.addEventListener('click', function() {
            pageWrapper.classList.toggle('toggled');
        });
    }
    
    if (closeSidebarBtn) {
        closeSidebarBtn.addEventListener('click', function() {
            pageWrapper.classList.remove('toggled');
        });
    }
    
    // Load default dashboard
    loadDashboard();
});