from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

#####################
#     Company       #
#####################
class Company(models.Model):
    """Entreprise/Organisation - pour isoler les données par tenant"""
    name = models.CharField("Nom de l'entreprise", max_length=200, unique=True)
    code = models.CharField("Code entreprise", max_length=20, unique=True,
                           help_text="Code unique de l'entreprise")
    email = models.EmailField("Email", max_length=100, blank=True)
    telephone = models.CharField("Téléphone", max_length=50, blank=True)
    adresse = models.TextField("Adresse", blank=True)

    # Paramètres fiscaux
    tax_id = models.CharField("Numéro fiscal", max_length=50, blank=True,
                             help_text="Numéro d'identification fiscale (ICE, SIREN, etc.)")

    is_active = models.BooleanField("Entreprise active", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Entreprise"
        verbose_name_plural = "Entreprises"

    def __str__(self):
        return f"{self.code} - {self.name}"


class UserProfile(models.Model):
    """Profil utilisateur lié à une entreprise"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='users',
                               help_text="Entreprise à laquelle l'utilisateur appartient")

    # Rôles dans l'entreprise (optionnel, peut être géré par les groupes Django)
    ROLES = (
        ('admin', 'Administrateur'),
        ('manager', 'Gestionnaire'),
        ('employee', 'Employé'),
    )
    role = models.CharField(max_length=20, choices=ROLES, default='employee')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Profil utilisateur"
        verbose_name_plural = "Profils utilisateurs"

    def __str__(self):
        return f"{self.user.username} - {self.company.name} ({self.role})"


class AuditLog(models.Model):
    actor = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='audit_actions')
    action = models.CharField(max_length=100)
    target_model = models.CharField(max_length=100, blank=True, default='')
    target_id = models.CharField(max_length=100, blank=True, default='')
    target_repr = models.TextField(blank=True, default='')
    metadata = models.TextField(blank=True, default='')  # JSON string
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.created_at} - {self.action} by {self.actor} on {self.target_model}({self.target_id})"
from django.utils import timezone
from decimal import Decimal
import json
from django.contrib.auth.models import User

from django.utils.formats import localize
# Create your models here.

#####################
#   Devises et Taux #
#####################
class Currency(models.Model):
    code = models.CharField(max_length=3, unique=True, help_text="Code ISO 4217 (ex: USD, EUR, MAD)")
    name = models.CharField(max_length=50, help_text="Nom de la devise")
    symbol = models.CharField(max_length=5, help_text="Symbole (ex: $, DA, DH)")
    is_default = models.BooleanField(default=False, help_text="Devise par défaut du système")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['code']
        verbose_name = "Devise"
        verbose_name_plural = "Devises"
    
    def __str__(self):
        return f"{self.code} - {self.name} ({self.symbol})"
    
    def save(self, *args, **kwargs):
        # S'assurer qu'une seule devise est par défaut
        if self.is_default:
            Currency.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)
    
    @classmethod
    def get_default(cls):
        """Retourne la devise par défaut configurée dans les paramètres système.
        Fallback: utilise is_default=True si SystemConfig n'a pas de devise configurée."""
        try:
            from .models import SystemConfig
            config = SystemConfig.get_solo()
            if config and config.default_currency:
                return config.default_currency
        except Exception:
            pass
        # Fallback vers l'ancien système
        return cls.objects.filter(is_default=True).first()

class ExchangeRate(models.Model):
    from_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='rates_from')
    to_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='rates_to')
    rate = models.DecimalField(max_digits=15, decimal_places=6, help_text="Taux de change (1 from_currency = rate to_currency)")
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
        unique_together = ['from_currency', 'to_currency', 'date']
        verbose_name = "Taux de change"
        verbose_name_plural = "Taux de change"
    
    def __str__(self):
        return f"1 {self.from_currency.code} = {self.rate} {self.to_currency.code} ({self.date})"
    
    @classmethod
    def get_rate(cls, from_currency, to_currency, date=None):
        """Obtenir le taux de change entre deux devises à une date donnée"""
        if date is None:
            date = timezone.now().date()
        
        if from_currency == to_currency:
            return Decimal('1.0')
        
        # Chercher le taux direct
        rate = cls.objects.filter(
            from_currency=from_currency,
            to_currency=to_currency,
            date__lte=date,
            is_active=True
        ).first()
        
        if rate:
            return rate.rate
        
        # Chercher le taux inverse
        rate = cls.objects.filter(
            from_currency=to_currency,
            to_currency=from_currency,
            date__lte=date,
            is_active=True
        ).first()
        
        if rate:
            return Decimal('1.0') / rate.rate
        
        # Si pas de taux trouvé, essayer via la devise par défaut
        default_currency = Currency.get_default()
        if default_currency and default_currency != from_currency and default_currency != to_currency:
            rate1 = cls.get_rate(from_currency, default_currency, date)
            rate2 = cls.get_rate(default_currency, to_currency, date)
            if rate1 and rate2:
                return rate1 * rate2
        
        return None
    
    @classmethod
    def convert_amount(cls, amount, from_currency, to_currency, date=None):
        """Convertir un montant d'une devise à une autre"""
        rate = cls.get_rate(from_currency, to_currency, date)
        if rate is not None:
            return amount * rate
        return None

class Administrateur(models.Model):
    nom = models.CharField(max_length=50)
    prenom = models.CharField(max_length=50)
    login = models.CharField(max_length=50)
    password = models.CharField(max_length=50)
    image = models.CharField(max_length=50)
    def __str__(self):
        return '{} {} {}'.format(self.nom, self.prenom, self.login)


"""
class Fournisseur(models.Model):
    libelle = models.CharField(max_length=50)
    email = models.EmailField(max_length=50)
    telephone = models.CharField(max_length=50)
    adresse = models.CharField(max_length=50)

    def __str__(self):
        return '{} by {}'.format(self.libele, self.email)
"""

#####################
#    Fournisseurs  #
#####################
class Fournisseur(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='fournisseurs',
                               null=True, blank=True,
                               help_text="Entreprise propriétaire de ce fournisseur")
    libelle = models.CharField(max_length=50)
    telephone = models.CharField("Téléphone", max_length=20)
    email = models.EmailField("E-Mail", blank=True)
    adresse = models.CharField(max_length=200)

    # Informations fiscales (optionnelles)
    nif = models.CharField("NIF (Numéro d'Identification Fiscale)", max_length=20, blank=True,
                          help_text="Numéro d'Identification Fiscale")
    nis = models.CharField("NIS (Numéro d'Identification Statistique)", max_length=20, blank=True,
                          help_text="Numéro d'Identification Statistique")
    ai = models.CharField("AI (Article d'Imposition)", max_length=20, blank=True,
                         help_text="Article d'Imposition")
    rc = models.CharField("RC (Registre de Commerce)", max_length=20, blank=True,
                         help_text="Numéro du Registre de Commerce")

    class Meta:
        ordering = ["libelle",]

    def __str__(self):
         return '{} {} {} {}'.format(self.libelle, self.telephone, self.email, self.adresse)


#####################
#   Catégories      #
#####################
class Categorie(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='categories',
                               null=True, blank=True,
                               help_text="Entreprise propriétaire de cette catégorie")
    nom = models.CharField(max_length=100)
    description = models.TextField(blank=True, help_text="Description de la catégorie")
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE,
                              related_name='sous_categories', help_text="Catégorie parent pour hiérarchie")
    couleur = models.CharField(max_length=7, default='#007bff', help_text="Couleur d'affichage (hex)")
    icone = models.CharField(max_length=50, default='fa-cube', help_text="Icône Font Awesome")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['nom']
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        unique_together = ['company', 'nom']
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.nom} > {self.nom}"
        return self.nom
    
    def get_full_path(self):
        """Retourne le chemin complet de la catégorie"""
        path = [self.nom]
        parent = self.parent
        while parent:
            path.insert(0, parent.nom)
            parent = parent.parent
        return " > ".join(path)
    
    def get_all_children(self):
        """Retourne toutes les sous-catégories (récursif)"""
        children = list(self.sous_categories.filter(is_active=True))
        for child in list(children):
            children.extend(child.get_all_children())
        return children
    
    def get_products_count(self):
        """Nombre de produits dans cette catégorie et ses sous-catégories"""
        count = self.produits.filter(is_active=True).count()
        for child in self.sous_categories.filter(is_active=True):
            count += child.get_products_count()
        return count

#####################
#   Types de Prix   #
#####################
class CodePrix(models.Model):
    """Codes de prix pour les promotions/périodes (ex: STANDARD, AID, RAMADAN)"""
    code = models.CharField(max_length=20, unique=True, help_text="Code unique (ex: STANDARD, AID, RAMADAN)")
    libelle = models.CharField(max_length=100, help_text="Libellé du code de prix")
    description = models.TextField(blank=True, help_text="Description du code de prix")
    date_debut = models.DateField("Date début", null=True, blank=True, help_text="Date de début de validité")
    date_fin = models.DateField("Date fin", null=True, blank=True, help_text="Date de fin de validité")
    ordre = models.IntegerField(default=0, help_text="Ordre d'affichage")
    is_default = models.BooleanField(default=False, help_text="Code de prix par défaut")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['ordre', 'libelle']
        verbose_name = "Code de prix"
        verbose_name_plural = "Codes de prix"

    def __str__(self):
        return f"{self.code} - {self.libelle}"

    def save(self, *args, **kwargs):
        if self.is_default:
            CodePrix.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_default(cls):
        return cls.objects.filter(is_default=True, is_active=True).first()


