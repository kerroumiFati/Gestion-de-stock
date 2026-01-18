"""
Serializers pour l'API de distribution mobile
"""
from rest_framework import serializers
from django.utils import timezone
from django.db import models
from .distribution_models import (
    LivreurDistribution, TourneeMobile, ArretTourneeMobile, VenteTourneeMobile,
    LigneVenteTourneeMobile, RapportCaisseMobile, DepenseTourneeMobile, SyncLogMobile,
    CommandeClient, LigneCommandeClient, PlanningHebdomadaire, ClientLivreurHebdo
    # BonLivraisonVan, LigneBonLivraisonVan  # TODO: Models not yet created
)
from .models import Client, Produit, Company, CodePrix, PrixProduit, TypePrix
from django.contrib.auth import get_user_model

User = get_user_model()


class ProduitMobileSerializer(serializers.ModelSerializer):
    """
    Serializer pour les produits - optimisé pour l'application mobile
    Pour la nomenclature complète des produits (pas seulement le stock du van)
    """
    categorie_nom = serializers.CharField(source='categorie.nom', read_only=True)
    unite_mesure_display = serializers.CharField(source='get_unite_mesure_display', read_only=True)
    stock = serializers.SerializerMethodField()

    class Meta:
        model = Produit
        fields = (
            'id', 'reference', 'code_barre', 'designation', 'description',
            'categorie', 'categorie_nom',
            'prixU', 'unite_mesure', 'unite_mesure_display',
            'stock', 'quantite',
            'is_active', 'updated_at'
        )

    def get_stock(self, obj):
        """
        Calcule le stock total depuis ProductStock (somme de tous les entrepôts non-van).
        Exclut les vans pour avoir le stock disponible en entrepôt principal.
        Si ProductStock est vide, utilise le champ quantite du modèle Produit.
        """
        from .models import ProductStock
        # Calculer le stock total depuis ProductStock (entrepôts principaux uniquement, pas les vans)
        total_stock = ProductStock.objects.filter(
            produit=obj,
            warehouse__is_active=True
        ).exclude(
            warehouse__code__icontains='van'
        ).aggregate(total=models.Sum('quantity'))['total']

        # Si pas de stock dans ProductStock, utiliser le champ quantite du produit
        if total_stock is None or total_stock == 0:
            return obj.quantite or 0
        return total_stock


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
    type_prix_code = serializers.SerializerMethodField()
    type_prix_libelle = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = (
            'id', 'nom', 'prenom', 'telephone', 'adresse',
            'lat', 'lng', 'visite', 'ordre_visite', 'solde_actuel',
            'type_prix_code', 'type_prix_libelle', 'updated_at'
        )

    def get_lat(self, obj):
        """Coordonnée GPS latitude"""
        if obj.lat is not None:
            return float(obj.lat)
        return None

    def get_lng(self, obj):
        """Coordonnée GPS longitude"""
        if obj.lng is not None:
            return float(obj.lng)
        return None

    def get_visite(self, obj):
        """Statut de visite - géré côté mobile uniquement"""
        return False

    def get_ordre_visite(self, obj):
        """Ordre de visite - défini lors de la création de la tournée"""
        return None

    def get_solde_actuel(self, obj):
        """Solde du compte client"""
        # Retourner le solde initial du client (champ sur le modèle)
        return float(obj.solde) if obj.solde is not None else 0.0

    def get_type_prix_code(self, obj):
        """Code du type de prix (DETAIL, GROS, SUPERETTE, etc.)"""
        if obj.type_prix:
            return obj.type_prix.code
        return 'DETAIL'  # Valeur par défaut

    def get_type_prix_libelle(self, obj):
        """Libellé du type de prix"""
        if obj.type_prix:
            return obj.type_prix.libelle
        return 'Détail'

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
    entrepot_nom = serializers.CharField(source='entrepot.name', read_only=True, allow_null=True)
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
        """
        Un livreur est disponible s'il est actif ET n'a aucune tournée en cours ou planifiée
        """
        if obj.statut != 'actif':
            return False
        # Vérifier s'il a des tournées actives (planifiée ou en_cours)
        return obj.tournees_actives().count() == 0

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
    client_code = serializers.CharField(source='client.code', read_only=True, allow_null=True)
    # Coordonnées GPS du client
    client_lat = serializers.DecimalField(source='client.lat', max_digits=10, decimal_places=7, read_only=True, allow_null=True)
    client_lng = serializers.DecimalField(source='client.lng', max_digits=10, decimal_places=7, read_only=True, allow_null=True)

    class Meta:
        model = ArretTourneeMobile
        fields = [
            'id', 'tournee', 'client', 'client_nom', 'client_code',
            'client_adresse', 'client_telephone',
            'client_lat', 'client_lng',
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
    # Informations du client pour affichage
    client_nom = serializers.CharField(source='client.nom', read_only=True)
    client_adresse = serializers.CharField(source='client.adresse', read_only=True)
    client_telephone = serializers.CharField(source='client.telephone', read_only=True)
    # Coordonnées GPS du client (pour navigation)
    client_lat = serializers.DecimalField(source='client.lat', max_digits=10, decimal_places=7, read_only=True, allow_null=True)
    client_lng = serializers.DecimalField(source='client.lng', max_digits=10, decimal_places=7, read_only=True, allow_null=True)

    class Meta:
        model = ArretTourneeMobile
        fields = [
            'id', 'client', 'client_nom', 'client_adresse', 'client_telephone',
            'client_lat', 'client_lng',
            'ordre_passage', 'statut',
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
        from API.models import ProductStock

        lignes_data = validated_data.pop('lignes')
        vente = VenteTourneeMobile.objects.create(**validated_data)

        # Récupérer le van du livreur pour décrémenter le stock
        livreur = None
        if vente.tournee and vente.tournee.livreur:
            livreur = vente.tournee.livreur

        for ligne_data in lignes_data:
            ligne = LigneVenteTourneeMobile.objects.create(vente=vente, **ligne_data)

            # Décrémenter le stock du van si le livreur a un entrepôt
            if livreur and livreur.entrepot and ligne.produit:
                try:
                    stock = ProductStock.objects.get(
                        warehouse=livreur.entrepot,
                        produit=ligne.produit
                    )
                    stock.quantity = max(0, stock.quantity - ligne.quantite)
                    stock.save()
                except ProductStock.DoesNotExist:
                    pass  # Pas de stock pour ce produit dans ce van

        # Marquer comme synchronisé
        vente.est_synchronise = True
        vente.date_synchronisation = timezone.now()
        vente.save()

        return vente


class LigneVenteMobileSerializer(serializers.Serializer):
    """Serializer pour les lignes de vente depuis l'app mobile"""
    # Accepter string ou int pour produit (le mobile peut envoyer une string)
    produit = serializers.CharField(max_length=50)
    quantite = serializers.DecimalField(max_digits=10, decimal_places=2)
    prix_unitaire = serializers.DecimalField(max_digits=10, decimal_places=2)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    montant = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)  # Alias pour total


class VenteMobileCreateSerializer(serializers.Serializer):
    """Serializer pour création de vente depuis l'app mobile (format simplifié)"""
    app_id = serializers.CharField(max_length=200, required=False)
    # Accepter string ou int pour client (le mobile peut envoyer une string)
    client = serializers.CharField(max_length=50)
    # ID du livreur pour décrémenter le stock du van (envoyé par l'app mobile)
    livreur = serializers.IntegerField(required=False, allow_null=True)
    mode_paiement = serializers.ChoiceField(choices=['especes', 'credit', 'cheque', 'virement'])
    montant_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    montant_paye = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0)
    montant_rendu = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0)
    reste_a_payer = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0)
    lignes_vente = LigneVenteMobileSerializer(many=True)

    def create(self, validated_data):
        import logging
        import uuid
        from API.models import ProductStock, Client as ClientModel
        from .distribution_models import LivreurDistribution, TourneeMobile, ClientLivreurHebdo

        logger = logging.getLogger(__name__)

        lignes_data = validated_data.pop('lignes_vente')
        client_id_str = validated_data.pop('client')
        livreur_id_from_mobile = validated_data.pop('livreur', None)  # ID du livreur envoyé par l'app mobile
        mode_paiement = validated_data.pop('mode_paiement')
        montant_total = validated_data.pop('montant_total')
        montant_paye = validated_data.pop('montant_paye', 0)
        montant_rendu = validated_data.pop('montant_rendu', 0)
        reste_a_payer = validated_data.pop('reste_a_payer', 0)
        app_id = validated_data.pop('app_id', None)

        # Convertir client_id en int (le mobile peut envoyer une string)
        try:
            client_id = int(str(client_id_str).strip())
        except (ValueError, TypeError):
            raise serializers.ValidationError({'client': f'ID client invalide: {client_id_str}'})

        # Vérifier si une vente avec cet app_id existe déjà (déduplication)
        if app_id:
            existing_vente = VenteTourneeMobile.objects.filter(numero_vente__contains=app_id).first()
            if existing_vente:
                logger.info(f"Vente déjà synchronisée avec app_id={app_id}, retour de la vente existante")
                return existing_vente

        # Récupérer le client
        try:
            client = ClientModel.objects.get(id=client_id)
        except ClientModel.DoesNotExist:
            raise serializers.ValidationError({'client': f'Client introuvable avec ID: {client_id}'})

        # PRIORITÉ 1: Utiliser le livreur_id envoyé par l'app mobile (le plus fiable)
        livreur = None
        if livreur_id_from_mobile:
            try:
                livreur = LivreurDistribution.objects.get(id=livreur_id_from_mobile)
                logger.info(f"Livreur trouvé via ID mobile: {livreur.nom} (ID: {livreur_id_from_mobile})")
            except LivreurDistribution.DoesNotExist:
                logger.warning(f"Livreur avec ID {livreur_id_from_mobile} introuvable, recherche alternative...")

        # PRIORITÉ 2: Chercher dans clients_assignes (assignation directe)
        if not livreur:
            livreur = LivreurDistribution.objects.filter(clients_assignes=client).first()
            if livreur:
                logger.info(f"Livreur trouvé via clients_assignes: {livreur.nom}")

        # PRIORITÉ 3: Chercher via le planning hebdomadaire
        if not livreur:
            jour_semaine = timezone.now().weekday()  # 0=lundi, 6=dimanche
            client_hebdo = ClientLivreurHebdo.objects.filter(
                client=client,
                jour_semaine=jour_semaine,
                is_active=True
            ).select_related('livreur').first()
            if client_hebdo:
                livreur = client_hebdo.livreur
                logger.info(f"Livreur trouvé via planning hebdomadaire: {livreur.nom}")

        # PRIORITÉ 4: Chercher via les tournées actives du jour
        if not livreur:
            today = timezone.now().date()
            arret = ArretTourneeMobile.objects.filter(
                client=client,
                tournee__date_tournee=today,
                tournee__statut__in=['en_cours', 'planifiee']
            ).select_related('tournee__livreur').first()
            if arret and arret.tournee and arret.tournee.livreur:
                livreur = arret.tournee.livreur
                logger.info(f"Livreur trouvé via tournée active: {livreur.nom}")

        if not livreur:
            logger.warning(f"Aucun livreur trouvé pour le client {client.id} ({client.nom}). Le stock ne sera pas décrémenté.")
        else:
            logger.info(f"✅ Livreur trouvé: {livreur.nom} (ID: {livreur.id}), entrepot: {livreur.entrepot.name if livreur.entrepot else 'AUCUN'}")

        # Mapper mode_paiement vers type_paiement
        type_paiement_map = {
            'especes': 'especes',
            'credit': 'credit',
            'cheque': 'cheque',
            'virement': 'virement'
        }

        # Générer un numéro de vente unique (inclure app_id pour traçabilité)
        numero_vente = f"VM-{timezone.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
        if app_id:
            numero_vente = f"{numero_vente}-{app_id[-8:]}"  # Ajouter les 8 derniers caractères de app_id

        # Trouver la tournée active du livreur pour lier la vente
        tournee = None
        arret = None
        today = timezone.now().date()

        if livreur:
            # Chercher une tournée active ou en cours pour ce livreur
            tournee = TourneeMobile.objects.filter(
                livreur=livreur,
                date_tournee=today,
                statut__in=['en_cours', 'planifiee']
            ).first()

            # Si pas de tournée aujourd'hui, chercher la tournée la plus récente
            if not tournee:
                tournee = TourneeMobile.objects.filter(
                    livreur=livreur,
                    statut__in=['en_cours', 'planifiee', 'terminee']
                ).order_by('-date_tournee').first()

            if tournee:
                logger.info(f"Tournée trouvée pour la vente: {tournee.id} ({tournee.date_tournee})")
                # Chercher l'arrêt correspondant au client dans cette tournée
                arret = ArretTourneeMobile.objects.filter(
                    tournee=tournee,
                    client=client
                ).first()
                if arret:
                    logger.info(f"Arrêt trouvé: {arret.id}")
            else:
                logger.warning(f"Aucune tournée trouvée pour le livreur {livreur.id}")

        # Créer la vente
        vente = VenteTourneeMobile.objects.create(
            client=client,
            tournee=tournee,  # Lier à la tournée
            arret=arret,      # Lier à l'arrêt
            numero_vente=numero_vente,
            montant_total=montant_total,
            montant_paye=montant_paye,
            montant_rendu=montant_rendu,
            type_paiement=type_paiement_map.get(mode_paiement, 'especes'),
            date_vente=timezone.now(),
            est_synchronise=True,
            date_synchronisation=timezone.now()
        )

        # Créer les lignes et décrémenter le stock
        logger.info(f"Création de {len(lignes_data)} lignes pour vente {vente.numero_vente}")
        lignes_creees = 0

        for idx, ligne_data in enumerate(lignes_data):
            produit_id_raw = ligne_data.get('produit')
            quantite = ligne_data.get('quantite', 0)
            prix_unitaire = ligne_data.get('prix_unitaire', 0)

            logger.info(f"Ligne {idx}: produit_id_raw={produit_id_raw} (type={type(produit_id_raw).__name__}), quantite={quantite}, prix={prix_unitaire}")

            # Convertir produit_id en int (le mobile peut envoyer une string)
            try:
                produit_id = int(str(produit_id_raw).strip())
            except (ValueError, TypeError) as e:
                logger.error(f"ID produit invalide: {produit_id_raw}, erreur: {e}, ligne ignorée")
                continue

            try:
                produit = Produit.objects.get(id=produit_id)
                logger.info(f"Produit trouvé: {produit.id} - {produit.designation}")
            except Produit.DoesNotExist:
                logger.error(f"Produit introuvable avec ID: {produit_id}, ligne ignorée")
                continue

            # Si prix_unitaire n'est pas fourni ou est 0, utiliser le prix de PrixProduit
            if not prix_unitaire or prix_unitaire == 0:
                prix_unitaire = produit.prixU or 0  # Fallback par défaut

                # Essayer de récupérer le prix du CodePrix par défaut
                type_prix_client = client.type_prix if client else None
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
                        prix_unitaire = float(prix_produit.prix)
                        logger.info(f"Prix récupéré de PrixProduit: {prix_unitaire} pour {produit.designation}")

            # Créer la ligne de vente
            try:
                ligne = LigneVenteTourneeMobile.objects.create(
                    vente=vente,
                    produit=produit,
                    quantite=quantite,
                    prix_unitaire=prix_unitaire,
                    montant_ttc=quantite * prix_unitaire
                )
                lignes_creees += 1
                logger.info(f"Ligne créée: {ligne.id} - {produit.designation} x {quantite}")
            except Exception as e:
                logger.error(f"Erreur création ligne: {e}")

            # Décrémenter le stock du van du livreur
            if livreur and livreur.entrepot:
                try:
                    # Récupérer ou créer le stock dans le van
                    stock, created = ProductStock.objects.get_or_create(
                        warehouse=livreur.entrepot,
                        produit=produit,
                        defaults={'quantity': 0}
                    )
                    if created:
                        logger.info(f"Stock créé pour {produit.designation} dans {livreur.entrepot.name}")

                    # Décrémenter le stock
                    old_qty = stock.quantity
                    stock.quantity = max(0, stock.quantity - quantite)
                    stock.save()
                    logger.info(f"✅ Stock décrémenté: {produit.designation} {old_qty} -> {stock.quantity} (-{quantite}) dans {livreur.entrepot.name}")
                except Exception as e:
                    logger.error(f"❌ Erreur décrémentation stock: {e}")
            elif livreur and not livreur.entrepot:
                logger.warning(f"⚠️ Livreur {livreur.nom} n'a pas d'entrepôt (van) assigné - stock non décrémenté pour produit {produit.id}")
            elif not livreur:
                logger.warning(f"⚠️ Pas de livreur - stock non décrémenté pour produit {produit.id}")

        # Si reste à payer > 0, enregistrer l'info
        if reste_a_payer > 0:
            logger.info(f"Vente avec paiement partiel pour client {client.id} ({client.nom}): reste à payer = {reste_a_payer} DZD")
            # TODO: Ajouter le champ solde_actuel au modèle Client si besoin de suivre les dettes

        logger.info(f"Vente {vente.numero_vente} créée avec {lignes_creees}/{len(lignes_data)} lignes")

        return vente


