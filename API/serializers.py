from rest_framework import serializers
from .models import *
from decimal import Decimal
from django.contrib.auth.models import User

# Serializers pour Multi-Tenancy
class CompanySerializer(serializers.ModelSerializer):
    """Serializer pour les entreprises/organisations"""
    users_count = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = ['id', 'name', 'code', 'email', 'telephone', 'adresse',
                 'tax_id', 'is_active', 'users_count', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def get_users_count(self, obj):
        """Nombre d'utilisateurs dans cette entreprise"""
        return obj.users.count()


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer pour les profils utilisateurs"""
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    full_name = serializers.SerializerMethodField()
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'username', 'email', 'full_name',
                 'company', 'company_name', 'role', 'created_at']
        read_only_fields = ['created_at']

    def get_full_name(self, obj):
        """Nom complet de l'utilisateur"""
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username


# Serializers pour les Catégories
class CategorieSerializer(serializers.ModelSerializer):
    parent_nom = serializers.CharField(source='parent.nom', read_only=True)
    full_path = serializers.CharField(source='get_full_path', read_only=True)
    products_count = serializers.IntegerField(source='get_products_count', read_only=True)
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

# Serializers pour les Codes de Prix et Types de Prix
class CodePrixSerializer(serializers.ModelSerializer):
    """Serializer pour les codes promotionnels (STANDARD, AID, RAMADAN, etc.)"""
    nombre_tournees = serializers.SerializerMethodField()

    class Meta:
        model = CodePrix
        fields = ['id', 'code', 'libelle', 'description', 'date_debut', 'date_fin',
                 'ordre', 'is_default', 'is_active', 'created_at', 'nombre_tournees']

    def get_nombre_tournees(self, obj):
        return obj.tournees.count()

class TypePrixSerializer(serializers.ModelSerializer):
    nombre_prix = serializers.SerializerMethodField()

    class Meta:
        model = TypePrix
        fields = ['id', 'code', 'libelle', 'description', 'ordre', 'is_default', 'is_active',
                 'created_at', 'nombre_prix']

    def get_nombre_prix(self, obj):
        return obj.prix.filter(is_active=True).count()

class PrixProduitSerializer(serializers.ModelSerializer):
    code_prix_libelle = serializers.CharField(source='code_prix.libelle', read_only=True, allow_null=True)
    code_prix_code = serializers.CharField(source='code_prix.code', read_only=True, allow_null=True)
    type_prix_libelle = serializers.CharField(source='type_prix.libelle', read_only=True)
    type_prix_code = serializers.CharField(source='type_prix.code', read_only=True)
    produit_reference = serializers.CharField(source='produit.reference', read_only=True)
    produit_designation = serializers.CharField(source='produit.designation', read_only=True)
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    currency_symbol = serializers.CharField(source='currency.symbol', read_only=True)
    prix_formatted = serializers.SerializerMethodField()
    is_valid = serializers.SerializerMethodField()

    class Meta:
        model = PrixProduit
        fields = ['id', 'produit', 'produit_reference', 'produit_designation',
                 'code_prix', 'code_prix_libelle', 'code_prix_code',
                 'type_prix', 'type_prix_libelle', 'type_prix_code',
                 'prix', 'currency', 'currency_code', 'currency_symbol', 'prix_formatted',
                 'quantite_min', 'is_active', 'is_valid', 'created_at', 'updated_at']

    def get_prix_formatted(self, obj):
        currency = obj.get_effective_currency()
        symbol = currency.symbol if currency else 'DA'
        return f"{obj.prix} {symbol}"

    def get_is_valid(self, obj):
        return obj.is_valid_now()

class FournisseurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fournisseur
        fields = ('id','libelle', 'telephone','email','adresse', 'nif', 'nis', 'ai', 'rc')
class ProduitSerializer(serializers.ModelSerializer):
    stock_mouvements = serializers.SerializerMethodField()
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    currency_symbol = serializers.CharField(source='currency.symbol', read_only=True)
    prix_formatted = serializers.SerializerMethodField()
    categorie_nom = serializers.CharField(source='categorie.nom', read_only=True)
    categorie_path = serializers.CharField(source='categorie.get_full_path', read_only=True)
    fournisseur_nom = serializers.CharField(source='fournisseur.libelle', read_only=True, allow_null=True)
    stock_status = serializers.SerializerMethodField()
    stock_status_display = serializers.CharField(source='get_stock_status_display', read_only=True)
    stock_class = serializers.CharField(source='get_stock_class', read_only=True)
    prix_multiples = PrixProduitSerializer(many=True, read_only=True)
    nombre_prix = serializers.SerializerMethodField()

    class Meta:
        model = Produit
        fields = (
            'id', 'reference', 'code_barre', 'designation', 'description', 'image',
            'categorie', 'categorie_nom', 'categorie_path',
            'prixU', 'currency', 'currency_code', 'currency_symbol', 'prix_formatted',
            'quantite', 'seuil_alerte', 'seuil_critique', 'unite_mesure',
            'fournisseur', 'fournisseur_nom',
            'stock_mouvements', 'stock_status', 'stock_status_display', 'stock_class',
            'prix_multiples', 'nombre_prix',
            'company',  # IMPORTANT: Inclure company pour préserver l'affectation lors de l'édition
            'is_active', 'created_at', 'updated_at'
        )
        extra_kwargs = {
            'fournisseur': {'required': False, 'allow_null': True},
            'company': {'required': False, 'allow_null': True},  # Company optionnelle pour compatibilité
            'quantite': {'required': False, 'default': 0},
            'description': {'required': False, 'allow_blank': True},
            'image': {'required': False, 'allow_null': True},
            'currency': {'required': False, 'allow_null': True},
            'seuil_alerte': {'required': False},
            'seuil_critique': {'required': False},
            'unite_mesure': {'required': False},
        }
    
    def get_stock_mouvements(self, obj):
        from django.db.models import Sum
        agg = obj.mouvements.aggregate(total=Sum('delta'))
        total = agg.get('total') or 0
        return total
    
    def get_prix_formatted(self, obj):
        currency = obj.currency or Currency.get_default()
        symbol = currency.symbol if currency else 'DA'
        return f"{obj.prixU} {symbol}"
    
    def get_stock_status(self, obj):
        return obj.get_stock_status()

    def get_nombre_prix(self, obj):
        return obj.prix_multiples.filter(is_active=True).count()

class ClientSerializer(serializers.ModelSerializer):
    produits = ProduitSerializer(many=True, read_only=True)
    secteur_nom = serializers.CharField(source='secteur.nom', read_only=True, allow_null=True)
    secteur_code = serializers.CharField(source='secteur.code', read_only=True, allow_null=True)
    secteur_couleur = serializers.CharField(source='secteur.couleur', read_only=True, allow_null=True)
    type_prix_code = serializers.CharField(source='type_prix.code', read_only=True, allow_null=True)
    type_prix_libelle = serializers.CharField(source='type_prix.libelle', read_only=True, allow_null=True)

    class Meta:
        model = Client
        fields = ('id', 'uuid', 'nom', 'prenom', 'email', 'telephone', 'adresse', 'lat', 'lng',
                  'secteur', 'secteur_nom', 'secteur_code', 'secteur_couleur', 'produits',
                  'nif', 'nis', 'ai', 'rc', 'type_prix', 'type_prix_code', 'type_prix_libelle')

class AchatSerializer(serializers.ModelSerializer):
    fournisseur_nom = serializers.CharField(source='fournisseur.libelle', read_only=True)
    fournisseur_prenom = serializers.CharField(source='fournisseur.telephone', read_only=True)
    produit_reference = serializers.CharField(source='produit.reference', read_only=True)
    produit_designation = serializers.CharField(source='produit.designation', read_only=True)
    currency_symbol = serializers.CharField(source='produit.currency.symbol', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    total_achat = serializers.SerializerMethodField()
    quantite_pieces = serializers.SerializerMethodField()
    prix_unitaire_piece = serializers.SerializerMethodField()
    unite_achat_display = serializers.CharField(source='get_unite_achat_display', read_only=True)

    class Meta:
        model = Achat
        fields = (
            'id','date_Achat','date_expiration',
            'unite_achat','unite_achat_display','quantite','pieces_par_carton',
            'quantite_pieces','prix_achat','prix_unitaire_piece','total_achat','currency_symbol',
            'fournisseur','fournisseur_nom','fournisseur_prenom',
            'produit','produit_reference','produit_designation',
            'warehouse','warehouse_name'
        )

    def get_total_achat(self, obj):
        try:
            return obj.get_prix_total()
        except Exception:
            return 0

    def get_quantite_pieces(self, obj):
        try:
            return obj.get_quantite_pieces()
        except Exception:
            return obj.quantite

    def get_prix_unitaire_piece(self, obj):
        try:
            return obj.get_prix_unitaire_piece()
        except Exception:
            return obj.prix_achat

class LigneLivraisonSerializer(serializers.ModelSerializer):
    class Meta:
        model = LigneLivraison
        fields = ('id', 'produit', 'quantite', 'prixU_snapshot')

class BonLivraisonSerializer(serializers.ModelSerializer):
    lignes = LigneLivraisonSerializer(many=True)

    class Meta:
        model = BonLivraison
        fields = ('id', 'numero', 'date_creation', 'client', 'statut', 'observations', 'lignes')
        extra_kwargs = {
            'numero': {'required': False}  # Permet la génération automatique
        }

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
    client_nom = serializers.CharField(source='client.nom', read_only=True)
    client_prenom = serializers.CharField(source='client.prenom', read_only=True)

    class Meta:
        model = Facture
        fields = (
            'id', 'numero', 'date_emission', 'client', 'client_nom', 'client_prenom',
            'bon_livraison', 'statut', 'tva_rate', 'total_ht', 'total_tva', 'total_ttc', 'lignes'
        )
        read_only_fields = ('total_ht', 'total_tva', 'total_ttc', 'client_nom', 'client_prenom')

    def to_representation(self, instance):
        """Convertir datetime en date pour éviter l'erreur de sérialisation"""
        ret = super().to_representation(instance)
        # Convertir date_emission de datetime à date si nécessaire
        if 'date_emission' in ret and ret['date_emission']:
            # Si c'est un datetime string avec heure, on extrait juste la date
            if isinstance(ret['date_emission'], str) and 'T' in ret['date_emission']:
                ret['date_emission'] = ret['date_emission'].split('T')[0]
        return ret

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
    is_completed = serializers.SerializerMethodField()
    counted_by_username = serializers.SerializerMethodField()

    class Meta:
        model = InventoryLine
        fields = ('id', 'produit', 'produit_reference', 'produit_designation',
                 'counted_qty', 'snapshot_qty', 'variance', 'is_completed',
                 'counted_by', 'counted_by_username', 'counted_at')

    def get_variance(self, obj):
        try:
            return obj.get_variance() if hasattr(obj, 'get_variance') else None
        except Exception:
            return None

    def get_is_completed(self, obj):
        try:
            return obj.is_completed() if hasattr(obj, 'is_completed') else False
        except Exception:
            return False

    def get_counted_by_username(self, obj):
        try:
            return obj.counted_by.username if obj.counted_by else None
        except Exception:
            return None

class InventorySessionSerializer(serializers.ModelSerializer):
    lignes = InventoryLineSerializer(many=True, required=False)
    created_by_username = serializers.SerializerMethodField()
    validated_by_username = serializers.SerializerMethodField()
    statut_display = serializers.CharField(source='get_statut_display', read_only=True, required=False)
    can_be_validated = serializers.SerializerMethodField()
    missing_products_count = serializers.SerializerMethodField()

    class Meta:
        model = InventorySession
        fields = ('id', 'numero', 'date', 'statut', 'statut_display', 'note',
                 'created_by', 'created_by_username', 'validated_by', 'validated_by_username',
                 'total_products', 'completed_products', 'completion_percentage',
                 'can_be_validated', 'missing_products_count', 'lignes')

    def get_created_by_username(self, obj):
        try:
            return obj.created_by.username if obj.created_by else None
        except Exception:
            return None

    def get_validated_by_username(self, obj):
        try:
            return obj.validated_by.username if obj.validated_by else None
        except Exception:
            return None

    def get_missing_products_count(self, obj):
        try:
            return obj.get_missing_products().count() if hasattr(obj, 'get_missing_products') else 0
        except Exception:
            return 0

    def get_can_be_validated(self, obj):
        try:
            return obj.can_be_validated() if hasattr(obj, 'can_be_validated') else False
        except Exception:
            return False

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

    # Champs promotion
    promotion_code = serializers.CharField(source='promotion.code', read_only=True)
    promotion_nom = serializers.CharField(source='promotion.nom', read_only=True)
    a_promotion = serializers.SerializerMethodField()
    economie_totale = serializers.SerializerMethodField()

    class Meta:
        model = LigneVente
        fields = ['id', 'produit', 'produit_nom', 'produit_reference', 'produit_stock_actuel',
                 'designation', 'quantite', 'prixU_snapshot', 'currency', 'currency_code',
                 'currency_symbol', 'prix_formatted', 'total_ligne', 'total_ligne_vente_currency',
                 'promotion', 'promotion_code', 'promotion_nom', 'prix_original', 'remise_promo',
                 'quantite_offerte', 'a_promotion', 'economie_totale']

    def get_a_promotion(self, obj):
        return obj.promotion is not None

    def get_economie_totale(self, obj):
        if obj.prix_original and obj.prixU_snapshot:
            return float((obj.prix_original - obj.prixU_snapshot) * obj.quantite)
        return 0
    
    def get_total_ligne(self, obj):
        return obj.quantite * obj.prixU_snapshot
    
    def get_total_ligne_vente_currency(self, obj):
        return obj.get_total_in_sale_currency()
    
    def get_prix_formatted(self, obj):
        currency = obj.currency or obj.vente.get_sale_currency()
        symbol = currency.symbol if currency else 'DA'
        return f"{obj.prixU_snapshot} {symbol}"

class PaiementVenteSerializer(serializers.ModelSerializer):
    moyen_paiement_display = serializers.CharField(source='get_moyen_paiement_display', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = PaiementVente
        fields = ['id', 'vente', 'date_paiement', 'montant', 'moyen_paiement',
                 'moyen_paiement_display', 'reference', 'notes', 'created_by',
                 'created_by_username', 'created_at']
        read_only_fields = ['created_by', 'created_at']

class VenteSerializer(serializers.ModelSerializer):
    lignes = LigneVenteSerializer(many=True, read_only=True)
    paiements = PaiementVenteSerializer(many=True, read_only=True)
    client_nom = serializers.CharField(source='client.nom', read_only=True)
    client_prenom = serializers.CharField(source='client.prenom', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    type_paiement_display = serializers.CharField(source='get_type_paiement_display', read_only=True)
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    currency_symbol = serializers.CharField(source='currency.symbol', read_only=True)
    warehouse_code = serializers.CharField(source='warehouse.code', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    nombre_articles = serializers.SerializerMethodField()
    total_formatted = serializers.SerializerMethodField()
    montant_paye = serializers.SerializerMethodField()
    reste_a_payer = serializers.SerializerMethodField()
    is_paye = serializers.SerializerMethodField()

    class Meta:
        model = Vente
        fields = ['id', 'numero', 'date_vente', 'client', 'client_nom', 'client_prenom',
                 'type_paiement', 'type_paiement_display', 'statut', 'statut_display',
                 'warehouse', 'warehouse_code', 'warehouse_name',
                 'currency', 'currency_code', 'currency_symbol', 'exchange_rate_snapshot',
                 'total_ht', 'total_ttc', 'total_formatted', 'remise_percent', 'observations',
                 'bon_livraison', 'facture', 'lignes', 'paiements', 'nombre_articles',
                 'montant_paye', 'reste_a_payer', 'is_paye']
        read_only_fields = ['total_ht', 'total_ttc']
    
    def get_nombre_articles(self, obj):
        return obj.lignes.count()

    def get_total_formatted(self, obj):
        currency = obj.get_sale_currency()
        symbol = currency.symbol if currency else 'DA'
        return f"{obj.total_ttc} {symbol}"

    def get_montant_paye(self, obj):
        return float(obj.get_montant_paye())

    def get_reste_a_payer(self, obj):
        return float(obj.get_reste_a_payer())

    def get_is_paye(self, obj):
        return obj.is_paye()

class VenteCreateSerializer(serializers.ModelSerializer):
    lignes = LigneVenteSerializer(many=True)

    class Meta:
        model = Vente
        fields = ['numero', 'client', 'type_paiement', 'statut', 'warehouse', 'currency', 'remise_percent', 'observations', 'lignes']
        extra_kwargs = {
            'numero': {'required': False},
            'statut': {'required': False}
        }
    
    def create(self, validated_data):
        from django.db import transaction
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

        # Exiger un entrepôt: utiliser par défaut si non fourni
        from .models import SystemConfig, Warehouse, ProductStock
        wh = validated_data.get('warehouse')
        if not wh or (hasattr(wh, 'is_active') and not wh.is_active):
            wh = SystemConfig.ensure_default_warehouse()
            validated_data['warehouse'] = wh

        # Définir la devise par défaut si pas spécifiée
        if not validated_data.get('currency'):
            validated_data['currency'] = Currency.get_default()

        # Définir le statut par défaut à 'draft' si pas spécifié
        if 'statut' not in validated_data:
            validated_data['statut'] = 'draft'

        # Pré-vérifier le stock disponible pour chaque ligne SEULEMENT si la vente est completed
        if validated_data.get('statut') == 'completed':
            insuffisants = []
            for ld in lignes_data:
                produit = ld['produit']
                qty = int(ld.get('quantite') or 0)
                if qty <= 0:
                    continue
                if produit.quantite < qty:
                    insuffisants.append({'produit': produit.id, 'reference': produit.reference, 'stock': produit.quantite, 'demande': qty})
            if insuffisants:
                raise serializers.ValidationError({'detail': 'Stock insuffisant', 'lignes': insuffisants})

        with transaction.atomic():
            vente = Vente.objects.create(**validated_data)

            for ligne_data in lignes_data:
                produit = ligne_data['produit']
                qty = int(ligne_data.get('quantite') or 0)

                # Utiliser le prix configuré dans PrixProduit si pas spécifié
                if 'prixU_snapshot' not in ligne_data:
                    prix_final = produit.prixU  # Fallback par défaut

                    # Essayer de récupérer le prix du CodePrix par défaut
                    client = vente.client
                    type_prix_client = client.type_prix if client else None

                    # Récupérer le CodePrix par défaut ou actif
                    code_prix_defaut = CodePrix.get_default()

                    if code_prix_defaut and type_prix_client:
                        # Chercher le prix configuré pour ce produit/code_prix/type_prix
                        prix_produit = PrixProduit.objects.filter(
                            produit=produit,
                            code_prix=code_prix_defaut,
                            type_prix=type_prix_client,
                            is_active=True
                        ).first()

                        if prix_produit:
                            prix_final = prix_produit.prix

                    ligne_data['prixU_snapshot'] = prix_final

                # Utiliser le nom du produit si designation pas spécifiée
                if 'designation' not in ligne_data:
                    ligne_data['designation'] = produit.designation

                # Définir la devise de la ligne (héritée du produit)
                if 'currency' not in ligne_data:
                    ligne_data['currency'] = produit.currency or vente.get_sale_currency()

                LigneVente.objects.create(vente=vente, **ligne_data)

                # Décrémenter le stock SEULEMENT si la vente est finalisée (completed)
                if qty > 0 and vente.statut == 'completed':
                    # décrément agrégé (back-compat)
                    produit.quantite = produit.quantite - qty
                    produit.save(update_fields=['quantite'])
                    # décrément par entrepôt
                    ps, _ = ProductStock.objects.get_or_create(produit=produit, warehouse=vente.warehouse, defaults={'quantity': 0})
                    ps.quantity = max(0, (ps.quantity or 0) - qty)
                    ps.save(update_fields=['quantity'])
                    # mouvement de sortie rattaché à l'entrepôt
                    StockMove.objects.create(produit=produit, warehouse=vente.warehouse, delta=-(qty), source='VENTE', ref_id=str(vente.id), note=f"Vente {vente.numero}")

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

                # Utiliser le prix configuré dans PrixProduit si pas spécifié
                if 'prixU_snapshot' not in ligne_data:
                    prix_final = produit.prixU  # Fallback par défaut

                    # Essayer de récupérer le prix du CodePrix par défaut
                    client = instance.client
                    type_prix_client = client.type_prix if client else None

                    # Récupérer le CodePrix par défaut ou actif
                    code_prix_defaut = CodePrix.get_default()

                    if code_prix_defaut and type_prix_client:
                        # Chercher le prix configuré pour ce produit/code_prix/type_prix
                        prix_produit = PrixProduit.objects.filter(
                            produit=produit,
                            code_prix=code_prix_defaut,
                            type_prix=type_prix_client,
                            is_active=True
                        ).first()

                        if prix_produit:
                            prix_final = prix_produit.prix

                    ligne_data['prixU_snapshot'] = prix_final

                if 'designation' not in ligne_data:
                    ligne_data['designation'] = produit.designation
                LigneVente.objects.create(vente=instance, **ligne_data)

        instance.recompute_totals()
        instance.save()
        return instance


# ==========================================
# SERIALIZERS MODULE DE DISTRIBUTION
# ==========================================

class LivreurSerializer(serializers.ModelSerializer):
    """Serializer pour le modèle Livreur"""
    full_name = serializers.SerializerMethodField()
    nombre_tournees = serializers.SerializerMethodField()
    tournees_en_cours = serializers.SerializerMethodField()

    class Meta:
        model = Livreur
        fields = [
            'id', 'nom', 'prenom', 'full_name', 'telephone', 'email', 'adresse',
            'vehicule_type', 'vehicule_marque', 'immatriculation', 'capacite_charge',
            'numero_permis', 'date_expiration_permis',
            'is_active', 'is_disponible',
            'nombre_tournees', 'tournees_en_cours',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_nombre_tournees(self, obj):
        """Retourne le nombre total de tournées effectuées"""
        return obj.tournees.filter(statut__in=['terminee', 'en_cours']).count()

    def get_tournees_en_cours(self, obj):
        """Retourne le nombre de tournées en cours"""
        return obj.tournees.filter(statut='en_cours').count()


class ArretLivraisonSerializer(serializers.ModelSerializer):
    """Serializer pour le modèle ArretLivraison"""
    client_nom = serializers.CharField(source='client.nom', read_only=True)
    client_telephone = serializers.CharField(source='client.telephone', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    duree_arret = serializers.SerializerMethodField()
    bon_livraison_numero = serializers.CharField(source='bon_livraison.numero', read_only=True, allow_null=True)
    vente_numero = serializers.CharField(source='vente.numero', read_only=True, allow_null=True)

    class Meta:
        model = ArretLivraison
        fields = [
            'id', 'tournee', 'bon_livraison', 'bon_livraison_numero',
            'vente', 'vente_numero', 'client', 'client_nom', 'client_telephone',
            'ordre', 'heure_prevue', 'heure_arrivee', 'heure_depart',
            'adresse_livraison', 'statut', 'statut_display',
            'signature_client', 'nom_recepteur',
            'commentaire', 'raison_echec', 'photo_livraison',
            'duree_arret', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_duree_arret(self, obj):
        return obj.get_duree_arret()


class TourneeSerializer(serializers.ModelSerializer):
    """Serializer pour le modèle Tournee"""
    livreur_nom = serializers.SerializerMethodField()
    warehouse_nom = serializers.CharField(source='warehouse.name', read_only=True, allow_null=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    code_prix_libelle = serializers.CharField(source='code_prix.libelle', read_only=True, allow_null=True)
    code_prix_code = serializers.CharField(source='code_prix.code', read_only=True, allow_null=True)
    nombre_arrets = serializers.SerializerMethodField()
    arrets_livres = serializers.SerializerMethodField()
    taux_reussite = serializers.SerializerMethodField()
    arrets = ArretLivraisonSerializer(many=True, read_only=True)

    class Meta:
        model = Tournee
        fields = [
            'id', 'numero', 'date', 'livreur', 'livreur_nom',
            'warehouse', 'warehouse_nom',
            'heure_depart_prevue', 'heure_depart_reelle',
            'heure_retour_prevue', 'heure_retour_reelle',
            'statut', 'statut_display',
            'code_prix', 'code_prix_libelle', 'code_prix_code',
            'distance_km', 'commentaire',
            'nombre_arrets', 'arrets_livres', 'taux_reussite',
            'arrets', 'created_at', 'updated_at'
        ]
        read_only_fields = ['numero', 'created_at', 'updated_at']

    def get_livreur_nom(self, obj):
        if obj.livreur:
            return obj.livreur.get_full_name()
        return None

    def get_nombre_arrets(self, obj):
        return obj.get_nombre_arrets()

    def get_arrets_livres(self, obj):
        return obj.get_arrets_livres()

    def get_taux_reussite(self, obj):
        return obj.get_taux_reussite()

    def create(self, validated_data):
        """Générer automatiquement le numéro de tournée"""
        from datetime import datetime

        # Générer le numéro automatiquement
        date = validated_data.get('date', datetime.now().date())
        date_str = date.strftime('%Y%m%d')

        # Trouver le dernier numéro de tournée du jour
        from API.models import Tournee
        last_tournee = Tournee.objects.filter(
            numero__startswith=f'TOUR-{date_str}'
        ).order_by('-numero').first()

        if last_tournee:
            # Extraire le compteur et incrémenter
            last_counter = int(last_tournee.numero.split('-')[-1])
            counter = last_counter + 1
        else:
            counter = 1

        # Générer le numéro
        numero = f'TOUR-{date_str}-{counter:03d}'
        validated_data['numero'] = numero

        return super().create(validated_data)


class TourneeListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour la liste des tournées (sans les arrêts)"""
    livreur_nom = serializers.SerializerMethodField()
    warehouse_nom = serializers.CharField(source='warehouse.name', read_only=True, allow_null=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    code_prix_libelle = serializers.CharField(source='code_prix.libelle', read_only=True, allow_null=True)
    code_prix_code = serializers.CharField(source='code_prix.code', read_only=True, allow_null=True)
    nombre_arrets = serializers.SerializerMethodField()
    arrets_livres = serializers.SerializerMethodField()
    taux_reussite = serializers.SerializerMethodField()

    class Meta:
        model = Tournee
        fields = [
            'id', 'numero', 'date', 'livreur', 'livreur_nom',
            'warehouse', 'warehouse_nom',
            'heure_depart_prevue', 'heure_depart_reelle',
            'heure_retour_prevue', 'heure_retour_reelle',
            'statut', 'statut_display',
            'code_prix', 'code_prix_libelle', 'code_prix_code',
            'distance_km',
            'nombre_arrets', 'arrets_livres', 'taux_reussite',
            'created_at'
        ]

    def get_livreur_nom(self, obj):
        if obj.livreur:
            return obj.livreur.get_full_name()
        return None

    def get_nombre_arrets(self, obj):
        return obj.get_nombre_arrets()

    def get_arrets_livres(self, obj):
        return obj.get_arrets_livres()

    def get_taux_reussite(self, obj):
        return obj.get_taux_reussite()


# ==========================================
# SERIALIZERS VISITES CLIENTS
# ==========================================

class VisiteClientSerializer(serializers.ModelSerializer):
    """Serializer pour les visites clients"""
    client_nom = serializers.CharField(source='client.nom', read_only=True)
    client_adresse = serializers.CharField(source='client.adresse', read_only=True)
    livreur_nom = serializers.CharField(source='livreur.nom', read_only=True)
    resultat_display = serializers.CharField(source='get_resultat_display', read_only=True)

    class Meta:
        from .distribution_models import VisiteClient
        model = VisiteClient
        fields = [
            'id', 'client', 'client_nom', 'client_adresse', 'livreur', 'livreur_nom', 'tournee',
            'date_visite', 'heure_visite', 'latitude', 'longitude',
            'resultat', 'resultat_display', 'notes', 'app_id',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def create(self, validated_data):
        from .distribution_models import VisiteClient
        # Assigner la company depuis le client si pas fournie
        if 'company' not in validated_data and validated_data.get('client'):
            validated_data['company'] = validated_data['client'].company
        return VisiteClient.objects.create(**validated_data)


# ==========================================
# SERIALIZERS CONDITIONNEMENT
# ==========================================

class ConditionnementSerializer(serializers.ModelSerializer):
    """Serializer pour le conditionnement des produits"""
    produit_reference = serializers.CharField(source='produit.reference', read_only=True)
    produit_designation = serializers.CharField(source='produit.designation', read_only=True)
    produit_prix_unitaire = serializers.DecimalField(
        source='produit.prixU', max_digits=10, decimal_places=2, read_only=True
    )
    prix_carton_calcule = serializers.SerializerMethodField()
    prix_colis_calcule = serializers.SerializerMethodField()
    unites_par_colis = serializers.SerializerMethodField()
    unites_par_palette = serializers.SerializerMethodField()

    class Meta:
        model = Conditionnement
        fields = [
            'id', 'produit', 'produit_reference', 'produit_designation', 'produit_prix_unitaire',
            'unites_par_carton', 'prix_carton', 'prix_carton_calcule',
            'cartons_par_colis', 'prix_colis', 'prix_colis_calcule', 'unites_par_colis',
            'colis_par_palette', 'prix_palette', 'unites_par_palette',
            'prix_demunerisation',
            'poids_carton', 'dimensions_carton',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_prix_carton_calcule(self, obj):
        return obj.get_prix_carton_calcule()

    def get_prix_colis_calcule(self, obj):
        return obj.get_prix_colis_calcule()

    def get_unites_par_colis(self, obj):
        return obj.get_unites_par_colis()

    def get_unites_par_palette(self, obj):
        return obj.get_unites_par_palette()


# ==========================================
# SERIALIZERS PROMOTIONS
# ==========================================

class PromotionSerializer(serializers.ModelSerializer):
    """Serializer complet pour les promotions"""
    produit_reference = serializers.CharField(source='produit.reference', read_only=True, allow_null=True)
    produit_designation = serializers.CharField(source='produit.designation', read_only=True, allow_null=True)
    produit_prix = serializers.DecimalField(
        source='produit.prixU', max_digits=10, decimal_places=2, read_only=True, allow_null=True
    )
    categorie_nom = serializers.CharField(source='categorie.nom', read_only=True, allow_null=True)
    currency_code = serializers.CharField(source='currency.code', read_only=True, allow_null=True)
    currency_symbol = serializers.CharField(source='currency.symbol', read_only=True, allow_null=True)
    code_prix_code = serializers.CharField(source='code_prix.code', read_only=True, allow_null=True)
    code_prix_libelle = serializers.CharField(source='code_prix.libelle', read_only=True, allow_null=True)
    type_promotion_display = serializers.CharField(source='get_type_promotion_display', read_only=True)
    unite_application_display = serializers.CharField(source='get_unite_application_display', read_only=True)
    conditionnement_minimum_display = serializers.CharField(source='get_conditionnement_minimum_display', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    types_prix_eligibles_list = serializers.SerializerMethodField()
    is_valid = serializers.SerializerMethodField()
    usage_restant = serializers.SerializerMethodField()
    jours_restants = serializers.SerializerMethodField()

    class Meta:
        model = Promotion
        fields = [
            'id', 'code', 'nom', 'description',
            'type_promotion', 'type_promotion_display',
            'valeur_pourcentage', 'valeur_fixe', 'prix_special',
            'quantite_achat', 'quantite_offerte',
            'unite_application', 'unite_application_display',
            'currency', 'currency_code', 'currency_symbol',
            'code_prix', 'code_prix_code', 'code_prix_libelle',
            'produit', 'produit_reference', 'produit_designation', 'produit_prix',
            'categorie', 'categorie_nom',
            'date_debut', 'date_fin', 'jours_restants',
            'quantite_minimum', 'quantite_maximum',
            'conditionnement_minimum', 'conditionnement_minimum_display',
            'carton_complet_requis',
            'est_cumulable', 'priorite',
            'usage_maximum', 'usage_par_client', 'usage_actuel', 'usage_restant',
            'types_prix_eligibles', 'types_prix_eligibles_list',
            'statut', 'statut_display', 'is_valid',
            'created_by', 'created_by_username',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['usage_actuel', 'created_at', 'updated_at']

    def get_types_prix_eligibles_list(self, obj):
        return [{'id': tp.id, 'code': tp.code, 'libelle': tp.libelle}
                for tp in obj.types_prix_eligibles.all()]

    def get_is_valid(self, obj):
        return obj.is_valid()

    def get_usage_restant(self, obj):
        if obj.usage_maximum:
            return max(0, obj.usage_maximum - obj.usage_actuel)
        return None

    def get_jours_restants(self, obj):
        from django.utils import timezone
        now = timezone.now()
        if obj.date_fin > now:
            delta = obj.date_fin - now
            return delta.days
        return 0

    def validate(self, data):
        """Validation personnalisée pour les promotions"""
        type_promo = data.get('type_promotion')

        # Validation selon le type de promotion
        if type_promo == 'pourcentage':
            if not data.get('valeur_pourcentage'):
                raise serializers.ValidationError({
                    'valeur_pourcentage': 'Le pourcentage est requis pour ce type de promotion.'
                })
            if data.get('valeur_pourcentage', 0) <= 0 or data.get('valeur_pourcentage', 0) > 100:
                raise serializers.ValidationError({
                    'valeur_pourcentage': 'Le pourcentage doit être entre 0 et 100.'
                })

        elif type_promo == 'valeur_fixe':
            if not data.get('valeur_fixe'):
                raise serializers.ValidationError({
                    'valeur_fixe': 'La valeur fixe est requise pour ce type de promotion.'
                })

        elif type_promo == 'prix_special':
            if not data.get('prix_special'):
                raise serializers.ValidationError({
                    'prix_special': 'Le prix spécial est requis pour ce type de promotion.'
                })

        elif type_promo in ['achetez_x_payez_y', 'achetez_x_offert_y']:
            if not data.get('quantite_achat'):
                raise serializers.ValidationError({
                    'quantite_achat': 'La quantité à acheter est requise pour ce type de promotion.'
                })
            if not data.get('quantite_offerte'):
                raise serializers.ValidationError({
                    'quantite_offerte': 'La quantité offerte/payée est requise pour ce type de promotion.'
                })

        # Vérifier qu'au moins un produit ou une catégorie est sélectionné
        if not data.get('produit') and not data.get('categorie'):
            raise serializers.ValidationError({
                'produit': 'Veuillez sélectionner un produit ou une catégorie.',
                'categorie': 'Veuillez sélectionner un produit ou une catégorie.'
            })

        # Vérifier les dates
        date_debut = data.get('date_debut')
        date_fin = data.get('date_fin')
        if date_debut and date_fin and date_fin <= date_debut:
            raise serializers.ValidationError({
                'date_fin': 'La date de fin doit être postérieure à la date de début.'
            })

        return data

    def create(self, validated_data):
        types_prix = validated_data.pop('types_prix_eligibles', [])
        promotion = Promotion.objects.create(**validated_data)
        if types_prix:
            promotion.types_prix_eligibles.set(types_prix)
        return promotion

    def update(self, instance, validated_data):
        types_prix = validated_data.pop('types_prix_eligibles', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if types_prix is not None:
            instance.types_prix_eligibles.set(types_prix)
        return instance


class PromotionListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour la liste des promotions"""
    produit_designation = serializers.CharField(source='produit.designation', read_only=True, allow_null=True)
    categorie_nom = serializers.CharField(source='categorie.nom', read_only=True, allow_null=True)
    type_promotion_display = serializers.CharField(source='get_type_promotion_display', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    is_valid = serializers.SerializerMethodField()
    resume = serializers.SerializerMethodField()

    class Meta:
        model = Promotion
        fields = [
            'id', 'code', 'nom', 'type_promotion', 'type_promotion_display',
            'produit', 'produit_designation', 'categorie', 'categorie_nom',
            'date_debut', 'date_fin',
            'statut', 'statut_display', 'is_valid',
            'usage_actuel', 'usage_maximum',
            'priorite', 'resume'
        ]

    def get_is_valid(self, obj):
        return obj.is_valid()

    def get_resume(self, obj):
        """Génère un résumé textuel de la promotion"""
        if obj.type_promotion == 'pourcentage':
            return f"-{obj.valeur_pourcentage}%"
        elif obj.type_promotion == 'valeur_fixe':
            symbol = obj.currency.symbol if obj.currency else 'DA'
            return f"-{obj.valeur_fixe} {symbol}"
        elif obj.type_promotion == 'prix_special':
            symbol = obj.currency.symbol if obj.currency else 'DA'
            return f"{obj.prix_special} {symbol}"
        elif obj.type_promotion == 'achetez_x_payez_y':
            return f"Achetez {obj.quantite_achat}, payez {obj.quantite_offerte}"
        elif obj.type_promotion == 'achetez_x_offert_y':
            return f"Achetez {obj.quantite_achat}, {obj.quantite_offerte} offert(s)"
        return obj.nom


class PromotionUsageSerializer(serializers.ModelSerializer):
    """Serializer pour le suivi d'utilisation des promotions"""
    promotion_code = serializers.CharField(source='promotion.code', read_only=True)
    promotion_nom = serializers.CharField(source='promotion.nom', read_only=True)
    client_nom = serializers.CharField(source='client.nom', read_only=True)
    vente_numero = serializers.CharField(source='vente.numero', read_only=True, allow_null=True)

    class Meta:
        model = PromotionUsage
        fields = [
            'id', 'promotion', 'promotion_code', 'promotion_nom',
            'client', 'client_nom',
            'vente', 'vente_numero',
            'date_utilisation', 'montant_economise'
        ]
        read_only_fields = ['date_utilisation']


class PromotionSimulationSerializer(serializers.Serializer):
    """Serializer pour simuler l'application d'une promotion"""
    promotion_id = serializers.IntegerField()
    produit_id = serializers.IntegerField()
    quantite = serializers.IntegerField(min_value=1)
    type_conditionnement = serializers.ChoiceField(
        choices=['unite', 'carton', 'colis', 'palette'],
        default='unite'
    )
    type_prix_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, data):
        # Vérifier que la promotion existe
        try:
            promotion = Promotion.objects.get(id=data['promotion_id'])
            data['promotion'] = promotion
        except Promotion.DoesNotExist:
            raise serializers.ValidationError({'promotion_id': 'Promotion non trouvée.'})

        # Vérifier que le produit existe
        try:
            produit = Produit.objects.get(id=data['produit_id'])
            data['produit'] = produit
        except Produit.DoesNotExist:
            raise serializers.ValidationError({'produit_id': 'Produit non trouvé.'})

        # Vérifier que la promotion s'applique au produit
        if not promotion.is_applicable_to_product(produit):
            raise serializers.ValidationError({
                'promotion_id': 'Cette promotion ne s\'applique pas à ce produit.'
            })

        return data

    def get_simulation_result(self):
        """Calcule le résultat de la simulation"""
        data = self.validated_data
        promotion = data['promotion']
        produit = data['produit']
        quantite = data['quantite']
        type_conditionnement = data['type_conditionnement']

        # Récupérer le prix selon le conditionnement
        prix_unitaire = produit.prixU
        conditionnement = produit.conditionnements.filter(is_active=True).first()

        if type_conditionnement == 'carton' and conditionnement:
            quantite_unites = quantite * conditionnement.unites_par_carton
            prix_base = conditionnement.get_prix_carton_calcule()
        elif type_conditionnement == 'colis' and conditionnement:
            quantite_unites = quantite * conditionnement.get_unites_par_colis()
            prix_base = conditionnement.get_prix_colis_calcule()
        else:
            quantite_unites = quantite
            prix_base = prix_unitaire

        # Prix sans promotion
        prix_total_sans_promo = prix_base * quantite

        # Prix avec promotion
        prix_total_avec_promo = promotion.calculer_prix_promotion(prix_base, quantite)

        # Calcul pour offres spéciales
        offre_speciale = promotion.calculer_offre_speciale(quantite)

        # Économie
        economie = promotion.get_economie(prix_base, quantite)

        return {
            'produit': {
                'id': produit.id,
                'reference': produit.reference,
                'designation': produit.designation,
                'prix_unitaire': float(prix_unitaire)
            },
            'promotion': {
                'id': promotion.id,
                'code': promotion.code,
                'nom': promotion.nom,
                'type': promotion.type_promotion
            },
            'conditionnement': type_conditionnement,
            'quantite_demandee': quantite,
            'quantite_en_unites': quantite_unites,
            'prix_unitaire_base': float(prix_base),
            'prix_total_sans_promotion': float(prix_total_sans_promo),
            'prix_total_avec_promotion': float(prix_total_avec_promo),
            'economie_montant': float(economie['montant']),
            'economie_pourcentage': float(economie['pourcentage']),
            'offre_speciale': {
                'quantite_a_payer': offre_speciale['quantite_a_payer'],
                'quantite_gratuite': offre_speciale['quantite_gratuite'],
                'quantite_totale': offre_speciale['quantite_totale']
            }
        }


# ==========================================
# SERIALIZERS SECTEURS
# ==========================================

class SecteurSerializer(serializers.ModelSerializer):
    """Serializer pour les secteurs géographiques/commerciaux"""
    clients_count = serializers.SerializerMethodField()

    class Meta:
        model = Secteur
        fields = [
            'id', 'company', 'code', 'nom', 'description', 'couleur',
            'is_active', 'clients_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['company', 'created_at', 'updated_at']

    def get_clients_count(self, obj):
        return obj.get_clients_count()
