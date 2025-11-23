"""
Modèles pour la gestion de la distribution mobile
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
import json

User = get_user_model()


class LivreurDistribution(models.Model):
    """Livreur / Distributeur mobile pour le système de tournées"""
    STATUS_CHOICES = [
        ('actif', 'Actif'),
        ('inactif', 'Inactif'),
        ('conge', 'En congé'),
        ('suspendu', 'Suspendu'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='livreur_distribution_profile', null=True, blank=True)
    matricule = models.CharField('Matricule', max_length=20, unique=True)
    nom = models.CharField('Nom complet', max_length=200)
    telephone = models.CharField('Téléphone', max_length=20)
    email = models.EmailField('Email', blank=True)

    # Van/Véhicule
    vehicule_immatriculation = models.CharField('Immatriculation', max_length=20, blank=True)
    vehicule_marque = models.CharField('Marque du véhicule', max_length=100, blank=True)

    # Position GPS en temps réel
    current_lat = models.DecimalField('Latitude actuelle', max_digits=10, decimal_places=7, null=True, blank=True,
                                     help_text='Position GPS actuelle du livreur')
    current_lng = models.DecimalField('Longitude actuelle', max_digits=10, decimal_places=7, null=True, blank=True,
                                     help_text='Position GPS actuelle du livreur')
    last_location_update = models.DateTimeField('Dernière mise à jour GPS', null=True, blank=True,
                                                help_text='Horodatage de la dernière position GPS')

    # Statut
    statut = models.CharField('Statut', max_length=20, choices=STATUS_CHOICES, default='actif')
    date_embauche = models.DateField('Date d\'embauche', null=True, blank=True)

    # Entrepôt mobile (stock du van)
    entrepot = models.ForeignKey('Warehouse', on_delete=models.SET_NULL, null=True,
                                 related_name='livreur_associe',
                                 help_text='Entrepôt mobile associé au van')

    # Clients assignés à ce livreur
    clients_assignes = models.ManyToManyField('Client', blank=True,
                                              related_name='livreurs_assignes',
                                              help_text='Clients assignés à ce livreur pour les tournées')

    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Livreur Distribution'
        verbose_name_plural = 'Livreurs Distribution'
        ordering = ['nom']
        db_table = 'api_livreur_distribution'

    def __str__(self):
        return f"{self.matricule} - {self.nom}"

    def tournees_actives(self):
        """Retourne les tournées actives du livreur"""
        return self.tournees.filter(
            statut__in=['planifiee', 'en_cours']
        )


class TourneeMobile(models.Model):
    """Tournée journalière d'un livreur"""
    STATUT_CHOICES = [
        ('planifiee', 'Planifiée'),
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
        ('annulee', 'Annulée'),
        ('cloturee', 'Clôturée et verrouillée'),
    ]

    livreur = models.ForeignKey(LivreurDistribution, on_delete=models.CASCADE, related_name='tournees')
    date_tournee = models.DateField('Date de la tournée')
    numero_tournee = models.CharField('N° Tournée', max_length=50, unique=True)

    # Statut et suivi
    statut = models.CharField('Statut', max_length=20, choices=STATUT_CHOICES, default='planifiee')
    heure_debut = models.TimeField('Heure de début', null=True, blank=True)
    heure_fin = models.TimeField('Heure de fin', null=True, blank=True)

    # Géolocalisation
    position_depart_lat = models.DecimalField('Latitude départ', max_digits=10, decimal_places=7, null=True, blank=True)
    position_depart_lng = models.DecimalField('Longitude départ', max_digits=10, decimal_places=7, null=True, blank=True)
    position_fin_lat = models.DecimalField('Latitude fin', max_digits=10, decimal_places=7, null=True, blank=True)
    position_fin_lng = models.DecimalField('Longitude fin', max_digits=10, decimal_places=7, null=True, blank=True)

    # Distance parcourue (en km)
    distance_km = models.DecimalField('Distance (km)', max_digits=10, decimal_places=2, null=True, blank=True)

    # Argent de départ prédéfini
    argent_depart = models.DecimalField('Argent de départ', max_digits=12, decimal_places=2, default=0,
                                        help_text='Montant prédéfini donné au livreur en début de tournée')

    # Clôture
    est_cloturee = models.BooleanField('Clôturée', default=False)
    date_cloture = models.DateTimeField('Date de clôture', null=True, blank=True)
    cloturee_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                     related_name='tournees_cloturees')

    # Notes
    notes = models.TextField('Notes', blank=True)

    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='tournees_creees')

    # Multi-tenancy
    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='tournees_mobiles',
                               null=True, blank=True,  # Temporarily nullable for migration
                               help_text='Entreprise à laquelle appartient cet enregistrement')

    class Meta:
        verbose_name = 'Tournée'
        verbose_name_plural = 'Tournées'
        ordering = ['-date_tournee', 'numero_tournee']
        unique_together = [['livreur', 'date_tournee']]

    def __str__(self):
        return f"{self.numero_tournee} - {self.livreur.nom} - {self.date_tournee}"

    def clean(self):
        if self.est_cloturee and self.statut not in ['terminee', 'cloturee']:
            raise ValidationError('Une tournée ne peut être clôturée que si elle est terminée.')

    def cloturer(self, user):
        """Clôturer et verrouiller la tournée"""
        if self.est_cloturee:
            raise ValidationError('Cette tournée est déjà clôturée.')

        self.est_cloturee = True
        self.statut = 'cloturee'
        self.date_cloture = timezone.now()
        self.cloturee_par = user
        self.save()

    def stats(self):
        """Statistiques de la tournée"""
        arrets = self.arrets.all()
        total_arrets = arrets.count()
        arrets_livres = arrets.filter(statut='livre').count()
        arrets_echec = arrets.filter(statut='echec').count()
        arrets_en_attente = arrets.filter(statut='en_attente').count()

        ca_total = sum(
            vente.montant_total for vente in self.ventes.all()
        )

        return {
            'total_arrets': total_arrets,
            'arrets_livres': arrets_livres,
            'arrets_echec': arrets_echec,
            'arrets_en_attente': arrets_en_attente,
            'taux_reussite': round((arrets_livres / total_arrets * 100) if total_arrets > 0 else 0, 2),
            'ca_total': ca_total,
        }