class TourneeSerializer(serializers.ModelSerializer):
    """Serializer pour Tournee"""
    livreur_nom = serializers.CharField(source='livreur.nom', read_only=True)
    livreur_matricule = serializers.CharField(source='livreur.matricule', read_only=True)
    code_prix_libelle = serializers.CharField(source='code_prix.libelle', read_only=True, allow_null=True)
    code_prix_code = serializers.CharField(source='code_prix.code', read_only=True, allow_null=True)
    arrets = ArretTourneeSerializer(many=True, read_only=True)
    statistiques = serializers.SerializerMethodField()

    class Meta:
        model = TourneeMobile
        fields = [
            'id', 'livreur', 'livreur_nom', 'livreur_matricule',
            'date_tournee', 'numero_tournee', 'statut',
            'code_prix', 'code_prix_libelle', 'code_prix_code',
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
                # Coordonnées GPS du client
                'client_lat': float(arret.client.lat) if arret.client and arret.client.lat else None,
                'client_lng': float(arret.client.lng) if arret.client and arret.client.lng else None,
                # Coordonnées GPS de l'arrêt (capturées lors de la livraison)
                'latitude': float(arret.latitude) if arret.latitude else None,
                'longitude': float(arret.longitude) if arret.longitude else None,
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
    """Serializer pour LigneCommandeClient (lecture)"""
    produit_reference = serializers.CharField(source='produit.reference', read_only=True)
    produit_designation = serializers.CharField(source='produit.designation', read_only=True)
    produit_image = serializers.ImageField(source='produit.image', read_only=True)

    class Meta:
        model = LigneCommandeClient
        fields = [
            'id', 'produit', 'produit_reference', 'produit_designation', 'produit_image',
            'quantite', 'prix_unitaire_ht', 'taux_tva',
            'montant_ht', 'montant_tva', 'montant_ttc',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['montant_ht', 'montant_tva', 'montant_ttc', 'created_at', 'updated_at']


class LigneCommandeClientCreateSerializer(serializers.Serializer):
    """Serializer pour créer des lignes de commande depuis l'application mobile"""
    produit = serializers.PrimaryKeyRelatedField(queryset=Produit.objects.all())
    quantite = serializers.DecimalField(max_digits=10, decimal_places=2)
    prix_unitaire_ht = serializers.DecimalField(max_digits=10, decimal_places=2)
    taux_tva = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, default=0)


class CommandeClientSerializer(serializers.ModelSerializer):
    """Serializer pour lire les commandes clients"""
    lignes = LigneCommandeClientSerializer(many=True, read_only=True)
    client_nom = serializers.CharField(source='client.nom', read_only=True)
    client_prenom = serializers.CharField(source='client.prenom', read_only=True)
    client_telephone = serializers.CharField(source='client.telephone', read_only=True, allow_null=True)
    client_adresse = serializers.CharField(source='client.adresse', read_only=True, allow_null=True)
    # Coordonnées GPS du client (pour navigation)
    client_lat = serializers.DecimalField(source='client.lat', max_digits=10, decimal_places=7, read_only=True, allow_null=True)
    client_lng = serializers.DecimalField(source='client.lng', max_digits=10, decimal_places=7, read_only=True, allow_null=True)
    livreur_nom = serializers.SerializerMethodField()
    # Informations supplémentaires du livreur et du van
    livreur_matricule = serializers.SerializerMethodField()
    vehicule_immatriculation = serializers.SerializerMethodField()
    entrepot_nom = serializers.SerializerMethodField()

    class Meta:
        model = CommandeClient
        fields = [
            'id', 'reference', 'company',
            'client', 'client_nom', 'client_prenom',
            'client_telephone', 'client_adresse',
            'client_lat', 'client_lng',
            'livreur', 'livreur_nom', 'livreur_matricule',
            'vehicule_immatriculation', 'entrepot_nom',
            'statut', 'date_commande', 'date_livraison_souhaitee', 'date_livraison_reelle',
            'montant_total_ht', 'montant_total_ttc',
            # Champs de paiement
            'est_paye', 'type_paiement', 'montant_paye', 'date_paiement',
            'notes', 'notes_preparation',
            'lignes', 'app_id', 'synced_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['reference', 'created_at', 'updated_at', 'synced_at']

    def get_livreur_nom(self, obj):
        """Retourne le nom du livreur"""
        if obj.livreur:
            return obj.livreur.nom
        return None

    def get_livreur_matricule(self, obj):
        """Retourne le matricule du livreur"""
        if obj.livreur:
            return obj.livreur.matricule
        return None

    def get_vehicule_immatriculation(self, obj):
        """Retourne l'immatriculation du véhicule du livreur"""
        if obj.livreur:
            return obj.livreur.vehicule_immatriculation
        return None

    def get_entrepot_nom(self, obj):
        """Retourne le nom du van/entrepôt du livreur"""
        if obj.livreur and obj.livreur.entrepot:
            return obj.livreur.entrepot.name
        return None


class CommandeClientCreateSerializer(serializers.ModelSerializer):
    """Serializer pour créer des commandes depuis l'application mobile"""
    lignes = LigneCommandeClientCreateSerializer(many=True)
    company = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(),
        required=False,
        allow_null=True
    )
    client = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(),
        required=False,
        allow_null=True
    )
    # Champs pour gérer les clients créés localement dans l'app mobile
    app_client_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    client_nom = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    livreur = serializers.PrimaryKeyRelatedField(
        queryset=LivreurDistribution.objects.all(),
        required=False,
        allow_null=True
    )
    # Champs de paiement
    est_paye = serializers.BooleanField(required=False, default=False)
    type_paiement = serializers.ChoiceField(
        choices=CommandeClient.TYPE_PAIEMENT_CHOICES,
        required=False,
        default='non_paye',
        allow_blank=True
    )
    montant_paye = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        default=0
    )
    date_paiement = serializers.DateTimeField(required=False, allow_null=True)

    class Meta:
        model = CommandeClient
        fields = [
            'company', 'client', 'app_client_id', 'client_nom', 'livreur',
            'date_livraison_souhaitee', 'notes', 'app_id', 'lignes',
            # Champs de paiement
            'est_paye', 'type_paiement', 'montant_paye', 'date_paiement'
        ]

    def create(self, validated_data):
        import logging
        logger = logging.getLogger(__name__)

        logger.info('[COMMANDE CREATE] ===== DÉBUT =====')
        print(f'[COMMANDE CREATE] validated_data: {validated_data}')

        lignes_data = validated_data.pop('lignes')
        app_client_id = validated_data.pop('app_client_id', None)
        client_nom = validated_data.pop('client_nom', None)

        # Gérer le client: si client est null mais app_client_id fourni
        client = validated_data.get('client')
        if not client and app_client_id:
            print(f'[COMMANDE CREATE] Client null, recherche par app_client_id: {app_client_id}')
            # Essayer de trouver un client existant avec cet app_client_id
            # ou par nom si fourni
            if client_nom:
                from .distribution_models import Client
                # Rechercher par nom (approximatif)
                client = Client.objects.filter(nom__icontains=client_nom.split()[-1] if client_nom else '').first()
                if client:
                    print(f'[COMMANDE CREATE] Client trouvé par nom: {client.id} - {client.nom}')
                    validated_data['client'] = client
                else:
                    print(f'[COMMANDE CREATE - WARNING] Aucun client trouvé avec le nom: {client_nom}')
                    # On ne peut pas créer la commande sans client valide
                    raise serializers.ValidationError({
                        'client': f'Client introuvable. Veuillez d\'abord synchroniser le client "{client_nom}".'
                    })

        if not validated_data.get('client'):
            print('[COMMANDE CREATE - ERROR] Client manquant après résolution')
            raise serializers.ValidationError({'client': 'Le client est obligatoire pour créer une commande.'})

        # Auto-assigner la company depuis le client si non fournie
        # DÉSACTIVÉ: Pour que les commandes mobile restent avec company=null et apparaissent dans toutes les interfaces
        # client = validated_data.get('client')
        # if not validated_data.get('company') and client:
        #     if hasattr(client, 'company') and client.company:
        #         validated_data['company'] = client.company
        #     else:
        #         # Fallback: utiliser la première company disponible
        #         from .models import Company
        #         default_company = Company.objects.first()
        #         if default_company:
        #             validated_data['company'] = default_company

        # Laisser company=null pour les commandes mobile (permet le filtre Q(company__isnull=True))
        client = validated_data.get('client')
        print(f'[COMMANDE CREATE] Company fournie: {validated_data.get("company")}, sera laissée à null pour compatibilité filtres')

        # Auto-assigner le livreur depuis le client si non fourni
        if not validated_data.get('livreur') and client:
            # ATTENTION: Auto-assignation du livreur - peut causer des problèmes si plusieurs livreurs ont le même client
            print(f'[COMMANDE CREATE - WARNING] Livreur non fourni, auto-assignation depuis client {client.id}')
            # Trouver le livreur assigné à ce client
            livreur = LivreurDistribution.objects.filter(clients_assignes=client).first()
            if livreur:
                print(f'[COMMANDE CREATE] Livreur auto-assigné: {livreur.id} - {livreur.nom}')
                validated_data['livreur'] = livreur
            else:
                print(f'[COMMANDE CREATE - WARNING] Aucun livreur assigné au client {client.id}, commande créée sans livreur')
                # Ne pas lever d'erreur, permettre la création sans livreur
                # Cela pourrait être corrigé manuellement plus tard via l'interface web

        # Créer la commande d'abord pour calculer le montant total
        commande = CommandeClient.objects.create(**validated_data)

        print(f'[COMMANDE CREATE] Commande créée: id={commande.id}, company={commande.company_id if commande.company else None}, livreur={commande.livreur_id if commande.livreur else None}, client={commande.client_id if commande.client else None}')

        # Créer les lignes de commande
        for ligne_data in lignes_data:
            # Retirer les champs calculés s'ils sont présents
            ligne_data.pop('produit_reference', None)
            ligne_data.pop('produit_designation', None)
            # Pour les objets Produit du PrimaryKeyRelatedField
            produit = ligne_data.pop('produit')
            LigneCommandeClient.objects.create(
                commande=commande,
                produit=produit,
                **ligne_data
            )

        # Recalculer les totaux à partir des lignes
        commande.calculer_totaux()

        # Logique intelligente pour montant_paye et est_paye
        type_paiement = commande.type_paiement
        montant_paye = commande.montant_paye
        montant_total = commande.montant_total_ttc

        print(f"[COMMANDE] Avant traitement: type_paiement={type_paiement}, montant_paye={montant_paye}, montant_total={montant_total}")

        # Si montant_paye n'est pas fourni ou est 0, déduire du type_paiement
        if montant_paye == 0:
            if type_paiement in ['especes', 'carte', 'cheque', 'virement']:
                # Paiement immédiat complet
                commande.montant_paye = montant_total
                commande.est_paye = True
                if not commande.date_paiement:
                    commande.date_paiement = timezone.now()
                print(f"[COMMANDE] Paiement complet déduit: montant_paye={commande.montant_paye}")
            elif type_paiement in ['credit', 'non_paye']:
                # Pas de paiement
                commande.montant_paye = 0
                commande.est_paye = False
                commande.date_paiement = None
                print(f"[COMMANDE] Pas de paiement (crédit)")
        else:
            # montant_paye est fourni par l'app mobile
            if montant_paye >= montant_total:
                # Paiement complet
                commande.est_paye = True
                if not commande.date_paiement:
                    commande.date_paiement = timezone.now()
                print(f"[COMMANDE] Paiement complet: montant_paye={montant_paye}")
            else:
                # Paiement partiel
                commande.est_paye = False
                if not commande.date_paiement:
                    commande.date_paiement = timezone.now()
                print(f"[COMMANDE] Paiement partiel: montant_paye={montant_paye}, reste={montant_total - montant_paye}")

        # Marquer comme synchronisé
        commande.synced_at = timezone.now()
        commande.save()

        print(f"[COMMANDE] Après traitement: est_paye={commande.est_paye}, montant_paye={commande.montant_paye}, date_paiement={commande.date_paiement}")

        return commande

    def update(self, instance, validated_data):
        """Mise à jour d'une commande avec ses lignes"""
        import logging
        logger = logging.getLogger(__name__)

        print(f"[COMMANDE UPDATE] ===== DÉBUT UPDATE =====")
        print(f"[COMMANDE UPDATE] Commande ID: {instance.id}")
        print(f"[COMMANDE UPDATE] Data reçue: {validated_data}")

        # Extraire les lignes si présentes
        lignes_data = validated_data.pop('lignes', None)

        # Mettre à jour les champs de base
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            print(f"[COMMANDE UPDATE] Champ '{attr}' mis à jour: {value}")

        # Mettre à jour les lignes si fournies
        if lignes_data is not None:
            print(f"[COMMANDE UPDATE] Nombre de lignes à traiter: {len(lignes_data)}")

            # Compter les lignes avant suppression
            nb_lignes_avant = instance.lignes.count()
            print(f"[COMMANDE UPDATE] Lignes avant suppression: {nb_lignes_avant}")

            # Supprimer les anciennes lignes
            instance.lignes.all().delete()

            # Vérifier que les lignes sont supprimées
            nb_lignes_apres_delete = instance.lignes.count()
            print(f"[COMMANDE UPDATE] Lignes après suppression: {nb_lignes_apres_delete}")

            # Créer les nouvelles lignes
            lignes_creees = []
            for idx, ligne_data in enumerate(lignes_data):
                print(f"[COMMANDE UPDATE] ===== Ligne {idx} =====")
                print(f"[COMMANDE UPDATE] Données brutes reçues: {ligne_data}")
                print(f"[COMMANDE UPDATE] Type de ligne_data: {type(ligne_data)}")
                print(f"[COMMANDE UPDATE] Clés disponibles: {ligne_data.keys() if hasattr(ligne_data, 'keys') else 'N/A'}")

                # Retirer les champs calculés s'ils sont présents
                ligne_data.pop('produit_reference', None)
                ligne_data.pop('produit_designation', None)
                ligne_data.pop('produit_image', None)

                # Pour les objets Produit du PrimaryKeyRelatedField
                produit = ligne_data.pop('produit')
                print(f"[COMMANDE UPDATE] Produit ID: {produit.id if hasattr(produit, 'id') else produit}")

                # Log des données avant création
                print(f"[COMMANDE UPDATE] Données après nettoyage: {ligne_data}")
                print(f"[COMMANDE UPDATE] Prix dans ligne_data: prix_unitaire_ht={ligne_data.get('prix_unitaire_ht', 'NON TROUVÉ')}")

                nouvelle_ligne = LigneCommandeClient.objects.create(
                    commande=instance,
                    produit=produit,
                    **ligne_data
                )

                print(f"[COMMANDE UPDATE] Ligne {idx} créée - ID: {nouvelle_ligne.id}, "
                          f"Qté: {nouvelle_ligne.quantite}, Prix HT: {nouvelle_ligne.prix_unitaire_ht}, "
                          f"Montant HT: {nouvelle_ligne.montant_ht}, Montant TTC: {nouvelle_ligne.montant_ttc}")

                lignes_creees.append(nouvelle_ligne)

            # Vérifier le nombre de lignes après création
            nb_lignes_finales = instance.lignes.count()
            print(f"[COMMANDE UPDATE] Lignes après création: {nb_lignes_finales}")

            # Recalculer les totaux
            print(f"[COMMANDE UPDATE] Appel de calculer_totaux()")
            instance.calculer_totaux()

            # Recharger depuis la DB pour voir les nouvelles valeurs
            instance.refresh_from_db()
            print(f"[COMMANDE UPDATE] Après calculer_totaux - Total HT: {instance.montant_total_ht}, "
                      f"Total TTC: {instance.montant_total_ttc}")

        # Sauvegarder l'instance
        instance.synced_at = timezone.now()
        instance.save()

        print(f"[COMMANDE UPDATE] ===== FIN UPDATE =====")
        print(f"[COMMANDE UPDATE] Valeurs finales - HT: {instance.montant_total_ht}, TTC: {instance.montant_total_ttc}")

        return instance


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