class TypePrix(models.Model):
    """Types de prix par client : Détail, Supérette, Gros, etc."""
    code = models.CharField(max_length=20, unique=True, help_text="Code du type de prix (ex: DETAIL, SUPERETTE, GROS)")
    libelle = models.CharField(max_length=100, help_text="Libellé du type de prix")
    description = models.TextField(blank=True, help_text="Description du type de prix")
    ordre = models.IntegerField(default=0, help_text="Ordre d'affichage")
    is_default = models.BooleanField(default=False, help_text="Type de prix par défaut")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['ordre', 'libelle']
        verbose_name = "Type de prix"
        verbose_name_plural = "Types de prix"

    def __str__(self):
        return f"{self.code} - {self.libelle}"

    def save(self, *args, **kwargs):
        if self.is_default:
            TypePrix.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_default(cls):
        return cls.objects.filter(is_default=True, is_active=True).first()

#####################
#    Produits       #
#####################
class Produit(models.Model):
    UNITES_MESURE = (
        ('piece', 'Pièce'),
        ('kg', 'Kilogramme'),
        ('g', 'Gramme'),
        ('l', 'Litre'),
        ('ml', 'Millilitre'),
        ('m', 'Mètre'),
        ('cm', 'Centimètre'),
        ('m2', 'Mètre carré'),
        ('m3', 'Mètre cube'),
    )

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='produits',
                               null=True, blank=True,
                               help_text="Entreprise propriétaire de ce produit")
    reference = models.CharField(max_length=50)
    code_barre = models.CharField("Code-barres", max_length=64)
    designation = models.CharField(max_length=100)
    description = models.TextField(blank=True, help_text="Description détaillée du produit")
    
    # Catégorisation
    categorie = models.ForeignKey(Categorie, on_delete=models.PROTECT, related_name='produits',
                                 help_text="Catégorie du produit")
    
    # Prix et devise
    prixU = models.DecimalField("Prix unitaire", max_digits=8, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, null=True, blank=True, 
                                help_text="Devise du prix (si vide, utilise la devise par défaut)")
    
    # Stock et alertes
    quantite = models.IntegerField("Quantité en stock", default=0,
                                   help_text="Quantité initiale en stock (optionnel)")
    seuil_alerte = models.IntegerField("Seuil d'alerte", default=10,
                                      help_text="Niveau de stock déclenchant une alerte")
    seuil_critique = models.IntegerField("Seuil critique", default=5,
                                        help_text="Niveau de stock critique (urgent)")
    
    # Caractéristiques physiques
    unite_mesure = models.CharField("Unité de mesure", max_length=10, choices=UNITES_MESURE, default='piece')
    poids = models.DecimalField("Poids (kg)", max_digits=8, decimal_places=3, null=True, blank=True)
    dimensions = models.CharField("Dimensions (LxlxH)", max_length=50, blank=True)
    
    # Gestion
    fournisseur = models.ForeignKey(Fournisseur, on_delete=models.SET_NULL,
                                    null=True, blank=True,
                                    help_text="Fournisseur principal du produit (optionnel)")
    is_active = models.BooleanField("Produit actif", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['reference']
        verbose_name = "Produit"
        verbose_name_plural = "Produits"
        unique_together = [
            ['company', 'reference'],
            ['company', 'code_barre']
        ]
    
    def __str__(self):
        currency_symbol = self.currency.symbol if self.currency else Currency.get_default().symbol if Currency.get_default() else 'DA'
        stock_status = self.get_stock_status_display()
        return f'{self.reference} - {self.designation} ({self.quantite} {self.get_unite_mesure_display()}) {stock_status}'
    
    def get_price_in_currency(self, target_currency, date=None):
        """Obtenir le prix du produit dans une devise spécifique"""
        product_currency = self.currency or Currency.get_default()
        if not product_currency:
            return self.prixU
        
        converted_amount = ExchangeRate.convert_amount(
            self.prixU, product_currency, target_currency, date
        )
        return converted_amount if converted_amount is not None else self.prixU
    
    # Méthodes de gestion des alertes stock
    def is_low_stock(self):
        """Vérifie si le stock est en alerte (bas)"""
        return self.quantite <= self.seuil_alerte and self.quantite > self.seuil_critique
    
    def is_critical_stock(self):
        """Vérifie si le stock est critique (très bas)"""
        return self.quantite <= self.seuil_critique
    
    def is_out_of_stock(self):
        """Vérifie si le produit est en rupture de stock"""
        return self.quantite <= 0
    
    def get_stock_status(self):
        """Retourne le statut du stock"""
        if self.is_out_of_stock():
            return 'out_of_stock'
        elif self.is_critical_stock():
            return 'critical'
        elif self.is_low_stock():
            return 'low'
        else:
            return 'normal'
    
    def get_stock_status_display(self):
        """Retourne le libellé du statut du stock"""
        status = self.get_stock_status()
        statuses = {
            'out_of_stock': '🔴 RUPTURE',
            'critical': '🟠 CRITIQUE', 
            'low': '🟡 ALERTE',
            'normal': '🟢 OK'
        }
        return statuses.get(status, 'OK')
    
    def get_stock_class(self):
        """Retourne la classe CSS pour l'affichage du stock"""
        status = self.get_stock_status()
        classes = {
            'out_of_stock': 'danger',
            'critical': 'warning',
            'low': 'info',
            'normal': 'success'
        }
        return classes.get(status, 'secondary')
    
    def get_stock_percentage(self):
        """Calcule le pourcentage de stock par rapport au seuil d'alerte"""
        if self.seuil_alerte <= 0:
            return 100
        return min(100, (self.quantite / self.seuil_alerte) * 100)
    
    def get_reorder_suggestion(self):
        """Suggère une quantité de réapprovisionnement"""
        if self.is_critical_stock() or self.is_out_of_stock():
            # Suggestion : 3 fois le seuil d'alerte
            return max(self.seuil_alerte * 3, 50)
        elif self.is_low_stock():
            # Suggestion : 2 fois le seuil d'alerte
            return max(self.seuil_alerte * 2, 30)
        return 0

#####################
#   Prix Produits   #
#####################
class PrixProduit(models.Model):
    """Prix multiples pour un produit selon le code de prix et type de client"""
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE, related_name='prix_multiples',
                                help_text="Produit concerné")
    code_prix = models.ForeignKey(CodePrix, on_delete=models.PROTECT, related_name='prix',
                                  null=True, blank=True,
                                  help_text="Code de prix (STANDARD, AID, RAMADAN, etc.)")
    type_prix = models.ForeignKey(TypePrix, on_delete=models.PROTECT, related_name='prix',
                                  help_text="Type de client (Détail, Supérette, Gros)")
    prix = models.DecimalField("Prix", max_digits=10, decimal_places=2,
                               help_text="Montant du prix pour cette combinaison")
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, null=True, blank=True,
                                help_text="Devise du prix (si vide, hérite de la devise du produit)")

    # Optionnel : quantité minimum pour ce prix
    quantite_min = models.IntegerField("Quantité minimum", default=1,
                                       help_text="Quantité minimum pour appliquer ce prix")

    is_active = models.BooleanField("Prix actif", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['produit', 'code_prix__ordre', 'type_prix__ordre']
        verbose_name = "Prix produit"
        verbose_name_plural = "Prix produits"
        unique_together = ['produit', 'code_prix', 'type_prix']  # Un seul prix par combinaison produit/code/type

    def __str__(self):
        currency_symbol = self.currency.symbol if self.currency else self.produit.currency.symbol if self.produit.currency else '€'
        code_label = self.code_prix.code if self.code_prix else 'STD'
        return f"{self.produit.reference} - {code_label}/{self.type_prix.code}: {self.prix} {currency_symbol}"

    def is_valid_now(self):
        """Vérifie si ce prix est valide aujourd'hui (basé sur les dates du code_prix)"""
        if not self.is_active:
            return False
        # Si pas de code_prix, c'est un prix standard toujours valide
        if not self.code_prix:
            return True
        if not self.code_prix.is_active:
            return False
        today = timezone.now().date()
        if self.code_prix.date_debut and today < self.code_prix.date_debut:
            return False
        if self.code_prix.date_fin and today > self.code_prix.date_fin:
            return False
        return True

    def get_effective_currency(self):
        """Retourne la devise effective (propre ou héritée du produit)"""
        return self.currency or self.produit.currency or Currency.get_default()


class Client(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='clients',
                               null=True, blank=True,
                               help_text="Entreprise propriétaire de ce client")
    secteur = models.ForeignKey(
        'Secteur',
        on_delete=models.SET_NULL,
        related_name='clients',
        null=True,
        blank=True,
        help_text="Secteur géographique/commercial du client"
    )
    nom = models.CharField(max_length=50)
    prenom = models.CharField(max_length=50)
    email = models.EmailField(max_length=50)
    telephone = models.CharField(max_length=50)
    adresse = models.CharField(max_length=50)
    lat = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True,
                             help_text="Latitude GPS")
    lng = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True,
                             help_text="Longitude GPS")

    # Type de prix pour les promotions
    type_prix = models.ForeignKey(
        'TypePrix',
        on_delete=models.SET_NULL,
        related_name='clients',
        null=True,
        blank=True,
        help_text="Type de prix appliqué à ce client (Détail, Supérette, Gros)"
    )

    # Informations fiscales (optionnelles)
    nif = models.CharField("NIF (Numéro d'Identification Fiscale)", max_length=20, blank=True,
                          help_text="Numéro d'Identification Fiscale")
    nis = models.CharField("NIS (Numéro d'Identification Statistique)", max_length=20, blank=True,
                          help_text="Numéro d'Identification Statistique")
    ai = models.CharField("AI (Article d'Imposition)", max_length=20, blank=True,
                         help_text="Article d'Imposition")
    rc = models.CharField("RC (Registre de Commerce)", max_length=20, blank=True,
                         help_text="Numéro du Registre de Commerce")

    def __str__(self):
        return '{} {}'.format(self.nom, self.prenom)

