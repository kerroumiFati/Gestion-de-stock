"""
Serializers pour l'API de distribution mobile
"""
from rest_framework import serializers
from django.utils import timezone
from .distribution_models import (
    LivreurDistribution, TourneeMobile, ArretTourneeMobile, VenteTourneeMobile,
    LigneVenteTourneeMobile, RapportCaisseMobile, DepenseTourneeMobile, SyncLogMobile,
    CommandeClient, LigneCommandeClient
    # BonLivraisonVan, LigneBonLivraisonVan  # TODO: Models not yet created
)
from .models import Client, Produit
from django.contrib.auth import get_user_model

User = get_user_model()


class ProduitMobileSerializer(serializers.ModelSerializer):
    """
    Serializer pour les produits - optimisé pour l'application mobile
    Pour la nomenclature complète des produits (pas seulement le stock du van)
    """
    categorie_nom = serializers.CharField(source='categorie.nom', read_only=True)
    unite_mesure_display = serializers.CharField(source='get_unite_mesure_display', read_only=True)
    stock = serializers.IntegerField(source='quantite', read_only=True)

    class Meta:
        model = Produit
        fields = (
            'id', 'reference', 'code_barre', 'designation', 'description',
            'categorie', 'categorie_nom',
            'prixU', 'unite_mesure', 'unite_mesure_display',
            'stock', 'quantite',
            'is_active', 'updated_at'
        )


class ClientMobileSerializer(serializers.ModelSerializer):
    """
    Serializer pour les clients - optimisé pour l'application mobile
    Inclut tous les champs nécessaires pour la synchronisation offline
    """
    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()
    visite = serializers.SerializerMethodField()
    ordre_visite = serializers.SerializerMethodField()
    solde_actuel = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = (
            'id', 'nom', 'prenom', 'telephone', 'adresse',
            'lat', 'lng', 'visite', 'ordre_visite', 'solde_actuel', 'updated_at'
        )

    def get_lat(self, obj):
        """Coordonnée GPS latitude - à implémenter si disponible"""
        return None

    def get_lng(self, obj):
        """Coordonnée GPS longitude - à implémenter si disponible"""
        return None

    def get_visite(self, obj):
        """Statut de visite - géré côté mobile uniquement"""
        return False

    def get_ordre_visite(self, obj):
        """Ordre de visite - défini lors de la création de la tournée"""
        return None

    def get_solde_actuel(self, obj):
        """Solde du compte client - TODO: calculer depuis les ventes"""
        return 0.0

    def get_updated_at(self, obj):
        """Timestamp de dernière mise à jour"""
        if hasattr(obj, 'updated_at') and obj.updated_at:
            return obj.updated_at.isoformat()
        elif hasattr(obj, 'created_at') and obj.created_at:
            return obj.created_at.isoformat()
        return timezone.now().isoformat()