# ========================================
# Planning Hebdomadaire
# ========================================

class PlanningHebdomadaireSerializer(serializers.ModelSerializer):
    """Serializer pour PlanningHebdomadaire"""
    livreur_nom = serializers.CharField(source='livreur.nom', read_only=True)
    livreur_matricule = serializers.CharField(source='livreur.matricule', read_only=True)
    code_prix_libelle = serializers.CharField(source='code_prix.libelle', read_only=True, allow_null=True)
    code_prix_code = serializers.CharField(source='code_prix.code', read_only=True, allow_null=True)
    jour_semaine_display = serializers.CharField(source='get_jour_semaine_display', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)

    class Meta:
        from .distribution_models import PlanningHebdomadaire
        model = PlanningHebdomadaire
        fields = [
            'id', 'company', 'livreur', 'livreur_nom', 'livreur_matricule',
            'jour_semaine', 'jour_semaine_display',
            'code_prix', 'code_prix_libelle', 'code_prix_code',
            'is_active', 'date_debut', 'date_fin', 'notes',
            'created_by', 'created_by_username',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class PlanningHebdomadaireCreateSerializer(serializers.ModelSerializer):
    """Serializer pour créer un planning hebdomadaire"""
    company = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        from .distribution_models import PlanningHebdomadaire
        model = PlanningHebdomadaire
        fields = [
            'company', 'livreur', 'jour_semaine', 'code_prix',
            'is_active', 'date_debut', 'date_fin', 'notes'
        ]

    def create(self, validated_data):
        from .distribution_models import PlanningHebdomadaire

        # Auto-assigner created_by si disponible dans le contexte
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user

        # Auto-assigner company si disponible dans le contexte
        if not validated_data.get('company') and request and hasattr(request, 'company'):
            validated_data['company'] = request.company

        return PlanningHebdomadaire.objects.create(**validated_data)


# ========================================
# Configuration Client-Livreur Hebdomadaire
# ========================================

class ClientLivreurHebdoSerializer(serializers.ModelSerializer):
    """Serializer pour ClientLivreurHebdo"""
    client_nom = serializers.SerializerMethodField()
    client_code = serializers.CharField(source='client.code_client', read_only=True)
    client_telephone = serializers.CharField(source='client.telephone', read_only=True)
    client_adresse = serializers.CharField(source='client.adresse', read_only=True)
    client_lat = serializers.DecimalField(source='client.lat', max_digits=10, decimal_places=7, read_only=True, allow_null=True)
    client_lng = serializers.DecimalField(source='client.lng', max_digits=10, decimal_places=7, read_only=True, allow_null=True)
    livreur_nom = serializers.CharField(source='livreur.nom', read_only=True)
    livreur_matricule = serializers.CharField(source='livreur.matricule', read_only=True)
    jour_semaine_display = serializers.CharField(source='get_jour_semaine_display', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)

    def get_client_nom(self, obj):
        """Retourne le nom complet du client (nom + prénom)"""
        if obj.client:
            nom = obj.client.nom or ''
            prenom = obj.client.prenom or ''
            full_name = f"{nom} {prenom}".strip()
            return full_name if full_name else f"Client #{obj.client.id}"
        return "Client inconnu"

    class Meta:
        model = ClientLivreurHebdo
        fields = [
            'id', 'company', 'client', 'client_nom', 'client_code',
            'client_telephone', 'client_adresse', 'client_lat', 'client_lng',
            'livreur', 'livreur_nom', 'livreur_matricule',
            'jour_semaine', 'jour_semaine_display', 'ordre_passage',
            'is_active', 'date_debut', 'date_fin', 'notes',
            'created_by', 'created_by_username',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ClientLivreurHebdoCreateSerializer(serializers.ModelSerializer):
    """Serializer pour créer une configuration client-livreur hebdomadaire"""

    class Meta:
        model = ClientLivreurHebdo
        fields = [
            'client', 'livreur', 'jour_semaine',
            'ordre_passage', 'is_active', 'date_debut', 'date_fin', 'notes'
        ]
        extra_kwargs = {
            'ordre_passage': {'required': False, 'allow_null': True},
            'is_active': {'required': False, 'default': True},
            'date_debut': {'required': False, 'allow_null': True},
            'date_fin': {'required': False, 'allow_null': True},
            'notes': {'required': False, 'allow_blank': True},
        }