class ArretTourneeMobile(models.Model):
    """Arrêt client dans une tournée"""
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('livre', 'Livré'),
        ('echec', 'Échec'),
        ('reporte', 'Reporté'),
    ]

    tournee = models.ForeignKey(TourneeMobile, on_delete=models.CASCADE, related_name='arrets')
    client = models.ForeignKey('Client', on_delete=models.CASCADE, related_name='arrets')
    ordre_passage = models.PositiveIntegerField('Ordre de passage', default=1)

    # Statut
    statut = models.CharField('Statut', max_length=20, choices=STATUT_CHOICES, default='en_attente')

    # Horaires
    heure_prevue = models.TimeField('Heure prévue', null=True, blank=True)
    heure_arrivee = models.DateTimeField('Heure d\'arrivée', null=True, blank=True)
    heure_depart = models.DateTimeField('Heure de départ', null=True, blank=True)

    # Géolocalisation
    latitude = models.DecimalField('Latitude', max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField('Longitude', max_digits=10, decimal_places=7, null=True, blank=True)

    # Preuve de livraison
    signature_base64 = models.TextField('Signature (base64)', blank=True)
    photo_livraison = models.ImageField('Photo de livraison', upload_to='livraisons/', null=True, blank=True)
    nom_receptionnaire = models.CharField('Nom du réceptionnaire', max_length=200, blank=True)

    # En cas d'échec
    motif_echec = models.CharField('Motif d\'échec', max_length=200, blank=True)
    notes_echec = models.TextField('Notes échec', blank=True)

    # Notes
    notes = models.TextField('Notes', blank=True)


    # Multi-tenancy
    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='arrets_tournees_mobiles',
                               null=True, blank=True,  # Temporarily nullable for migration
                               help_text='Entreprise à laquelle appartient cet enregistrement')

    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Arrêt tournée'
        verbose_name_plural = 'Arrêts tournées'
        ordering = ['tournee', 'ordre_passage']
        unique_together = [['tournee', 'ordre_passage']]

    def __str__(self):
        return f"Arrêt {self.ordre_passage} - {self.client.nom} ({self.tournee.numero_tournee})"

    def clean(self):
        if self.tournee.est_cloturee:
            raise ValidationError('Impossible de modifier un arrêt d\'une tournée clôturée.')


