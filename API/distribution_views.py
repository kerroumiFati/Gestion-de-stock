"""
Vues API pour la gestion de la distribution mobile
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404, render
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
import random
import string

from .distribution_models import (
    LivreurDistribution, TourneeMobile, ArretTourneeMobile, VenteTourneeMobile,
    LigneVenteTourneeMobile, RapportCaisseMobile, DepenseTourneeMobile, SyncLogMobile,
    CommandeClient, LigneCommandeClient
    # BonLivraisonVan, LigneBonLivraisonVan  # TODO: Models not yet created
)
from .distribution_serializers import (
    LivreurSerializer, LivreurDetailSerializer,
    TourneeSerializer, TourneeSyncSerializer,
    ArretTourneeSerializer, ArretTourneeSyncSerializer,
    VenteTourneeSerializer, VenteTourneeCreateSerializer,
    RapportCaisseSerializer, DepenseTourneeSerializer,
    SyncLogSerializer,
    SyncDeltaSerializer, SyncResponseSerializer, MobileSyncPushSerializer,
    CommandeClientSerializer, CommandeClientCreateSerializer, LigneCommandeClientSerializer
    # BonLivraisonVanSerializer, BonLivraisonVanCreateSerializer, BonLivraisonVanMobileSerializer  # TODO: Serializers not yet created
)

User = get_user_model()


class LivreurViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des livreurs de distribution"""
    queryset = LivreurDistribution.objects.all()
    serializer_class = LivreurSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return LivreurDetailSerializer
        return LivreurSerializer

    def get_permissions(self):
        """
        Seuls les administrateurs peuvent créer ou supprimer des livreurs
        Les autres utilisateurs authentifiés peuvent lire
        """
        if self.action in ['create', 'destroy']:
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]

    def generate_password(self, username):
        """
        Générer un mot de passe basé sur username + jour + mois de création
        Format: username + JJMM
        Exemple: LIV001 créé le 13 novembre -> LIV0011311
        """
        from django.utils import timezone
        now = timezone.now()
        jour = now.strftime('%d')  # Jour sur 2 chiffres (ex: 13)
        mois = now.strftime('%m')  # Mois sur 2 chiffres (ex: 11)
        password = f"{username}{jour}{mois}"
        return password

    def create(self, request, *args, **kwargs):
        """Créer un livreur et son compte utilisateur automatiquement"""
        from django.contrib.auth.models import Group

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Sauvegarder le livreur
        livreur = serializer.save()

        # Créer un compte utilisateur si pas encore créé
        username = None
        password = None
        compte_cree = False

        if not livreur.user:
            # Utiliser le matricule comme username
            username = livreur.matricule

            # Vérifier si l'username existe déjà
            if User.objects.filter(username=username).exists():
                username = f"{livreur.matricule}_{livreur.id}"

            # Générer un mot de passe basé sur username + date
            password = self.generate_password(username)

            # Créer l'utilisateur
            user = User.objects.create_user(
                username=username,
                password=password,
                email=livreur.email or '',
                first_name=livreur.nom.split()[0] if livreur.nom else '',
                last_name=' '.join(livreur.nom.split()[1:]) if len(livreur.nom.split()) > 1 else ''
            )

            # Créer le groupe "livreurs" s'il n'existe pas
            livreurs_group, created = Group.objects.get_or_create(name='livreurs')
            if created:
                print('[INFO] Groupe "livreurs" créé automatiquement')

            # Ajouter l'utilisateur au groupe "livreurs"
            user.groups.add(livreurs_group)

            livreur.user = user
            livreur.save()
            compte_cree = True

        # Préparer la réponse avec les informations de connexion
        headers = self.get_success_headers(serializer.data)
        response_data = serializer.data

        if compte_cree:
            response_data = {
                **serializer.data,
                'compte_cree': True,
                'username': username,
                'mot_de_passe_initial': password,
                'groupe': 'livreurs',
                'message': f'Compte créé. Username: {username}, Mot de passe: {password}'
            }

        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['get'])
    def tournees(self, request, pk=None):
        """Récupérer les tournées d'un livreur"""
        livreur = self.get_object()
        date_debut = request.query_params.get('date_debut')
        date_fin = request.query_params.get('date_fin')

        tournees = livreur.tournees.all()

        if date_debut:
            tournees = tournees.filter(date_tournee__gte=date_debut)
        if date_fin:
            tournees = tournees.filter(date_tournee__lte=date_fin)

        serializer = TourneeSerializer(tournees, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def statistiques(self, request, pk=None):
        """Statistiques d'un livreur"""
        livreur = self.get_object()
        periode = request.query_params.get('periode', '30')  # jours

        date_debut = timezone.now().date() - timedelta(days=int(periode))
        tournees = livreur.tournees.filter(date_tournee__gte=date_debut)

        stats = {
            'periode_jours': int(periode),
            'nb_tournees_total': tournees.count(),
            'nb_tournees_terminees': tournees.filter(statut='terminee').count(),
            'nb_tournees_en_cours': tournees.filter(statut='en_cours').count(),
            'nb_tournees_planifiees': tournees.filter(statut='planifiee').count(),
            'taux_completion': 0,
            'ca_total': 0,
            'nb_clients_visites': 0,
        }

        if stats['nb_tournees_total'] > 0:
            stats['taux_completion'] = round(
                stats['nb_tournees_terminees'] / stats['nb_tournees_total'] * 100, 2
            )

        # CA total
        ventes = VenteTourneeMobile.objects.filter(tournee__in=tournees)
        stats['ca_total'] = float(sum(v.montant_total for v in ventes))

        # Clients uniques visités
        arrets_livres = ArretTourneeMobile.objects.filter(
            tournee__in=tournees,
            statut='livre'
        )
        stats['nb_clients_visites'] = arrets_livres.values('client').distinct().count()

        return Response(stats)

    @action(detail=True, methods=['get'])
    def clients_assignes(self, request, pk=None):
        """Récupérer les clients assignés à un livreur"""
        livreur = self.get_object()
        clients = livreur.clients_assignes.all()

        from .distribution_serializers import ClientMobileSerializer
        serializer = ClientMobileSerializer(clients, many=True)
        return Response({
            'livreur_id': livreur.id,
            'livreur_nom': livreur.nom,
            'clients': serializer.data
        })

    @action(detail=False, methods=['post'], url_path='update-location')
    def update_location(self, request):
        """
        Mettre à jour la position GPS du livreur connecté
        POST /API/distribution/livreurs/update-location/
        Body: { "lat": 36.7538, "lng": 3.0588 }
        """
        # Récupérer le livreur du user connecté
        try:
            livreur = LivreurDistribution.objects.get(user=request.user)
        except LivreurDistribution.DoesNotExist:
            return Response(
                {'error': 'Aucun livreur associé à cet utilisateur'},
                status=status.HTTP_404_NOT_FOUND
            )

        lat = request.data.get('lat')
        lng = request.data.get('lng')

        if lat is None or lng is None:
            return Response(
                {'error': 'Les champs lat et lng sont requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Arrondir à 7 décimales
            lat = round(float(lat), 7)
            lng = round(float(lng), 7)

            # Mettre à jour la position
            livreur.current_lat = lat
            livreur.current_lng = lng
            livreur.last_location_update = timezone.now()
            livreur.save(update_fields=['current_lat', 'current_lng', 'last_location_update'])

            return Response({
                'success': True,
                'livreur_id': livreur.id,
                'livreur_nom': livreur.nom,
                'lat': float(livreur.current_lat),
                'lng': float(livreur.current_lng),
                'last_update': livreur.last_location_update
            })
        except (ValueError, TypeError) as e:
            return Response(
                {'error': f'Coordonnées GPS invalides: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def assigner_clients(self, request, pk=None):
        """Assigner des clients à un livreur"""
        livreur = self.get_object()
        client_ids = request.data.get('client_ids', [])

        if not isinstance(client_ids, list):
            return Response(
                {'error': 'client_ids doit être une liste'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from API.models import Client
        clients = Client.objects.filter(id__in=client_ids)
        livreur.clients_assignes.set(clients)

        return Response({
            'message': f'{clients.count()} client(s) assigné(s) avec succès',
            'livreur_id': livreur.id,
            'nb_clients': clients.count()
        })

    @action(detail=True, methods=['post'])
    def ajouter_client(self, request, pk=None):
        """Ajouter un client à un livreur"""
        livreur = self.get_object()
        client_id = request.data.get('client_id')

        if not client_id:
            return Response(
                {'error': 'client_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from API.models import Client
        try:
            client = Client.objects.get(id=client_id)
            livreur.clients_assignes.add(client)

            return Response({
                'message': f'Client {client.nom} {client.prenom} ajouté avec succès',
                'livreur_id': livreur.id,
                'client_id': client.id
            })
        except Client.DoesNotExist:
            return Response(
                {'error': 'Client introuvable'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def retirer_client(self, request, pk=None):
        """Retirer un client d'un livreur"""
        livreur = self.get_object()
        client_id = request.data.get('client_id')

        if not client_id:
            return Response(
                {'error': 'client_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from API.models import Client
        try:
            client = Client.objects.get(id=client_id)
            livreur.clients_assignes.remove(client)

            return Response({
                'message': f'Client {client.nom} {client.prenom} retiré avec succès',
                'livreur_id': livreur.id,
                'client_id': client.id
            })
        except Client.DoesNotExist:
            return Response(
                {'error': 'Client introuvable'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def creer_compte(self, request, pk=None):
        """Créer un compte utilisateur pour un livreur qui n'en a pas"""
        from django.contrib.auth.models import Group

        livreur = self.get_object()

        # Vérifier que l'utilisateur est admin
        if not request.user.is_staff:
            return Response({
                'error': 'Seuls les administrateurs peuvent créer des comptes'
            }, status=status.HTTP_403_FORBIDDEN)

        if livreur.user:
            return Response({
                'error': 'Ce livreur a déjà un compte utilisateur',
                'username': livreur.user.username
            }, status=status.HTTP_400_BAD_REQUEST)

        # Utiliser le matricule comme username
        username = livreur.matricule

        # Vérifier si l'username existe déjà
        if User.objects.filter(username=username).exists():
            username = f"{livreur.matricule}_{livreur.id}"

        # Générer un mot de passe basé sur username + date
        password = self.generate_password(username)

        # Créer l'utilisateur
        user = User.objects.create_user(
            username=username,
            password=password,
            email=livreur.email or '',
            first_name=livreur.nom.split()[0] if livreur.nom else '',
            last_name=' '.join(livreur.nom.split()[1:]) if len(livreur.nom.split()) > 1 else ''
        )

        # Créer le groupe "livreurs" s'il n'existe pas et ajouter l'utilisateur
        livreurs_group, created = Group.objects.get_or_create(name='livreurs')
        user.groups.add(livreurs_group)

        livreur.user = user
        livreur.save()

        return Response({
            'message': 'Compte créé avec succès',
            'username': username,
            'mot_de_passe': password,
            'groupe': 'livreurs',
            'livreur_id': livreur.id,
            'format_mot_de_passe': 'username + jour + mois (JJMM)'
        })

    @action(detail=True, methods=['post'])
    def reinitialiser_mot_de_passe(self, request, pk=None):
        """Réinitialiser le mot de passe d'un livreur"""
        livreur = self.get_object()

        # Vérifier que l'utilisateur est admin
        if not request.user.is_staff:
            return Response({
                'error': 'Seuls les administrateurs peuvent réinitialiser les mots de passe'
            }, status=status.HTTP_403_FORBIDDEN)

        if not livreur.user:
            return Response({
                'error': 'Ce livreur n\'a pas de compte utilisateur. Utilisez l\'action creer_compte d\'abord.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Générer un nouveau mot de passe basé sur username + date actuelle
        new_password = self.generate_password(livreur.user.username)

        # Mettre à jour le mot de passe
        livreur.user.set_password(new_password)
        livreur.user.save()

        return Response({
            'message': 'Mot de passe réinitialisé avec succès',
            'username': livreur.user.username,
            'nouveau_mot_de_passe': new_password,
            'livreur_id': livreur.id,
            'format_mot_de_passe': 'username + jour + mois (JJMM)',
            'info': 'Le mot de passe a été réinitialisé avec la date actuelle'
        })

    @action(detail=True, methods=['get'])
    def infos_connexion(self, request, pk=None):
        """Récupérer les informations de connexion d'un livreur"""
        livreur = self.get_object()

        if not livreur.user:
            return Response({
                'a_compte': False,
                'message': 'Ce livreur n\'a pas de compte utilisateur',
                'livreur_id': livreur.id,
                'livreur_nom': livreur.nom
            })

        return Response({
            'a_compte': True,
            'username': livreur.user.username,
            'email': livreur.user.email,
            'date_creation': livreur.user.date_joined,
            'dernier_login': livreur.user.last_login,
            'livreur_id': livreur.id,
            'livreur_nom': livreur.nom
        })

    @action(detail=True, methods=['get'])
    def stock_van(self, request, pk=None):
        """Récupérer le stock du van assigné au livreur"""
        from API.models import ProductStock, Currency

        livreur = self.get_object()

        if not livreur.entrepot:
            return Response({
                'error': 'Ce livreur n\'a pas de van assigné',
                'livreur_id': livreur.id,
                'livreur_nom': livreur.nom
            }, status=status.HTTP_404_NOT_FOUND)

        # Récupérer la devise par défaut
        currency = Currency.objects.filter(is_default=True, is_active=True).first()
        if not currency:
            currency = Currency.objects.filter(is_active=True).first()
        currency_symbol = currency.symbol if currency else 'DA'

        # Récupérer tous les stocks du van
        stocks = ProductStock.objects.filter(
            warehouse=livreur.entrepot
        ).select_related('produit', 'produit__categorie').order_by('produit__reference')

        # Filtrer les stocks vides si demandé
        hide_empty = request.query_params.get('hide_empty', 'false').lower() == 'true'
        if hide_empty:
            stocks = stocks.filter(quantity__gt=0)

        # Préparer les données
        stocks_data = []
        total_products = 0
        total_quantity = 0
        total_value = 0

        for stock in stocks:
            if stock.quantity > 0 or not hide_empty:
                product_value = float(stock.quantity * stock.produit.prixU if stock.produit.prixU else 0)

                # Déterminer le statut du stock
                if stock.quantity <= 0:
                    stock_status = 'rupture'
                    stock_status_label = 'Rupture'
                elif stock.quantity <= stock.produit.seuil_critique:
                    stock_status = 'critique'
                    stock_status_label = 'Critique'
                elif stock.quantity <= stock.produit.seuil_alerte:
                    stock_status = 'alerte'
                    stock_status_label = 'Alerte'
                else:
                    stock_status = 'ok'
                    stock_status_label = 'OK'

                stocks_data.append({
                    'id': stock.id,
                    'produit_id': stock.produit.id,
                    'reference': stock.produit.reference,
                    'code_barre': stock.produit.code_barre,
                    'designation': stock.produit.designation,
                    'categorie': stock.produit.categorie.nom if stock.produit.categorie else None,
                    'quantite': stock.quantity,
                    'prix_unitaire': float(stock.produit.prixU) if stock.produit.prixU else 0,
                    'valeur': product_value,
                    'unite_mesure': stock.produit.get_unite_mesure_display(),
                    'seuil_alerte': stock.produit.seuil_alerte,
                    'seuil_critique': stock.produit.seuil_critique,
                    'stock_status': stock_status,
                    'stock_status_label': stock_status_label,
                })

                if stock.quantity > 0:
                    total_products += 1
                    total_quantity += stock.quantity
                    total_value += product_value

        return Response({
            'livreur': {
                'id': livreur.id,
                'nom': livreur.nom,
                'matricule': livreur.matricule,
            },
            'van': {
                'id': livreur.entrepot.id,
                'code': livreur.entrepot.code,
                'name': livreur.entrepot.name,
                'is_active': livreur.entrepot.is_active,
            },
            'statistiques': {
                'nb_produits': total_products,
                'nb_references': len(stocks_data),
                'total_quantite': total_quantity,
                'valeur_stock': total_value,
                'currency_symbol': currency_symbol,
            },
            'stocks': stocks_data
        })


class TourneeViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des tournées"""
    queryset = TourneeMobile.objects.all()
    serializer_class = TourneeSerializer
    permission_classes = [AllowAny]  # TODO: Ajouter authentification en production

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filtres
        livreur_id = self.request.query_params.get('livreur')
        assigned_to = self.request.query_params.get('assigned_to')
        date_tournee = self.request.query_params.get('date')
        statut = self.request.query_params.get('statut')

        # Filtre spécial pour l'app mobile : assigned_to='me'
        if assigned_to == 'me':
            # Récupérer le livreur depuis l'utilisateur connecté
            if self.request.user and self.request.user.is_authenticated:
                try:
                    livreur = LivreurDistribution.objects.get(user=self.request.user)
                    queryset = queryset.filter(livreur=livreur)
                except LivreurDistribution.DoesNotExist:
                    # Si pas de livreur lié, retourner queryset vide
                    queryset = queryset.none()
            else:
                # Si pas authentifié, retourner queryset vide
                queryset = queryset.none()
        elif livreur_id:
            queryset = queryset.filter(livreur_id=livreur_id)

        if date_tournee:
            queryset = queryset.filter(date_tournee=date_tournee)
        if statut:
            queryset = queryset.filter(statut=statut)

        return queryset.select_related('livreur').prefetch_related('arrets', 'arrets__client')

    @action(detail=True, methods=['post'])
    def cloturer(self, request, pk=None):
        """Clôturer et verrouiller une tournée"""
        tournee = self.get_object()

        try:
            tournee.cloturer(request.user)
            return Response({
                'message': 'Tournée clôturée avec succès',
                'tournee': TourneeSerializer(tournee).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def demarrer(self, request, pk=None):
        """Démarrer une tournée"""
        tournee = self.get_object()

        if tournee.statut != 'planifiee':
            return Response(
                {'error': 'La tournée ne peut pas être démarrée'},
                status=status.HTTP_400_BAD_REQUEST
            )

        tournee.statut = 'en_cours'
        tournee.heure_debut = timezone.now().time()
        tournee.position_depart_lat = request.data.get('latitude')
        tournee.position_depart_lng = request.data.get('longitude')
        tournee.save()

        return Response({
            'message': 'Tournée démarrée',
            'tournee': TourneeSerializer(tournee).data
        })

    @action(detail=True, methods=['post'])
    def terminer(self, request, pk=None):
        """Terminer une tournée"""
        tournee = self.get_object()

        if tournee.statut != 'en_cours':
            return Response(
                {'error': 'La tournée n\'est pas en cours'},
                status=status.HTTP_400_BAD_REQUEST
            )

        tournee.statut = 'terminee'
        tournee.heure_fin = timezone.now().time()
        tournee.position_fin_lat = request.data.get('latitude')
        tournee.position_fin_lng = request.data.get('longitude')
        tournee.distance_km = request.data.get('distance_km')
        tournee.save()

        return Response({
            'message': 'Tournée terminée',
            'tournee': TourneeSerializer(tournee).data
        })


class ArretTourneeViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des arrêts"""
    queryset = ArretTourneeMobile.objects.all()
    serializer_class = ArretTourneeSerializer
    permission_classes = [AllowAny]  # TODO: Ajouter authentification en production

    def get_queryset(self):
        queryset = super().get_queryset()
        tournee_id = self.request.query_params.get('tournee')

        if tournee_id:
            queryset = queryset.filter(tournee_id=tournee_id)

        return queryset.select_related('tournee', 'client').order_by('ordre_passage')

    @action(detail=True, methods=['post'])
    def livrer(self, request, pk=None):
        """Marquer un arrêt comme livré"""
        arret = self.get_object()

        if arret.tournee.est_cloturee:
            return Response(
                {'error': 'La tournée est clôturée'},
                status=status.HTTP_400_BAD_REQUEST
            )

        arret.statut = 'livre'
        arret.heure_arrivee = request.data.get('heure_arrivee', timezone.now())
        arret.heure_depart = request.data.get('heure_depart', timezone.now())
        arret.latitude = request.data.get('latitude')
        arret.longitude = request.data.get('longitude')
        arret.signature_base64 = request.data.get('signature_base64', '')
        arret.nom_receptionnaire = request.data.get('nom_receptionnaire', '')
        arret.notes = request.data.get('notes', '')
        arret.save()

        return Response({
            'message': 'Arrêt marqué comme livré',
            'arret': ArretTourneeSerializer(arret).data
        })

    @action(detail=True, methods=['post'])
    def echec(self, request, pk=None):
        """Marquer un arrêt comme échec"""
        arret = self.get_object()

        if arret.tournee.est_cloturee:
            return Response(
                {'error': 'La tournée est clôturée'},
                status=status.HTTP_400_BAD_REQUEST
            )

        arret.statut = 'echec'
        arret.heure_arrivee = request.data.get('heure_arrivee', timezone.now())
        arret.latitude = request.data.get('latitude')
        arret.longitude = request.data.get('longitude')
        arret.motif_echec = request.data.get('motif_echec', '')
        arret.notes_echec = request.data.get('notes_echec', '')
        arret.save()

        return Response({
            'message': 'Arrêt marqué comme échec',
            'arret': ArretTourneeSerializer(arret).data
        })


class VenteTourneeViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des ventes"""
    queryset = VenteTourneeMobile.objects.all()
    serializer_class = VenteTourneeSerializer
    permission_classes = [AllowAny]  # TODO: Ajouter authentification en production

    def get_serializer_class(self):
        if self.action == 'create':
            # Détecter le format mobile (lignes_vente) vs format standard (lignes)
            if 'lignes_vente' in self.request.data:
                from .distribution_serializers import VenteMobileCreateSerializer
                return VenteMobileCreateSerializer
            return VenteTourneeCreateSerializer
        return VenteTourneeSerializer

    def create(self, request, *args, **kwargs):
        """Override create pour gérer le format mobile"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vente = serializer.save()

        # Retourner la vente créée
        return Response({
            'id': vente.id,
            'message': 'Vente créée avec succès',
            'montant_total': float(vente.montant_total) if vente.montant_total else 0
        }, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        queryset = super().get_queryset()
        tournee_id = self.request.query_params.get('tournee')

        if tournee_id:
            queryset = queryset.filter(tournee_id=tournee_id)

        return queryset.prefetch_related('lignes', 'lignes__produit')

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Création en masse de ventes (depuis mobile)"""
        ventes_data = request.data.get('ventes', [])

        if not ventes_data:
            return Response(
                {'error': 'Aucune vente fournie'},
                status=status.HTTP_400_BAD_REQUEST
            )

        created_ventes = []
        errors = []

        with transaction.atomic():
            for vente_data in ventes_data:
                serializer = VenteTourneeCreateSerializer(data=vente_data)
                if serializer.is_valid():
                    vente = serializer.save()
                    vente.est_synchronise = True
                    vente.date_synchronisation = timezone.now()
                    vente.save()
                    created_ventes.append(vente)
                else:
                    errors.append({
                        'data': vente_data,
                        'errors': serializer.errors
                    })

        return Response({
            'created': len(created_ventes),
            'errors': errors,
            'ventes': VenteTourneeSerializer(created_ventes, many=True).data
        })


class RapportCaisseViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des rapports de caisse"""
    queryset = RapportCaisseMobile.objects.all()
    serializer_class = RapportCaisseSerializer
    permission_classes = [AllowAny]  # TODO: Ajouter authentification en production

    def get_serializer_class(self):
        """Utiliser RapportCaisseCreateSerializer pour create/update depuis mobile"""
        from .distribution_serializers import RapportCaisseCreateSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return RapportCaisseCreateSerializer
        return RapportCaisseSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        tournee_id = self.request.query_params.get('tournee')
        livreur_id = self.request.query_params.get('livreur')

        if tournee_id:
            queryset = queryset.filter(tournee_id=tournee_id)

        if livreur_id:
            queryset = queryset.filter(tournee__livreur_id=livreur_id)

        return queryset.select_related('tournee', 'tournee__livreur')

    @action(detail=True, methods=['post'])
    def calculer(self, request, pk=None):
        """Recalculer les totaux du rapport"""
        rapport = self.get_object()
        rapport.calculer_totaux()

        return Response({
            'message': 'Totaux recalculés',
            'rapport': RapportCaisseSerializer(rapport).data
        })

    @action(detail=True, methods=['post'])
    def valider(self, request, pk=None):
        """Valider un rapport de caisse"""
        rapport = self.get_object()

        try:
            rapport.valider(request.user)
            return Response({
                'message': 'Rapport validé',
                'rapport': RapportCaisseSerializer(rapport).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def anomalies(self, request):
        """Liste des rapports avec anomalies"""
        rapports = self.queryset.filter(a_des_anomalies=True)
        serializer = self.get_serializer(rapports, many=True)
        return Response(serializer.data)


class CommandeClientViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des commandes clients passées par les livreurs"""
    queryset = CommandeClient.objects.all()
    serializer_class = CommandeClientSerializer
    permission_classes = [AllowAny]  # TODO: Ajouter authentification en production

    def get_serializer_class(self):
        """Utiliser CommandeClientCreateSerializer pour create depuis mobile"""
        if self.action == 'create':
            return CommandeClientCreateSerializer
        return CommandeClientSerializer

    def create(self, request, *args, **kwargs):
        """Override create pour ajouter du logging et gérer les doublons"""
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"=== CREATE COMMANDE REQUEST ===")
        logger.info(f"Data received: {request.data}")

        # Vérifier si une commande avec le même app_id existe déjà
        app_id = request.data.get('app_id')
        if app_id:
            existing = CommandeClient.objects.filter(app_id=app_id).first()
            if existing:
                logger.info(f"Commande avec app_id={app_id} existe déjà, retour de l'existante")
                serializer = CommandeClientSerializer(existing)
                return Response(serializer.data, status=status.HTTP_200_OK)

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Validation errors: {serializer.errors}")
            logger.error(f"Data that failed: {request.data}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            logger.info(f"Commande créée avec succès: {serializer.data}")
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as e:
            logger.error(f"Error creating commande: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self):
        from django.db.models import Q
        queryset = super().get_queryset()

        # Filtrer par company de l'utilisateur OU commandes sans company assignée
        if hasattr(self.request.user, 'company') and self.request.user.company:
            # Inclure les commandes de la company de l'utilisateur ET les commandes sans company
            queryset = queryset.filter(
                Q(company=self.request.user.company) | Q(company__isnull=True)
            )

        # Filtres optionnels
        livreur_id = self.request.query_params.get('livreur')
        client_id = self.request.query_params.get('client')
        statut = self.request.query_params.get('statut')
        date_debut = self.request.query_params.get('date_debut')
        date_fin = self.request.query_params.get('date_fin')

        if livreur_id:
            queryset = queryset.filter(livreur_id=livreur_id)

        if client_id:
            queryset = queryset.filter(client_id=client_id)

        if statut:
            queryset = queryset.filter(statut=statut)

        if date_debut:
            queryset = queryset.filter(date_commande__gte=date_debut)

        if date_fin:
            queryset = queryset.filter(date_commande__lte=date_fin)

        return queryset.select_related('client', 'livreur').prefetch_related('lignes', 'lignes__produit')

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Création en masse de commandes (depuis mobile)"""
        commandes_data = request.data.get('commandes', [])

        if not commandes_data:
            return Response(
                {'error': 'Aucune commande fournie'},
                status=status.HTTP_400_BAD_REQUEST
            )

        created_commandes = []
        errors = []

        with transaction.atomic():
            for commande_data in commandes_data:
                serializer = CommandeClientCreateSerializer(data=commande_data)
                if serializer.is_valid():
                    commande = serializer.save()
                    created_commandes.append(commande)
                else:
                    errors.append({
                        'data': commande_data,
                        'errors': serializer.errors
                    })

        return Response({
            'created': len(created_commandes),
            'errors': errors,
            'commandes': CommandeClientSerializer(created_commandes, many=True).data
        })

    @action(detail=True, methods=['patch'])
    def changer_statut(self, request, pk=None):
        """Changer le statut d'une commande"""
        commande = self.get_object()
        nouveau_statut = request.data.get('statut')

        if not nouveau_statut:
            return Response(
                {'error': 'Statut requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if nouveau_statut not in dict(CommandeClient.STATUT_CHOICES):
            return Response(
                {'error': f'Statut invalide. Choix: {[s[0] for s in CommandeClient.STATUT_CHOICES]}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        commande.statut = nouveau_statut

        # Si livré, enregistrer la date de livraison réelle
        if nouveau_statut == 'delivered':
            commande.date_livraison_reelle = timezone.now()

        commande.save()

        return Response({
            'message': f'Statut changé à {nouveau_statut}',
            'commande': CommandeClientSerializer(commande).data
        })

    @action(detail=False, methods=['get'])
    def en_attente(self, request):
        """Liste des commandes en attente"""
        commandes = self.get_queryset().filter(statut='pending')
        serializer = CommandeClientSerializer(commandes, many=True)
        return Response(serializer.data)


class SyncViewSet(viewsets.ViewSet):
    """ViewSet pour la synchronisation mobile"""
    permission_classes = [AllowAny]  # TODO: Ajouter authentification en production

    @action(detail=False, methods=['post'])
    def pull(self, request):
        """Pull: Récupérer les données depuis le serveur (Serveur -> Mobile)"""
        serializer = SyncDeltaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        livreur_id = serializer.validated_data['livreur_id']
        derniere_sync = serializer.validated_data.get('derniere_sync')

        livreur = get_object_or_404(LivreurDistribution, id=livreur_id)

        # Récupérer les tournées modifiées depuis la dernière sync
        tournees = TourneeMobile.objects.filter(livreur=livreur)

        if derniere_sync:
            tournees = tournees.filter(updated_at__gte=derniere_sync)
        else:
            # Première sync: tournées du jour et futures
            aujourd_hui = timezone.now().date()
            tournees = tournees.filter(date_tournee__gte=aujourd_hui)

        # Exclure les tournées clôturées (sauf si dernière sync)
        if not derniere_sync:
            tournees = tournees.exclude(est_cloturee=True)

        tournees = tournees.prefetch_related('arrets', 'arrets__client')

        # Log de sync
        sync_log = SyncLogMobile.objects.create(
            livreur=livreur,
            type_sync='pull',
            statut='succes',
            nb_tournees=tournees.count(),
            nb_arrets=sum(t.arrets.count() for t in tournees),
            device_id=serializer.validated_data.get('device_id', ''),
            app_version=serializer.validated_data.get('app_version', '')
        )

        response_data = {
            'timestamp': timezone.now(),
            'tournees': TourneeSyncSerializer(tournees, many=True).data,
            'nb_tournees': tournees.count(),
            'nb_arrets': sum(t.arrets.count() for t in tournees),
            'message': f'Synchronisation réussie: {tournees.count()} tournée(s)'
        }

        return Response(response_data)

    @action(detail=False, methods=['post'])
    def push(self, request):
        """Push: Envoyer les données vers le serveur (Mobile -> Serveur)"""
        serializer = MobileSyncPushSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        livreur_id = serializer.validated_data['livreur_id']
        livreur = get_object_or_404(LivreurDistribution, id=livreur_id)

        nb_ventes = 0
        nb_arrets = 0
        errors = []

        with transaction.atomic():
            # Synchroniser les ventes
            ventes_data = serializer.validated_data.get('ventes', [])
            for vente_data in ventes_data:
                vente_serializer = VenteTourneeCreateSerializer(data=vente_data)
                if vente_serializer.is_valid():
                    vente = vente_serializer.save()
                    vente.est_synchronise = True
                    vente.date_synchronisation = timezone.now()
                    vente.save()
                    nb_ventes += 1
                else:
                    errors.append({
                        'type': 'vente',
                        'data': vente_data,
                        'errors': vente_serializer.errors
                    })

            # Synchroniser les mises à jour d'arrêts
            arrets_updates = serializer.validated_data.get('arrets_updates', [])
            for arret_data in arrets_updates:
                arret_id = arret_data.get('id')
                if arret_id:
                    try:
                        arret = ArretTourneeMobile.objects.get(id=arret_id)
                        if not arret.tournee.est_cloturee:
                            for field, value in arret_data.items():
                                if field != 'id':
                                    setattr(arret, field, value)
                            arret.save()
                            nb_arrets += 1
                    except ArretTournee.DoesNotExist:
                        errors.append({
                            'type': 'arret',
                            'error': f'Arrêt {arret_id} introuvable'
                        })

            # Log de sync
            sync_log = SyncLogMobile.objects.create(
                livreur=livreur,
                type_sync='push',
                statut='succes' if not errors else 'partiel',
                nb_ventes=nb_ventes,
                nb_arrets=nb_arrets,
                message=f'Synchronisé: {nb_ventes} vente(s), {nb_arrets} arrêt(s)',
                erreur_details=str(errors) if errors else '',
                device_id=serializer.validated_data.get('device_id', ''),
                app_version=serializer.validated_data.get('app_version', '')
            )

        return Response({
            'success': True,
            'nb_ventes': nb_ventes,
            'nb_arrets': nb_arrets,
            'errors': errors,
            'message': f'Synchronisation réussie: {nb_ventes} vente(s), {nb_arrets} arrêt(s)'
        })

    @action(detail=False, methods=['get'])
    def logs(self, request):
        """Récupérer l'historique des synchronisations"""
        livreur_id = request.query_params.get('livreur')

        if not livreur_id:
            return Response(
                {'error': 'livreur_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        logs = SyncLogMobile.objects.filter(livreur_id=livreur_id).order_by('-date_sync')[:50]
        serializer = SyncLogSerializer(logs, many=True)
        return Response(serializer.data)


# TODO: BonLivraisonVanViewSet removed - models not yet created
# Re-add when BonLivraisonVan and LigneBonLivraisonVan models are implemented


############################
# Produits pour Mobile App #
############################

class ProduitMobileViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour la nomenclature des produits - app mobile
    Liste TOUS les produits disponibles (pas seulement le stock du van)
    Pour permettre aux livreurs de passer des commandes
    """
    from .distribution_serializers import ProduitMobileSerializer
    from .models import Produit

    queryset = Produit.objects.filter(is_active=True).order_by('designation')
    serializer_class = ProduitMobileSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Pas de pagination pour l'app mobile

    def get_queryset(self):
        """Filtre par company de l'utilisateur"""
        queryset = super().get_queryset()

        # Filtrer par company (utiliser request.company du middleware)
        if hasattr(self.request, 'company') and self.request.company:
            queryset = queryset.filter(company=self.request.company)

        return queryset