class Achat(models.Model):
    UNITE_CHOICES = (
        ('piece', 'Pièce'),
        ('carton', 'Carton'),
    )

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='achats',
                               null=True, blank=True,
                               help_text="Entreprise propriétaire de cet achat")
    date_Achat = models.DateField(default=timezone.now)
    date_expiration = models.DateField("Date d'expiration", null=True, blank=True)

    # Type d'unité d'achat
    unite_achat = models.CharField(
        "Unité d'achat",
        max_length=10,
        choices=UNITE_CHOICES,
        default='piece',
        help_text="Unité d'achat: pièce ou carton"
    )

    # Quantité achetée (en cartons ou pièces selon unite_achat)
    quantite = models.IntegerField()

    # Nombre de pièces par carton (utilisé seulement si unite_achat='carton')
    pieces_par_carton = models.IntegerField(
        "Pièces par carton",
        default=1,
        help_text="Nombre de pièces contenues dans un carton"
    )

    # Prix d'achat unitaire (par carton ou par pièce selon unite_achat)
    prix_achat = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    fournisseur = models.ForeignKey(Fournisseur, on_delete=models.CASCADE, null=True, blank=True)
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    warehouse = models.ForeignKey('Warehouse', on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='achats', help_text="Entrepôt de destination pour cet achat")

    def get_quantite_pieces(self):
        """Retourne la quantité totale en pièces"""
        if self.unite_achat == 'carton':
            return self.quantite * self.pieces_par_carton
        return self.quantite

    def get_prix_unitaire_piece(self):
        """Retourne le prix unitaire par pièce"""
        if self.unite_achat == 'carton':
            return self.prix_achat / self.pieces_par_carton if self.pieces_par_carton > 0 else 0
        return self.prix_achat

    def get_prix_total(self):
        """Retourne le prix total de l'achat"""
        return self.quantite * self.prix_achat

    def __str__(self):
        unite_display = dict(self.UNITE_CHOICES).get(self.unite_achat, 'unités')
        return '{} - {} {}'.format(self.date_Achat, self.quantite, unite_display)

    class Meta:
        ordering = ['date_Achat',]

#####################
# Bons de livraison #
#####################
class BonLivraison(models.Model):
    STATUTS = (
        ('draft', 'Brouillon'),
        ('validated', 'Validé'),
        ('canceled', 'Annulé'),
    )
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='bons_livraison',
                               null=True, blank=True,
                               help_text="Entreprise propriétaire de ce bon de livraison")
    numero = models.CharField(max_length=50)
    date_creation = models.DateField(default=timezone.now)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='bons')
    statut = models.CharField(max_length=10, choices=STATUTS, default='draft')
    observations = models.TextField(blank=True)

    class Meta:
        ordering = ['-date_creation', 'numero']
        unique_together = ['company', 'numero']

    def __str__(self):
        return f"BL {self.numero} - {self.client} ({self.statut})"

class LigneLivraison(models.Model):
    bon = models.ForeignKey(BonLivraison, on_delete=models.CASCADE, related_name='lignes')
    produit = models.ForeignKey(Produit, on_delete=models.PROTECT)
    quantite = models.PositiveIntegerField()
    prixU_snapshot = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.produit} x {self.quantite} (BL {self.bon.numero})"

#####################
# Factures clients  #
#####################
class Facture(models.Model):
    STATUTS = (
        ('draft', 'Brouillon'),
        ('issued', 'Émise'),
        ('paid', 'Payée'),
        ('canceled', 'Annulée'),
    )
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='factures',
                               null=True, blank=True,
                               help_text="Entreprise propriétaire de cette facture")
    numero = models.CharField(max_length=50)
    date_emission = models.DateField(default=timezone.now)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='factures')
    bon_livraison = models.ForeignKey(BonLivraison, on_delete=models.SET_NULL, null=True, blank=True, related_name='factures')
    statut = models.CharField(max_length=10, choices=STATUTS, default='draft')
    tva_rate = models.DecimalField(max_digits=4, decimal_places=2, default=20.00)  # 20% par défaut
    total_ht = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_tva = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_ttc = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ['-date_emission', 'numero']
        unique_together = ['company', 'numero']

    def __str__(self):
        return f"FA {self.numero} - {self.client} ({self.statut})"

    def recompute_totals(self):
        from decimal import Decimal
        ht = sum((l.prixU_snapshot * l.quantite for l in self.lignes.all()), Decimal('0'))
        tva = (ht * (self.tva_rate / Decimal('100'))).quantize(Decimal('0.01'))
        ttc = ht + tva
        self.total_ht = ht
        self.total_tva = tva
        self.total_ttc = ttc
        return ht, tva, ttc

class LigneFacture(models.Model):
    facture = models.ForeignKey(Facture, on_delete=models.CASCADE, related_name='lignes')
    produit = models.ForeignKey(Produit, on_delete=models.PROTECT)
    designation = models.CharField(max_length=100)
    quantite = models.PositiveIntegerField()
    prixU_snapshot = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.designation} x {self.quantite} (FA {self.facture.numero})"

############################
# Inventaire et mouvements #
############################
class Warehouse(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='warehouses',
                               null=True, blank=True,
                               help_text="Entreprise propriétaire de cet entrepôt")
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Entrepôt'
        verbose_name_plural = 'Entrepôts'
        unique_together = [
            ['company', 'code'],
            ['company', 'name']
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

class ProductStock(models.Model):
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE, related_name='stocks')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stocks')
    quantity = models.IntegerField(default=0)

    class Meta:
        unique_together = ('produit', 'warehouse')

    def __str__(self):
        return f"{self.produit.reference} @ {self.warehouse.code}: {self.quantity}"

class StockMove(models.Model):
    SOURCE_CHOICES = (
        ('BL', 'Bon de livraison'),
        ('BC', 'Bon de commande'),
        ('ACHAT', 'Achat'),
        ('VENTE', 'Vente'),
        ('INV', 'Inventaire'),
        ('CORR', 'Correction'),
        ('PERTE', 'Perte'),
        ('CASSE', 'Casse'),
        ('EXP', 'Expiration'),
        ('TRANS', 'Transfert'),
        ('SAMPLE', 'Échantillon'),
        ('DON', 'Don'),
        ('CONS', 'Consommation interne'),
        ('RETOUR', 'Retour fournisseur'),
        ('AUTRE', 'Autre'),
    )
    produit = models.ForeignKey(Produit, on_delete=models.PROTECT, related_name='mouvements')
    warehouse = models.ForeignKey('Warehouse', on_delete=models.SET_NULL, null=True, blank=True, related_name='mouvements')
    delta = models.IntegerField()  # + entrée, - sortie
    source = models.CharField(max_length=15, choices=SOURCE_CHOICES, default='AUTRE')
    ref_id = models.CharField(max_length=50, blank=True, default='')  # id de la pièce liée
    date = models.DateTimeField(default=timezone.now)
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['-date', 'id']

    def __str__(self):
        return f"{self.date.date()} {self.produit.reference} {self.delta} ({self.source} #{self.ref_id})"