class VenteTourneeMobile(models.Model):
    """Vente effectuée lors d'une tournée"""
    TYPE_PAIEMENT_CHOICES = [
        ('especes', 'Espèces'),
        ('carte', 'Carte'),
        ('cheque', 'Chèque'),
        ('credit', 'À crédit'),
        ('virement', 'Virement'),
    ]

    tournee = models.ForeignKey(TourneeMobile, on_delete=models.CASCADE, related_name='ventes',
                                null=True, blank=True, help_text='Tournée associée (optionnel pour ventes directes)')
    arret = models.ForeignKey(ArretTourneeMobile, on_delete=models.CASCADE, related_name='ventes',
                             null=True, blank=True, help_text='Arrêt associé (optionnel pour ventes directes)')
    client = models.ForeignKey('Client', on_delete=models.CASCADE, related_name='ventes_tournees')

    # Référence
    numero_vente = models.CharField('N° Vente', max_length=50, unique=True, blank=True)
    date_vente = models.DateTimeField('Date vente', default=timezone.now)

    # Montants
    montant_ht = models.DecimalField('Montant HT', max_digits=12, decimal_places=2, default=0)
    montant_tva = models.DecimalField('Montant TVA', max_digits=12, decimal_places=2, default=0)
    montant_total = models.DecimalField('Montant total TTC', max_digits=12, decimal_places=2, default=0)

    # Paiement
    type_paiement = models.CharField('Type de paiement', max_length=20, choices=TYPE_PAIEMENT_CHOICES)
    montant_paye = models.DecimalField('Montant payé', max_digits=12, decimal_places=2, default=0)
    montant_rendu = models.DecimalField('Monnaie rendue', max_digits=12, decimal_places=2, default=0)

    # Synchronisation
    est_synchronise = models.BooleanField('Synchronisé', default=False)
    date_synchronisation = models.DateTimeField('Date synchronisation', null=True, blank=True)

    # Notes
    notes = models.TextField('Notes', blank=True)


    # Multi-tenancy
    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='ventes_tournees_mobiles',
                               null=True, blank=True,  # Temporarily nullable for migration
                               help_text='Entreprise à laquelle appartient cet enregistrement')

    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Vente tournée'
        verbose_name_plural = 'Ventes tournées'
        ordering = ['-date_vente']

    def __str__(self):
        return f"{self.numero_vente} - {self.client.nom} - {self.montant_total}€"

    def save(self, *args, **kwargs):
        # Vérifier si la tournée est clôturée (seulement si une tournée existe)
        if self.tournee_id and self.tournee.est_cloturee and not self.pk:
            raise ValidationError('Impossible d\'ajouter une vente à une tournée clôturée.')
        super().save(*args, **kwargs)


class LigneVenteTourneeMobile(models.Model):
    """Ligne de vente dans une vente tournée"""
    vente = models.ForeignKey(VenteTourneeMobile, on_delete=models.CASCADE, related_name='lignes')
    produit = models.ForeignKey('Produit', on_delete=models.CASCADE, related_name='lignes_ventes_tournees')

    quantite = models.DecimalField('Quantité', max_digits=10, decimal_places=2)
    prix_unitaire = models.DecimalField('Prix unitaire', max_digits=10, decimal_places=2)
    taux_tva = models.DecimalField('Taux TVA (%)', max_digits=5, decimal_places=2, default=20)

    montant_ht = models.DecimalField('Montant HT', max_digits=12, decimal_places=2)
    montant_tva = models.DecimalField('Montant TVA', max_digits=12, decimal_places=2)
    montant_ttc = models.DecimalField('Montant TTC', max_digits=12, decimal_places=2)


    # Multi-tenancy
    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='lignes_ventes_tournees_mobiles',
                               null=True, blank=True,  # Temporarily nullable for migration
                               help_text='Entreprise à laquelle appartient cet enregistrement')

    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Ligne vente tournée'
        verbose_name_plural = 'Lignes ventes tournées'

    def __str__(self):
        return f"{self.produit.designation} x {self.quantite}"

    def save(self, *args, **kwargs):
        from decimal import Decimal
        # Calcul automatique des montants
        self.montant_ht = self.quantite * self.prix_unitaire
        self.montant_tva = self.montant_ht * (self.taux_tva / Decimal('100'))
        self.montant_ttc = self.montant_ht + self.montant_tva
        super().save(*args, **kwargs)


