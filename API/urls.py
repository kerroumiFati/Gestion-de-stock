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
    ArretTourneeViewSet as ArretTourneeDistributionViewSet,
    LivraisonConfirmerView, LivraisonEchecView
)

# Try to import with error handling
try:
    from .views_import import ImportPreviewView, ImportExecuteView, ImportTemplateView, ExportProductsView
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
    class ExportProductsView(APIView):
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
                      'categorie', 'fournisseur', 'quantite', 'seuil_alerte', 'seuil_critique', 'unite_mesure']
            filename = 'template_produits'
            example_data = [
                {
                    'reference': 'PROD-001',
                    'code_barre': '6111234567890',
                    'designation': 'Coca-Cola 1.5L',
                    'description': 'Boisson gazeuse Coca-Cola bouteille 1.5 litres',
                    'prixU': '150',
                    'categorie': 'Boissons',
                    'fournisseur': 'Coca-Cola Company',
                    'quantite': '500',
                    'seuil_alerte': '50',
                    'seuil_critique': '20',
                    'unite_mesure': 'bouteille'
                },
                {
                    'reference': 'PROD-002',
                    'code_barre': '6111234567891',
                    'designation': 'Pepsi 2L',
                    'description': 'Boisson gazeuse Pepsi bouteille 2 litres',
                    'prixU': '180',
                    'categorie': 'Boissons',
                    'fournisseur': 'PepsiCo',
                    'quantite': '300',
                    'seuil_alerte': '30',
                    'seuil_critique': '15',
                    'unite_mesure': 'bouteille'
                },
                {
                    'reference': 'PROD-003',
                    'code_barre': '6111234567892',
                    'designation': 'Eau Ifri 1.5L',
                    'description': 'Eau minérale naturelle Ifri',
                    'prixU': '50',
                    'categorie': 'Boissons',
                    'fournisseur': 'Ifri',
                    'quantite': '1000',
                    'seuil_alerte': '100',
                    'seuil_critique': '50',
                    'unite_mesure': 'bouteille'
                },
                {
                    'reference': 'PROD-004',
                    'code_barre': '6111234567893',
                    'designation': 'Chips Bingo 100g',
                    'description': 'Chips nature sachet 100g',
                    'prixU': '80',
                    'categorie': 'Snacks',
                    'fournisseur': 'Bingo',
                    'quantite': '200',
                    'seuil_alerte': '20',
                    'seuil_critique': '10',
                    'unite_mesure': 'sachet'
                },
                {
                    'reference': 'PROD-005',
                    'code_barre': '6111234567894',
                    'designation': 'Biscuit Bimo 200g',
                    'description': 'Biscuits au chocolat paquet 200g',
                    'prixU': '120',
                    'categorie': 'Biscuits',
                    'fournisseur': 'Bimo',
                    'quantite': '150',
                    'seuil_alerte': '15',
                    'seuil_critique': '8',
                    'unite_mesure': 'paquet'
                }
            ]
        elif import_type == 'categories':
            columns = ['nom', 'parent', 'description', 'couleur', 'icone']
            filename = 'template_categories'
            example_data = [
                {
                    'nom': 'Boissons',
                    'parent': '',
                    'description': 'Toutes les boissons (eau, jus, sodas)',
                    'couleur': '#3B82F6',
                    'icone': 'fas fa-glass-water'
                },
                {
                    'nom': 'Sodas',
                    'parent': 'Boissons',
                    'description': 'Boissons gazeuses sucrées',
                    'couleur': '#EF4444',
                    'icone': 'fas fa-bottle-water'
                },
                {
                    'nom': 'Eaux',
                    'parent': 'Boissons',
                    'description': 'Eaux minérales et de source',
                    'couleur': '#06B6D4',
                    'icone': 'fas fa-droplet'
                },
                {
                    'nom': 'Snacks',
                    'parent': '',
                    'description': 'Chips, cacahuètes et autres snacks',
                    'couleur': '#F59E0B',
                    'icone': 'fas fa-cookie'
                },
                {
                    'nom': 'Biscuits',
                    'parent': '',
                    'description': 'Biscuits sucrés et salés',
                    'couleur': '#8B5CF6',
                    'icone': 'fas fa-cookie-bite'
                }
            ]

        elif import_type == 'fournisseurs':
            columns = ['libelle', 'telephone', 'email', 'adresse', 'nif', 'nis', 'ai', 'rc']
            filename = 'template_fournisseurs'
            example_data = [
                {
                    'libelle': 'Coca-Cola Company',
                    'telephone': '021123456',
                    'email': 'contact@coca-cola.dz',
                    'adresse': 'Zone Industrielle, Alger',
                    'nif': '001234567890123',
                    'nis': '001234567890123',
                    'ai': '12345678901',
                    'rc': '16/00-0123456B19'
                },
                {
                    'libelle': 'Ifri',
                    'telephone': '034567890',
                    'email': 'contact@ifri.dz',
                    'adresse': 'Ighzer Amokrane, Bejaia',
                    'nif': '002345678901234',
                    'nis': '002345678901234',
                    'ai': '23456789012',
                    'rc': '06/00-0234567B06'
                },
                {
                    'libelle': 'Bimo',
                    'telephone': '025678901',
                    'email': 'contact@bimo.dz',
                    'adresse': 'Zone Industrielle, Blida',
                    'nif': '003456789012345',
                    'nis': '003456789012345',
                    'ai': '34567890123',
                    'rc': '09/00-0345678B09'
                }
            ]

        elif import_type == 'clients':
            columns = ['nom', 'prenom', 'telephone', 'email', 'adresse', 'lat', 'lng', 'secteur', 'nif', 'nis', 'ai', 'rc']
            filename = 'template_clients'
            example_data = [
                {
                    'nom': 'Superette El Baraka',
                    'prenom': '',
                    'telephone': '0555123456',
                    'email': 'elbaraka@email.com',
                    'adresse': '15 Rue Didouche Mourad, Alger',
                    'lat': '36.7538',
                    'lng': '3.0588',
                    'secteur': 'Centre',
                    'nif': '111234567890123',
                    'nis': '111234567890123',
                    'ai': '11123456789',
                    'rc': '16/00-1112345B16'
                },
                {
                    'nom': 'Mini Market Essalam',
                    'prenom': '',
                    'telephone': '0555234567',
                    'email': 'essalam@email.com',
                    'adresse': '23 Boulevard Amirouche, Bejaia',
                    'lat': '36.7509',
                    'lng': '5.0567',
                    'secteur': 'Est',
                    'nif': '222345678901234',
                    'nis': '222345678901234',
                    'ai': '22234567890',
                    'rc': '06/00-2223456B06'
                },
                {
                    'nom': 'Alimentation Rahma',
                    'prenom': '',
                    'telephone': '0555345678',
                    'email': 'rahma@email.com',
                    'adresse': '8 Avenue de l\'ALN, Oran',
                    'lat': '35.6969',
                    'lng': '-0.6331',
                    'secteur': 'Ouest',
                    'nif': '333456789012345',
                    'nis': '333456789012345',
                    'ai': '33345678901',
                    'rc': '31/00-3334567B31'
                }
            ]

        elif import_type == 'pricelists':
            columns = ['code_article', 'reference', 'code_prix', 'type_prix', 'prix']
            filename = 'template_liste_prix'
            example_data = [
                {
                    'code_article': '6111234567890',
                    'reference': 'PROD-001',
                    'code_prix': 'STANDARD',
                    'type_prix': 'DETAIL',
                    'prix': '150'
                },
                {
                    'code_article': '6111234567890',
                    'reference': 'PROD-001',
                    'code_prix': 'STANDARD',
                    'type_prix': 'GROS',
                    'prix': '130'
                },
                {
                    'code_article': '6111234567891',
                    'reference': 'PROD-002',
                    'code_prix': 'AID',
                    'type_prix': 'DETAIL',
                    'prix': '165'
                },
                {
                    'code_article': '6111234567891',
                    'reference': 'PROD-002',
                    'code_prix': 'AID',
                    'type_prix': 'GROS',
                    'prix': '145'
                },
                {
                    'code_article': '6111234567892',
                    'reference': 'PROD-003',
                    'code_prix': 'RAMADAN',
                    'type_prix': 'DETAIL',
                    'prix': '55'
                },
                {
                    'code_article': '6111234567892',
                    'reference': 'PROD-003',
                    'code_prix': 'RAMADAN',
                    'type_prix': 'SUPERETTE',
                    'prix': '50'
                }
            ]

        else:
            return JsonResponse({'error': 'Type non supporté: ' + import_type}, status=400)

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
router.register(r'stock-moves', views.StockMoveViewSet, basename='stock-moves')  # Alias anglais
router.register(r'entrepots', views.WarehouseViewSet)
router.register(r'warehouses', views.WarehouseViewSet, basename='warehouses')  # Alias anglais
router.register(r'stocks', views.ProductStockViewSet)
router.register(r'inventaires', views.InventorySessionViewSet)
router.register(r'ventes', views.VenteViewSet)
router.register(r'lignes-vente', views.LigneVenteViewSet)
router.register(r'paiements-vente', views.PaiementVenteViewSet)
router.register(r'currencies', views.CurrencyViewSet)
router.register(r'exchange-rates', views.ExchangeRateViewSet)
router.register(r'codes-prix', views.CodePrixViewSet)
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
router.register(r'visites-clients', views.VisiteClientViewSet, basename='visites-clients')

