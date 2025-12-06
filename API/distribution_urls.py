"""
URLs pour l'API de distribution mobile
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .distribution_views import (
    LivreurViewSet, TourneeViewSet, ArretTourneeViewSet,
    VenteTourneeViewSet, RapportCaisseViewSet, CommandeClientViewSet, SyncViewSet,
    PlanningHebdomadaireViewSet, ClientLivreurHebdoViewSet,
    # BonLivraisonVanViewSet,  # TODO: Disabled - models not yet created
    ProduitMobileViewSet,
    StatsLivreursAPIView
)

router = DefaultRouter()
router.register(r'livreurs', LivreurViewSet, basename='livreur')
router.register(r'tournees', TourneeViewSet, basename='tournee')
router.register(r'arrets', ArretTourneeViewSet, basename='arret')
router.register(r'ventes', VenteTourneeViewSet, basename='vente')
router.register(r'commandes', CommandeClientViewSet, basename='commande')
router.register(r'rapports-caisse', RapportCaisseViewSet, basename='rapport-caisse')
router.register(r'plannings-hebdo', PlanningHebdomadaireViewSet, basename='planning-hebdo')
router.register(r'clients-livreurs-hebdo', ClientLivreurHebdoViewSet, basename='client-livreur-hebdo')
# router.register(r'bons-livraison', BonLivraisonVanViewSet, basename='bon-livraison')  # TODO: Disabled - models not yet created
router.register(r'produits', ProduitMobileViewSet, basename='produit-mobile')
router.register(r'sync', SyncViewSet, basename='sync')

urlpatterns = [
    path('', include(router.urls)),
    path('stats-livreurs/', StatsLivreursAPIView.as_view(), name='stats-livreurs'),
]
