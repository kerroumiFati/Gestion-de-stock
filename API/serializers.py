from rest_framework import serializers
from .models import *
from decimal import Decimal
from django.contrib.auth.models import User

# Serializers pour les Catégories
class CategorieSerializer(serializers.ModelSerializer):
    parent_nom = serializers.CharField(source='parent.nom', read_only=True)
    full_path = serializers.CharField(source='get_full_path', read_only=True)
    products_count = serializers.CharField(source='get_products_count', read_only=True)
    sous_categories_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Categorie
        fields = ['id', 'nom', 'description', 'parent', 'parent_nom', 'full_path', 
                 'couleur', 'icone', 'is_active', 'products_count', 'sous_categories_count', 'created_at']
    
    def get_sous_categories_count(self, obj):
        return obj.sous_categories.filter(is_active=True).count()

class CategorieTreeSerializer(serializers.ModelSerializer):
    """Serializer pour affichage hiérarchique des catégories"""
    sous_categories = serializers.SerializerMethodField()
    products_count = serializers.CharField(source='get_products_count', read_only=True)
    
    class Meta:
        model = Categorie
        fields = ['id', 'nom', 'description', 'couleur', 'icone', 'is_active', 
                 'products_count', 'sous_categories']
    
    def get_sous_categories(self, obj):
        if obj.sous_categories.filter(is_active=True).exists():
            return CategorieTreeSerializer(obj.sous_categories.filter(is_active=True), many=True).data
        return []

from django.contrib.auth.models import Group, Permission
from .models import AuditLog

class GroupSerializer(serializers.ModelSerializer):
    permissions = serializers.PrimaryKeyRelatedField(queryset=Permission.objects.all(), many=True, required=False)

    class Meta:
        model = Group
        fields = ['id', 'name', 'permissions']

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'codename', 'name', 'content_type']

class AuditLogSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source='actor.username', read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'created_at', 'actor', 'actor_username', 'action', 'target_model', 'target_id', 'target_repr', 'metadata', 'ip_address', 'user_agent']
        read_only_fields = fields

class UserSerializer(serializers.ModelSerializer):
    groups = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all(), many=True, required=False)
    group_names = serializers.SlugRelatedField(source='groups', slug_field='name', read_only=True, many=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'groups', 'group_names']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False}
        }

    def create(self, validated_data):
        groups = validated_data.pop('groups', [])
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        if groups:
            user.groups.set(groups)
        return user

    def update(self, instance, validated_data):
        groups = validated_data.pop('groups', None)
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        if groups is not None:
            instance.groups.set(groups)
        return instance

# Serializers pour les Devises et Taux de Change
class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ['id', 'code', 'name', 'symbol', 'is_default', 'is_active']

class ExchangeRateSerializer(serializers.ModelSerializer):
    from_currency_code = serializers.CharField(source='from_currency.code', read_only=True)
    to_currency_code = serializers.CharField(source='to_currency.code', read_only=True)
    from_currency_symbol = serializers.CharField(source='from_currency.symbol', read_only=True)
    to_currency_symbol = serializers.CharField(source='to_currency.symbol', read_only=True)
    
    class Meta:
        model = ExchangeRate
        fields = ['id', 'from_currency', 'to_currency', 'from_currency_code', 'to_currency_code',
                 'from_currency_symbol', 'to_currency_symbol', 'rate', 'date', 'is_active']
class FournisseurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fournisseur
        fields = ('id','libelle', 'telephone','email','adresse')
class ProduitSerializer(serializers.ModelSerializer):
    stock_mouvements = serializers.SerializerMethodField()
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    currency_symbol = serializers.CharField(source='currency.symbol', read_only=True)
    prix_formatted = serializers.SerializerMethodField()
    categorie_nom = serializers.CharField(source='categorie.nom', read_only=True)
    categorie_path = serializers.CharField(source='categorie.get_full_path', read_only=True)
    fournisseur_nom = serializers.CharField(source='fournisseur.libelle', read_only=True)
    stock_status = serializers.SerializerMethodField()
    stock_status_display = serializers.CharField(source='get_stock_status_display', read_only=True)
    stock_class = serializers.CharField(source='get_stock_class', read_only=True)
    
    class Meta:
        model = Produit
        fields = (
            'id', 'reference', 'code_barre', 'designation', 'description',
            'categorie', 'categorie_nom', 'categorie_path',
            'prixU', 'currency', 'currency_code', 'currency_symbol', 'prix_formatted',
            'quantite', 'seuil_alerte', 'seuil_critique', 'unite_mesure',
            'fournisseur', 'fournisseur_nom',
            'stock_mouvements', 'stock_status', 'stock_status_display', 'stock_class',
            'is_active', 'created_at', 'updated_at'
        )
    
    def get_stock_mouvements(self, obj):
        from django.db.models import Sum
        agg = obj.mouvements.aggregate(total=Sum('delta'))
        total = agg.get('total') or 0
        return total
    
    def get_prix_formatted(self, obj):
        currency = obj.currency or Currency.get_default()
        symbol = currency.symbol if currency else '€'
        return f"{obj.prixU} {symbol}"
    
    def get_stock_status(self, obj):
        return obj.get_stock_status()
