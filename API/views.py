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

from .serializers import *  # noqa: F401
from .serializers import StockMoveSerializer, InventorySessionSerializer
from .models import *
from .audit import log_event

# Configure logging
logger = logging.getLogger(__name__)

# Simple raw endpoint to fetch categories directly from DB for diagnostics
from rest_framework.decorators import api_view
@api_view(['GET'])
def categories_raw(request):
    try:
        rows = list(Categorie.objects.values('id','nom','description','parent','couleur','icone','is_active'))
        return Response(rows)
    except Exception as e:
        logger.exception('categories_raw failed: %s', e)
        return Response({'error': str(e)}, status=500)

# API pour les Catégories
class CategorieViewSet(viewsets.ModelViewSet):
    queryset = Categorie.objects.all().order_by('nom')
    serializer_class = CategorieSerializer
    pagination_class = None  # Désactiver la pagination pour simplifier le front

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
        """Retourne la hiérarchie complète des catégories sous forme d'arbre"""
        # Récupérer seulement les catégories racines (sans parent)
        root_categories = Categorie.objects.filter(parent=None, is_active=True).order_by('nom')
        serializer = CategorieTreeSerializer(root_categories, many=True)
        return Response(serializer.data)
    
    @action(detail=False)
    def roots(self, request):
        """Retourne uniquement les catégories racines (sans parent)"""
        root_categories = Categorie.objects.filter(parent=None, is_active=True).order_by('nom')
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
        """Statistiques des catégories"""
        stats = {
            'total_categories': Categorie.objects.filter(is_active=True).count(),
            'categories_racines': Categorie.objects.filter(parent=None, is_active=True).count(),
            'categories_avec_produits': Categorie.objects.filter(
                produits__is_active=True, is_active=True
            ).distinct().count(),
        }
        return Response(stats)

class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all().order_by('nom')
    serializer_class = ClientSerializer

class FournisseurViewSet(viewsets.ModelViewSet):
    queryset = Fournisseur.objects.all().order_by('libelle')
    serializer_class = FournisseurSerializer
    pagination_class = None

class ProduitViewSet(viewsets.ModelViewSet):
    queryset = Produit.objects.filter(is_active=True).order_by('reference')
    serializer_class = ProduitSerializer
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
        obj = serializer.save()
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
    # def destroy(self, request, *args, **kwargs):
    #     instance = self.get_object()
    #     self.perform_destroy(instance)
    #     return Response(status=status.HTTP_204_NO_CONTENT)
    #
    # def perform_destroy(self, instance):
    #     instance.delete()

class AchatViewSet(viewsets.ModelViewSet):
    queryset = Achat.objects.all().order_by('date_Achat')
    serializer_class = AchatSerializer

    def perform_create(self, serializer):
        obj = serializer.save()
        try:
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

class BonLivraisonViewSet(viewsets.ModelViewSet):
    queryset = BonLivraison.objects.all().order_by('-date_creation')
    serializer_class = BonLivraisonSerializer

    def perform_create(self, serializer):
        obj = serializer.save()
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

