"""
Corbeille des produits : produits supprimés (désactivés) dans le logiciel.

La suppression d'un produit est logique (is_active=False). Cette API permet à
l'administrateur de :
  - lister les produits désactivés, avec leur stock restant et leurs documents ;
  - les réactiver ;
  - les supprimer définitivement (un par un ou en lot) avec toutes leurs données
    (stock, prix, conditionnement, promotions, photo). Les factures, BL, ventes et
    mouvements déjà enregistrés restent intacts : si le produit y figure, une fiche
    archivée invisible est conservée pour eux.

Routes (préfixe /API/) :
  GET    produits-supprimes/                 liste
  POST   produits-supprimes/<id>/restaurer/  réactivation
  DELETE produits-supprimes/<id>/            suppression définitive
  POST   produits-supprimes/supprimer-lot/   {"ids": [..]} suppression définitive en lot
"""
import logging

from django.db import transaction
from django.db.models import Q, Sum
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .audit import log_event
from .models import Produit

logger = logging.getLogger(__name__)

# Documents / historique qui référencent le produit : (accesseur inverse, libellé).
# S'il en existe, la suppression définitive garde une fiche archivée (invisible)
# pour que ces documents restent lisibles ; sinon le produit est effacé entièrement.
_HISTORIQUE = (
    ('lignevente', 'ligne(s) de vente'),
    ('lignes_ventes_tournees', 'vente(s) de tournée mobile'),
    ('lignecommandeclient', 'ligne(s) de commande client'),
    ('lignefacture', 'ligne(s) de facture'),
    ('lignelivraison', 'ligne(s) de bon de livraison'),
    ('achat', 'achat(s)'),
    ('mouvements', 'mouvement(s) de stock'),
    ('inventoryline', "ligne(s) d'inventaire"),
    ('lignetransfertstock', 'ligne(s) de transfert'),
)


def _related_count(produit, accessor):
    """Nombre d'objets liés via l'accesseur inverse (0 si l'accesseur n'existe pas)."""
    manager = getattr(produit, accessor, None)
    if manager is None:
        manager = getattr(produit, f'{accessor}_set', None)
    if manager is None:
        return 0
    return manager.count()


def analyser_produit(produit):
    """Retourne (historique, stocks) d'un produit désactivé.

    historique : documents qui resteront visibles après la suppression définitive
    stocks     : quantités encore enregistrées par entrepôt / van (seront effacées)
    """
    historique = []
    for accessor, libelle in _HISTORIQUE:
        n = _related_count(produit, accessor)
        if n:
            historique.append({'type': accessor, 'nombre': n, 'libelle': f'{n} {libelle}'})

    stocks = [
        {'entrepot': s.warehouse.name if s.warehouse else '?', 'quantite': s.quantity}
        for s in produit.stocks.select_related('warehouse').exclude(quantity=0)
    ]
    return historique, stocks


def _base_queryset(request):
    """Produits désactivés (pas encore supprimés définitivement) visibles par l'utilisateur."""
    qs = Produit.objects.filter(is_active=False, est_archive=False).select_related('categorie')
    company = getattr(request, 'company', None)
    if company is not None:
        return qs.filter(Q(company=company) | Q(company__isnull=True))
    if request.user.is_superuser:
        return qs
    return qs.filter(company__isnull=True)