class InventorySession(models.Model):
    STATUTS = (
        ('draft', 'Brouillon'),
        ('in_progress', 'En cours'),
        ('validated', 'Validé'),
        ('canceled', 'Annulé'),
    )
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='inventory_sessions',
                               null=True, blank=True,
                               help_text="Entreprise propriétaire de cette session d'inventaire")
    numero = models.CharField(max_length=50)
    date = models.DateField(default=timezone.now)
    statut = models.CharField(max_length=15, choices=STATUTS, default='draft')
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, 
                                 related_name='inventory_sessions_created',
                                 help_text="Utilisateur qui a créé la session d'inventaire")
    validated_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True,
                                   related_name='inventory_sessions_validated',
                                   help_text="Utilisateur qui a validé l'inventaire")
    total_products = models.IntegerField(default=0, help_text="Nombre total de produits à inventorier")
    completed_products = models.IntegerField(default=0, help_text="Nombre de produits déjà comptés")
    completion_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, 
                                              help_text="Pourcentage de completion de l'inventaire")

    class Meta:
        ordering = ['-date', 'numero']
        unique_together = ['company', 'numero']

    def __str__(self):
        return f"INV {self.numero} ({self.statut}) - {self.completion_percentage}%"
    
    def update_completion_percentage(self):
        """Met à jour le pourcentage de completion de l'inventaire"""
        total_lines = self.lignes.count()
        completed_lines = self.lignes.filter(counted_qty__isnull=False).count()
        
        self.total_products = total_lines
        self.completed_products = completed_lines
        
        if total_lines > 0:
            self.completion_percentage = (completed_lines / total_lines) * 100
        else:
            self.completion_percentage = 0
        
        # Mettre à jour le statut automatiquement
        if self.completion_percentage == 100 and self.statut == 'in_progress':
            # Ne pas changer automatiquement en validé, mais garder en cours
            pass
        elif self.completion_percentage > 0 and self.statut == 'draft':
            self.statut = 'in_progress'
        
        self.save(update_fields=['total_products', 'completed_products', 'completion_percentage', 'statut'])
    
    def can_be_validated(self):
        """Vérifie si l'inventaire peut être validé"""
        return self.completion_percentage == 100 and self.statut in ['in_progress', 'draft']
    
    def get_missing_products(self):
        """Retourne la liste des produits non encore comptés"""
        return self.lignes.filter(counted_qty__isnull=True)

class InventoryLine(models.Model):
    session = models.ForeignKey(InventorySession, on_delete=models.CASCADE, related_name='lignes')
    produit = models.ForeignKey(Produit, on_delete=models.PROTECT)
    counted_qty = models.IntegerField(null=True, blank=True)  # quantité comptée physiquement
    snapshot_qty = models.IntegerField()  # quantité théorique au moment du comptage
    counted_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True,
                                 related_name='inventory_lines_counted',
                                 help_text="Utilisateur qui a compté ce produit")
    counted_at = models.DateTimeField(null=True, blank=True, 
                                    help_text="Date et heure du comptage")

    def __str__(self):
        if self.counted_qty is not None:
            return f"{self.produit.reference} compté {self.counted_qty} (théorique {self.snapshot_qty})"
        else:
            return f"{self.produit.reference} non compté (théorique {self.snapshot_qty})"
    
    def save(self, *args, **kwargs):
        # Mettre à jour counted_at si counted_qty vient d'être défini
        if self.counted_qty is not None and not self.counted_at:
            from django.utils import timezone
            self.counted_at = timezone.now()
        
        super().save(*args, **kwargs)
        
        # Mettre à jour le pourcentage de la session parent
        self.session.update_completion_percentage()
    
    def get_variance(self):
        """Retourne l'écart entre quantité comptée et théorique"""
        if self.counted_qty is not None:
            return self.counted_qty - self.snapshot_qty
        return None
    
    def is_completed(self):
        """Vérifie si ce produit a été compté"""
        return self.counted_qty is not None

#####################
#      Ventes       #
#####################
class SystemConfig(models.Model):
    """Configuration système (singleton) pour paramètres globaux"""
    default_warehouse = models.ForeignKey('Warehouse', on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name='as_default_for')
    default_currency = models.ForeignKey('Currency', on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='as_default_currency_for')

    # Paramètres généraux
    LANGUAGE_CHOICES = [
        ('fr', 'Français'),
        ('en', 'English'),
        ('ar', 'العربية'),
    ]
    language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default='fr',
                               help_text="Langue de l'interface")

    # Paramètres de caisse
    auto_print_ticket = models.BooleanField(default=False,
                                           help_text="Générer automatiquement le ticket de caisse")
    ticket_footer_message = models.TextField(blank=True,
                                            help_text="Message à afficher au pied du ticket (merci, mentions légales, etc.)")
    ticket_company_name = models.CharField(max_length=200, blank=True,
                                          help_text="Nom de l'entreprise à afficher sur le ticket")
    ticket_company_address = models.TextField(blank=True,
                                             help_text="Adresse de l'entreprise")
    ticket_company_phone = models.CharField(max_length=50, blank=True,
                                           help_text="Téléphone de l'entreprise")

    def save(self, *args, **kwargs):
        # enforce singleton id=1
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @classmethod
    def ensure_default_warehouse(cls):
        cfg = cls.get_solo()
        if cfg.default_warehouse and cfg.default_warehouse.is_active:
            return cfg.default_warehouse
        # try to find any active warehouse
        w = Warehouse.objects.filter(is_active=True).first()
        if not w:
            # create a sensible default
            base_code = 'DEF'
            code = base_code
            i = 1
            while Warehouse.objects.filter(code=code).exists():
                i += 1
                code = f"{base_code}{i}"
            w = Warehouse.objects.create(name='Entrepôt par défaut', code=code, is_active=True)
        cfg.default_warehouse = w
        cfg.save(update_fields=['default_warehouse'])
        return w


class Vente(models.Model):
    STATUTS = (
        ('draft', 'Brouillon'),
        ('completed', 'Terminée'),
        ('canceled', 'Annulée'),
    )
    TYPES_PAIEMENT = (
        ('cash', 'Espèces'),
        ('card', 'Carte bancaire'),
        ('check', 'Chèque'),
        ('transfer', 'Virement'),
        ('credit', 'Crédit'),
    )

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='ventes',
                               null=True, blank=True,
                               help_text="Entreprise propriétaire de cette vente")
    numero = models.CharField(max_length=50)
    date_vente = models.DateTimeField(default=timezone.now)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='ventes')
    type_paiement = models.CharField(max_length=10, choices=TYPES_PAIEMENT, default='cash')
    statut = models.CharField(max_length=10, choices=STATUTS, default='draft')
    
    # Entrepôt d'où la vente est effectuée
    warehouse = models.ForeignKey('Warehouse', on_delete=models.SET_NULL, null=True, blank=True, related_name='ventes', help_text="Entrepôt de sortie pour cette vente")
    
    # Gestion des devises
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, null=True, blank=True,
                                help_text="Devise de la vente (si vide, utilise la devise par défaut)")
    exchange_rate_snapshot = models.DecimalField(max_digits=15, decimal_places=6, null=True, blank=True,
                                               help_text="Taux de change figé au moment de la vente")
    
    total_ht = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_ttc = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remise_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    observations = models.TextField(blank=True)
    
    # Liens vers autres documents
    bon_livraison = models.ForeignKey(BonLivraison, on_delete=models.SET_NULL, null=True, blank=True, related_name='ventes')
    facture = models.ForeignKey(Facture, on_delete=models.SET_NULL, null=True, blank=True, related_name='ventes')

    class Meta:
        ordering = ['-date_vente', 'numero']
        unique_together = ['company', 'numero']

    def __str__(self):
        currency_symbol = self.currency.symbol if self.currency else Currency.get_default().symbol if Currency.get_default() else 'DA'
        return f"Vente {self.numero} - {self.client} ({self.total_ttc} {currency_symbol}) ({self.statut})"

    def get_sale_currency(self):
        """Obtenir la devise de la vente ou la devise par défaut"""
        return self.currency or Currency.get_default()

    def recompute_totals(self):
        """Recalculer les totaux en tenant compte des conversions de devises"""
        sale_currency = self.get_sale_currency()
        ht = Decimal('0')
        
        for ligne in self.lignes.all():
            # Convertir le prix de chaque ligne dans la devise de la vente
            if ligne.currency and ligne.currency != sale_currency:
                converted_price = ExchangeRate.convert_amount(
                    ligne.prixU_snapshot, ligne.currency, sale_currency, self.date_vente.date()
                )
                if converted_price is not None:
                    ligne_total = converted_price * ligne.quantite
                else:
                    ligne_total = ligne.prixU_snapshot * ligne.quantite
            else:
                ligne_total = ligne.prixU_snapshot * ligne.quantite
            
            ht += ligne_total
        
        # Appliquer la remise
        if self.remise_percent > 0:
            ht = ht * (Decimal('100') - self.remise_percent) / Decimal('100')
        
        self.total_ht = ht
        self.total_ttc = ht  # Simplifié, pas de TVA pour les ventes directes
        return ht

    def get_total_in_currency(self, target_currency):
        """Obtenir le total de la vente dans une devise spécifique"""
        sale_currency = self.get_sale_currency()
        if sale_currency == target_currency:
            return self.total_ttc
        
        converted_amount = ExchangeRate.convert_amount(
            self.total_ttc, sale_currency, target_currency, self.date_vente.date()
        )
        return converted_amount if converted_amount is not None else self.total_ttc

    def get_montant_paye(self):
        """Calculer le montant total payé pour cette vente"""
        return self.paiements.aggregate(total=models.Sum('montant'))['total'] or Decimal('0')

    def get_reste_a_payer(self):
        """Calculer le reste à payer"""
        return self.total_ttc - self.get_montant_paye()

    def is_paye(self):
        """Vérifier si la vente est entièrement payée"""
        return self.get_reste_a_payer() <= 0

