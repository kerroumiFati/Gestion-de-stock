# API/urls.py
from django.urls import re_path
from django.urls import include, path
from rest_framework import routers
from django.http import JsonResponse, HttpResponse
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views
from .distribution_views import (
    LivreurViewSet as LivreurDistributionViewSet,
    TourneeViewSet as TourneeDistributionViewSet,
    ArretTourneeViewSet as ArretTourneeDistributionViewSet
)

# Try to import with error handling
try:
    from .views_import import ImportPreviewView, ImportExecuteView, ImportTemplateView
    IMPORT_VIEWS_LOADED = True
    IMPORT_ERROR = None
except Exception as e:
    IMPORT_VIEWS_LOADED = False
    IMPORT_ERROR = str(e)
    # Create dummy views
    from rest_framework.views import APIView
    from rest_framework.response import Response
    class ImportPreviewView(APIView):
        def post(self, request):
            return Response({'error': 'Import views failed to load', 'details': IMPORT_ERROR}, status=500)
    class ImportExecuteView(APIView):
        def post(self, request):
            return Response({'error': 'Import views failed to load', 'details': IMPORT_ERROR}, status=500)
    class ImportTemplateView(APIView):
        def get(self, request):
            return Response({'error': 'Import views failed to load', 'details': IMPORT_ERROR}, status=500)

# Test views
def test_import(request):
    return JsonResponse({
        'status': 'OK',
        'message': 'Import URLs are working',
        'views_loaded': IMPORT_VIEWS_LOADED,
        'import_error': IMPORT_ERROR
    })

def test_template_simple(request):
    """Test template generation without pandas"""
    from django.http import HttpResponse
    content = "reference,designation,prixU\nPROD-001,Test Product,99.99"
    response = HttpResponse(content, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="test.csv"'
    return response

def test_template_pandas(request):
    """Test template generation WITH pandas"""
    try:
        import pandas as pd
        import io
        df = pd.DataFrame([{'reference': 'PROD-001', 'designation': 'Test', 'prixU': '99.99'}])
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="test_pandas.csv"'
        return response
    except Exception as e:
        return JsonResponse({'error': str(e), 'type': str(type(e))}, status=500)

def download_template_view(request):
    """Vue fonction simple pour télécharger un template"""
    try:
        import pandas as pd
        import io

        import_type = request.GET.get('type', 'products')
        format_type = request.GET.get('format', 'csv')

        if import_type == 'products':
            columns = ['reference', 'code_barre', 'designation', 'description', 'prixU',
                      'categorie', 'fournisseur', 'quantite', 'stock_min', 'stock_max', 'unite_mesure']
            filename = 'template_produits'
            example_data = [{
                'reference': 'PROD-001',
                'code_barre': '1234567890123',
                'designation': 'Exemple Produit 1',
                'description': 'Description du produit',
                'prixU': '99.99',
                'categorie': 'Électronique',
                'fournisseur': 'Fournisseur A',
                'quantite': '100',
                'stock_min': '10',
                'stock_max': '500',
                'unite_mesure': 'unité'
            }]
        else:  # categories
            columns = ['nom', 'parent', 'description', 'couleur', 'icone']
            filename = 'template_categories'
            example_data = [{
                'nom': 'Électronique',
                'parent': '',
                'description': 'Produits électroniques',
                'couleur': '#3B82F6',
                'icone': 'fas fa-laptop'
            }]

        df = pd.DataFrame(example_data, columns=columns)

        if format_type == 'excel':
            output = io.BytesIO()
            try:
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Données')
                output.seek(0)
                response = HttpResponse(
                    output.read(),
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
            except:
                # Fallback to CSV
                format_type = 'csv'

        if format_type == 'csv':
            output = io.StringIO()
            df.to_csv(output, index=False, encoding='utf-8-sig')
            output.seek(0)
            response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8-sig')
            response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'

        return response

    except Exception as e:
        return JsonResponse({'error': str(e), 'details': str(type(e))}, status=500)

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
router.register(r'companies', views.CompanyViewSet)
router.register(r'user-profiles', views.UserProfileViewSet)
router.register(r'roles', views.GroupViewSet)
router.register(r'permissions', views.PermissionViewSet)
router.register(r'audit-logs', views.AuditLogViewSet)

# Module de distribution - nouveau système complet
router.register(r'livreurs', LivreurDistributionViewSet, basename='livreur-compat')
router.register(r'tournees', TourneeDistributionViewSet, basename='tournee-compat')
router.register(r'arrets-livraison', ArretTourneeDistributionViewSet, basename='arret-compat')

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    # JWT auth endpoints
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Exports de rapports (Excel & PDF) - DOIT ÊTRE AVANT le router
    path('reports/stock-valuation/', views.export_stock_valuation, name='export-stock-valuation'),
    path('reports/sales/', views.export_sales_report, name='export-sales-report'),
    path('reports/inventory/', views.export_inventory_report, name='export-inventory-report'),

    # Import de données - DOIT ÊTRE AVANT le router
    path('import/test/', test_import, name='import-test'),
    path('import/test-simple/', test_template_simple, name='test-simple'),
    path('import/test-pandas/', test_template_pandas, name='test-pandas'),
    path('import/preview/', ImportPreviewView.as_view(), name='import-preview'),
    path('import/execute/', ImportExecuteView.as_view(), name='import-execute'),
    path('import/template/', download_template_view, name='import-template'),  # Vue fonction au lieu de classe

    # Module de distribution mobile (nouveau système complet)
    path('distribution/', include('API.distribution_urls')),

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