class RapportCaisseMobile(models.Model):
    """Rapport de caisse quotidienne d'une tournée"""
    STATUT_CHOICES = [
        ('ouvert', 'Ouvert'),
        ('valide', 'Validé'),
        ('cloture', 'Clôturé'),
    ]

    tournee = models.OneToOneField(TourneeMobile, on_delete=models.CASCADE, related_name='rapport_caisse')

    # Fonds de départ
    fonds_depart = models.DecimalField('Fonds de départ', max_digits=12, decimal_places=2, default=0)

    # Encaissements
    total_especes = models.DecimalField('Total espèces', max_digits=12, decimal_places=2, default=0)
    total_cartes = models.DecimalField('Total cartes', max_digits=12, decimal_places=2, default=0)
    total_cheques = models.DecimalField('Total chèques', max_digits=12, decimal_places=2, default=0)
    total_credits = models.DecimalField('Total à crédit', max_digits=12, decimal_places=2, default=0)
    total_encaissements = models.DecimalField('Total encaissements', max_digits=12, decimal_places=2, default=0)

    # Dépenses
    carburant = models.DecimalField('Carburant', max_digits=10, decimal_places=2, default=0)
    reparations = models.DecimalField('Réparations', max_digits=10, decimal_places=2, default=0)
    autres_depenses = models.DecimalField('Autres dépenses', max_digits=10, decimal_places=2, default=0)
    total_depenses = models.DecimalField('Total dépenses', max_digits=10, decimal_places=2, default=0)

    # Solde final
    solde_final_theorique = models.DecimalField('Solde théorique', max_digits=12, decimal_places=2, default=0)
    solde_final_reel = models.DecimalField('Solde réel', max_digits=12, decimal_places=2, default=0)
    ecart = models.DecimalField('Écart', max_digits=12, decimal_places=2, default=0)

    # Justification écart
    justification_ecart = models.TextField('Justification écart', blank=True)

    # Statut
    statut = models.CharField('Statut', max_length=20, choices=STATUT_CHOICES, default='ouvert')

    # Validation
    valide_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='rapports_caisse_valides')
    date_validation = models.DateTimeField('Date validation', null=True, blank=True)

    # Alertes
    a_des_anomalies = models.BooleanField('Anomalies détectées', default=False)
    notes_anomalies = models.TextField('Notes anomalies', blank=True)


    # Multi-tenancy
    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='rapports_caisses_mobiles',
                               null=True, blank=True,  # Temporarily nullable for migration
                               help_text='Entreprise à laquelle appartient cet enregistrement')

    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Rapport de caisse'
        verbose_name_plural = 'Rapports de caisse'
        ordering = ['-created_at']

    def __str__(self):
        return f"Caisse {self.tournee.numero_tournee} - {self.statut}"

    def calculer_totaux(self):
        """Recalcule tous les totaux"""
        # Total encaissements
        self.total_encaissements = (
            self.total_especes +
            self.total_cartes +
            self.total_cheques +
            self.total_credits
        )

        # Total dépenses
        self.total_depenses = (
            self.carburant +
            self.reparations +
            self.autres_depenses
        )

        # Solde théorique
        self.solde_final_theorique = (
            self.fonds_depart +
            self.total_especes -
            self.total_depenses
        )

        # Écart
        self.ecart = self.solde_final_reel - self.solde_final_theorique

        # Détection anomalies
        if abs(self.ecart) > 10:  # Seuil de 10€
            self.a_des_anomalies = True

        self.save()

    def valider(self, user):
        """Valider le rapport de caisse"""
        if self.statut == 'cloture':
            raise ValidationError('Le rapport est déjà clôturé.')

        self.calculer_totaux()
        self.statut = 'valide'
        self.valide_par = user
        self.date_validation = timezone.now()
        self.save()


