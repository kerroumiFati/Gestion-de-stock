# API/urls.py
from django.urls import re_path
from django.urls import include, path
from rest_framework import routers
from . import views
from .views_import import ImportPreviewView, ImportExecuteView, ImportTemplateView

router = routers.DefaultRouter()
router.register(r'categories', views.CategorieViewSet)
router.register(r'clients', views.ClientViewSet)
router.register(r'fournisseurs', views.FournisseurViewSet)
router.register(r'produits', views.ProduitViewSet)
router.register(r'achats', views.AchatViewSet)
router.register(r'bons', views.BonLivraisonViewSet)
router.register(r'factures', views.FactureViewSet)
router.register(r'mouvements', views.StockMoveViewSet)
router.register(r'entrepots', views.WarehouseViewSet)
router.register(r'stocks', views.ProductStockViewSet)
router.register(r'inventaires', views.InventorySessionViewSet)
router.register(r'ventes', views.VenteViewSet)
router.register(r'lignes-vente', views.LigneVenteViewSet)
router.register(r'currencies', views.CurrencyViewSet)
router.register(r'exchange-rates', views.ExchangeRateViewSet)
router.register(r'types-prix', views.TypePrixViewSet)
router.register(r'prix-produits', views.PrixProduitViewSet)
router.register(r'users', views.UserViewSet)
router.register(r'roles', views.GroupViewSet)
router.register(r'permissions', views.PermissionViewSet)
router.register(r'audit-logs', views.AuditLogViewSet)
# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    # Exports de rapports (Excel & PDF) - DOIT ÊTRE AVANT le router
    path('reports/stock-valuation/', views.export_stock_valuation, name='export-stock-valuation'),
    path('reports/sales/', views.export_sales_report, name='export-sales-report'),
    path('reports/inventory/', views.export_inventory_report, name='export-inventory-report'),

    # Import de données
    path('import/preview/', ImportPreviewView.as_view(), name='import-preview'),
    path('import/execute/', ImportExecuteView.as_view(), name='import-execute'),
    path('import/template/', ImportTemplateView.as_view(), name='import-template'),

    path('', include(router.urls)),
    path('categories_raw/', views.categories_raw),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('system-config/', views.SystemConfigView.as_view(), name='system-config'),
    #path('clients/<int:pk>/', views.ClientDetail.as_view())
    re_path(r'^prod/count/$', views.CountViewSet.as_view(), name='produits-count'),
    re_path(r'^statistics/charts/$', views.StatisticsChartsViewSet.as_view(), name='statistics-charts'),
    re_path(r'^risk/$', views.RiskViewSet.as_view(), name='risk'),
    re_path(r'^alerts/$', views.AlertsView.as_view(), name='alerts'),
    re_path(r'^welcome/$', views.WelcomeView.as_view(), name='welcome'),
    ]