class FactureViewSet(viewsets.ModelViewSet):
    queryset = Facture.objects.all().order_by('-date_emission')
    serializer_class = FactureSerializer

    def perform_create(self, serializer):
        obj = serializer.save()
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
        # Numéro automatique si absent
        if not numero:
            numero = f"FA-{Facture.objects.count()+1:05d}"
        facture = Facture.objects.create(
            numero=numero,
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
                prixU_snapshot=l.produit.prixU,
            )
        facture.recompute_totals()
        facture.save(update_fields=['total_ht', 'total_tva', 'total_ttc'])
        return Response(FactureSerializer(facture).data, status=201)

    @action(detail=True, methods=['get'])
    def printable(self, request, pk=None):
        f = self.get_object()
        # Simple HTML imprimable (export via impression PDF navigateur)
        rows = ''.join([
            f"<tr><td>{i+1}</td><td>{l.designation}</td><td>{l.quantite}</td><td>{l.prixU_snapshot}</td><td>{l.quantite * l.prixU_snapshot}</td></tr>"
            for i, l in enumerate(f.lignes.all())
        ])
        html = f"""
        <html><head><meta charset='utf-8'><title>Facture {f.numero}</title>
        <style>table{{width:100%;border-collapse:collapse}}td,th{{border:1px solid #ddd;padding:8px;text-align:left}}</style>
        </head><body onload='window.print()'>
        <h2>Facture {f.numero}</h2>
        <p>Date: {f.date_emission} - Client: {f.client.nom} {f.client.prenom} - Statut: {f.statut}</p>
        <table><thead><tr><th>#</th><th>Désignation</th><th>Qté</th><th>PU</th><th>Total</th></tr></thead>
        <tbody>{rows}</tbody></table>
        <h3>Total HT: {f.total_ht} | TVA({f.tva_rate}%): {f.total_tva} | TTC: {f.total_ttc}</h3>
        </body></html>
        """
        return Response(html, content_type='text/html')

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

class StockMoveViewSet(viewsets.ModelViewSet):
    queryset = StockMove.objects.all().select_related('produit','warehouse')
    serializer_class = StockMoveSerializer

    def perform_create(self, serializer):
        obj = serializer.save()
        # Update stock per warehouse and aggregate product stock
        if obj.warehouse is None:
            pass
        else:
            ps, _ = ProductStock.objects.get_or_create(produit=obj.produit, warehouse=obj.warehouse, defaults={'quantity': 0})
            ps.quantity = ps.quantity + obj.delta
            ps.save(update_fields=['quantity'])
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
    filter_backends = [DjangoFilterBackend]
    filterset_class = StockMoveFilter
    pagination_class = None

    def perform_create(self, serializer):
        obj = serializer.save()
        # Update stock per warehouse and aggregate product stock
        if obj.warehouse is None:
            # fallback: no warehouse specified, do nothing per-location
            pass
        else:
            ps, _ = ProductStock.objects.get_or_create(produit=obj.produit, warehouse=obj.warehouse, defaults={'quantity': 0})
            ps.quantity = ps.quantity + obj.delta
            ps.save(update_fields=['quantity'])
        # keep Produit.quantite as sum across warehouses for backward compatibility
        total = obj.produit.stocks.aggregate(total=Sum('quantity')).get('total') or 0
        obj.produit.quantite = total
        obj.produit.save(update_fields=['quantite'])

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

class InventorySessionViewSet(viewsets.ModelViewSet):
    def perform_create(self, serializer):
        obj = serializer.save()
        try:
            log_event(self.request, 'inventorysession.create', target=obj, metadata={'id': obj.id})
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
    queryset = InventorySession.objects.all().order_by('-date')
    serializer_class = InventorySessionSerializer

    def perform_create(self, serializer):
        # Définir l'utilisateur créateur
        serializer.save(created_by=self.request.user)

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
        """Mettre à jour une ligne d'inventaire"""
        session = self.get_object()
        if session.statut not in ('draft', 'in_progress'):
            return Response({'detail': 'Cette session ne peut plus être modifiée.'}, status=400)
        
        line_id = request.data.get('line_id')
        counted_qty = request.data.get('counted_qty')
        
        try:
            line = session.lignes.get(id=line_id)
            if counted_qty is not None:
                line.counted_qty = int(counted_qty)
                line.counted_by = request.user
                line.save()  # La méthode save() mettra à jour automatiquement le pourcentage
            
            return Response({
                'detail': 'Ligne mise à jour',
                'completion_percentage': session.completion_percentage,
                'variance': line.get_variance()
            })
        except InventoryLine.DoesNotExist:
            return Response({'detail': 'Ligne d\'inventaire non trouvée'}, status=404)
        except (ValueError, TypeError):
            return Response({'detail': 'Quantité invalide'}, status=400)

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
                'produits_rupture': produits_rupture
            }
            return Response(content)
        except Exception as e:
            logger.exception('CountViewSet failed: %s', e)
            return Response({'error': str(e)}, status=500)