class DepenseTourneeMobile(models.Model):
    """Dépense effectuée pendant une tournée"""
    TYPE_DEPENSE_CHOICES = [
        ('carburant', 'Carburant'),
        ('reparation', 'Réparation'),
        ('peage', 'Péage'),
        ('parking', 'Parking'),
        ('repas', 'Repas'),
        ('autre', 'Autre'),
    ]

    rapport_caisse = models.ForeignKey(RapportCaisseMobile, on_delete=models.CASCADE, related_name='depenses')
    type_depense = models.CharField('Type de dépense', max_length=20, choices=TYPE_DEPENSE_CHOICES)
    montant = models.DecimalField('Montant', max_digits=10, decimal_places=2)
    description = models.CharField('Description', max_length=200)

    # Justificatif
    photo_recu = models.ImageField('Photo du reçu', upload_to='depenses/', null=True, blank=True)

    # Métadonnées
    date_depense = models.DateTimeField('Date dépense', default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Dépense tournée'
        verbose_name_plural = 'Dépenses tournées'
        ordering = ['-date_depense']

    def __str__(self):
        return f"{self.type_depense} - {self.montant}€"


class SyncLogMobile(models.Model):
    """Journal de synchronisation entre mobile et serveur"""
    TYPE_SYNC_CHOICES = [
        ('push', 'Push (Mobile -> Serveur)'),
        ('pull', 'Pull (Serveur -> Mobile)'),
    ]

    STATUT_CHOICES = [
        ('en_cours', 'En cours'),
        ('succes', 'Succès'),
        ('echec', 'Échec'),
        ('partiel', 'Partiel'),
    ]

    livreur = models.ForeignKey(LivreurDistribution, on_delete=models.CASCADE, related_name='sync_logs')
    type_sync = models.CharField('Type de sync', max_length=10, choices=TYPE_SYNC_CHOICES)
    statut = models.CharField('Statut', max_length=20, choices=STATUT_CHOICES)

    # Données synchronisées
    nb_tournees = models.PositiveIntegerField('Nb tournées', default=0)
    nb_ventes = models.PositiveIntegerField('Nb ventes', default=0)
    nb_arrets = models.PositiveIntegerField('Nb arrêts', default=0)

    # Détails
    message = models.TextField('Message', blank=True)
    erreur_details = models.TextField('Détails erreur', blank=True)

    # Métadonnées
    date_sync = models.DateTimeField('Date synchronisation', default=timezone.now)
    duree_secondes = models.PositiveIntegerField('Durée (sec)', null=True, blank=True)

    # Device info
    device_id = models.CharField('ID Device', max_length=100, blank=True)
    app_version = models.CharField('Version app', max_length=20, blank=True)

    class Meta:
        verbose_name = 'Log de synchronisation'
        verbose_name_plural = 'Logs de synchronisation'
        ordering = ['-date_sync']

    def __str__(self):
        return f"{self.type_sync} - {self.livreur.nom} - {self.statut} - {self.date_sync}"


#####################
# Commandes Clients #
#####################

class CommandeClient(models.Model):
    """
    Commande passée par un livreur pour un client
    (pour livraison ultérieure, sans limite de stock)
    """
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
    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='commandes_clients',
                               null=True, blank=True,
                               help_text='Entreprise - auto-assignée depuis le client si non fournie')
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
        """Génère une référence unique pour la commande"""
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
        """Recalcule les montants totaux à partir des lignes"""
        lignes = self.lignes.all()
        self.montant_total_ht = sum(ligne.montant_ht for ligne in lignes)
        self.montant_total_ttc = sum(ligne.montant_ttc for ligne in lignes)
        self.save(update_fields=['montant_total_ht', 'montant_total_ttc'])


class LigneCommandeClient(models.Model):
    """Ligne de commande client"""
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
        """Calcule automatiquement les montants"""
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