def _supprimer(request, produit):
    """Supprime définitivement un produit désactivé. Retourne (ok, message).

    - Sans historique : le produit et toutes ses données sont effacés.
    - Avec historique : stock, prix, conditionnement, promotions et photo sont
      effacés ; une fiche archivée (invisible) est gardée pour les documents.
    """
    historique, stocks = analyser_produit(produit)
    stock_total = sum(s['quantite'] for s in stocks)
    pid, ref, designation = produit.id, produit.reference, produit.designation
    image = produit.image if produit.image else None

    try:
        with transaction.atomic():
            if historique:
                produit.stocks.all().delete()
                produit.prix_multiples.all().delete()
                produit.conditionnements.all().delete()
                produit.promotions.all().delete()  # promotions propres à ce produit
                produit.image = None
                produit.quantite = 0
                produit.est_archive = True
                produit.archive_le = timezone.now()
                produit.save()
                mode = 'archive'
            else:
                # Supprime aussi prix, stocks, conditionnements et promotions (cascade)
                produit.delete()
                mode = 'complet'
    except ProtectedError:
        return False, 'Impossible : le produit est encore utilisé dans des documents.'

    if image:
        try:
            image.delete(save=False)
        except Exception:  # fichier déjà absent : sans importance
            logger.warning('Image du produit %s introuvable lors de la suppression', pid)

    metadata = {'id': pid, 'reference': ref, 'designation': designation,
                'stock_supprime': stock_total}
    if stocks:
        metadata['detail_stock'] = ', '.join(f"{s['entrepot']} : {s['quantite']}" for s in stocks)
    if historique:
        metadata['documents_conserves'] = ', '.join(h['libelle'] for h in historique)
    try:
        log_event(request, 'produit.purge', target=None, metadata=metadata)
    except Exception:
        pass

    if mode == 'archive':
        return True, 'Supprimé définitivement (conservé uniquement dans les documents)'
    return True, 'Supprimé définitivement'


class ProduitsSupprimesListView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        data = []
        for p in _base_queryset(request).order_by('-updated_at'):
            historique, stocks = analyser_produit(p)
            data.append({
                'id': p.id,
                'reference': p.reference,
                'code_barre': p.code_barre,
                'designation': p.designation,
                'categorie': p.categorie.nom if p.categorie else None,
                'prixU': str(p.prixU),
                'image': p.image.url if p.image else None,
                'date_desactivation': p.updated_at,
                'historique': historique,
                'stocks': stocks,
                'stock_restant': sum(s['quantite'] for s in stocks),
                'avec_historique': bool(historique),
            })
        return Response({
            'count': len(data),
            'sans_historique': sum(1 for d in data if not d['avec_historique']),
            'avec_historique': sum(1 for d in data if d['avec_historique']),
            'results': data,
        })


class ProduitSupprimeDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def _get(self, request, pk):
        return _base_queryset(request).filter(pk=pk).first()

    def delete(self, request, pk):
        produit = self._get(request, pk)
        if produit is None:
            return Response({'error': 'Produit désactivé introuvable'}, status=status.HTTP_404_NOT_FOUND)
        ok, message = _supprimer(request, produit)
        if not ok:
            return Response({'error': message}, status=status.HTTP_409_CONFLICT)
        return Response({'message': message})


class ProduitSupprimeRestaurerView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, pk):
        produit = _base_queryset(request).filter(pk=pk).first()
        if produit is None:
            return Response({'error': 'Produit désactivé introuvable'}, status=status.HTTP_404_NOT_FOUND)
        produit.is_active = True
        produit.save(update_fields=['is_active', 'updated_at'])
        try:
            log_event(request, 'produit.restore', target=produit, metadata={'reference': produit.reference})
        except Exception:
            pass
        return Response({'message': f'Produit « {produit.designation} » réactivé'})


class ProduitsSupprimesLotView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        ids = request.data.get('ids') or []
        if not isinstance(ids, list) or not ids:
            return Response({'error': 'Liste « ids » requise'}, status=status.HTTP_400_BAD_REQUEST)

        resultats = []
        for produit in _base_queryset(request).filter(pk__in=ids):
            ok, message = _supprimer(request, produit)
            resultats.append({'id': produit.id, 'designation': produit.designation,
                              'supprime': ok, 'message': message})
        return Response({
            'supprimes': sum(1 for r in resultats if r['supprime']),
            'refuses': sum(1 for r in resultats if not r['supprime']),
            'resultats': resultats,
        })