class LigneVente(models.Model):
    vente = models.ForeignKey(Vente, on_delete=models.CASCADE, related_name='lignes')
    produit = models.ForeignKey(Produit, on_delete=models.PROTECT)
    designation = models.CharField(max_length=100)
    quantite = models.PositiveIntegerField()
    prixU_snapshot = models.DecimalField(max_digits=8, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, null=True, blank=True,
                                help_text="Devise du prix unitaire (héritée du produit)")

    # Champs pour les promotions
    promotion = models.ForeignKey(
        'Promotion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lignes_vente',
        help_text="Promotion appliquée à cette ligne"
    )
    prix_original = models.DecimalField(
        "Prix original (avant promo)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Prix unitaire avant application de la promotion"
    )
    remise_promo = models.DecimalField(
        "Remise promotion",
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Montant de la remise appliquée par la promotion"
    )
    quantite_offerte = models.PositiveIntegerField(
        "Quantité offerte",
        default=0,
        help_text="Quantité offerte gratuitement (pour promos X+Y)"
    )

    def __str__(self):
        currency_symbol = self.currency.symbol if self.currency else self.vente.get_sale_currency().symbol if self.vente.get_sale_currency() else '€'
        return f"{self.designation} x {self.quantite} à {self.prixU_snapshot} {currency_symbol} (Vente {self.vente.numero})"
    
    def get_total_in_sale_currency(self):
        """Obtenir le total de la ligne dans la devise de la vente"""
        sale_currency = self.vente.get_sale_currency()

        if self.currency and self.currency != sale_currency:
            converted_price = ExchangeRate.convert_amount(
                self.prixU_snapshot, self.currency, sale_currency, self.vente.date_vente.date()
            )
            if converted_price is not None:
                return converted_price * self.quantite

        return self.prixU_snapshot * self.quantite


class PaiementVente(models.Model):
    """
    Paiements effectués pour une vente.
    Permet de gérer les paiements partiels et multiples pour une même vente.
    """
    MOYENS_PAIEMENT = (
        ('cash', 'Espèces'),
        ('card', 'Carte bancaire'),
        ('check', 'Chèque'),
        ('transfer', 'Virement'),
        ('other', 'Autre'),
    )

    vente = models.ForeignKey(Vente, on_delete=models.CASCADE, related_name='paiements')
    date_paiement = models.DateTimeField(default=timezone.now, help_text="Date du paiement")
    montant = models.DecimalField(max_digits=12, decimal_places=2, help_text="Montant payé")
    moyen_paiement = models.CharField(max_length=10, choices=MOYENS_PAIEMENT, default='cash')
    reference = models.CharField(max_length=100, blank=True, help_text="Numéro de chèque, référence de virement, etc.")
    notes = models.TextField(blank=True, help_text="Notes additionnelles sur le paiement")
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='paiements_crees')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_paiement']
        verbose_name = "Paiement de vente"
        verbose_name_plural = "Paiements de ventes"

    def __str__(self):
        return f"Paiement {self.montant} DA pour {self.vente.numero} - {self.date_paiement.strftime('%d/%m/%Y')}"


# ==========================================
# MODULE DE DISTRIBUTION
# ==========================================

class Livreur(models.Model):
    """
    Livreur/Chauffeur pour la distribution
    """
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='livreurs',
        null=True,
        blank=True,
        help_text="Entreprise à laquelle appartient le livreur"
    )

    nom = models.CharField("Nom", max_length=100)
    prenom = models.CharField("Prénom", max_length=100)
    telephone = models.CharField("Téléphone", max_length=20)
    email = models.EmailField("Email", max_length=100, blank=True)
    adresse = models.TextField("Adresse", blank=True)

    # Informations du véhicule
    vehicule_type = models.CharField("Type de véhicule", max_length=100, blank=True,
                                    help_text="Ex: Camion, Camionnette, Moto")
    vehicule_marque = models.CharField("Marque du véhicule", max_length=100, blank=True)
    immatriculation = models.CharField("Immatriculation", max_length=20, blank=True)
    capacite_charge = models.DecimalField("Capacité de charge (kg)", max_digits=10, decimal_places=2,
                                         null=True, blank=True)

    # Permis et documents
    numero_permis = models.CharField("Numéro de permis", max_length=50, blank=True)
    date_expiration_permis = models.DateField("Date d'expiration du permis", null=True, blank=True)

    # Statut
    is_active = models.BooleanField("Actif", default=True)
    is_disponible = models.BooleanField("Disponible", default=True,
                                       help_text="Indique si le livreur est disponible pour une tournée")

    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nom', 'prenom']
        verbose_name = "Livreur"
        verbose_name_plural = "Livreurs"
        unique_together = [['company', 'telephone']]

    def __str__(self):
        return f"{self.nom} {self.prenom} - {self.vehicule_type or 'Livreur'}"

    def get_full_name(self):
        return f"{self.nom} {self.prenom}"


class Tournee(models.Model):
    """
    Tournée de livraison planifiée ou en cours
    """
    STATUT_CHOICES = (
        ('planifiee', 'Planifiée'),
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
        ('annulee', 'Annulée'),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='tournees',
        null=True,
        blank=True,
        help_text="Entreprise à laquelle appartient la tournée"
    )

    numero = models.CharField("Numéro de tournée", max_length=50, unique=True,
                             help_text="Généré automatiquement (ex: TOUR-20250107-001)")
    date = models.DateField("Date de la tournée")

    # Livreur assigné
    livreur = models.ForeignKey(
        Livreur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tournees',
        help_text="Livreur assigné à cette tournée"
    )

    # Entrepôt de départ
    warehouse = models.ForeignKey(
        'Warehouse',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tournees',
        help_text="Entrepôt de départ de la tournée"
    )

    # Horaires
    heure_depart_prevue = models.TimeField("Heure de départ prévue")
    heure_depart_reelle = models.TimeField("Heure de départ réelle", null=True, blank=True)
    heure_retour_prevue = models.TimeField("Heure de retour prévue", null=True, blank=True)
    heure_retour_reelle = models.TimeField("Heure de retour réelle", null=True, blank=True)

    # Statut
    statut = models.CharField("Statut", max_length=20, choices=STATUT_CHOICES, default='planifiee')

    # Code de prix à utiliser pour les ventes de cette tournée
    code_prix = models.ForeignKey(
        CodePrix,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tournees',
        help_text="Code de prix à utiliser pour les ventes (STANDARD, AID, RAMADAN, etc.)"
    )

    # Informations complémentaires
    distance_km = models.DecimalField("Distance totale (km)", max_digits=10, decimal_places=2,
                                     null=True, blank=True)
    commentaire = models.TextField("Commentaire", blank=True)

    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = "Tournée"
        verbose_name_plural = "Tournées"
        unique_together = [['company', 'numero']]
        permissions = [
            ('edit_tournee_en_cours', 'Peut modifier une tournée en cours'),
        ]

    def __str__(self):
        return f"{self.numero} - {self.date} ({self.get_statut_display()})"

    def get_nombre_arrets(self):
        """Retourne le nombre d'arrêts dans la tournée"""
        return self.arrets.count()

    def get_arrets_livres(self):
        """Retourne le nombre d'arrêts livrés avec succès"""
        return self.arrets.filter(statut='livre').count()

    def get_taux_reussite(self):
        """Calcule le taux de réussite de la tournée"""
        total = self.get_nombre_arrets()
        if total == 0:
            return 0
        livres = self.get_arrets_livres()
        return round((livres / total) * 100, 2)


class ArretLivraison(models.Model):
    """
    Arrêt de livraison dans une tournée
    """
    STATUT_CHOICES = (
        ('en_attente', 'En attente'),
        ('en_cours', 'En cours'),
        ('livre', 'Livré'),
        ('echec', 'Échec'),
        ('reporte', 'Reporté'),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='arrets_livraison',
        null=True,
        blank=True,
        help_text="Entreprise à laquelle appartient l'arrêt"
    )

    # Tournée
    tournee = models.ForeignKey(
        Tournee,
        on_delete=models.CASCADE,
        related_name='arrets',
        help_text="Tournée à laquelle appartient cet arrêt"
    )

    # Documents de livraison
    bon_livraison = models.ForeignKey(
        BonLivraison,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='arrets_tournee',
        help_text="Bon de livraison associé"
    )

    vente = models.ForeignKey(
        Vente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='arrets_tournee',
        help_text="Vente associée"
    )

    # Client
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='arrets_livraison',
        help_text="Client destinataire"
    )

    # Ordre et planification
    ordre = models.PositiveIntegerField("Ordre dans la tournée",
                                       help_text="Ordre de passage (1, 2, 3...)")
    heure_prevue = models.TimeField("Heure prévue")
    heure_arrivee = models.TimeField("Heure d'arrivée", null=True, blank=True)
    heure_depart = models.TimeField("Heure de départ", null=True, blank=True)

    # Adresse de livraison
    adresse_livraison = models.TextField("Adresse de livraison",
                                        help_text="Adresse complète de livraison")

    # Statut et résultat
    statut = models.CharField("Statut", max_length=20, choices=STATUT_CHOICES, default='en_attente')

    # Signature et confirmation
    signature_client = models.TextField("Signature client (base64)", blank=True,
                                       help_text="Signature électronique du client")
    nom_recepteur = models.CharField("Nom du récepteur", max_length=200, blank=True,
                                    help_text="Nom de la personne qui a réceptionné")

    # Commentaires et problèmes
    commentaire = models.TextField("Commentaire", blank=True)
    raison_echec = models.TextField("Raison de l'échec", blank=True,
                                   help_text="Si statut = échec, raison de l'échec")

    # Photo de preuve (optionnel)
    photo_livraison = models.TextField("Photo de livraison (base64)", blank=True,
                                      help_text="Photo de preuve de livraison")

    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['tournee', 'ordre']
        verbose_name = "Arrêt de livraison"
        verbose_name_plural = "Arrêts de livraison"
        unique_together = [['tournee', 'ordre']]

    def __str__(self):
        return f"Arrêt #{self.ordre} - {self.client.nom} ({self.get_statut_display()})"

    def get_duree_arret(self):
        """Calcule la durée de l'arrêt en minutes"""
        if self.heure_arrivee and self.heure_depart:
            from datetime import datetime, timedelta
            arrivee = datetime.combine(datetime.today(), self.heure_arrivee)
            depart = datetime.combine(datetime.today(), self.heure_depart)
            duree = (depart - arrivee).total_seconds() / 60
            return round(duree, 2)
        return None