class StatisticsChartsViewSet(APIView):
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
            
            return Response({
                'ventes_par_mois': ventes_par_mois,
                'top_produits': list(top_produits),
                'ventes_par_categorie': ventes_par_categorie,
                'mouvements_stock': mouvements_stock,
                'stock_status': stock_status,
                'ventes_paiement': ventes_paiement
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
                return Response(user)
            return Response(user)

# API pour les Ventes
class VenteViewSet(viewsets.ModelViewSet):
    queryset = Vente.objects.all().order_by('-date_vente')
    
    def perform_create(self, serializer):
        obj = serializer.save()
        try:
            log_event(self.request, 'vente.create', target=obj, metadata={'id': obj.id, 'numero': getattr(obj, 'numero', None)})
        except Exception:
            pass

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
            
            # Créer les mouvements de stock pour diminuer les quantités
            for ligne in vente.lignes.select_related('produit'):
                ligne.produit.quantite = ligne.produit.quantite - ligne.quantite
                ligne.produit.save(update_fields=['quantite'])
                
                StockMove.objects.create(
                    produit=ligne.produit,
                    delta=-ligne.quantite,
                    source='vente',
                    ref_id=vente.id,
                    note=f"Vente {vente.numero}"
                )
            
            try:
                log_event(self.request, 'vente.complete', target=vente, metadata={'id': vente.id, 'numero': getattr(vente, 'numero', None)})
            except Exception:
                pass
            return Response({'status': 'Vente terminée'})
        return Response({'error': 'Vente déjà terminée ou annulée'}, status=400)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Annuler une vente"""
        vente = self.get_object()
        if vente.statut in ['draft', 'completed']:
            old_statut = vente.statut
            vente.statut = 'canceled'
            vente.save()
            
            # Si la vente était terminée, restaurer le stock
            if old_statut == 'completed':
                for ligne in vente.lignes.select_related('produit'):
                    ligne.produit.quantite = ligne.produit.quantite + ligne.quantite
                    ligne.produit.save(update_fields=['quantite'])
                    
                    StockMove.objects.create(
                        produit=ligne.produit,
                        delta=ligne.quantite,
                        source='vente_cancel',
                        ref_id=vente.id,
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
        """Statistiques des ventes"""
        from django.db.models import Sum, Count
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        today = now.date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        stats = {
            'total_ventes': Vente.objects.filter(statut='completed').count(),
            'ventes_aujourd_hui': Vente.objects.filter(statut='completed', date_vente__date=today).count(),
            'ventes_semaine': Vente.objects.filter(statut='completed', date_vente__date__gte=week_ago).count(),
            'ventes_mois': Vente.objects.filter(statut='completed', date_vente__date__gte=month_ago).count(),
            'ca_total': Vente.objects.filter(statut='completed').aggregate(total=Sum('total_ttc'))['total'] or 0,
            'ca_aujourd_hui': Vente.objects.filter(statut='completed', date_vente__date=today).aggregate(total=Sum('total_ttc'))['total'] or 0,
            'ca_semaine': Vente.objects.filter(statut='completed', date_vente__date__gte=week_ago).aggregate(total=Sum('total_ttc'))['total'] or 0,
            'ca_mois': Vente.objects.filter(statut='completed', date_vente__date__gte=month_ago).aggregate(total=Sum('total_ttc'))['total'] or 0,
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

class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all().order_by('name')
    serializer_class = WarehouseSerializer

    def perform_create(self, serializer):
        obj = serializer.save()
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

class ProductStockViewSet(viewsets.ModelViewSet):
    queryset = ProductStock.objects.select_related('produit','warehouse').all()
    serializer_class = ProductStockSerializer
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
class CurrencyViewSet(viewsets.ModelViewSet):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer

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