class LivreurSerializer(serializers.ModelSerializer):
    """Serializer pour LivreurDistribution"""
    username = serializers.SerializerMethodField()
    has_user_account = serializers.SerializerMethodField()
    entrepot_nom = serializers.CharField(source='entrepot.nom', read_only=True, allow_null=True)
    tournees_actives_count = serializers.SerializerMethodField()

    # Champs de compatibilité avec l'ancien frontend
    full_name = serializers.CharField(source='nom', read_only=True)
    vehicule_type = serializers.CharField(source='vehicule_marque', read_only=True)
    immatriculation = serializers.CharField(source='vehicule_immatriculation', read_only=True)
    is_disponible = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = LivreurDistribution
        fields = [
            'id', 'matricule', 'nom', 'telephone', 'email',
            'vehicule_immatriculation', 'vehicule_marque',
            'statut', 'date_embauche', 'entrepot', 'entrepot_nom',
            'username', 'has_user_account', 'tournees_actives_count',
            'full_name', 'vehicule_type', 'immatriculation', 'is_disponible', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_username(self, obj):
        return obj.user.username if obj.user else None

    def get_has_user_account(self, obj):
        return obj.user is not None

    def get_is_disponible(self, obj):
        return obj.statut == 'actif'

    def get_is_active(self, obj):
        return obj.statut == 'actif'

    def get_tournees_actives_count(self, obj):
        return obj.tournees_actives().count()


class LivreurDetailSerializer(LivreurSerializer):
    """Serializer détaillé pour LivreurDistribution"""
    statistiques = serializers.SerializerMethodField()

    class Meta(LivreurSerializer.Meta):
        fields = LivreurSerializer.Meta.fields + ['statistiques']

    def get_statistiques(self, obj):
        from django.db.models import Count, Sum, Avg
        from django.utils import timezone
        from datetime import timedelta

        # Stats des 30 derniers jours
        date_debut = timezone.now().date() - timedelta(days=30)
        tournees = obj.tournees.filter(date_tournee__gte=date_debut)

        return {
            'nb_tournees_30j': tournees.count(),
            'nb_tournees_terminees': tournees.filter(statut='terminee').count(),
            'taux_completion': round(
                tournees.filter(statut='terminee').count() / tournees.count() * 100
                if tournees.count() > 0 else 0, 2
            ),
        }


class ArretTourneeSerializer(serializers.ModelSerializer):
    """Serializer pour ArretTournee"""
    client_nom = serializers.CharField(source='client.nom', read_only=True)
    client_adresse = serializers.CharField(source='client.adresse', read_only=True)
    client_telephone = serializers.CharField(source='client.telephone', read_only=True)
    client_code = serializers.CharField(source='client.code_client', read_only=True)

    class Meta:
        model = ArretTourneeMobile
        fields = [
            'id', 'tournee', 'client', 'client_nom', 'client_code',
            'client_adresse', 'client_telephone',
            'ordre_passage', 'statut',
            'heure_prevue', 'heure_arrivee', 'heure_depart',
            'latitude', 'longitude',
            'signature_base64', 'photo_livraison', 'nom_receptionnaire',
            'motif_echec', 'notes_echec', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ArretTourneeSyncSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour synchronisation mobile"""
    class Meta:
        model = ArretTourneeMobile
        fields = [
            'id', 'client', 'ordre_passage', 'statut',
            'heure_prevue', 'heure_arrivee', 'heure_depart',
            'latitude', 'longitude',
            'signature_base64', 'nom_receptionnaire',
            'motif_echec', 'notes_echec', 'notes'
        ]


class LigneVenteTourneeSerializer(serializers.ModelSerializer):
    """Serializer pour LigneVenteTournee"""
    produit_reference = serializers.CharField(source='produit.reference', read_only=True)
    produit_designation = serializers.CharField(source='produit.designation', read_only=True)

    class Meta:
        model = LigneVenteTourneeMobile
        fields = [
            'id', 'vente', 'produit', 'produit_reference', 'produit_designation',
            'quantite', 'prix_unitaire', 'taux_tva',
            'montant_ht', 'montant_tva', 'montant_ttc',
            'created_at'
        ]
        read_only_fields = ['montant_ht', 'montant_tva', 'montant_ttc', 'created_at']


class VenteTourneeSerializer(serializers.ModelSerializer):
    """Serializer pour VenteTournee"""
    lignes = LigneVenteTourneeSerializer(many=True, read_only=True)
    client_nom = serializers.CharField(source='client.nom', read_only=True)

    class Meta:
        model = VenteTourneeMobile
        fields = [
            'id', 'tournee', 'arret', 'client', 'client_nom',
            'numero_vente', 'date_vente',
            'montant_ht', 'montant_tva', 'montant_total',
            'type_paiement', 'montant_paye', 'montant_rendu',
            'est_synchronise', 'date_synchronisation',
            'notes', 'lignes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'est_synchronise', 'date_synchronisation']


class VenteTourneeCreateSerializer(serializers.ModelSerializer):
    """Serializer pour création de vente depuis mobile"""
    lignes = LigneVenteTourneeSerializer(many=True)

    class Meta:
        model = VenteTourneeMobile
        fields = [
            'tournee', 'arret', 'client',
            'numero_vente', 'date_vente',
            'montant_ht', 'montant_tva', 'montant_total',
            'type_paiement', 'montant_paye', 'montant_rendu',
            'notes', 'lignes'
        ]

    def create(self, validated_data):
        lignes_data = validated_data.pop('lignes')
        vente = VenteTourneeMobile.objects.create(**validated_data)

        for ligne_data in lignes_data:
            LigneVenteTourneeMobile.objects.create(vente=vente, **ligne_data)

        # Marquer comme synchronisé
        vente.est_synchronise = True
        vente.date_synchronisation = timezone.now()
        vente.save()

        return vente


class TourneeSerializer(serializers.ModelSerializer):
    """Serializer pour Tournee"""
    livreur_nom = serializers.CharField(source='livreur.nom', read_only=True)
    livreur_matricule = serializers.CharField(source='livreur.matricule', read_only=True)
    arrets = ArretTourneeSerializer(many=True, read_only=True)
    statistiques = serializers.SerializerMethodField()

    class Meta:
        model = TourneeMobile
        fields = [
            'id', 'livreur', 'livreur_nom', 'livreur_matricule',
            'date_tournee', 'numero_tournee', 'statut',
            'heure_debut', 'heure_fin',
            'position_depart_lat', 'position_depart_lng',
            'position_fin_lat', 'position_fin_lng',
            'distance_km', 'argent_depart',
            'est_cloturee', 'date_cloture', 'cloturee_par',
            'notes', 'arrets', 'statistiques',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'est_cloturee', 'date_cloture']

    def get_statistiques(self, obj):
        import json
        from decimal import Decimal

        stats = obj.stats()

        # Ajouter détails des arrêts par statut
        arrets = obj.arrets.all().select_related('client')
        arrets_visites = []
        arrets_restants = []

        for arret in arrets:
            arret_data = {
                'id': arret.id,
                'client_nom': arret.client.nom if arret.client else 'Client inconnu',
                'client_prenom': arret.client.prenom if arret.client else '',
                'adresse': arret.client.adresse if arret.client else '',
                'ordre': arret.ordre_passage,
                'heure_prevue': str(arret.heure_prevue) if arret.heure_prevue else None,
                'statut': arret.statut,
                'heure_arrivee': str(arret.heure_arrivee) if arret.heure_arrivee else None,
                'nom_receptionnaire': arret.nom_receptionnaire or '',
                'motif_echec': arret.motif_echec or ''
            }

            if arret.statut in ['livre', 'echec']:
                arrets_visites.append(arret_data)
            else:
                arrets_restants.append(arret_data)

        stats['arrets_visites'] = arrets_visites
        stats['arrets_restants'] = arrets_restants

        # Ajouter informations caisse si disponible
        try:
            rapport_caisse = obj.rapport_caisse

            # Détail des billets
            detail_billets = {}
            if hasattr(rapport_caisse, 'detail_billets_json') and rapport_caisse.detail_billets_json:
                try:
                    detail_billets = json.loads(rapport_caisse.detail_billets_json)
                except (json.JSONDecodeError, ValueError):
                    detail_billets = {}

            stats['caisse'] = {
                'fonds_depart': float(rapport_caisse.fonds_depart or 0),
                'total_especes': float(rapport_caisse.total_especes or 0),
                'total_cartes': float(rapport_caisse.total_cartes or 0),
                'total_cheques': float(rapport_caisse.total_cheques or 0),
                'total_credits': float(rapport_caisse.total_credits or 0),
                'total_encaissements': float(rapport_caisse.total_encaissements or 0),
                'total_depenses': float(rapport_caisse.total_depenses or 0),
                'solde_final_theorique': float(rapport_caisse.solde_final_theorique or 0),
                'solde_final_reel': float(rapport_caisse.solde_final_reel or 0),
                'ecart': float(rapport_caisse.ecart or 0),
                'detail_billets': detail_billets,
                'statut': rapport_caisse.statut
            }
        except RapportCaisseMobile.DoesNotExist:
            stats['caisse'] = None

        return stats


class TourneeSyncSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour synchronisation mobile"""
    arrets = ArretTourneeSyncSerializer(many=True, read_only=True)

    class Meta:
        model = TourneeMobile
        fields = [
            'id', 'date_tournee', 'numero_tournee', 'statut',
            'heure_debut', 'heure_fin',
            'position_depart_lat', 'position_depart_lng',
            'distance_km', 'argent_depart', 'arrets'
        ]


class DepenseTourneeSerializer(serializers.ModelSerializer):
    """Serializer pour DepenseTournee"""
    class Meta:
        model = DepenseTourneeMobile
        fields = [
            'id', 'rapport_caisse', 'type_depense', 'montant',
            'description', 'photo_recu', 'date_depense',
            'created_at'
        ]
        read_only_fields = ['created_at']


class RapportCaisseSerializer(serializers.ModelSerializer):
    """Serializer pour RapportCaisse"""
    depenses = DepenseTourneeSerializer(many=True, read_only=True)
    tournee_numero = serializers.CharField(source='tournee.numero_tournee', read_only=True)
    livreur_nom = serializers.CharField(source='tournee.livreur.nom', read_only=True)

    class Meta:
        model = RapportCaisseMobile
        fields = [
            'id', 'tournee', 'tournee_numero', 'livreur_nom',
            'fonds_depart',
            'total_especes', 'total_cartes', 'total_cheques', 'total_credits',
            'total_encaissements',
            'carburant', 'reparations', 'autres_depenses', 'total_depenses',
            'solde_final_theorique', 'solde_final_reel', 'ecart',
            'justification_ecart',
            'statut', 'valide_par', 'date_validation',
            'a_des_anomalies', 'notes_anomalies',
            'depenses',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'total_encaissements', 'total_depenses',
            'solde_final_theorique', 'ecart', 'a_des_anomalies',
            'created_at', 'updated_at'
        ]


class SyncLogSerializer(serializers.ModelSerializer):
    """Serializer pour SyncLog"""
    livreur_nom = serializers.CharField(source='livreur.nom', read_only=True)

    class Meta:
        model = SyncLogMobile
        fields = [
            'id', 'livreur', 'livreur_nom',
            'type_sync', 'statut',
            'nb_tournees', 'nb_ventes', 'nb_arrets',
            'message', 'erreur_details',
            'date_sync', 'duree_secondes',
            'device_id', 'app_version'
        ]
        read_only_fields = ['date_sync']


# Serializers pour synchronisation complète


class SyncDeltaSerializer(serializers.Serializer):
    """Serializer pour les deltas de synchronisation (changements depuis dernière sync)"""
    derniere_sync = serializers.DateTimeField(required=False, allow_null=True)
    livreur_id = serializers.IntegerField(required=True)
    device_id = serializers.CharField(max_length=100, required=False)
    app_version = serializers.CharField(max_length=20, required=False)


class SyncResponseSerializer(serializers.Serializer):
    """Serializer pour la réponse de synchronisation"""
    timestamp = serializers.DateTimeField()
    tournees = TourneeSyncSerializer(many=True)
    nb_tournees = serializers.IntegerField()
    nb_arrets = serializers.IntegerField()
    message = serializers.CharField()


class MobileSyncPushSerializer(serializers.Serializer):
    """Serializer pour push de données depuis mobile vers serveur"""
    livreur_id = serializers.IntegerField()
    device_id = serializers.CharField(max_length=100, required=False)
    app_version = serializers.CharField(max_length=20, required=False)

    # Données à synchroniser
    ventes = VenteTourneeCreateSerializer(many=True, required=False)
    arrets_updates = ArretTourneeSyncSerializer(many=True, required=False)
    tournee_updates = serializers.DictField(required=False)
    depenses = DepenseTourneeSerializer(many=True, required=False)


# ========================================
# Serializers pour Commandes Clients
# ========================================

class LigneCommandeClientSerializer(serializers.ModelSerializer):
    """Serializer pour LigneCommandeClient"""
    produit_reference = serializers.CharField(source='produit.reference', read_only=True)
    produit_designation = serializers.CharField(source='produit.designation', read_only=True)

    class Meta:
        model = LigneCommandeClient
        fields = [
            'id', 'produit', 'produit_reference', 'produit_designation',
            'quantite', 'prix_unitaire_ht', 'taux_tva',
            'montant_ht', 'montant_tva', 'montant_ttc',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['montant_ht', 'montant_tva', 'montant_ttc', 'created_at', 'updated_at']


class CommandeClientSerializer(serializers.ModelSerializer):
    """Serializer pour lire les commandes clients"""
    lignes = LigneCommandeClientSerializer(many=True, read_only=True)
    client_nom = serializers.CharField(source='client.nom', read_only=True)
    client_prenom = serializers.CharField(source='client.prenom', read_only=True)
    livreur_nom = serializers.CharField(source='livreur.nom', read_only=True)

    class Meta:
        model = CommandeClient
        fields = [
            'id', 'reference', 'company',
            'client', 'client_nom', 'client_prenom',
            'livreur', 'livreur_nom',
            'statut', 'date_commande', 'date_livraison_souhaitee', 'date_livraison_reelle',
            'montant_total_ht', 'montant_total_ttc',
            'notes', 'notes_preparation',
            'lignes', 'app_id', 'synced_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['reference', 'created_at', 'updated_at', 'synced_at']


class CommandeClientCreateSerializer(serializers.ModelSerializer):
    """Serializer pour créer des commandes depuis l'application mobile"""
    lignes = LigneCommandeClientSerializer(many=True)

    class Meta:
        model = CommandeClient
        fields = [
            'company', 'client', 'livreur',
            'date_livraison_souhaitee', 'notes', 'app_id', 'lignes'
        ]

    def create(self, validated_data):
        lignes_data = validated_data.pop('lignes')
        commande = CommandeClient.objects.create(**validated_data)

        for ligne_data in lignes_data:
            # Retirer les champs calculés s'ils sont présents
            ligne_data.pop('produit_reference', None)
            ligne_data.pop('produit_designation', None)
            LigneCommandeClient.objects.create(commande=commande, **ligne_data)

        # Marquer comme synchronisé
        commande.synced_at = timezone.now()
        commande.save()

        return commande


class RapportCaisseCreateSerializer(serializers.ModelSerializer):
    """Serializer pour créer/mettre à jour un rapport de caisse depuis l'app mobile"""
    depenses = DepenseTourneeSerializer(many=True, required=False)

    class Meta:
        model = RapportCaisseMobile
        fields = [
            'tournee', 'fonds_depart',
            'total_especes', 'total_cartes', 'total_cheques', 'total_credits',
            'carburant', 'reparations', 'autres_depenses',
            'solde_final_reel', 'justification_ecart',
            'notes_anomalies', 'depenses'
        ]

    def create(self, validated_data):
        depenses_data = validated_data.pop('depenses', [])
        rapport = RapportCaisseMobile.objects.create(**validated_data)

        for depense_data in depenses_data:
            DepenseTourneeMobile.objects.create(rapport_caisse=rapport, **depense_data)

        # Calculer les totaux
        rapport.calculer_totaux()

        return rapport

    def update(self, instance, validated_data):
        depenses_data = validated_data.pop('depenses', None)

        # Mettre à jour les champs
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Mettre à jour les dépenses si fournies
        if depenses_data is not None:
            # Supprimer les anciennes dépenses
            instance.depenses.all().delete()
            # Créer les nouvelles
            for depense_data in depenses_data:
                DepenseTourneeMobile.objects.create(rapport_caisse=instance, **depense_data)

        # Recalculer les totaux
        instance.calculer_totaux()

        return instance


# ========================================
# TODO: Serializers for BonLivraisonVan removed - models not yet created
# Re-add when BonLivraisonVan and LigneBonLivraisonVan models are implemented