#####################
# Transferts Stock  #
#####################
class TransfertStock(models.Model):
    """Transferts de stock entre entrepôts (notamment vers les vans)"""
    STATUT_CHOICES = (
        ('brouillon', 'Brouillon'),
        ('valide', 'Validé'),
        ('en_transit', 'En transit'),
        ('receptionne', 'Réceptionné'),
        ('annule', 'Annulé'),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='transferts_stock',
        null=True,
        blank=True,
        help_text="Entreprise propriétaire de ce transfert"
    )

    # Numérotation
    numero = models.CharField('Numéro de transfert', max_length=50, unique=True)
    date_creation = models.DateTimeField('Date de création', default=timezone.now)
    date_validation = models.DateTimeField('Date de validation', null=True, blank=True)
    date_reception = models.DateTimeField('Date de réception', null=True, blank=True)

    # Origine et destination
    entrepot_source = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name='transferts_sortants',
        help_text="Entrepôt d'origine"
    )
    entrepot_destination = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name='transferts_entrants',
        help_text="Entrepôt de destination (van ou autre entrepôt)"
    )

    # Statut et traçabilité
    statut = models.CharField('Statut', max_length=20, choices=STATUT_CHOICES, default='brouillon')

    # Responsables
    demandeur = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transferts_demandes',
        help_text="Utilisateur qui a créé le transfert"
    )
    valideur = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transferts_valides',
        help_text="Utilisateur qui a validé le transfert"
    )
    recepteur = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transferts_receptionnes',
        help_text="Utilisateur qui a réceptionné le transfert"
    )

    # Notes
    notes = models.TextField('Notes', blank=True)
    motif_annulation = models.TextField('Motif d\'annulation', blank=True)

    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_creation', 'numero']
        verbose_name = 'Transfert de stock'
        verbose_name_plural = 'Transferts de stock'
        unique_together = ['company', 'numero']

    def __str__(self):
        return f"{self.numero} - {self.entrepot_source.code} → {self.entrepot_destination.code} ({self.get_statut_display()})"

    def save(self, *args, **kwargs):
        # Générer le numéro automatiquement
        if not self.numero:
            from datetime import datetime
            date_str = datetime.now().strftime('%Y%m%d')
            # Compter les transferts du jour
            count = TransfertStock.objects.filter(
                numero__startswith=f'TRANS-{date_str}'
            ).count() + 1
            self.numero = f'TRANS-{date_str}-{count:04d}'
        super().save(*args, **kwargs)

    def valider(self, user):
        """Valide le transfert et crée les mouvements de stock"""
        if self.statut != 'brouillon':
            raise ValidationError("Seuls les transferts en brouillon peuvent être validés")

        if not self.lignes.exists():
            raise ValidationError("Le transfert doit contenir au moins une ligne")

        from django.db import transaction

        with transaction.atomic():
            # Mettre à jour le statut
            self.statut = 'valide'
            self.date_validation = timezone.now()
            self.valideur = user
            self.save()

            # Créer les mouvements de stock pour chaque ligne
            for ligne in self.lignes.all():
                # Sortie de l'entrepôt source
                # Si le ProductStock n'existe pas, l'initialiser avec la quantité du produit
                stock_source, created = ProductStock.objects.get_or_create(
                    produit=ligne.produit,
                    warehouse=self.entrepot_source,
                    defaults={'quantity': ligne.produit.quantite or 0}
                )

                # Si le stock est à 0, utiliser la quantité du produit (Produit.quantite)
                if stock_source.quantity == 0 and ligne.produit.quantite > 0:
                    stock_source.quantity = ligne.produit.quantite
                    stock_source.save()

                # Vérifier le stock disponible
                if stock_source.quantity < ligne.quantite:
                    raise ValidationError(
                        f"Stock insuffisant pour {ligne.produit.designation}: "
                        f"disponible={stock_source.quantity}, demandé={ligne.quantite}"
                    )

                # Décrémenter le stock source
                stock_source.quantity -= ligne.quantite
                stock_source.save()

                # Mouvement de sortie
                StockMove.objects.create(
                    produit=ligne.produit,
                    warehouse=self.entrepot_source,
                    delta=-ligne.quantite,
                    source='TRANS',
                    ref_id=self.numero,
                    note=f'Transfert vers {self.entrepot_destination.code}'
                )

                # Entrée dans l'entrepôt destination
                stock_dest, _ = ProductStock.objects.get_or_create(
                    produit=ligne.produit,
                    warehouse=self.entrepot_destination,
                    defaults={'quantity': 0}
                )
                stock_dest.quantity += ligne.quantite
                stock_dest.save()

                # Mouvement d'entrée
                StockMove.objects.create(
                    produit=ligne.produit,
                    warehouse=self.entrepot_destination,
                    delta=+ligne.quantite,
                    source='TRANS',
                    ref_id=self.numero,
                    note=f'Transfert depuis {self.entrepot_source.code}'
                )

                # Mettre à jour Produit.quantite (somme de tous les stocks sauf vans)
                from django.db.models import Sum
                total_stock = ProductStock.objects.filter(
                    produit=ligne.produit,
                    warehouse__is_active=True
                ).exclude(
                    warehouse__code__icontains='van'
                ).aggregate(total=Sum('quantity'))['total'] or 0
                ligne.produit.quantite = total_stock
                ligne.produit.save(update_fields=['quantite'])

    def annuler(self, user, motif):
        """Annule le transfert"""
        if self.statut == 'receptionne':
            raise ValidationError("Impossible d'annuler un transfert déjà réceptionné")

        self.statut = 'annule'
        self.motif_annulation = motif
        self.save()

    def get_nombre_lignes(self):
        """Retourne le nombre de lignes du transfert"""
        return self.lignes.count()

    def get_nombre_produits(self):
        """Retourne le nombre total de produits transférés"""
        return sum(ligne.quantite for ligne in self.lignes.all())


class LigneTransfertStock(models.Model):
    """Ligne de transfert de stock"""
    transfert = models.ForeignKey(
        TransfertStock,
        on_delete=models.CASCADE,
        related_name='lignes',
        help_text="Transfert parent"
    )
    produit = models.ForeignKey(
        Produit,
        on_delete=models.PROTECT,
        help_text="Produit à transférer"
    )
    quantite = models.PositiveIntegerField('Quantité à transférer')
    quantite_recue = models.PositiveIntegerField(
        'Quantité reçue',
        null=True,
        blank=True,
        help_text="Quantité effectivement reçue (peut différer de la quantité envoyée)"
    )
    notes = models.TextField('Notes', blank=True)

    class Meta:
        verbose_name = 'Ligne de transfert'
        verbose_name_plural = 'Lignes de transfert'
        unique_together = ['transfert', 'produit']

    def __str__(self):
        return f"{self.produit.reference} x {self.quantite} ({self.transfert.numero})"

    def get_stock_disponible(self):
        """Retourne le stock disponible dans l'entrepôt source"""
        try:
            stock = ProductStock.objects.get(
                produit=self.produit,
                warehouse=self.transfert.entrepot_source
            )
            return stock.quantity
        except ProductStock.DoesNotExist:
            return 0


