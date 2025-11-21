"""
Script pour ajouter les modèles de Commande à distribution_models.py
"""

models_code = """

#####################
# Commandes Clients #
#####################

class CommandeClient(models.Model):
    \"\"\"
    Commande passée par un livreur pour un client
    (pour livraison ultérieure, sans limite de stock)
    \"\"\"
    STATUT_CHOICES = (
        ('pending', 'En attente'),
        ('confirmed', 'Confirmée'),
        ('preparing', 'En préparation'),
        ('ready', 'Prête'),
        ('delivered', 'Livrée'),
        ('cancelled', 'Annulée'),
    )

    # Référence unique
    reference = models.CharField(max_length=100, unique=True, blank=True)

    # Relations
    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='commandes_clients')
    client = models.ForeignKey('Client', on_delete=models.PROTECT, related_name='commandes')
    livreur = models.ForeignKey(LivreurDistribution, on_delete=models.PROTECT, related_name='commandes_prises')

    # Informations de la commande
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='pending')
    date_commande = models.DateTimeField(auto_now_add=True)
    date_livraison_souhaitee = models.DateField(null=True, blank=True)
    date_livraison_reelle = models.DateTimeField(null=True, blank=True)

    # Montants
    montant_total_ht = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    montant_total_ttc = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Notes
    notes = models.TextField(blank=True, null=True)
    notes_preparation = models.TextField(blank=True, null=True)

    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    synced_at = models.DateTimeField(null=True, blank=True)

    # ID depuis l'app mobile (pour éviter les doublons)
    app_id = models.CharField(max_length=200, unique=True, null=True, blank=True)

    class Meta:
        db_table = 'distribution_commande_client'
        verbose_name = 'Commande client'
        verbose_name_plural = 'Commandes clients'
        ordering = ['-date_commande']
        indexes = [
            models.Index(fields=['company', 'statut']),
            models.Index(fields=['livreur', 'date_commande']),
            models.Index(fields=['client', 'statut']),
            models.Index(fields=['app_id']),
        ]

    def __str__(self):
        return f"Commande {self.reference} - {self.client} ({self.statut})"

    def save(self, *args, **kwargs):
        # Générer la référence si elle n'existe pas
        if not self.reference:
            self.reference = self.generer_reference()

        super().save(*args, **kwargs)

    def generer_reference(self):
        \"\"\"Génère une référence unique pour la commande\"\"\"
        from django.db.models import Max
        import re

        date_str = self.date_commande.strftime('%Y%m%d') if self.date_commande else timezone.now().strftime('%Y%m%d')
        prefix = f"CMD-{date_str}-"

        # Trouver le dernier numéro du jour
        last_cmd = CommandeClient.objects.filter(
            reference__startswith=prefix
        ).aggregate(Max('reference'))['reference__max']

        if last_cmd:
            match = re.search(r'-(\d+)$', last_cmd)
            if match:
                counter = int(match.group(1)) + 1
            else:
                counter = 1
        else:
            counter = 1

        return f"{prefix}{counter:04d}"

    def calculer_totaux(self):
        \"\"\"Recalcule les montants totaux à partir des lignes\"\"\"
        lignes = self.lignes.all()
        self.montant_total_ht = sum(ligne.montant_ht for ligne in lignes)
        self.montant_total_ttc = sum(ligne.montant_ttc for ligne in lignes)
        self.save(update_fields=['montant_total_ht', 'montant_total_ttc'])


class LigneCommandeClient(models.Model):
    \"\"\"Ligne de commande client\"\"\"
    commande = models.ForeignKey(CommandeClient, on_delete=models.CASCADE, related_name='lignes')
    produit = models.ForeignKey('Produit', on_delete=models.PROTECT)

    # Quantité et prix
    quantite = models.DecimalField(max_digits=10, decimal_places=2)
    prix_unitaire_ht = models.DecimalField(max_digits=10, decimal_places=2)
    taux_tva = models.DecimalField(max_digits=5, decimal_places=2, default=19)

    # Montants calculés
    montant_ht = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    montant_tva = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    montant_ttc = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'distribution_ligne_commande_client'
        verbose_name = 'Ligne de commande'
        verbose_name_plural = 'Lignes de commande'

    def __str__(self):
        return f"{self.produit.designation} x {self.quantite}"

    def save(self, *args, **kwargs):
        \"\"\"Calcule automatiquement les montants\"\"\"
        from decimal import Decimal

        # Calcul montant HT
        self.montant_ht = self.quantite * self.prix_unitaire_ht

        # Calcul TVA
        self.montant_tva = self.montant_ht * (self.taux_tva / Decimal('100'))

        # Calcul TTC
        self.montant_ttc = self.montant_ht + self.montant_tva

        super().save(*args, **kwargs)

        # Recalculer les totaux de la commande
        self.commande.calculer_totaux()
"""

# Lire le fichier actuel
with open('API/distribution_models.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Ajouter les nouveaux modèles
with open('API/distribution_models.py', 'w', encoding='utf-8') as f:
    f.write(content + models_code)

print("OK - Modeles de commande ajoutes a distribution_models.py")