class ClientSerializer(serializers.ModelSerializer):
    produits = ProduitSerializer(many=True,read_only=True)
    class Meta:
        model = Client
        fields = ('id','nom', 'prenom','email','telephone','adresse','produits')

class AchatSerializer(serializers.ModelSerializer):
    client_nom = serializers.CharField(source='client.nom', read_only=True)
    client_prenom = serializers.CharField(source='client.prenom', read_only=True)
    produit_reference = serializers.CharField(source='produit.reference', read_only=True)
    produit_designation = serializers.CharField(source='produit.designation', read_only=True)
    class Meta:
        model = Achat
        fields = (
            'id','date_Achat','date_expiration','quantite',
            'client','client_nom','client_prenom',
            'produit','produit_reference','produit_designation'
        )

class LigneLivraisonSerializer(serializers.ModelSerializer):
    class Meta:
        model = LigneLivraison
        fields = ('id', 'produit', 'quantite', 'prixU_snapshot')

class BonLivraisonSerializer(serializers.ModelSerializer):
    lignes = LigneLivraisonSerializer(many=True)

    class Meta:
        model = BonLivraison
        fields = ('id', 'numero', 'date_creation', 'client', 'statut', 'observations', 'lignes')

    def create(self, validated_data):
        lignes_data = validated_data.pop('lignes', [])
        numero = validated_data.get('numero')
        if not numero:
            base = 'BL-'
            n = BonLivraison.objects.count() + 1
            # ensure unique number
            while True:
                candidate = f"{base}{n:05d}"
                if not BonLivraison.objects.filter(numero=candidate).exists():
                    numero = candidate
                    break
                n += 1
            validated_data['numero'] = numero
        bon = BonLivraison.objects.create(**validated_data)
        for ld in lignes_data:
            LigneLivraison.objects.create(bon=bon, **ld)
        return bon

    def update(self, instance, validated_data):
        lignes_data = validated_data.pop('lignes', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lignes_data is not None:
            instance.lignes.all().delete()
            for ld in lignes_data:
                LigneLivraison.objects.create(bon=instance, **ld)
        return instance

class LigneFactureSerializer(serializers.ModelSerializer):
    class Meta:
        model = LigneFacture
        fields = ('id', 'produit', 'designation', 'quantite', 'prixU_snapshot')

class FactureSerializer(serializers.ModelSerializer):
    lignes = LigneFactureSerializer(many=True)

    class Meta:
        model = Facture
        fields = (
            'id', 'numero', 'date_emission', 'client', 'bon_livraison', 'statut',
            'tva_rate', 'total_ht', 'total_tva', 'total_ttc', 'lignes'
        )
        read_only_fields = ('total_ht', 'total_tva', 'total_ttc')

    def create(self, validated_data):
        lignes_data = validated_data.pop('lignes', [])
        facture = Facture.objects.create(**validated_data)
        for ld in lignes_data:
            # default designation from produit if missing
            if not ld.get('designation'):
                p = Produit.objects.get(pk=ld['produit'].id)
                ld['designation'] = p.designation
            LigneFacture.objects.create(facture=facture, **ld)
        facture.recompute_totals()
        facture.save(update_fields=['total_ht', 'total_tva', 'total_ttc'])
        return facture

    def update(self, instance, validated_data):
        lignes_data = validated_data.pop('lignes', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lignes_data is not None:
            instance.lignes.all().delete()
            for ld in lignes_data:
                if not ld.get('designation'):
                    p = Produit.objects.get(pk=ld['produit'].id)
                    ld['designation'] = p.designation
                LigneFacture.objects.create(facture=instance, **ld)
        instance.recompute_totals()
        instance.save(update_fields=['total_ht', 'total_tva', 'total_ttc'])
        return instance

class WarehouseSerializer(serializers.ModelSerializer):
    stocks_count = serializers.SerializerMethodField()
    stocks_total = serializers.SerializerMethodField()

    class Meta:
        model = Warehouse
        fields = ('id', 'name', 'code', 'is_active', 'stocks_count', 'stocks_total')

    def get_stocks_count(self, obj):
        try:
            return obj.stocks.count()
        except Exception:
            return 0

    def get_stocks_total(self, obj):
        try:
            from django.db.models import Sum
            return obj.stocks.aggregate(total=Sum('quantity')).get('total') or 0
        except Exception:
            return 0

class ProductStockSerializer(serializers.ModelSerializer):
    produit_reference = serializers.CharField(source='produit.reference', read_only=True)
    produit_designation = serializers.CharField(source='produit.designation', read_only=True)
    warehouse_code = serializers.CharField(source='warehouse.code', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)

    class Meta:
        model = ProductStock
        fields = ('id', 'produit', 'produit_reference', 'produit_designation', 'warehouse', 'warehouse_code', 'warehouse_name', 'quantity')

class StockMoveSerializer(serializers.ModelSerializer):
    produit_reference = serializers.CharField(source='produit.reference', read_only=True)
    produit_designation = serializers.CharField(source='produit.designation', read_only=True)
    warehouse_code = serializers.CharField(source='warehouse.code', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    class Meta:
        model = StockMove
        fields = ('id', 'produit', 'produit_reference', 'produit_designation', 'warehouse', 'warehouse_code', 'warehouse_name', 'delta', 'source', 'source_display', 'ref_id', 'date', 'note')

class InventoryLineSerializer(serializers.ModelSerializer):
    produit_reference = serializers.CharField(source='produit.reference', read_only=True)
    produit_designation = serializers.CharField(source='produit.designation', read_only=True)
    variance = serializers.SerializerMethodField()
    is_completed = serializers.BooleanField(source='is_completed', read_only=True)
    counted_by_username = serializers.CharField(source='counted_by.username', read_only=True)
    
    class Meta:
        model = InventoryLine
        fields = ('id', 'produit', 'produit_reference', 'produit_designation', 
                 'counted_qty', 'snapshot_qty', 'variance', 'is_completed',
                 'counted_by', 'counted_by_username', 'counted_at')
    
    def get_variance(self, obj):
        return obj.get_variance()

class InventorySessionSerializer(serializers.ModelSerializer):
    lignes = InventoryLineSerializer(many=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    validated_by_username = serializers.CharField(source='validated_by.username', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    can_be_validated = serializers.SerializerMethodField()
    missing_products_count = serializers.SerializerMethodField()

    class Meta:
        model = InventorySession
        fields = ('id', 'numero', 'date', 'statut', 'statut_display', 'note', 
                 'created_by', 'created_by_username', 'validated_by', 'validated_by_username',
                 'total_products', 'completed_products', 'completion_percentage',
                 'can_be_validated', 'missing_products_count', 'lignes')
    
    def get_missing_products_count(self, obj):
        return obj.get_missing_products().count()
    
    def get_can_be_validated(self, obj):
        return obj.can_be_validated()

    def create(self, validated_data):
        lignes_data = validated_data.pop('lignes', [])
        session = InventorySession.objects.create(**validated_data)
        for ld in lignes_data:
            InventoryLine.objects.create(session=session, **ld)
        return session

    def update(self, instance, validated_data):
        lignes_data = validated_data.pop('lignes', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lignes_data is not None:
            instance.lignes.all().delete()
            for ld in lignes_data:
                InventoryLine.objects.create(session=instance, **ld)
        return instance

# Serializers pour les Ventes
class LigneVenteSerializer(serializers.ModelSerializer):
    produit_nom = serializers.CharField(source='produit.designation', read_only=True)
    produit_reference = serializers.CharField(source='produit.reference', read_only=True)
    produit_stock_actuel = serializers.IntegerField(source='produit.quantite', read_only=True)
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    currency_symbol = serializers.CharField(source='currency.symbol', read_only=True)
    total_ligne = serializers.SerializerMethodField()
    total_ligne_vente_currency = serializers.SerializerMethodField()
    prix_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = LigneVente
        fields = ['id', 'produit', 'produit_nom', 'produit_reference', 'produit_stock_actuel', 
                 'designation', 'quantite', 'prixU_snapshot', 'currency', 'currency_code', 
                 'currency_symbol', 'prix_formatted', 'total_ligne', 'total_ligne_vente_currency']
    
    def get_total_ligne(self, obj):
        return obj.quantite * obj.prixU_snapshot
    
    def get_total_ligne_vente_currency(self, obj):
        return obj.get_total_in_sale_currency()
    
    def get_prix_formatted(self, obj):
        currency = obj.currency or obj.vente.get_sale_currency()
        symbol = currency.symbol if currency else '€'
        return f"{obj.prixU_snapshot} {symbol}"

class VenteSerializer(serializers.ModelSerializer):
    lignes = LigneVenteSerializer(many=True, read_only=True)
    client_nom = serializers.CharField(source='client.nom', read_only=True)
    client_prenom = serializers.CharField(source='client.prenom', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    type_paiement_display = serializers.CharField(source='get_type_paiement_display', read_only=True)
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    currency_symbol = serializers.CharField(source='currency.symbol', read_only=True)
    nombre_articles = serializers.SerializerMethodField()
    total_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = Vente
        fields = ['id', 'numero', 'date_vente', 'client', 'client_nom', 'client_prenom',
                 'type_paiement', 'type_paiement_display', 'statut', 'statut_display',
                 'currency', 'currency_code', 'currency_symbol', 'exchange_rate_snapshot',
                 'total_ht', 'total_ttc', 'total_formatted', 'remise_percent', 'observations',
                 'bon_livraison', 'facture', 'lignes', 'nombre_articles']
        read_only_fields = ['total_ht', 'total_ttc']
    
    def get_nombre_articles(self, obj):
        return obj.lignes.count()
    
    def get_total_formatted(self, obj):
        currency = obj.get_sale_currency()
        symbol = currency.symbol if currency else '€'
        return f"{obj.total_ttc} {symbol}"

class VenteCreateSerializer(serializers.ModelSerializer):
    lignes = LigneVenteSerializer(many=True)
    
    class Meta:
        model = Vente
        fields = ['numero', 'client', 'type_paiement', 'currency', 'remise_percent', 'observations', 'lignes']
    
    def create(self, validated_data):
        lignes_data = validated_data.pop('lignes')
        
        # Générer un numéro automatique si pas fourni
        if not validated_data.get('numero'):
            base = 'VTE-'
            n = Vente.objects.count() + 1
            while True:
                candidate = f"{base}{n:05d}"
                if not Vente.objects.filter(numero=candidate).exists():
                    validated_data['numero'] = candidate
                    break
                n += 1
        
        # Définir la devise par défaut si pas spécifiée
        if not validated_data.get('currency'):
            validated_data['currency'] = Currency.get_default()
        
        vente = Vente.objects.create(**validated_data)
        
        for ligne_data in lignes_data:
            produit = ligne_data['produit']
            
            # Utiliser le prix de vente du produit si pas spécifié
            if 'prixU_snapshot' not in ligne_data:
                ligne_data['prixU_snapshot'] = produit.prixU
            
            # Utiliser le nom du produit si designation pas spécifiée
            if 'designation' not in ligne_data:
                ligne_data['designation'] = produit.designation
            
            # Définir la devise de la ligne (héritée du produit)
            if 'currency' not in ligne_data:
                ligne_data['currency'] = produit.currency or vente.get_sale_currency()
            
            LigneVente.objects.create(vente=vente, **ligne_data)
        
        vente.recompute_totals()
        vente.save()
        return vente
    
    def update(self, instance, validated_data):
        lignes_data = validated_data.pop('lignes', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if lignes_data is not None:
            instance.lignes.all().delete()
            for ligne_data in lignes_data:
                produit = ligne_data['produit']
                if 'prixU_snapshot' not in ligne_data:
                    ligne_data['prixU_snapshot'] = produit.prixU
                if 'designation' not in ligne_data:
                    ligne_data['designation'] = produit.designation
                LigneVente.objects.create(vente=instance, **ligne_data)
        
        instance.recompute_totals()
        instance.save()
        return instance