#####################
# Permissions Pages #
#####################
class PagePermission(models.Model):
    """
    Modèle pour gérer les permissions d'accès aux pages de l'application.
    Ce modèle n'a pas de données, il sert juste à créer des permissions Django.
    """
    class Meta:
        managed = False  # Pas de table en base de données
        default_permissions = ()  # Pas de permissions CRUD par défaut
        permissions = [
            # Ventes et Caisse
            ('view_caisse', 'Peut accéder à la caisse'),
            ('view_ventes', 'Peut voir les ventes'),
            ('create_vente', 'Peut créer des ventes'),

            # Stock
            ('view_stock_management', 'Peut voir la gestion des stocks'),
            ('view_stock_dashboard', 'Peut voir le tableau de bord des stocks'),
            ('manage_transferts', 'Peut gérer les transferts'),
            ('charger_van', 'Peut charger les vans'),

            # Distribution
            ('view_distribution', 'Peut voir le module distribution'),
            ('view_livreurs', 'Peut voir les livreurs'),
            ('manage_livreurs', 'Peut gérer les livreurs'),
            ('view_tournees', 'Peut voir les tournées'),
            ('manage_tournees', 'Peut gérer les tournées'),
            ('view_commandes_mobile', 'Peut voir les commandes mobile'),
            ('view_distribution_dashboard', 'Peut voir le tableau de bord distribution'),
            ('view_config_clients_chauffeurs', 'Peut voir la config clients/chauffeurs'),
            ('manage_config_clients_chauffeurs', 'Peut gérer la config clients/chauffeurs'),
            ('view_assignation_clients', 'Peut voir l\'onglet Assignation Clients'),
            ('view_config_par_jour', 'Peut voir l\'onglet Configuration par Jour'),
            ('view_stats_livreurs', 'Peut voir les statistiques livreurs'),
            ('view_app_mobile_livreurs', 'Peut accéder à l\'app mobile livreurs'),
            ('view_carte_gps_livreurs', 'Peut voir la carte GPS livreurs'),

            # Configuration
            ('view_parametres', 'Peut voir les paramètres'),
            ('manage_clients', 'Peut gérer les clients'),
            ('manage_fournisseurs', 'Peut gérer les fournisseurs'),
            ('manage_categories', 'Peut gérer les catégories'),
            ('manage_entrepots', 'Peut gérer les entrepôts'),

            # Rapports
            ('view_rapports', 'Peut voir les rapports'),
            ('view_statistiques', 'Peut voir les statistiques'),
            ('export_data', 'Peut exporter les données'),

            # Administration
            ('view_admin', 'Peut voir l\'administration'),
            ('manage_users', 'Peut gérer les utilisateurs'),
            ('manage_roles', 'Peut gérer les rôles'),

            # Promotions
            ('view_promotions', 'Peut voir les promotions'),
            ('manage_promotions', 'Peut gérer les promotions'),
        ]


