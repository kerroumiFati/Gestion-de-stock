import logging
from django.contrib.auth import authenticate
from django.shortcuts import render
from django.db.models import Sum, Q, F
from rest_framework import viewsets, generics, status
from rest_framework import permissions
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from .serializers import *  # noqa: F401
from .serializers import StockMoveSerializer, InventorySessionSerializer, InventoryLineSerializer
from .models import *
from django.shortcuts import get_object_or_404
from .audit import log_event
from .mixins import TenantFilterMixin, WarehouseRelatedTenantMixin

# Configure logging
logger = logging.getLogger(__name__)

# Simple raw endpoint to fetch categories directly from DB for diagnostics
from rest_framework.decorators import api_view, permission_classes
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def categories_raw(request):
    """Retourne les catégories de l'entreprise de l'utilisateur connecté"""
    try:
        # Filtrer par company de l'utilisateur
        if hasattr(request, 'company') and request.company is not None:
            categories = Categorie.objects.filter(company=request.company)
        else:
            # Si l'utilisateur n'a pas de company, retourner une liste vide
            categories = Categorie.objects.none()

        rows = []
        for cat in categories:
            rows.append({
                'id': cat.id,
                'nom': cat.nom,
                'description': cat.description,
                'parent': cat.parent_id,
                'couleur': cat.couleur,
                'icone': cat.icone,
                'is_active': cat.is_active,
                'products_count': cat.get_products_count()  # Calculer le nombre de produits
            })
        return Response(rows)
    except Exception as e:
        logger.exception('categories_raw failed: %s', e)
        return Response({'error': str(e)}, status=500)

# API pour les Catégories
class CategorieViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    queryset = Categorie.objects.all().order_by('nom')
    serializer_class = CategorieSerializer
    pagination_class = None  # Désactiver la pagination pour simplifier le front
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        try:
            logger.info('GET /API/categories/ called from %s', request.META.get('REMOTE_ADDR'))
            print('[API] /API/categories/ called from', request.META.get('REMOTE_ADDR'))
            qs = self.filter_queryset(self.get_queryset())
            count = qs.count()
            logger.info('Categories queryset count = %s', count, qs)
            print('[API] Categories queryset count =', count)
            serializer = self.get_serializer(qs, many=True)
            data = serializer.data
            # Log a compact preview of what we send to the front
            preview = data[:3] if isinstance(data, list) else data
            logger.info('Categories response preview (first 3): %s', preview)
            try:
                simple_preview = [ {'id': c.get('id'), 'nom': c.get('nom'), 'is_active': c.get('is_active')} for c in (data[:3] if isinstance(data, list) else []) ]
            except Exception:
                simple_preview = preview
            print('[API] Categories response preview (first 3 simplified):', simple_preview)
            print('[API] Categories total returned:', len(data) if isinstance(data, list) else 'non-list')
            return Response(data)
        except Exception as e:
            logger.exception('Error in categories list: %s', e)
            return Response({'error': str(e)}, status=500)
    
    def get_serializer_class(self):
        if self.action == 'tree':
            return CategorieTreeSerializer
        return CategorieSerializer
    
    @action(detail=False)
    def tree(self, request):
        """Retourne la hiérarchie complète des catégories sous forme d'arbre (filtrée par entreprise)"""
        # Utiliser get_queryset() pour avoir le filtrage automatique par entreprise
        base_qs = self.get_queryset()
        root_categories = base_qs.filter(parent=None, is_active=True).order_by('nom')
        serializer = CategorieTreeSerializer(root_categories, many=True)
        return Response(serializer.data)
    
    @action(detail=False)
    def roots(self, request):
        """Retourne uniquement les catégories racines (sans parent, filtrées par entreprise)"""
        # Utiliser get_queryset() pour avoir le filtrage automatique par entreprise
        base_qs = self.get_queryset()
        root_categories = base_qs.filter(parent=None, is_active=True).order_by('nom')
        serializer = self.get_serializer(root_categories, many=True)
        return Response(serializer.data)
    
    @action(detail=True)
    def children(self, request, pk=None):
        """Retourne les sous-catégories directes d'une catégorie"""
        categorie = self.get_object()
        children = categorie.sous_categories.filter(is_active=True).order_by('nom')
        serializer = self.get_serializer(children, many=True)
        return Response(serializer.data)
    
    @action(detail=True)
    def products(self, request, pk=None):
        """Retourne les produits d'une catégorie (sans les sous-catégories)"""
        categorie = self.get_object()
        products = categorie.produits.filter(is_active=True).order_by('reference')
        serializer = ProduitSerializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=True)
    def all_products(self, request, pk=None):
        """Retourne tous les produits d'une catégorie et de ses sous-catégories"""
        categorie = self.get_object()
        # Récupérer tous les IDs des catégories et sous-catégories
        category_ids = [categorie.id]
        for child in categorie.get_all_children():
            category_ids.append(child.id)
        
        products = Produit.objects.filter(
            categorie_id__in=category_ids, 
            is_active=True
        ).order_by('reference')
        serializer = ProduitSerializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=False)
    def stats(self, request):
        """Statistiques des catégories (filtrées par entreprise)"""
        # Utiliser get_queryset() pour avoir le filtrage automatique par entreprise
        base_qs = self.get_queryset()
        stats = {
            'total_categories': base_qs.filter(is_active=True).count(),
            'categories_racines': base_qs.filter(parent=None, is_active=True).count(),
            'categories_avec_produits': base_qs.filter(
                produits__is_active=True, is_active=True
            ).distinct().count(),
        }
        return Response(stats)

class ClientViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    queryset = Client.objects.all().order_by('nom')
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Override pour permettre l'accès aux clients pour les utilisateurs mobiles
        qui n'ont pas de company (livreurs)
        """
        queryset = Client.objects.all().order_by('nom')

        # Si l'utilisateur n'est pas authentifié, rien
        if not self.request.user.is_authenticated:
            return queryset.none()

        # Si l'utilisateur a une company, filtrer par company
        if hasattr(self.request, 'company') and self.request.company is not None:
            queryset = queryset.filter(company=self.request.company)
        # Sinon (utilisateur mobile sans company), retourner tous les clients
        # Cela permet aux livreurs d'accéder aux clients assignés

        return queryset

class FournisseurViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    queryset = Fournisseur.objects.all().order_by('libelle')
    serializer_class = FournisseurSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

class ProduitViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    queryset = Produit.objects.filter(is_active=True).order_by('reference')
    serializer_class = ProduitSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = {
        'quantite': ['gte', 'lte'],
        'code_barre': ['exact', 'icontains'],
        'reference': ['exact', 'icontains'],
        'categorie': ['exact'],
        'fournisseur': ['exact'],
        'prixU': ['gte', 'lte']
    }
    @action(detail=True, methods=['get'])
    def stock(self, request, pk=None):
        p = self.get_object()
        moves_sum = p.mouvements.aggregate(total=Sum('delta')).get('total') or 0
        data = {
            'book_quantity': p.quantite,
            'moves_sum': moves_sum,
            'delta': moves_sum - p.quantite
        }
        return Response(data)
    
    @action(detail=False)
    def by_category(self, request):
        """Retourne les produits groupés par catégorie"""
        category_id = request.GET.get('category_id')
        if category_id:
            try:
                categorie = Categorie.objects.get(id=category_id, is_active=True)
                products = self.queryset.filter(categorie=categorie)
                serializer = self.get_serializer(products, many=True)
                return Response({
                    'categorie': CategorieSerializer(categorie).data,
                    'produits': serializer.data
                })
            except Categorie.DoesNotExist:
                return Response({'error': 'Catégorie non trouvée'}, status=404)
        
        # Si pas de category_id, retourner tous les produits groupés
        categories = Categorie.objects.filter(is_active=True, produits__is_active=True).distinct()
        result = []
        for cat in categories:
            products = self.queryset.filter(categorie=cat)
            result.append({
                'categorie': CategorieSerializer(cat).data,
                'produits': self.get_serializer(products, many=True).data
            })
        return Response(result)
    
    @action(detail=False)
    def low_stock(self, request):
        """Retourne les produits avec un stock faible"""
        products = self.queryset.filter(quantite__lte=F('seuil_alerte'))
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=False)
    def critical_stock(self, request):
        """Retourne les produits avec un stock critique"""
        products = self.queryset.filter(quantite__lte=F('seuil_critique'))
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=False)
    def out_of_stock(self, request):
        """Retourne les produits en rupture de stock"""
        products = self.queryset.filter(quantite__lte=0)
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=False)
    def search(self, request):
        """Recherche de produits par nom, référence ou code-barres"""
        query = request.GET.get('q', '').strip()
        if not query:
            return Response([])
        
        products = self.queryset.filter(
            Q(designation__icontains=query) |
            Q(reference__icontains=query) |
            Q(code_barre__icontains=query)
        )[:20]  # Limiter à 20 résultats
        
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        # Appeler le parent (TenantFilterMixin) pour assigner automatiquement la company
        super().perform_create(serializer)
        obj = serializer.instance
        try:
            log_event(self.request, 'produit.create', target=obj, metadata={'id': obj.id, 'reference': getattr(obj, 'reference', None)})
        except Exception:
            pass

    def perform_update(self, serializer):
        obj = serializer.save()
        try:
            log_event(self.request, 'produit.update', target=obj, metadata={'id': obj.id})
        except Exception:
            pass

    def perform_destroy(self, instance):
        mid = instance.id
        ref = getattr(instance, 'reference', None)
        super().perform_destroy(instance)
        try:
            log_event(self.request, 'produit.delete', target=None, metadata={'id': mid, 'reference': ref})
        except Exception:
            pass
    def destroy(self, request, *args, **kwargs):
        """Suppression logique (soft delete) du produit"""
        instance = self.get_object()

        try:
            # Marquer comme inactif au lieu de supprimer
            instance.is_active = False
            instance.save()

            # Enregistrer l'audit log
            log_event(
                request=request,
                action='produit.delete',
                target=instance,
                metadata={'reference': instance.reference}
            )

            return Response(
                {'message': 'Produit désactivé avec succès'},
                status=status.HTTP_204_NO_CONTENT
            )
        except Exception as e:
            logger.exception(f"Erreur lors de la suppression du produit {instance.id}: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AchatViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    queryset = Achat.objects.all().order_by('date_Achat')
    serializer_class = AchatSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # Appeler le parent (TenantFilterMixin) pour assigner automatiquement la company
        super().perform_create(serializer)
        obj = serializer.instance
        try:
            # Optionnel: entrepôt spécifié dans la requête
            warehouse_id = self.request.data.get('warehouse') or self.request.data.get('warehouse_id')
            p = obj.produit
            qty = int(obj.quantite or 0)
            w = None
            if warehouse_id:
                try:
                    w = Warehouse.objects.get(pk=int(warehouse_id))
                except Exception:
                    w = None
            # Mettre à jour le stock par entrepôt si fourni
            if w is not None:
                ps, _ = ProductStock.objects.get_or_create(produit=p, warehouse=w, defaults={'quantity': 0})
                ps.quantity = ps.quantity + qty
                ps.save(update_fields=['quantity'])
                # Aggréger le stock total sur le produit
                from django.db.models import Sum
                total = p.stocks.aggregate(total=Sum('quantity')).get('total') or 0
                p.quantite = total
                p.save(update_fields=['quantite'])
            else:
                # Fallback: incrémenter directement le stock produit
                p.quantite = (p.quantite or 0) + qty
                p.save(update_fields=['quantite'])
            # Créer un mouvement de stock (entrée)
            StockMove.objects.create(produit=p, warehouse=w, delta=qty, source='ACHAT', ref_id=str(obj.id), note=f"Achat #{obj.id}")
            log_event(self.request, 'achat.create', target=obj, metadata={'id': obj.id})
        except Exception:
            pass

    def perform_update(self, serializer):
        obj = serializer.save()
        try:
            log_event(self.request, 'achat.update', target=obj, metadata={'id': obj.id})
        except Exception:
            pass

    def perform_destroy(self, instance):
        mid = instance.id
        super().perform_destroy(instance)
        try:
            log_event(self.request, 'achat.delete', target=None, metadata={'id': mid})
        except Exception:
            pass

class BonLivraisonViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    queryset = BonLivraison.objects.all().order_by('-date_creation')
    serializer_class = BonLivraisonSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        super().perform_create(serializer)
        obj = serializer.instance
        try:
            log_event(self.request, 'bonlivraison.create', target=obj, metadata={'id': obj.id, 'numero': getattr(obj, 'numero', None)})
        except Exception:
            pass

    def perform_update(self, serializer):
        obj = serializer.save()
        try:
            log_event(self.request, 'bonlivraison.update', target=obj, metadata={'id': obj.id})
        except Exception:
            pass

    def perform_destroy(self, instance):
        mid = instance.id
        num = getattr(instance, 'numero', None)
        super().perform_destroy(instance)
        try:
            log_event(self.request, 'bonlivraison.delete', target=None, metadata={'id': mid, 'numero': num})
        except Exception:
            pass

    @action(detail=True, methods=['post'])
    def valider(self, request, pk=None):
        bon = self.get_object()
        if bon.statut != 'draft':
            return Response({'detail': 'Seuls les bons en brouillon peuvent être validés.'}, status=400)
        # Vérifier les stocks
        insuffisants = []
        for l in bon.lignes.select_related('produit'):
            if l.produit.quantite < l.quantite:
                insuffisants.append({'produit': l.produit.id, 'stock': l.produit.quantite, 'demande': l.quantite})
        if insuffisants:
            return Response({'detail': 'Stock insuffisant', 'lignes': insuffisants}, status=400)
        # Décrémenter
        for l in bon.lignes.select_related('produit'):
            p = l.produit
            p.quantite = p.quantite - l.quantite
            p.save(update_fields=['quantite'])
            StockMove.objects.create(produit=p, delta=-(l.quantite), source='BL', ref_id=str(bon.id), note=f'BL {bon.numero}')
        bon.statut = 'validated'
        bon.save(update_fields=['statut'])
        try:
            log_event(self.request, 'bonlivraison.validate', target=bon, metadata={'id': bon.id, 'numero': getattr(bon, 'numero', None)})
        except Exception:
            pass
        return Response({'detail': 'Bon validé'}, status=200)

class FactureViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    queryset = Facture.objects.all().order_by('-date_emission')
    serializer_class = FactureSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        super().perform_create(serializer)
        obj = serializer.instance
        try:
            log_event(self.request, 'facture.create', target=obj, metadata={'id': obj.id, 'numero': getattr(obj, 'numero', None)})
        except Exception:
            pass

    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.statut != 'draft':
            raise serializers.ValidationError('Modification interdite: la facture n\'est plus en brouillon.')
        return super().perform_update(serializer)

    def perform_destroy(self, instance):
        if instance.statut in ('issued', 'paid'):
            raise serializers.ValidationError('Suppression interdite: la facture est émise ou payée.')
        return super().perform_destroy(instance)

    @action(detail=False, methods=['post'])
    def from_bl(self, request):
        try:
            bl_id = request.data.get('bon_livraison')
            tva_rate = request.data.get('tva_rate', 20)
            numero = request.data.get('numero')

            if not bl_id:
                return Response({'detail': 'bon_livraison requis'}, status=400)

            try:
                bl = BonLivraison.objects.select_related('client').prefetch_related('lignes__produit').get(pk=bl_id)
            except BonLivraison.DoesNotExist:
                return Response({'detail': 'Bon de livraison introuvable'}, status=404)

            if bl.statut != 'validated':
                return Response({'detail': 'Le bon de livraison doit être validé'}, status=400)

            if not bl.client:
                return Response({'detail': 'Le bon de livraison doit avoir un client associé'}, status=400)

            # Numéro automatique si absent
            if not numero:
                # Générer un numéro unique en vérifiant les doublons
                base = 'FA-'
                n = Facture.objects.count() + 1
                while True:
                    candidate = f"{base}{n:05d}"
                    if not Facture.objects.filter(numero=candidate).exists():
                        numero = candidate
                        break
                    n += 1

            # Créer la facture avec une date (pas datetime)
            from datetime import date
            facture = Facture.objects.create(
                numero=numero,
                date_emission=date.today(),  # Forcer une date, pas un datetime
                client=bl.client,
                bon_livraison=bl,
                tva_rate=tva_rate,
                statut='draft'
            )

            for l in bl.lignes.all():
                LigneFacture.objects.create(
                    facture=facture,
                    produit=l.produit,
                    designation=l.produit.designation,
                    quantite=l.quantite,
                    prixU_snapshot=l.prixU_snapshot,  # Utiliser le prix du BL, pas le prix actuel du produit
                )

            facture.recompute_totals()
            facture.save(update_fields=['total_ht', 'total_tva', 'total_ttc'])

            try:
                log_event(self.request, 'facture.create_from_bl', target=facture, metadata={
                    'id': facture.id, 'numero': facture.numero, 'bl_id': bl.id
                })
            except Exception:
                pass

            return Response(FactureSerializer(facture).data, status=201)

        except Exception as e:
            logger.exception('Erreur lors de la création de facture depuis BL: %s', e)
            return Response({'detail': f'Erreur: {str(e)}'}, status=500)

    @action(detail=True, methods=['get'])
    def printable(self, request, pk=None):
        from django.http import HttpResponse
        f = self.get_object()
        # Simple HTML imprimable (export via impression PDF navigateur)
        rows = ''.join([
            f"<tr><td>{i+1}</td><td>{l.designation}</td><td>{l.quantite}</td><td>{l.prixU_snapshot}</td><td>{l.quantite * l.prixU_snapshot}</td></tr>"
            for i, l in enumerate(f.lignes.all())
        ])
        html = f"""<!DOCTYPE html>
        <html><head><meta charset='utf-8'><title>Facture {f.numero}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h2 {{ color: #333; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            td, th {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .totals {{ margin-top: 20px; text-align: right; }}
            @media print {{
                button {{ display: none; }}
            }}
        </style>
        </head><body>
        <h2>Facture {f.numero}</h2>
        <p><strong>Date:</strong> {f.date_emission}</p>
        <p><strong>Client:</strong> {f.client.nom} {f.client.prenom}</p>
        <p><strong>Statut:</strong> {f.statut}</p>
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Désignation</th>
                    <th>Quantité</th>
                    <th>Prix Unitaire</th>
                    <th>Total</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        <div class="totals">
            <p><strong>Total HT:</strong> {f.total_ht}</p>
            <p><strong>TVA ({f.tva_rate}%):</strong> {f.total_tva}</p>
            <p><strong>Total TTC:</strong> {f.total_ttc}</p>
        </div>
        <button onclick="window.print()">Imprimer</button>
        </body></html>
        """
        return HttpResponse(html, content_type='text/html; charset=utf-8')

    @action(detail=True, methods=['post'])
    def issue(self, request, pk=None):
        facture = self.get_object()
        if facture.statut != 'draft':
            return Response({'detail': 'Seules les factures en brouillon peuvent être émises.'}, status=400)
        facture.statut = 'issued'
        facture.save(update_fields=['statut'])
        try:
            log_event(self.request, 'facture.issue', target=facture, metadata={'id': facture.id, 'numero': getattr(facture, 'numero', None)})
        except Exception:
            pass
        return Response({'detail': 'Facture émise'}, status=200)

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        facture = self.get_object()
        if facture.statut not in ('issued', 'paid'):
            return Response({'detail': 'La facture doit être émise pour être payée.'}, status=400)
        facture.statut = 'paid'
        facture.save(update_fields=['statut'])
        try:
            log_event(self.request, 'facture.pay', target=facture, metadata={'id': facture.id, 'numero': getattr(facture, 'numero', None)})
        except Exception:
            pass
        return Response({'detail': 'Facture payée'}, status=200)

from django_filters.rest_framework import DjangoFilterBackend, FilterSet, filters

class StockMoveFilter(FilterSet):
    date_after = filters.DateTimeFilter(field_name='date', lookup_expr='gte')
    date_before = filters.DateTimeFilter(field_name='date', lookup_expr='lte')
    class Meta:
        model = StockMove
        fields = ['produit', 'source', 'warehouse']

class StockMoveViewSet(WarehouseRelatedTenantMixin, viewsets.ModelViewSet):
    queryset = StockMove.objects.all().select_related('produit','warehouse')
    serializer_class = StockMoveSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend]
    filterset_class = StockMoveFilter
    pagination_class = None

    def perform_create(self, serializer):
        obj = serializer.save()
        # Update stock per warehouse and aggregate product stock
        if obj.warehouse is None:
            # If warehouse not specified, try to allocate negative deltas across existing per-warehouse stocks
            if obj.delta < 0:
                remaining = -int(obj.delta)
                # Consume from warehouses with highest quantity first
                stocks = list(ProductStock.objects.filter(produit=obj.produit).select_related('warehouse').order_by('-quantity'))
                for ps in stocks:
                    if remaining <= 0:
                        break
                    take = min(ps.quantity, remaining)
                    if take > 0:
                        ps.quantity = ps.quantity - take
                        ps.save(update_fields=['quantity'])
                        remaining -= take
                # Note: if remaining > 0 here, total product stock would go negative; keep per-warehouse at zero
            else:
                # Positive delta without warehouse: cannot attribute to a location; keep only product total in sync
                pass
        else:
            ps, _ = ProductStock.objects.get_or_create(produit=obj.produit, warehouse=obj.warehouse, defaults={'quantity': 0})
            ps.quantity = ps.quantity + obj.delta
            ps.save(update_fields=['quantity'])
        # keep Produit.quantite as sum across warehouses for backward compatibility
        total = obj.produit.stocks.aggregate(total=Sum('quantity')).get('total') or 0
        obj.produit.quantite = total
        obj.produit.save(update_fields=['quantite'])
        try:
            log_event(self.request, 'stockmove.create', target=obj, metadata={'id': obj.id, 'produit': obj.produit_id, 'warehouse': getattr(obj.warehouse, 'id', None), 'delta': obj.delta, 'source': obj.source, 'ref_id': obj.ref_id})
        except Exception:
            pass

    def perform_update(self, serializer):
        obj = serializer.save()
        total = obj.produit.stocks.aggregate(total=Sum('quantity')).get('total') or 0
        obj.produit.quantite = total
        obj.produit.save(update_fields=['quantite'])
        try:
            log_event(self.request, 'stockmove.update', target=obj, metadata={'id': obj.id})
        except Exception:
            pass

    def perform_destroy(self, instance):
        mid = instance.id
        prod = instance.produit_id
        wh = getattr(instance.warehouse, 'id', None)
        super().perform_destroy(instance)
        try:
            log_event(self.request, 'stockmove.delete', target=None, metadata={'id': mid, 'produit': prod, 'warehouse': wh})
        except Exception:
            pass

    @action(detail=False, methods=['post'])
    def transfer(self, request):
        """Transfert de stock entre entrepôts.
        Body: { produit: id, quantite: >0, from_warehouse: id, to_warehouse: id, note: str (opt) }
        """
        try:
            produit_id = int(request.data.get('produit') or request.data.get('produit_id'))
            qty = float(request.data.get('quantite') or request.data.get('qty') or 0)
        except (TypeError, ValueError):
            return Response({'detail': 'Paramètres invalides'}, status=400)
        if qty <= 0:
            return Response({'detail': 'La quantité doit être > 0'}, status=400)
        from_wh = request.data.get('from_warehouse') or request.data.get('from_wh')
        to_wh = request.data.get('to_warehouse') or request.data.get('to_wh')
        note = request.data.get('note') or ''
        if not from_wh or not to_wh:
            return Response({'detail': 'from_warehouse et to_warehouse requis'}, status=400)
        try:
            p = Produit.objects.get(pk=produit_id)
            w_from = Warehouse.objects.get(pk=int(from_wh))
            w_to = Warehouse.objects.get(pk=int(to_wh))
        except (Produit.DoesNotExist, Warehouse.DoesNotExist):
            return Response({'detail': 'Produit ou Entrepôt introuvable'}, status=404)
        # Check stock availability on source warehouse
        src_stock, _ = ProductStock.objects.get_or_create(produit=p, warehouse=w_from, defaults={'quantity': 0})
        if src_stock.quantity < qty:
            return Response({'detail': 'Stock insuffisant dans l\'entrepôt source', 'stock': src_stock.quantity, 'demande': qty}, status=400)
        # Perform transfer: decrement source, increment destination
        src_stock.quantity -= qty
        src_stock.save(update_fields=['quantity'])
        dst_stock, _ = ProductStock.objects.get_or_create(produit=p, warehouse=w_to, defaults={'quantity': 0})
        dst_stock.quantity += qty
        dst_stock.save(update_fields=['quantity'])
        # Create two moves with warehouses
        try:
            log_event(self.request, 'stockmove.transfer', target=None, metadata={'produit': p.id, 'qty': qty, 'from': w_from.id, 'to': w_to.id, 'note': note})
        except Exception:
            pass
        out_note = f"Transfert sortie {w_from.code} -> {w_to.code}"
        in_note = f"Transfert entrée {w_from.code} -> {w_to.code}"
        out_move = StockMove.objects.create(produit=p, warehouse=w_from, delta=-qty, source='TRANS', ref_id='', note=out_note + (f" | {note}" if note else ''))
        in_move = StockMove.objects.create(produit=p, warehouse=w_to, delta=qty, source='TRANS', ref_id='', note=in_note + (f" | {note}" if note else ''))
        # Aggregate total on product
        total = p.stocks.aggregate(total=Sum('quantity')).get('total') or 0
        p.quantite = total
        p.save(update_fields=['quantite'])
        return Response({'detail': 'Transfert enregistré', 'out': StockMoveSerializer(out_move).data, 'in': StockMoveSerializer(in_move).data}, status=201)

    @action(detail=False, methods=['post'])
    def loss(self, request):
        """Perte / Casse / Expiration: sortie du stock.
        Body: { produit: id, quantite: >0, type: 'PERTE'|'CASSE'|'EXP', warehouse: id, note: str (opt) }
        """
        try:
            produit_id = int(request.data.get('produit') or request.data.get('produit_id'))
            qty = float(request.data.get('quantite') or request.data.get('qty') or 0)
        except (TypeError, ValueError):
            return Response({'detail': 'Paramètres invalides'}, status=400)
        move_type = (request.data.get('type') or '').upper() or 'PERTE'
        if move_type not in ('PERTE', 'CASSE', 'EXP'):
            return Response({'detail': "Type invalide (PERTE|CASSE|EXP)"}, status=400)
        if qty <= 0:
            return Response({'detail': 'La quantité doit être > 0'}, status=400)
        note = request.data.get('note') or ''
        warehouse_id = request.data.get('warehouse') or request.data.get('warehouse_id')
        if not warehouse_id:
            return Response({'detail': 'warehouse requis'}, status=400)
        try:
            p = Produit.objects.get(pk=produit_id)
            w = Warehouse.objects.get(pk=int(warehouse_id))
        except (Produit.DoesNotExist, Warehouse.DoesNotExist):
            return Response({'detail': 'Produit ou Entrepôt introuvable'}, status=404)
        ps, _ = ProductStock.objects.get_or_create(produit=p, warehouse=w, defaults={'quantity': 0})
        if ps.quantity < qty:
            return Response({'detail': 'Stock insuffisant dans cet entrepôt', 'stock': ps.quantity, 'demande': qty}, status=400)
        ps.quantity -= qty
        ps.save(update_fields=['quantity'])
        move = StockMove.objects.create(produit=p, warehouse=w, delta=-qty, source=move_type, ref_id='', note=note)
        total = p.stocks.aggregate(total=Sum('quantity')).get('total') or 0
        p.quantite = total
        p.save(update_fields=['quantite'])
        return Response({'detail': 'Sortie enregistrée', 'move': StockMoveSerializer(move).data}, status=201)

    @action(detail=False, methods=['post'])
    def outflow(self, request):
        """Échantillon / Don / Consommation interne: sortie sans vente.
        Body: { produit: id, quantite: >0, type: 'SAMPLE'|'DON'|'CONS', note: str (opt) }
        """
        try:
            produit_id = int(request.data.get('produit') or request.data.get('produit_id'))
            qty = float(request.data.get('quantite') or request.data.get('qty') or 0)
        except (TypeError, ValueError):
            return Response({'detail': 'Paramètres invalides'}, status=400)
        move_type = (request.data.get('type') or '').upper() or 'SAMPLE'
        if move_type not in ('SAMPLE', 'DON', 'CONS'):
            return Response({'detail': "Type invalide (SAMPLE|DON|CONS)"}, status=400)
        if qty <= 0:
            return Response({'detail': 'La quantité doit être > 0'}, status=400)
        note = request.data.get('note') or ''
        note = request.data.get('note') or ''
        warehouse_id = request.data.get('warehouse') or request.data.get('warehouse_id')
        if not warehouse_id:
            return Response({'detail': 'warehouse requis'}, status=400)
        try:
            p = Produit.objects.get(pk=produit_id)
            w = Warehouse.objects.get(pk=int(warehouse_id))
        except (Produit.DoesNotExist, Warehouse.DoesNotExist):
            return Response({'detail': 'Produit ou Entrepôt introuvable'}, status=404)
        ps, _ = ProductStock.objects.get_or_create(produit=p, warehouse=w, defaults={'quantity': 0})
        if ps.quantity < qty:
            return Response({'detail': 'Stock insuffisant dans cet entrepôt', 'stock': ps.quantity, 'demande': qty}, status=400)
        ps.quantity -= qty
        ps.save(update_fields=['quantity'])
        move = StockMove.objects.create(produit=p, warehouse=w, delta=-qty, source=move_type, ref_id='', note=note)
        total = p.stocks.aggregate(total=Sum('quantity')).get('total') or 0
        p.quantite = total
        p.save(update_fields=['quantite'])
        return Response({'detail': 'Sortie enregistrée', 'move': StockMoveSerializer(move).data}, status=201)

    @action(detail=False, methods=['post'])
    def return_supplier(self, request):
        """Retour fournisseur: retour de produit défectueux ou non conforme au fournisseur.
        Body: { produit: id, quantite: >0, fournisseur: id, warehouse: id, reason: str, note: str (opt), date: str (opt) }
        """
        try:
            produit_id = int(request.data.get('produit') or request.data.get('produit_id'))
            qty = float(request.data.get('quantite') or request.data.get('qty') or 0)
        except (TypeError, ValueError):
            return Response({'detail': 'Paramètres invalides'}, status=400)

        if qty <= 0:
            return Response({'detail': 'La quantité doit être > 0'}, status=400)

        fournisseur_id = request.data.get('fournisseur') or request.data.get('fournisseur_id')
        warehouse_id = request.data.get('warehouse') or request.data.get('warehouse_id')
        reason = request.data.get('reason') or ''
        note = request.data.get('note') or ''
        date_str = request.data.get('date')

        if not fournisseur_id:
            return Response({'detail': 'fournisseur requis'}, status=400)
        if not warehouse_id:
            return Response({'detail': 'warehouse requis'}, status=400)
        if not reason:
            return Response({'detail': 'motif de retour requis'}, status=400)

        try:
            p = Produit.objects.get(pk=produit_id)
            f = Fournisseur.objects.get(pk=int(fournisseur_id))
            w = Warehouse.objects.get(pk=int(warehouse_id))
        except Produit.DoesNotExist:
            return Response({'detail': 'Produit introuvable'}, status=404)
        except Fournisseur.DoesNotExist:
            return Response({'detail': 'Fournisseur introuvable'}, status=404)
        except Warehouse.DoesNotExist:
            return Response({'detail': 'Entrepôt introuvable'}, status=404)

        # Vérifier le stock disponible
        ps, _ = ProductStock.objects.get_or_create(produit=p, warehouse=w, defaults={'quantity': 0})
        if ps.quantity < qty:
            return Response({
                'detail': 'Stock insuffisant dans cet entrepôt',
                'stock': ps.quantity,
                'demande': qty
            }, status=400)

        # Décrémenter le stock
        ps.quantity -= qty
        ps.save(update_fields=['quantity'])

        # Créer le mouvement de stock
        ref_id = f'RETOUR-F{f.id}'
        move = StockMove.objects.create(
            produit=p,
            warehouse=w,
            delta=-qty,
            source='RETOUR',
            ref_id=ref_id,
            note=note,
            date=date_str if date_str else timezone.now()
        )

        # Mettre à jour le stock agrégé
        total = p.stocks.aggregate(total=Sum('quantity')).get('total') or 0
        p.quantite = total
        p.save(update_fields=['quantite'])

        try:
            log_event(request, 'mouvement.return', target=p, metadata={
                'produit': p.id,
                'fournisseur': f.id,
                'fournisseur_libelle': f.libelle,
                'quantite': qty,
                'reason': reason,
                'warehouse': w.id
            })
        except Exception:
            pass

        return Response({
            'detail': 'Retour fournisseur enregistré',
            'move': StockMoveSerializer(move).data,
            'fournisseur': f.libelle
        }, status=201)

class InventorySessionViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    queryset = InventorySession.objects.all().order_by('-date')
    permission_classes = [IsAuthenticated]
    serializer_class = InventorySessionSerializer

    def perform_create(self, serializer):
        # Numérotation automatique INV-<YEAR>-NNNN si absente
        from django.utils import timezone
        from .models import InventorySession
        numero = serializer.validated_data.get('numero')
        if not numero or not str(numero).strip():
            year = timezone.now().year
            prefix = f"INV-{year}-"
            last = InventorySession.objects.filter(numero__startswith=prefix).order_by('-numero').first()
            seq = 1
            if last:
                try:
                    seq = int(str(last.numero).split('-')[-1]) + 1
                except Exception:
                    seq = 1
            numero = f"{prefix}{seq:04d}"
        obj = serializer.save(created_by=self.request.user, numero=numero)
        try:
            log_event(self.request, 'inventorysession.create', target=obj, metadata={'id': obj.id, 'numero': obj.numero})
        except Exception:
            pass

    def perform_update(self, serializer):
        obj = serializer.save()
        try:
            log_event(self.request, 'inventorysession.update', target=obj, metadata={'id': obj.id})
        except Exception:
            pass

    def perform_destroy(self, instance):
        mid = instance.id
        super().perform_destroy(instance)
        try:
            log_event(self.request, 'inventorysession.delete', target=None, metadata={'id': mid})
        except Exception:
            pass

    @action(detail=True, methods=['post'])
    def validate(self, request, pk=None):
        session = self.get_object()
        if session.statut not in ('draft', 'in_progress'):
            return Response({'detail': 'Seules les sessions en brouillon ou en cours peuvent être validées.'}, status=400)
        
        # Vérifier que tous les produits ont été comptés
        if not session.can_be_validated():
            return Response({
                'detail': 'Tous les produits doivent être comptés avant de valider l\'inventaire.',
                'completion_percentage': session.completion_percentage,
                'missing_products': session.missing_products_count
            }, status=400)
        
        # pour chaque ligne, créer un mouvement d'écart et mettre à jour le stock produit
        for l in session.lignes.select_related('produit'):
            if l.counted_qty is not None:
                # book stock: utiliser le champ produit.quantite (source actuelle de vérité), sinon somme des mouvements
                book = l.snapshot_qty if l.snapshot_qty is not None else l.produit.quantite
                delta = l.counted_qty - book
                if delta != 0:
                    StockMove.objects.create(produit=l.produit, delta=delta, source='INV', ref_id=str(session.id), note=f'Inventaire {session.numero}')
                    # maintenir la cohérence avec le champ quantite
                    l.produit.quantite = l.produit.quantite + delta
                    l.produit.save(update_fields=['quantite'])
        
        session.statut = 'validated'
        session.validated_by = request.user
        session.save(update_fields=['statut', 'validated_by'])
        return Response({'detail': 'Inventaire validé'}, status=200)

    @action(detail=True, methods=['post'])
    def save_progress(self, request, pk=None):
        """Sauvegarder le progrès de l'inventaire sans valider"""
        session = self.get_object()
        if session.statut not in ('draft', 'in_progress'):
            return Response({'detail': 'Cette session ne peut plus être modifiée.'}, status=400)
        
        # Mettre à jour le statut en 'in_progress' si c'était en 'draft'
        if session.statut == 'draft':
            session.statut = 'in_progress'
            session.save(update_fields=['statut'])
        
        return Response({
            'detail': 'Progrès sauvegardé',
            'completion_percentage': session.completion_percentage,
            'completed_products': session.completed_products,
            'total_products': session.total_products
        })

    @action(detail=True, methods=['post'])
    def update_line(self, request, pk=None):
        """Mettre à jour une ligne d'inventaire (accepte line_id OU produit_id)"""
        session = self.get_object()
        if session.statut not in ('draft', 'in_progress'):
            return Response({'detail': 'Cette session ne peut plus être modifiée.'}, status=400)

        line_id = request.data.get('line_id')
        produit_id = request.data.get('produit_id')
        counted_qty = request.data.get('counted_qty')

        if counted_qty is None:
            return Response({'detail': 'counted_qty est requis'}, status=400)

        try:
            counted_qty = int(counted_qty)
            if counted_qty < 0:
                return Response({'detail': 'La quantité ne peut pas être négative'}, status=400)
        except (ValueError, TypeError):
            return Response({'detail': 'Quantité invalide'}, status=400)

        # Méthode 1: Mise à jour par line_id
        if line_id:
            try:
                line = session.lignes.get(id=line_id)
                line.counted_qty = counted_qty
                line.counted_by = request.user
                line.save()

                session.update_completion_percentage()

                return Response({
                    'detail': 'Ligne mise à jour',
                    'completion_percentage': session.completion_percentage,
                    'variance': line.get_variance(),
                    'line': InventoryLineSerializer(line).data
                })
            except InventoryLine.DoesNotExist:
                return Response({'detail': 'Ligne d\'inventaire non trouvée'}, status=404)

        # Méthode 2: Mise à jour/création par produit_id
        elif produit_id:
            try:
                produit = Produit.objects.get(id=produit_id)
            except Produit.DoesNotExist:
                return Response({'detail': 'Produit non trouvé'}, status=404)

            # Chercher si la ligne existe déjà
            from .models import InventoryLine
            line = InventoryLine.objects.filter(session=session, produit=produit).first()

            if line:
                # Mise à jour
                line.counted_qty = counted_qty
                line.counted_by = request.user
                from django.utils import timezone
                line.counted_at = timezone.now()
                line.save()
            else:
                # Création
                from django.utils import timezone
                line = InventoryLine.objects.create(
                    session=session,
                    produit=produit,
                    snapshot_qty=produit.quantite,
                    counted_qty=counted_qty,
                    counted_by=request.user,
                    counted_at=timezone.now()
                )

            # Mettre à jour la progression de la session
            session.update_completion_percentage()

            # Recharger la session avec toutes les lignes
            session.refresh_from_db()
            serializer = self.get_serializer(session)

            # Log l'événement
            try:
                log_event(
                    actor=request.user,
                    action='inventoryline.update',
                    target_model='InventoryLine',
                    target_id=line.id,
                    target_repr=f'{session.numero} - {produit.designation}',
                    metadata={'produit_id': produit_id, 'counted_qty': counted_qty},
                    request=request
                )
            except Exception:
                pass

            return Response(serializer.data)

        else:
            return Response({'detail': 'line_id ou produit_id est requis'}, status=400)

    @action(detail=False)
    def in_progress(self, request):
        """Retourner les sessions d'inventaire en cours"""
        sessions = self.queryset.filter(statut='in_progress')
        serializer = self.get_serializer(sessions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def progress_report(self, request, pk=None):
        """Rapport détaillé du progrès de l'inventaire"""
        session = self.get_object()
        missing_products = session.get_missing_products()
        
        return Response({
            'session_info': self.get_serializer(session).data,
            'missing_products': InventoryLineSerializer(missing_products, many=True).data,
            'summary': {
                'total_products': session.total_products,
                'completed_products': session.completed_products,
                'completion_percentage': session.completion_percentage,
                'can_be_validated': session.can_be_validated()
            }
        })

from django.contrib.auth.models import User, Group, Permission
from rest_framework.permissions import IsAuthenticated, IsAdminUser

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

class CompanyViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les entreprises/organisations"""
    queryset = Company.objects.all().order_by('name')
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

class UserProfileViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les profils utilisateurs"""
    queryset = UserProfile.objects.all().select_related('user', 'company')
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all().order_by('name')
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Permission.objects.select_related('content_type').all().order_by('content_type__app_label', 'codename')
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

from .models import AuditLog
from .serializers import AuditLogSerializer

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

class CountViewSet(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request, format=None):
        try:
            from django.db.models import Sum, Count, Q
            from django.utils import timezone
            from datetime import timedelta, datetime
            
            # Compteurs de base
            Produit_count = Produit.objects.filter(is_active=True).count()
            Client_count = Client.objects.all().count()
            Fournisseur_count = Fournisseur.objects.all().count()
            Achat_count = Achat.objects.all().count()
            Vente_count = Vente.objects.filter(statut='completed').count()
            
            # Statistiques de stock
            produits_stock_bas = Produit.objects.filter(quantite__lte=F('seuil_alerte')).count()
            produits_stock_critique = Produit.objects.filter(quantite__lte=F('seuil_critique')).count()
            produits_rupture = Produit.objects.filter(quantite__lte=0).count()
            
            # Chiffre d'affaires
            ca_total = Vente.objects.filter(statut='completed').aggregate(
                total=Sum('total_ttc')
            )['total'] or 0
            
            # CA ce mois
            now = timezone.now()
            debut_mois = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            ca_mois = Vente.objects.filter(
                statut='completed',
                date_vente__gte=debut_mois
            ).aggregate(total=Sum('total_ttc'))['total'] or 0
            
            # Ventes aujourd'hui
            aujourd_hui = now.date()
            ventes_aujourd_hui = Vente.objects.filter(
                statut='completed',
                date_vente__date=aujourd_hui
            ).count()

            # Récupérer la devise par défaut
            default_currency = Currency.get_default()
            currency_symbol = default_currency.symbol if default_currency else ''

            content = {
                'produits_count': Produit_count,
                'clients_count': Client_count,
                'fournisseurs_count': Fournisseur_count,
                'achats_count': Achat_count,
                'ventes_count': Vente_count,
                'ventes_aujourd_hui': ventes_aujourd_hui,
                'ca_total': float(ca_total),
                'ca_mois': float(ca_mois),
                'produits_stock_bas': produits_stock_bas,
                'produits_stock_critique': produits_stock_critique,
                'produits_rupture': produits_rupture,
                'currency_symbol': currency_symbol
            }
            return Response(content)
        except Exception as e:
            logger.exception('CountViewSet failed: %s', e)
            return Response({'error': str(e)}, status=500)

class StatisticsChartsViewSet(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request, format=None):
        try:
            from django.db.models import Sum, Count, Q
            from django.utils import timezone
            from datetime import timedelta, datetime
            import calendar
            
            now = timezone.now()
            
            # Ventes par mois (12 derniers mois)
            ventes_par_mois = []
            mois_labels = []
            for i in range(11, -1, -1):
                date = now - timedelta(days=30*i)
                debut_mois = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                if i == 0:
                    fin_mois = now
                else:
                    fin_mois = (debut_mois + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
                
                ventes_mois = Vente.objects.filter(
                    statut='completed',
                    date_vente__gte=debut_mois,
                    date_vente__lte=fin_mois
                ).aggregate(
                    count=Count('id'),
                    total=Sum('total_ttc')
                )
                
                ventes_par_mois.append({
                    'mois': calendar.month_name[debut_mois.month][:3],
                    'ventes': ventes_mois['count'] or 0,
                    'ca': float(ventes_mois['total'] or 0)
                })
                mois_labels.append(calendar.month_name[debut_mois.month][:3])
            
            # Top 5 produits les plus vendus
            from django.db.models import Sum
            top_produits = LigneVente.objects.filter(
                vente__statut='completed'
            ).values(
                'produit__designation',
                'produit__reference'
            ).annotate(
                total_vendu=Sum('quantite')
            ).order_by('-total_vendu')[:5]
            
            # Répartition des ventes par catégorie
            ventes_par_categorie_qs = LigneVente.objects.filter(
                vente__statut='completed'
            ).values(
                'produit__categorie__nom'
            ).annotate(
                total_ventes=Sum('quantite'),
                ca_categorie=Sum('prixU_snapshot')
            ).order_by('-total_ventes')[:10]
            ventes_par_categorie = []
            for row in ventes_par_categorie_qs:
                ventes_par_categorie.append({
                    'produit__categorie__nom': row.get('produit__categorie__nom'),
                    'total_ventes': row.get('total_ventes') or 0,
                    'ca_categorie': float(row.get('ca_categorie') or 0)
                })
            
            # Évolution du stock (mouvements des 30 derniers jours)
            trente_jours = now - timedelta(days=30)
            mouvements_stock = []
            for i in range(30):
                date = (now - timedelta(days=29-i)).date()
                entrees = StockMove.objects.filter(
                    date__date=date,
                    delta__gt=0
                ).aggregate(total=Sum('delta'))['total'] or 0
                
                sorties = abs(StockMove.objects.filter(
                    date__date=date,
                    delta__lt=0
                ).aggregate(total=Sum('delta'))['total'] or 0)
                
                mouvements_stock.append({
                    'date': date.strftime('%d/%m'),
                    'entrees': entrees,
                    'sorties': sorties
                })
            
            # Statut des stocks
            stock_status = {
                'normal': Produit.objects.filter(
                    quantite__gt=F('seuil_alerte'),
                    is_active=True
                ).count(),
                'alerte': Produit.objects.filter(
                    quantite__lte=F('seuil_alerte'),
                    quantite__gt=F('seuil_critique'),
                    is_active=True
                ).count(),
                'critique': Produit.objects.filter(
                    quantite__lte=F('seuil_critique'),
                    quantite__gt=0,
                    is_active=True
                ).count(),
                'rupture': Produit.objects.filter(
                    quantite__lte=0,
                    is_active=True
                ).count()
            }
            
            # Ventes par type de paiement
            ventes_paiement_qs = Vente.objects.filter(
                statut='completed'
            ).values('type_paiement').annotate(
                count=Count('id'),
                total=Sum('total_ttc')
            ).order_by('-count')
            ventes_paiement = []
            for row in ventes_paiement_qs:
                ventes_paiement.append({
                    'type_paiement': row.get('type_paiement'),
                    'count': row.get('count') or 0,
                    'total': float(row.get('total') or 0)
                })

            # Récupérer la devise par défaut
            default_currency = Currency.get_default()
            currency_symbol = default_currency.symbol if default_currency else ''

            return Response({
                'ventes_par_mois': ventes_par_mois,
                'top_produits': list(top_produits),
                'ventes_par_categorie': ventes_par_categorie,
                'mouvements_stock': mouvements_stock,
                'stock_status': stock_status,
                'ventes_paiement': ventes_paiement,
                'currency_symbol': currency_symbol
            })
        except Exception as e:
            logger.exception('StatisticsChartsViewSet failed: %s', e)
            return Response({
                'ventes_par_mois': [],
                'top_produits': [],
                'ventes_par_categorie': [],
                'mouvements_stock': [],
                'stock_status': {'normal':0,'alerte':0,'critique':0,'rupture':0},
                'ventes_paiement': []
            })

class AlertsView(APIView):
    """Aggregate alerts for stock levels: rupture, critical, low."""
    permission_classes = [permissions.AllowAny]
    def get(self, request, format=None):
        limit = int(request.GET.get('limit', 5))
        low_qs = Produit.objects.filter(quantite__lte=F('seuil_alerte'), quantite__gt=F('seuil_critique')).order_by('quantite')
        critical_qs = Produit.objects.filter(quantite__lte=F('seuil_critique'), quantite__gt=0).order_by('quantite')
        rupture_qs = Produit.objects.filter(quantite__lte=0).order_by('quantite')
        def map_items(qs, level):
            items = []
            for p in qs[:limit]:
                items.append({
                    'id': p.id,
                    'reference': getattr(p, 'reference', ''),
                    'designation': getattr(p, 'designation', ''),
                    'quantite': p.quantite,
                    'seuil_alerte': p.seuil_alerte,
                    'seuil_critique': p.seuil_critique,
                    'level': level
                })
            return items
        data = {
            'counts': {
                'rupture': rupture_qs.count(),
                'critique': critical_qs.count(),
                'bas': low_qs.count(),
                'total': rupture_qs.count() + critical_qs.count() + low_qs.count(),
            },
            'items': map_items(rupture_qs, 'rupture') + map_items(critical_qs, 'critique') + map_items(low_qs, 'bas')
        }
        return Response(data)

class RiskViewSet(APIView):
    def get(self, request, format=None):
        # Optional: filter by product id if provided
        prodid = request.GET.get('prodid')
        qs = Produit.objects.filter(quantite__gt=0)
        if prodid:
            qs = qs.filter(id=prodid)
        data = ProduitSerializer(qs, many=True).data
        return Response(data)

class LoginViewSet(APIView):
    def get(self, request, format=None):
            username = request.GET.get('username', False)
            password = request.GET.get('password', False)
            user = authenticate(username=username, password=password)
            if user is not None and user.is_active:
                return Response({'status': 'success', 'username': user.username, 'id': user.id})
            return Response({'status': 'error', 'message': 'Invalid credentials'}, status=401)

# API pour les Ventes
class VenteViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Vente.objects.all().order_by('-date_vente')

    def perform_create(self, serializer):
        super().perform_create(serializer)
        obj = serializer.instance
        try:
            log_event(self.request, 'vente.create', target=obj, metadata={'id': obj.id, 'numero': getattr(obj, 'numero', None)})
        except Exception:
            pass

    def create(self, request, *args, **kwargs):
        """Override create to return full VenteSerializer after creation"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        instance = serializer.instance

        # Return full VenteSerializer representation
        output_serializer = VenteSerializer(instance)
        headers = self.get_success_headers(output_serializer.data)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_update(self, serializer):
        obj = serializer.save()
        try:
            log_event(self.request, 'vente.update', target=obj, metadata={'id': obj.id})
        except Exception:
            pass

    def perform_destroy(self, instance):
        mid = instance.id
        num = getattr(instance, 'numero', None)
        super().perform_destroy(instance)
        try:
            log_event(self.request, 'vente.delete', target=None, metadata={'id': mid, 'numero': num})
        except Exception:
            pass
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return VenteCreateSerializer
        return VenteSerializer
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Marquer une vente comme terminée"""
        vente = self.get_object()
        if vente.statut == 'draft':
            # Vérifier les stocks
            insuffisants = []
            for ligne in vente.lignes.select_related('produit'):
                if ligne.produit.quantite < ligne.quantite:
                    insuffisants.append({
                        'produit': ligne.produit.id, 
                        'reference': ligne.produit.reference,
                        'stock': ligne.produit.quantite, 
                        'demande': ligne.quantite
                    })
            
            if insuffisants:
                return Response({'detail': 'Stock insuffisant', 'lignes': insuffisants}, status=400)
            
            vente.statut = 'completed'
            vente.save()

            # Décrémenter les stocks maintenant que la vente est finalisée (passe de draft à completed)
            from .models import ProductStock, StockMove
            for ligne in vente.lignes.select_related('produit'):
                produit = ligne.produit
                qty = int(ligne.quantite or 0)
                if qty > 0:
                    # décrément agrégé (back-compat)
                    produit.quantite = produit.quantite - qty
                    produit.save(update_fields=['quantite'])
                    # décrément par entrepôt
                    ps, _ = ProductStock.objects.get_or_create(
                        produit=produit,
                        warehouse=vente.warehouse,
                        defaults={'quantity': 0}
                    )
                    ps.quantity = max(0, (ps.quantity or 0) - qty)
                    ps.save(update_fields=['quantity'])
                    # mouvement de sortie rattaché à l'entrepôt
                    StockMove.objects.create(
                        produit=produit,
                        warehouse=vente.warehouse,
                        delta=-(qty),
                        source='VENTE',
                        ref_id=str(vente.id),
                        note=f"Vente {vente.numero} - finalisée"
                    )

            # Créer automatiquement un Bon de Livraison validé si absent
            try:
                if not vente.bon_livraison_id:
                    from .serializers import BonLivraisonSerializer
                    lignes_data = []
                    for l in vente.lignes.select_related('produit'):
                        lignes_data.append({
                            'produit': l.produit.id,
                            'quantite': int(l.quantite or 0),
                            'prixU_snapshot': getattr(l, 'prixU_snapshot', getattr(l.produit, 'prixU', 0))
                        })
                    bl_payload = {
                        'client': vente.client.id if vente.client_id else None,
                        'statut': 'validated',
                        'lignes': lignes_data,
                    }
                    bl_ser = BonLivraisonSerializer(data=bl_payload)
                    bl_ser.is_valid(raise_exception=True)
                    bl = bl_ser.save()
                    vente.bon_livraison = bl
                    vente.save(update_fields=['bon_livraison'])
            except Exception as e:
                logger.exception('Erreur creation BL lors de la finalisation de la vente: %s', e)

            try:
                log_event(self.request, 'vente.complete', target=vente, metadata={'id': vente.id, 'numero': getattr(vente, 'numero', None)})
            except Exception:
                pass
            return Response({'status': 'Vente terminée'})
        return Response({'error': 'Vente déjà terminée ou annulée'}, status=400)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Annuler une vente et restaurer le stock"""
        vente = self.get_object()
        if vente.statut in ['draft', 'completed']:
            old_statut = vente.statut
            vente.statut = 'canceled'
            vente.save()

            # Restaurer le stock (car il a été décrémenté lors de la création de la vente)
            for ligne in vente.lignes.select_related('produit'):
                # Restaurer le stock agrégé
                ligne.produit.quantite = ligne.produit.quantite + ligne.quantite
                ligne.produit.save(update_fields=['quantite'])

                # Restaurer le stock par entrepôt si un entrepôt est associé
                if vente.warehouse:
                    ps, _ = ProductStock.objects.get_or_create(
                        produit=ligne.produit,
                        warehouse=vente.warehouse,
                        defaults={'quantity': 0}
                    )
                    ps.quantity = ps.quantity + ligne.quantite
                    ps.save(update_fields=['quantity'])

                # Créer un mouvement de correction
                StockMove.objects.create(
                    produit=ligne.produit,
                    warehouse=vente.warehouse,
                    delta=ligne.quantite,
                    source='CORR',
                    ref_id=str(vente.id),
                    note=f"Annulation vente {vente.numero}"
                )

            try:
                log_event(self.request, 'vente.cancel', target=vente, metadata={'id': vente.id, 'numero': getattr(vente, 'numero', None), 'old_statut': old_statut})
            except Exception:
                pass
            return Response({'status': 'Vente annulée'})
        return Response({'error': 'Vente déjà annulée'}, status=400)
    
    @action(detail=False)
    def stats(self, request):
        """Statistiques des ventes (filtrées par entreprise)"""
        from django.db.models import Sum, Count
        from django.utils import timezone
        from datetime import timedelta

        now = timezone.now()
        today = now.date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        # Utiliser get_queryset() pour avoir le filtrage automatique par entreprise
        base_qs = self.get_queryset()

        stats = {
            'total_ventes': base_qs.filter(statut='completed').count(),
            'ventes_aujourd_hui': base_qs.filter(statut='completed', date_vente__date=today).count(),
            'ventes_semaine': base_qs.filter(statut='completed', date_vente__date__gte=week_ago).count(),
            'ventes_mois': base_qs.filter(statut='completed', date_vente__date__gte=month_ago).count(),
            'ca_total': base_qs.filter(statut='completed').aggregate(total=Sum('total_ttc'))['total'] or 0,
            'ca_aujourd_hui': base_qs.filter(statut='completed', date_vente__date=today).aggregate(total=Sum('total_ttc'))['total'] or 0,
            'ca_semaine': base_qs.filter(statut='completed', date_vente__date__gte=week_ago).aggregate(total=Sum('total_ttc'))['total'] or 0,
            'ca_mois': base_qs.filter(statut='completed', date_vente__date__gte=month_ago).aggregate(total=Sum('total_ttc'))['total'] or 0,
        }

        return Response(stats)

    @action(detail=True, methods=['get'])
    def printable(self, request, pk=None):
        """Version imprimable de la vente"""
        vente = self.get_object()
        rows = ''.join([
            f"<tr><td>{i+1}</td><td>{l.designation}</td><td>{l.quantite}</td><td>{l.prixU_snapshot}</td><td>{l.quantite * l.prixU_snapshot}</td></tr>"
            for i, l in enumerate(vente.lignes.all())
        ])
        html = f"""
        <html><head><meta charset='utf-8'><title>Vente {vente.numero}</title>
        <style>table{{width:100%;border-collapse:collapse}}td,th{{border:1px solid #ddd;padding:8px;text-align:left}}</style>
        </head><body onload='window.print()'>
        <h2>Vente {vente.numero}</h2>
        <p>Date: {vente.date_vente} - Client: {vente.client.nom} {vente.client.prenom} - Statut: {vente.statut}</p>
        <p>Type de paiement: {vente.get_type_paiement_display()}</p>
        <table><thead><tr><th>#</th><th>Désignation</th><th>Qté</th><th>PU</th><th>Total</th></tr></thead>
        <tbody>{rows}</tbody></table>
        <h3>Total HT: {vente.total_ht} | Remise: {vente.remise_percent}% | Total TTC: {vente.total_ttc}</h3>
        </body></html>
        """
        return Response(html, content_type='text/html')

    @action(detail=True, methods=['get'])
    def ticket(self, request, pk=None):
        """Générer un ticket de caisse pour la vente"""
        from django.http import HttpResponse
        from datetime import datetime

        vente = self.get_object()
        cfg = SystemConfig.get_solo()

        # Informations de l'entreprise depuis la config
        company_name = cfg.ticket_company_name or "Votre Entreprise"
        company_address = cfg.ticket_company_address or ""
        company_phone = cfg.ticket_company_phone or ""
        footer_message = cfg.ticket_footer_message or "Merci de votre visite !"

        # Devise
        currency_symbol = vente.currency.symbol if vente.currency else '€'

        # Générer les lignes du ticket
        lignes_html = ''
        for ligne in vente.lignes.all():
            total_ligne = ligne.quantite * ligne.prixU_snapshot
            lignes_html += f"""
            <tr>
                <td style="padding: 5px 0; border-bottom: 1px dashed #ddd;">{ligne.designation}</td>
                <td style="padding: 5px 0; border-bottom: 1px dashed #ddd; text-align: center;">{ligne.quantite}</td>
                <td style="padding: 5px 0; border-bottom: 1px dashed #ddd; text-align: right;">{ligne.prixU_snapshot:.2f}</td>
                <td style="padding: 5px 0; border-bottom: 1px dashed #ddd; text-align: right; font-weight: bold;">{total_ligne:.2f}</td>
            </tr>
            """

        # Calculs
        remise_montant = vente.total_ht * (vente.remise_percent / 100) if vente.remise_percent else 0

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Ticket - {vente.numero}</title>
            <style>
                body {{
                    font-family: 'Courier New', monospace;
                    max-width: 300px;
                    margin: 0 auto;
                    padding: 10px;
                    font-size: 12px;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 15px;
                    border-bottom: 2px solid #000;
                    padding-bottom: 10px;
                }}
                .company-name {{
                    font-size: 16px;
                    font-weight: bold;
                    margin-bottom: 5px;
                }}
                .company-info {{
                    font-size: 10px;
                    margin: 2px 0;
                }}
                .ticket-info {{
                    margin: 15px 0;
                    font-size: 11px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 10px 0;
                }}
                th {{
                    text-align: left;
                    border-bottom: 2px solid #000;
                    padding: 5px 0;
                    font-size: 11px;
                }}
                .totals {{
                    border-top: 2px solid #000;
                    margin-top: 10px;
                    padding-top: 10px;
                }}
                .total-line {{
                    display: flex;
                    justify-content: space-between;
                    margin: 5px 0;
                }}
                .total-final {{
                    font-size: 14px;
                    font-weight: bold;
                    border-top: 2px solid #000;
                    padding-top: 5px;
                    margin-top: 5px;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 15px;
                    border-top: 2px solid #000;
                    padding-top: 10px;
                    font-size: 10px;
                }}
                @media print {{
                    body {{ margin: 0; padding: 5px; }}
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="company-name">{company_name}</div>
                {f'<div class="company-info">{company_address}</div>' if company_address else ''}
                {f'<div class="company-info">Tél: {company_phone}</div>' if company_phone else ''}
            </div>

            <div class="ticket-info">
                <div><strong>Ticket N°:</strong> {vente.numero}</div>
                <div><strong>Date:</strong> {vente.date_vente.strftime('%d/%m/%Y %H:%M')}</div>
                <div><strong>Client:</strong> {vente.client.nom} {vente.client.prenom if vente.client.prenom else ''}</div>
                <div><strong>Paiement:</strong> {vente.get_type_paiement_display()}</div>
            </div>

            <table>
                <thead>
                    <tr>
                        <th>Article</th>
                        <th style="text-align: center;">Qté</th>
                        <th style="text-align: right;">P.U.</th>
                        <th style="text-align: right;">Total</th>
                    </tr>
                </thead>
                <tbody>
                    {lignes_html}
                </tbody>
            </table>

            <div class="totals">
                <div class="total-line">
                    <span>Sous-total HT:</span>
                    <span>{vente.total_ht:.2f} {currency_symbol}</span>
                </div>
                {f'<div class="total-line"><span>Remise ({vente.remise_percent}%):</span><span>-{remise_montant:.2f} {currency_symbol}</span></div>' if vente.remise_percent else ''}
                <div class="total-line total-final">
                    <span>TOTAL TTC:</span>
                    <span>{vente.total_ttc:.2f} {currency_symbol}</span>
                </div>
            </div>

            <div class="footer">
                {footer_message}
                <br><br>
                -- Ticket généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} --
            </div>
        </body>
        </html>
        """

        return HttpResponse(html, content_type='text/html; charset=utf-8')

class WarehouseViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    queryset = Warehouse.objects.all().order_by('name')
    serializer_class = WarehouseSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        super().perform_create(serializer)
        obj = serializer.instance
        try:
            log_event(self.request, 'warehouse.create', target=obj, metadata={'id': obj.id, 'code': getattr(obj, 'code', None)})
        except Exception:
            pass

    def perform_update(self, serializer):
        obj = serializer.save()
        try:
            log_event(self.request, 'warehouse.update', target=obj, metadata={'id': obj.id})
        except Exception:
            pass
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        include_inactive = self.request.query_params.get('include_inactive')
        if include_inactive in (None, '', '0', 'false', 'False'):
            qs = qs.filter(is_active=True)
        return qs

    def perform_destroy(self, instance):
        # Prevent deletion if any product stock exists for this warehouse
        if ProductStock.objects.filter(warehouse=instance).exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'detail': "Impossible de supprimer: l'entrepôt est utilisé par des stocks. Mettez-le inactif à la place."})
        return super().perform_destroy(instance)

class ProductStockViewSet(WarehouseRelatedTenantMixin, viewsets.ModelViewSet):
    queryset = ProductStock.objects.select_related('produit','warehouse').all()
    serializer_class = ProductStockSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['produit', 'warehouse']
    pagination_class = None

    def _recompute_product_total(self, produit):
        total = produit.stocks.aggregate(total=Sum('quantity')).get('total') or 0
        produit.quantite = total
        produit.save(update_fields=['quantite'])

    def perform_create(self, serializer):
        obj = serializer.save()
        self._recompute_product_total(obj.produit)

    def perform_update(self, serializer):
        obj = serializer.save()
        self._recompute_product_total(obj.produit)

    def perform_destroy(self, instance):
        produit = instance.produit
        super().perform_destroy(instance)
        self._recompute_product_total(produit)

class LigneVenteViewSet(viewsets.ModelViewSet):
    queryset = LigneVente.objects.all()
    serializer_class = LigneVenteSerializer

# API pour les Devises et Taux de Change
class SystemConfigView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get system configuration"""
        try:
            cfg = SystemConfig.get_solo()
            if not cfg.default_warehouse:
                try:
                    cfg.default_warehouse = SystemConfig.ensure_default_warehouse()
                except Exception as e:
                    logger.warning(f"Could not ensure default warehouse: {e}")

            # Inclure les détails de la devise par défaut
            currency_data = None
            if cfg.default_currency:
                currency_data = {
                    'id': cfg.default_currency.id,
                    'code': cfg.default_currency.code,
                    'name': cfg.default_currency.name,
                    'symbol': cfg.default_currency.symbol
                }

            return Response({
                'default_warehouse': getattr(cfg.default_warehouse, 'id', None),
                'default_currency': getattr(cfg.default_currency, 'id', None),
                'default_currency_details': currency_data,
                'language': cfg.language or 'fr',
                'auto_print_ticket': cfg.auto_print_ticket,
                'ticket_footer_message': cfg.ticket_footer_message or '',
                'ticket_company_name': cfg.ticket_company_name or '',
                'ticket_company_address': cfg.ticket_company_address or '',
                'ticket_company_phone': cfg.ticket_company_phone or ''
            })
        except Exception as e:
            logger.exception("Error in SystemConfigView.get")
            return Response({'error': str(e)}, status=500)

    def put(self, request):
        """Update system configuration"""
        try:
            cfg = SystemConfig.get_solo()
            wid = request.data.get('default_warehouse')

            if wid:
                try:
                    w = Warehouse.objects.get(pk=int(wid))
                    if not w.is_active:
                        return Response({
                            'error': 'Cet entrepôt est inactif. Veuillez en sélectionner un autre.'
                        }, status=400)
                    cfg.default_warehouse = w
                except Warehouse.DoesNotExist:
                    return Response({
                        'error': f'Entrepôt #{wid} introuvable'
                    }, status=404)
                except ValueError:
                    return Response({
                        'error': 'ID d\'entrepôt invalide'
                    }, status=400)
            else:
                cfg.default_warehouse = None

            # Mettre à jour la devise par défaut si fournie
            cid = request.data.get('default_currency')
            if cid:
                try:
                    from .models import Currency
                    curr = Currency.objects.get(pk=int(cid))
                    cfg.default_currency = curr
                except Currency.DoesNotExist:
                    return Response({
                        'error': f'Devise #{cid} introuvable'
                    }, status=404)
                except ValueError:
                    return Response({
                        'error': 'ID de devise invalide'
                    }, status=400)
            elif 'default_currency' in request.data and not cid:
                cfg.default_currency = None

            # Mettre à jour la langue si fournie
            if 'language' in request.data:
                lang = request.data.get('language', 'fr')
                if lang in ['fr', 'en', 'ar']:
                    cfg.language = lang
                else:
                    return Response({'error': 'Langue non supportée'}, status=400)

            # Mettre à jour les paramètres de caisse si fournis
            if 'auto_print_ticket' in request.data:
                cfg.auto_print_ticket = bool(request.data.get('auto_print_ticket'))
            if 'ticket_footer_message' in request.data:
                cfg.ticket_footer_message = request.data.get('ticket_footer_message', '')
            if 'ticket_company_name' in request.data:
                cfg.ticket_company_name = request.data.get('ticket_company_name', '')
            if 'ticket_company_address' in request.data:
                cfg.ticket_company_address = request.data.get('ticket_company_address', '')
            if 'ticket_company_phone' in request.data:
                cfg.ticket_company_phone = request.data.get('ticket_company_phone', '')

            cfg.save()

            return Response({
                'default_warehouse': getattr(cfg.default_warehouse, 'id', None),
                'message': 'Configuration mise à jour avec succès'
            })
        except Exception as e:
            logger.exception("Error in SystemConfigView.put")
            return Response({'error': str(e)}, status=500)

class IsAdminOrReadOnlyAuthenticated(permissions.BasePermission):
    """Allow authenticated users to read; only staff can write."""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_staff

class CurrencyViewSet(viewsets.ModelViewSet):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
    permission_classes = [IsAdminOrReadOnlyAuthenticated]

    def perform_create(self, serializer):
        obj = serializer.save()
        try:
            log_event(self.request, 'currency.create', target=obj, metadata={'id': obj.id, 'code': obj.code})
        except Exception:
            pass

    def perform_update(self, serializer):
        obj = serializer.save()
        try:
            log_event(self.request, 'currency.update', target=obj, metadata={'id': obj.id, 'code': obj.code})
        except Exception:
            pass

    def perform_destroy(self, instance):
        cid = instance.id
        code = instance.code
        super().perform_destroy(instance)
        try:
            log_event(self.request, 'currency.delete', target=None, metadata={'id': cid, 'code': code})
        except Exception:
            pass
    
    @action(detail=False)
    def default(self, request):
        """Obtenir la devise par défaut"""
        default_currency = Currency.get_default()
        if default_currency:
            serializer = self.get_serializer(default_currency)
            return Response(serializer.data)
        return Response({'error': 'Aucune devise par défaut définie'}, status=404)
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Définir une devise comme devise par défaut"""
        currency = self.get_object()
        Currency.objects.filter(is_default=True).update(is_default=False)
        currency.is_default = True
        currency.save()
        try:
            log_event(self.request, 'currency.set_default', target=currency, metadata={'id': currency.id, 'code': currency.code})
        except Exception:
            pass
        return Response({'status': f'{currency.code} définie comme devise par défaut'})

class ExchangeRateViewSet(viewsets.ModelViewSet):
    queryset = ExchangeRate.objects.all()
    serializer_class = ExchangeRateSerializer
    permission_classes = [IsAdminOrReadOnlyAuthenticated]

    def perform_update(self, serializer):
        obj = serializer.save()
        try:
            log_event(self.request, 'exchange_rate.update', target=obj, metadata={'id': obj.id})
        except Exception:
            pass

    def perform_destroy(self, instance):
        rid = instance.id
        super().perform_destroy(instance)
        try:
            log_event(self.request, 'exchange_rate.delete', target=None, metadata={'id': rid})
        except Exception:
            pass
    
    def create(self, request, *args, **kwargs):
        """Créer ou mettre à jour un taux de change"""
        from_currency_id = request.data.get('from_currency')
        to_currency_id = request.data.get('to_currency')
        rate = request.data.get('rate')
        date = request.data.get('date', timezone.now().date())
        try:
            log_event(request, 'exchange_rate.upsert', target=None, metadata={'from': from_currency_id, 'to': to_currency_id, 'rate': rate, 'date': str(date)})
        except Exception:
            pass
        
        # Vérifier si un taux existe déjà pour cette date
        existing_rate = ExchangeRate.objects.filter(
            from_currency_id=from_currency_id,
            to_currency_id=to_currency_id,
            date=date
        ).first()
        
        if existing_rate:
            # Mettre à jour le taux existant
            existing_rate.rate = rate
            existing_rate.is_active = request.data.get('is_active', True)
            existing_rate.save()
            serializer = self.get_serializer(existing_rate)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            # Créer un nouveau taux
            return super().create(request, *args, **kwargs)
    
    @action(detail=False)
    def convert(self, request):
        """Convertir un montant entre deux devises"""
        amount = request.GET.get('amount')
        from_currency_id = request.GET.get('from_currency')
        to_currency_id = request.GET.get('to_currency')
        date = request.GET.get('date')  # Format YYYY-MM-DD
        
        if not all([amount, from_currency_id, to_currency_id]):
            return Response({'error': 'Paramètres manquants: amount, from_currency, to_currency'}, status=400)
        
        try:
            amount = Decimal(amount)
            from_currency = Currency.objects.get(id=from_currency_id)
            to_currency = Currency.objects.get(id=to_currency_id)
            
            if date:
                from datetime import datetime
                date = datetime.strptime(date, '%Y-%m-%d').date()
            
            converted_amount = ExchangeRate.convert_amount(amount, from_currency, to_currency, date)
            
            if converted_amount is not None:
                rate = ExchangeRate.get_rate(from_currency, to_currency, date)
                return Response({
                    'original_amount': amount,
                    'converted_amount': converted_amount,
                    'from_currency': from_currency.code,
                    'to_currency': to_currency.code,
                    'exchange_rate': rate,
                    'date': date or timezone.now().date()
                })
            else:
                return Response({'error': 'Taux de change non trouvé'}, status=404)
                
        except Currency.DoesNotExist:
            return Response({'error': 'Devise non trouvée'}, status=404)
        except ValueError as e:
            return Response({'error': f'Erreur de format: {str(e)}'}, status=400)
    
    @action(detail=False)
    def rates_matrix(self, request):
        """Obtenir une matrice des taux de change pour toutes les devises actives"""
        currencies = Currency.objects.filter(is_active=True)
        matrix = {}
        
        for from_curr in currencies:
            matrix[from_curr.code] = {}
            for to_curr in currencies:
                rate = ExchangeRate.get_rate(from_curr, to_curr)
                matrix[from_curr.code][to_curr.code] = {
                    'rate': rate,
                    'symbol_from': from_curr.symbol,
                    'symbol_to': to_curr.symbol
                }
        
        return Response({
            'currencies': [{'code': c.code, 'name': c.name, 'symbol': c.symbol} for c in currencies],
            'matrix': matrix
        })


# ==============================================
# VUES POUR EXPORTS DE RAPPORTS (Excel & PDF)
# ==============================================

from django.http import HttpResponse
from datetime import datetime
from .reports import (
    generate_stock_valuation_excel,
    generate_stock_valuation_pdf,
    generate_sales_report_excel,
    generate_sales_report_pdf,
    generate_inventory_report_excel,
    generate_inventory_report_pdf
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_stock_valuation(request):
    """
    Export du rapport de valorisation du stock
    Query params:
        - format: excel ou pdf (défaut: excel)
        - warehouse: ID de l'entrepôt (optionnel)
    """
    export_format = request.GET.get('format', 'excel').lower()
    warehouse_id = request.GET.get('warehouse', None)

    try:
        if export_format == 'pdf':
            buffer = generate_stock_valuation_pdf(warehouse_id)
            response = HttpResponse(buffer, content_type='application/pdf')
            filename = f'valorisation_stock_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
        else:
            buffer = generate_stock_valuation_excel(warehouse_id)
            response = HttpResponse(
                buffer,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            filename = f'valorisation_stock_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

        log_event(
            request=request,
            action='report.export_stock_valuation',
            target=None,
            metadata={'format': export_format, 'warehouse_id': warehouse_id}
        )

        return response

    except Exception as e:
        logger.exception(f"Erreur lors de l'export du rapport de valorisation: {e}")
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_sales_report(request):
    """
    Export du rapport des ventes
    Query params:
        - format: excel ou pdf (défaut: excel)
        - start_date: date de début (format YYYY-MM-DD)
        - end_date: date de fin (format YYYY-MM-DD)
    """
    export_format = request.GET.get('format', 'excel').lower()
    start_date_str = request.GET.get('start_date', None)
    end_date_str = request.GET.get('end_date', None)

    start_date = None
    end_date = None

    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        if export_format == 'pdf':
            buffer = generate_sales_report_pdf(start_date, end_date)
            response = HttpResponse(buffer, content_type='application/pdf')
            filename = f'rapport_ventes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
        else:
            buffer = generate_sales_report_excel(start_date, end_date)
            response = HttpResponse(
                buffer,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            filename = f'rapport_ventes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

        log_event(
            request=request,
            action='report.export_sales',
            target=None,
            metadata={
                'format': export_format,
                'start_date': start_date_str,
                'end_date': end_date_str
            }
        )

        return response

    except ValueError as e:
        return Response({'error': f'Format de date invalide: {str(e)}'}, status=400)
    except Exception as e:
        logger.exception(f"Erreur lors de l'export du rapport de ventes: {e}")
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_inventory_report(request):
    """
    Export du rapport d'inventaire complet
    Query params:
        - format: excel ou pdf (défaut: excel)
    """
    export_format = request.GET.get('format', 'excel').lower()

    try:
        if export_format == 'pdf':
            buffer = generate_inventory_report_pdf()
            response = HttpResponse(buffer, content_type='application/pdf')
            filename = f'inventaire_complet_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
        else:
            buffer = generate_inventory_report_excel()
            response = HttpResponse(
                buffer,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            filename = f'inventaire_complet_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

        log_event(
            request=request,
            action='report.export_inventory',
            target=None,
            metadata={'format': export_format}
        )

        return response

    except Exception as e:
        logger.exception(f"Erreur lors de l'export du rapport d'inventaire: {e}")
        return Response({'error': str(e)}, status=500)


#####################
# Types de Prix API #
#####################
class TypePrixViewSet(viewsets.ModelViewSet):
    queryset = TypePrix.objects.all().order_by('ordre', 'libelle')
    serializer_class = TypePrixSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = ['is_active', 'is_default']

    def perform_create(self, serializer):
        obj = serializer.save()
        try:
            log_event(self.request, 'typeprix.create', target=obj, metadata={'code': obj.code})
        except Exception:
            pass

    def perform_update(self, serializer):
        obj = serializer.save()
        try:
            log_event(self.request, 'typeprix.update', target=obj, metadata={'code': obj.code})
        except Exception:
            pass

#####################
# Prix Produits API #
#####################
class PrixProduitViewSet(viewsets.ModelViewSet):
    queryset = PrixProduit.objects.all().order_by('produit', 'type_prix__ordre')
    serializer_class = PrixProduitSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = ['produit', 'type_prix', 'is_active']

    def perform_create(self, serializer):
        obj = serializer.save()
        try:
            log_event(self.request, 'prixproduit.create', target=obj,
                     metadata={'produit': obj.produit.id, 'type_prix': obj.type_prix.code, 'prix': str(obj.prix)})
        except Exception:
            pass

    def perform_update(self, serializer):
        obj = serializer.save()
        try:
            log_event(self.request, 'prixproduit.update', target=obj,
                     metadata={'produit': obj.produit.id, 'type_prix': obj.type_prix.code, 'prix': str(obj.prix)})
        except Exception:
            pass

    def perform_destroy(self, instance):
        produit_id = instance.produit.id
        type_prix_code = instance.type_prix.code
        super().perform_destroy(instance)
        try:
            log_event(self.request, 'prixproduit.delete', target=None,
                     metadata={'produit': produit_id, 'type_prix': type_prix_code})
        except Exception:
            pass


class WelcomeView(APIView):
    """
    API endpoint that logs request metadata and returns a welcome message.
    """
    def get(self, request, format=None):
        # Log request metadata
        logger.info(f"Request received: {request.method} {request.path} from {request.META.get('REMOTE_ADDR', 'unknown')}")

        # Return welcome JSON response
        return Response({
            'message': 'Welcome to the Gestion de Stock API!'
        })


# ==========================================
# VIEWSETS MODULE DE DISTRIBUTION
# ==========================================

class LivreurViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    """
    ViewSet pour gérer les livreurs
    Filtré automatiquement par entreprise
    """
    queryset = Livreur.objects.all().order_by('nom', 'prenom')
    serializer_class = LivreurSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def disponibles(self, request):
        """Retourne les livreurs disponibles"""
        livreurs = self.get_queryset().filter(is_active=True, is_disponible=True)
        serializer = self.get_serializer(livreurs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def marquer_disponible(self, request, pk=None):
        """Marque un livreur comme disponible"""
        livreur = self.get_object()
        livreur.is_disponible = True
        livreur.save()
        return Response({'status': 'Livreur marqué comme disponible'})

    @action(detail=True, methods=['post'])
    def marquer_indisponible(self, request, pk=None):
        """Marque un livreur comme indisponible"""
        livreur = self.get_object()
        livreur.is_disponible = False
        livreur.save()
        return Response({'status': 'Livreur marqué comme indisponible'})

    @action(detail=True, methods=['get'])
    def historique(self, request, pk=None):
        """Retourne l'historique des tournées du livreur"""
        livreur = self.get_object()
        tournees = livreur.tournees.all().order_by('-date')[:20]
        serializer = TourneeListSerializer(tournees, many=True)
        return Response(serializer.data)


class TourneeViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    """
    ViewSet pour gérer les tournées de livraison
    Filtré automatiquement par entreprise
    """
    queryset = Tournee.objects.all().order_by('-date', '-created_at')
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Utiliser TourneeListSerializer pour la liste, TourneeSerializer pour le détail"""
        if self.action == 'list':
            return TourneeListSerializer
        return TourneeSerializer

    @action(detail=False, methods=['get'])
    def today(self, request):
        """Retourne les tournées du jour"""
        from django.utils import timezone
        today = timezone.now().date()
        tournees = self.get_queryset().filter(date=today)
        serializer = TourneeListSerializer(tournees, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def en_cours(self, request):
        """Retourne les tournées en cours"""
        tournees = self.get_queryset().filter(statut='en_cours')
        serializer = TourneeListSerializer(tournees, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def demarrer(self, request, pk=None):
        """Démarre une tournée"""
        from django.utils import timezone
        tournee = self.get_object()

        if tournee.statut != 'planifiee':
            return Response(
                {'error': 'Seules les tournées planifiées peuvent être démarrées'},
                status=400
            )

        tournee.statut = 'en_cours'
        tournee.heure_depart_reelle = timezone.now().time()
        tournee.save()

        # Marquer le livreur comme indisponible
        if tournee.livreur:
            tournee.livreur.is_disponible = False
            tournee.livreur.save()

        return Response({'status': 'Tournée démarrée'})

    @action(detail=True, methods=['post'])
    def terminer(self, request, pk=None):
        """Termine une tournée"""
        from django.utils import timezone
        tournee = self.get_object()

        if tournee.statut != 'en_cours':
            return Response(
                {'error': 'Seules les tournées en cours peuvent être terminées'},
                status=400
            )

        tournee.statut = 'terminee'
        tournee.heure_retour_reelle = timezone.now().time()
        tournee.save()

        # Marquer le livreur comme disponible
        if tournee.livreur:
            tournee.livreur.is_disponible = True
            tournee.livreur.save()

        return Response({
            'status': 'Tournée terminée',
            'taux_reussite': tournee.get_taux_reussite()
        })

    @action(detail=True, methods=['post'])
    def annuler(self, request, pk=None):
        """Annule une tournée"""
        tournee = self.get_object()

        if tournee.statut == 'terminee':
            return Response(
                {'error': 'Une tournée terminée ne peut pas être annulée'},
                status=400
            )

        tournee.statut = 'annulee'
        tournee.save()

        # Marquer le livreur comme disponible
        if tournee.livreur:
            tournee.livreur.is_disponible = True
            tournee.livreur.save()

        return Response({'status': 'Tournée annulée'})

    @action(detail=True, methods=['get'])
    def feuille_route(self, request, pk=None):
        """Retourne la feuille de route imprimable"""
        tournee = self.get_object()
        serializer = TourneeSerializer(tournee)
        return Response(serializer.data)


class ArretLivraisonViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    """
    ViewSet pour gérer les arrêts de livraison
    Filtré automatiquement par entreprise
    """
    queryset = ArretLivraison.objects.all().order_by('tournee', 'ordre')
    serializer_class = ArretLivraisonSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def marquer_livre(self, request, pk=None):
        """Marque un arrêt comme livré"""
        from django.utils import timezone
        arret = self.get_object()

        arret.statut = 'livre'
        if not arret.heure_arrivee:
            arret.heure_arrivee = timezone.now().time()
        if not arret.heure_depart:
            arret.heure_depart = timezone.now().time()

        # Récupérer les données de la requête
        arret.nom_recepteur = request.data.get('nom_recepteur', '')
        arret.signature_client = request.data.get('signature_client', '')
        arret.commentaire = request.data.get('commentaire', '')
        arret.photo_livraison = request.data.get('photo_livraison', '')

        arret.save()

        # Mettre à jour le bon de livraison si présent
        if arret.bon_livraison:
            arret.bon_livraison.statut = 'livre'
            arret.bon_livraison.date_livraison = timezone.now().date()
            arret.bon_livraison.save()

        return Response({'status': 'Arrêt marqué comme livré'})

    @action(detail=True, methods=['post'])
    def marquer_echec(self, request, pk=None):
        """Marque un arrêt comme échoué"""
        from django.utils import timezone
        arret = self.get_object()

        arret.statut = 'echec'
        if not arret.heure_arrivee:
            arret.heure_arrivee = timezone.now().time()
        if not arret.heure_depart:
            arret.heure_depart = timezone.now().time()

        arret.raison_echec = request.data.get('raison_echec', '')
        arret.commentaire = request.data.get('commentaire', '')

        arret.save()

        return Response({'status': 'Arrêt marqué comme échoué'})

    @action(detail=True, methods=['post'])
    def reporter(self, request, pk=None):
        """Reporte un arrêt à une autre tournée"""
        arret = self.get_object()

        arret.statut = 'reporte'
        arret.commentaire = request.data.get('commentaire', 'Reporté')
        arret.save()

        return Response({'status': 'Arrêt reporté'})

    @action(detail=False, methods=['get'])
    def par_tournee(self, request):
        """Retourne les arrêts d'une tournée spécifique"""
        tournee_id = request.query_params.get('tournee_id')
        if not tournee_id:
            return Response({'error': 'tournee_id requis'}, status=400)

        arrets = self.get_queryset().filter(tournee_id=tournee_id).order_by('ordre')
        serializer = self.get_serializer(arrets, many=True)
        return Response(serializer.data)