# Module Promotions et Conditionnement
router.register(r'conditionnements', views.ConditionnementViewSet, basename='conditionnements')
router.register(r'promotions', views.PromotionViewSet, basename='promotions')
router.register(r'promotions-usage', views.PromotionUsageViewSet, basename='promotions-usage')

# Module Secteurs
router.register(r'secteurs', views.SecteurViewSet, basename='secteurs')

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
    path('import/export-products/', ExportProductsView.as_view(), name='export-products'),  # Export liste des produits

    # Module de distribution mobile (nouveau système complet)
    path('distribution/', include('API.distribution_urls')),

    # Endpoints de livraison compat mobile
    path('livraisons/confirmer/', LivraisonConfirmerView.as_view(), name='livraison-confirmer'),
    path('livraisons/echec/', LivraisonEchecView.as_view(), name='livraison-echec'),

    path('', include(router.urls)),
    path('categories_raw/', views.categories_raw),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('system-config/', views.SystemConfigView.as_view(), name='system-config'),
    path('my-permissions/', views.my_permissions, name='my-permissions'),
    #path('clients/<int:pk>/', views.ClientDetail.as_view())
    re_path(r'^prod/count/$', views.CountViewSet.as_view(), name='produits-count'),
    re_path(r'^statistics/charts/$', views.StatisticsChartsViewSet.as_view(), name='statistics-charts'),
    re_path(r'^risk/$', views.RiskViewSet.as_view(), name='risk'),
    re_path(r'^alerts/$', views.AlertsView.as_view(), name='alerts'),
    re_path(r'^welcome/$', views.WelcomeView.as_view(), name='welcome'),
    ]