#####################
# Conditionnement   #
#####################
class Conditionnement(models.Model):
    """
    Définition du conditionnement d'un produit (unités par carton, cartons par colis, etc.)
    """
    TYPE_CONDITIONNEMENT = (
        ('unite', 'Unité'),
        ('carton', 'Carton'),
        ('colis', 'Colis'),
        ('palette', 'Palette'),
    )

    produit = models.ForeignKey(
        Produit,
        on_delete=models.CASCADE,
        related_name='conditionnements',
        help_text="Produit concerné"
    )

    # Configuration du carton
    unites_par_carton = models.PositiveIntegerField(
        "Unités par carton",
        default=1,
        help_text="Nombre d'unités dans un carton"
    )
    prix_carton = models.DecimalField(
        "Prix du carton",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Prix du carton complet (optionnel, sinon calculé automatiquement)"
    )

    # Configuration du colis (groupement de cartons)
    cartons_par_colis = models.PositiveIntegerField(
        "Cartons par colis",
        default=1,
        help_text="Nombre de cartons dans un colis"
    )
    prix_colis = models.DecimalField(
        "Prix du colis",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Prix du colis complet (optionnel)"
    )

    # Configuration de la palette (optionnel)
    colis_par_palette = models.PositiveIntegerField(
        "Colis par palette",
        null=True,
        blank=True,
        help_text="Nombre de colis dans une palette (optionnel)"
    )
    prix_palette = models.DecimalField(
        "Prix de la palette",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Prix de la palette complète (optionnel)"
    )

    # Prix de démunération (vente à l'unité depuis un carton ouvert)
    prix_demunerisation = models.DecimalField(
        "Prix de démunération",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Prix spécial pour vente à l'unité depuis carton ouvert"
    )

    # Poids et dimensions du carton
    poids_carton = models.DecimalField(
        "Poids du carton (kg)",
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True
    )
    dimensions_carton = models.CharField(
        "Dimensions carton (LxlxH cm)",
        max_length=50,
        blank=True
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['produit__designation']
        verbose_name = "Conditionnement"
        verbose_name_plural = "Conditionnements"

    def __str__(self):
        return f"{self.produit.designation} - {self.unites_par_carton} u/carton"

    def get_prix_carton_calcule(self):
        """Retourne le prix du carton (configuré ou calculé)"""
        if self.prix_carton:
            return self.prix_carton
        return self.produit.prixU * self.unites_par_carton

    def get_prix_colis_calcule(self):
        """Retourne le prix du colis (configuré ou calculé)"""
        if self.prix_colis:
            return self.prix_colis
        return self.get_prix_carton_calcule() * self.cartons_par_colis

    def get_unites_par_colis(self):
        """Retourne le nombre total d'unités par colis"""
        return self.unites_par_carton * self.cartons_par_colis

    def get_unites_par_palette(self):
        """Retourne le nombre total d'unités par palette"""
        if self.colis_par_palette:
            return self.get_unites_par_colis() * self.colis_par_palette
        return None


#####################
#    Promotions     #
#####################
class Promotion(models.Model):
    """
    Configuration complète d'une promotion sur un produit
    """
    TYPE_PROMOTION = (
        ('pourcentage', 'Réduction en pourcentage'),
        ('valeur_fixe', 'Réduction valeur fixe'),
        ('prix_special', 'Prix spécial'),
        ('achetez_x_payez_y', 'Achetez X, payez Y'),
        ('achetez_x_offert_y', 'Achetez X, Y offert(s)'),
        ('lot', 'Promotion lot'),
        ('demunerisation', 'Prix de démunération'),
        ('quantite', 'Réduction par quantité'),
    )

    UNITE_APPLICATION = (
        ('unite', 'Par unité'),
        ('carton', 'Par carton'),
        ('colis', 'Par colis'),
        ('palette', 'Par palette'),
    )

    STATUT_CHOICES = (
        ('brouillon', 'Brouillon'),
        ('active', 'Active'),
        ('planifiee', 'Planifiée'),
        ('expiree', 'Expirée'),
        ('suspendue', 'Suspendue'),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='promotions',
        null=True,
        blank=True,
        help_text="Entreprise propriétaire de cette promotion"
    )

    # Identification
    code = models.CharField(
        "Code promotion",
        max_length=50,
        unique=True,
        help_text="Code unique de la promotion (ex: PROMO-NOEL-2024)"
    )
    nom = models.CharField(
        "Nom de la promotion",
        max_length=200,
        help_text="Nom descriptif de la promotion"
    )
    description = models.TextField(
        "Description",
        blank=True,
        help_text="Description détaillée de la promotion"
    )

    # Type et configuration
    type_promotion = models.CharField(
        "Type de promotion",
        max_length=30,
        choices=TYPE_PROMOTION,
        default='pourcentage'
    )

    # Valeurs de la promotion selon le type
    valeur_pourcentage = models.DecimalField(
        "Pourcentage de réduction",
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Pourcentage de réduction (ex: 10 pour 10%)"
    )
    valeur_fixe = models.DecimalField(
        "Montant de réduction fixe",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Montant fixe de réduction (ex: 2.00 DA)"
    )
    prix_special = models.DecimalField(
        "Prix spécial",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Prix spécial fixe à appliquer"
    )

    # Configuration "Achetez X, payez Y" ou "Achetez X, Y offert"
    quantite_achat = models.PositiveIntegerField(
        "Quantité à acheter",
        null=True,
        blank=True,
        help_text="Nombre de produits à acheter pour déclencher l'offre"
    )
    quantite_offerte = models.PositiveIntegerField(
        "Quantité offerte/payée",
        null=True,
        blank=True,
        help_text="Nombre de produits offerts ou nombre à payer"
    )

    # Unité d'application
    unite_application = models.CharField(
        "S'applique sur",
        max_length=20,
        choices=UNITE_APPLICATION,
        default='unite',
        help_text="Unité sur laquelle la promotion s'applique"
    )

    # Devise pour les montants fixes
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Devise pour les montants de la promotion"
    )

    # Produit(s) concerné(s)
    produit = models.ForeignKey(
        Produit,
        on_delete=models.CASCADE,
        related_name='promotions',
        null=True,
        blank=True,
        help_text="Produit spécifique (optionnel si catégorie sélectionnée)"
    )
    categorie = models.ForeignKey(
        Categorie,
        on_delete=models.CASCADE,
        related_name='promotions',
        null=True,
        blank=True,
        help_text="Catégorie de produits (optionnel si produit sélectionné)"
    )

    # Validité temporelle
    date_debut = models.DateTimeField(
        "Date de début",
        help_text="Date et heure de début de la promotion"
    )
    date_fin = models.DateTimeField(
        "Date de fin",
        help_text="Date et heure de fin de la promotion"
    )

    # Conditions d'application
    quantite_minimum = models.PositiveIntegerField(
        "Quantité minimum",
        default=1,
        help_text="Quantité minimum pour activer la promotion"
    )
    quantite_maximum = models.PositiveIntegerField(
        "Quantité maximum",
        null=True,
        blank=True,
        help_text="Quantité maximum bénéficiant de la promotion (optionnel)"
    )

    # Conditionnement requis
    conditionnement_minimum = models.CharField(
        "Conditionnement minimum",
        max_length=20,
        choices=UNITE_APPLICATION,
        default='unite',
        help_text="Conditionnement minimum requis pour la promotion"
    )
    carton_complet_requis = models.BooleanField(
        "Carton complet requis",
        default=False,
        help_text="La promotion nécessite l'achat de cartons complets"
    )

    # Cumul et priorité
    est_cumulable = models.BooleanField(
        "Cumulable avec autres promotions",
        default=False,
        help_text="Peut être cumulée avec d'autres promotions"
    )
    priorite = models.IntegerField(
        "Priorité",
        default=0,
        help_text="Priorité d'application (plus élevé = prioritaire)"
    )

    # Limitation d'usage
    usage_maximum = models.PositiveIntegerField(
        "Usage maximum",
        null=True,
        blank=True,
        help_text="Nombre maximum d'utilisations (optionnel)"
    )
    usage_par_client = models.PositiveIntegerField(
        "Usage par client",
        null=True,
        blank=True,
        help_text="Nombre maximum d'utilisations par client (optionnel)"
    )
    usage_actuel = models.PositiveIntegerField(
        "Utilisations actuelles",
        default=0,
        help_text="Nombre d'utilisations de cette promotion"
    )

    # Types de clients éligibles
    types_prix_eligibles = models.ManyToManyField(
        TypePrix,
        related_name='promotions',
        blank=True,
        help_text="Types de clients éligibles (vide = tous)"
    )

    # Code de prix (période promotionnelle)
    code_prix = models.ForeignKey(
        'CodePrix',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='promotions_detail',
        help_text="Code de prix (période) auquel cette promotion est liée (ex: RAMADAN, STANDARD)"
    )

    # Statut
    statut = models.CharField(
        "Statut",
        max_length=20,
        choices=STATUT_CHOICES,
        default='brouillon'
    )

    # Métadonnées
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='promotions_creees'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priorite', '-created_at']
        verbose_name = "Promotion"
        verbose_name_plural = "Promotions"
        unique_together = ['company', 'code']

    def __str__(self):
        return f"{self.code} - {self.nom} ({self.get_type_promotion_display()})"

    def save(self, *args, **kwargs):
        # Mise à jour automatique du statut basé sur les dates
        self.update_statut()
        super().save(*args, **kwargs)

    def update_statut(self):
        """Met à jour le statut basé sur les dates"""
        # Ne pas modifier ces statuts automatiquement (définis manuellement)
        if self.statut in ['brouillon', 'suspendue', 'active']:
            # Si le statut est 'active' et la date est dépassée, le passer en expiré
            if self.statut == 'active':
                now = timezone.now()
                if now > self.date_fin:
                    self.statut = 'expiree'
            return

        now = timezone.now()
        if now < self.date_debut:
            self.statut = 'planifiee'
        elif now > self.date_fin:
            self.statut = 'expiree'
        else:
            self.statut = 'active'

    def is_valid(self):
        """Vérifie si la promotion est valide actuellement"""
        now = timezone.now()
        # Une promotion 'active' est valide même si date_debut est dans le futur
        # (activation manuelle anticipée)
        if self.statut == 'active':
            # Seule la date_fin doit être respectée pour les promos actives
            if now > self.date_fin:
                return False
            if self.usage_maximum and self.usage_actuel >= self.usage_maximum:
                return False
            return True
        # Pour les autres statuts, vérifier les dates normalement
        if self.statut != 'planifiee':
            return False
        if now < self.date_debut or now > self.date_fin:
            return False
        if self.usage_maximum and self.usage_actuel >= self.usage_maximum:
            return False
        return True

    def is_applicable_to_product(self, produit):
        """Vérifie si la promotion s'applique à un produit"""
        # Si aucun produit ni catégorie spécifié, la promo s'applique à tous les produits
        if not self.produit and not self.categorie:
            return True
        # Si un produit spécifique est défini
        if self.produit and self.produit.id == produit.id:
            return True
        # Si une catégorie est définie
        if self.categorie:
            # Vérifier si le produit est dans la catégorie ou ses sous-catégories
            cat = produit.categorie
            while cat:
                if cat.id == self.categorie.id:
                    return True
                cat = cat.parent
        return False

    def is_applicable_to_client_type(self, type_prix):
        """Vérifie si la promotion s'applique à un type de client"""
        if not self.types_prix_eligibles.exists():
            return True  # Si aucun type spécifié, tous sont éligibles
        return self.types_prix_eligibles.filter(id=type_prix.id).exists()

    def calculer_prix_promotion(self, prix_original, quantite=1):
        """Calcule le prix après application de la promotion"""
        if not self.is_valid():
            return prix_original

        if quantite < self.quantite_minimum:
            return prix_original

        if self.quantite_maximum and quantite > self.quantite_maximum:
            quantite_promo = self.quantite_maximum
            quantite_normale = quantite - self.quantite_maximum
            prix_promo = self._calculer_prix_unitaire(prix_original)
            return (prix_promo * quantite_promo) + (prix_original * quantite_normale)

        return self._calculer_prix_unitaire(prix_original) * quantite

    def _calculer_prix_unitaire(self, prix_original):
        """Calcule le prix unitaire après promotion"""
        if self.type_promotion == 'pourcentage' and self.valeur_pourcentage:
            reduction = prix_original * (self.valeur_pourcentage / Decimal('100'))
            return prix_original - reduction

        elif self.type_promotion == 'valeur_fixe' and self.valeur_fixe:
            return max(Decimal('0'), prix_original - self.valeur_fixe)

        elif self.type_promotion == 'prix_special' and self.prix_special:
            return self.prix_special

        return prix_original

    def calculer_offre_speciale(self, quantite):
        """Calcule pour les offres 'Achetez X, payez Y' ou 'Achetez X, Y offert'"""
        if self.type_promotion == 'achetez_x_payez_y':
            if quantite >= self.quantite_achat:
                lots = quantite // self.quantite_achat
                reste = quantite % self.quantite_achat
                return {
                    'quantite_a_payer': (lots * self.quantite_offerte) + reste,
                    'quantite_gratuite': lots * (self.quantite_achat - self.quantite_offerte),
                    'quantite_totale': quantite
                }

        elif self.type_promotion == 'achetez_x_offert_y':
            if quantite >= self.quantite_achat:
                lots = quantite // self.quantite_achat
                return {
                    'quantite_a_payer': quantite,
                    'quantite_gratuite': lots * self.quantite_offerte,
                    'quantite_totale': quantite + (lots * self.quantite_offerte)
                }

        return {
            'quantite_a_payer': quantite,
            'quantite_gratuite': 0,
            'quantite_totale': quantite
        }

    def get_economie(self, prix_original, quantite=1):
        """Calcule l'économie réalisée avec la promotion"""
        prix_sans_promo = prix_original * quantite
        prix_avec_promo = self.calculer_prix_promotion(prix_original, quantite)
        economie = prix_sans_promo - prix_avec_promo
        pourcentage = (economie / prix_sans_promo * 100) if prix_sans_promo > 0 else 0
        return {
            'montant': economie,
            'pourcentage': pourcentage
        }

    def incrementer_usage(self):
        """Incrémente le compteur d'utilisation"""
        self.usage_actuel += 1
        self.save(update_fields=['usage_actuel'])


class PromotionUsage(models.Model):
    """Suivi de l'utilisation des promotions par client"""
    promotion = models.ForeignKey(
        Promotion,
        on_delete=models.CASCADE,
        related_name='usages'
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='promotions_utilisees'
    )
    vente = models.ForeignKey(
        Vente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='promotions_appliquees'
    )
    date_utilisation = models.DateTimeField(auto_now_add=True)
    montant_economise = models.DecimalField(
        "Économie réalisée",
        max_digits=10,
        decimal_places=2,
        default=0
    )

    class Meta:
        ordering = ['-date_utilisation']
        verbose_name = "Utilisation promotion"
        verbose_name_plural = "Utilisations promotions"

    def __str__(self):
        return f"{self.promotion.code} - {self.client} - {self.date_utilisation.date()}"


#####################
#      Secteurs     #
#####################

class Secteur(models.Model):
    """Modèle pour gérer les secteurs géographiques/commerciaux"""
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='secteurs',
        null=True,
        blank=True,
        help_text="Entreprise propriétaire de ce secteur"
    )
    code = models.CharField(
        max_length=20,
        help_text="Code unique du secteur (ex: SEC001)"
    )
    nom = models.CharField(
        max_length=100,
        help_text="Nom du secteur"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description du secteur"
    )
    couleur = models.CharField(
        max_length=7,
        default='#3498db',
        help_text="Couleur d'affichage (hex)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Secteur actif ou non"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nom']
        verbose_name = "Secteur"
        verbose_name_plural = "Secteurs"
        unique_together = ['company', 'code']

    def __str__(self):
        return f"{self.code} - {self.nom}"

    def get_clients_count(self):
        """Retourne le nombre de clients dans ce secteur"""
        return self.clients.count() if hasattr(self, 'clients') else 0
