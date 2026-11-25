"""
Vues API pour la gestion de la distribution mobile
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from .mixins import TenantFilterMixin
from django.utils import timezone
from django.db import transaction, models
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, render
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
import random
import string

from .distribution_models import (
    LivreurDistribution, TourneeMobile, ArretTourneeMobile, VenteTourneeMobile,
    LigneVenteTourneeMobile, RapportCaisseMobile, DepenseTourneeMobile, SyncLogMobile,
    CommandeClient, LigneCommandeClient, PlanningHebdomadaire, ClientLivreurHebdo,
    EncaissementCommande,
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
    CommandeClientSerializer, CommandeClientCreateSerializer, LigneCommandeClientSerializer,
    PlanningHebdomadaireSerializer, PlanningHebdomadaireCreateSerializer,
    ClientLivreurHebdoSerializer, ClientLivreurHebdoCreateSerializer
    # BonLivraisonVanSerializer, BonLivraisonVanCreateSerializer, BonLivraisonVanMobileSerializer  # TODO: Serializers not yet created
)

User = get_user_model()


def _parse_date_param(valeur, nom):
    """Date YYYY-MM-DD d'un paramètre d'URL ; 400 si invalide."""
    from rest_framework.exceptions import ValidationError
    try:
        return datetime.strptime(str(valeur).strip()[:10], '%Y-%m-%d').date()
    except (TypeError, ValueError):
        raise ValidationError({nom: 'Date invalide (format attendu : AAAA-MM-JJ)'})


# Commande affectée à un livreur (stock transféré dans son van), pas encore livrée
STATUTS_COMMANDE_AFFECTEE = ('confirmed', 'preparing', 'ready')


def _avertissement_stock_van(commande, quantites_avant):
    """Texte d'avertissement si une quantité augmentée dépasse le stock du van du livreur
    (besoin = toutes ses commandes affectées non livrées), sinon None."""
    from .models import ProductStock
    if commande.statut not in STATUTS_COMMANDE_AFFECTEE or not commande.livreur_id:
        return None
    livreur = LivreurDistribution.objects.filter(pk=commande.livreur_id).select_related('entrepot').first()
    van = livreur.entrepot if livreur else None
    if van is None:
        return None
    hausses = {l.produit_id: l for l in commande.lignes.select_related('produit')
               if l.quantite > quantites_avant.get(l.produit_id, 0)}
    if not hausses:
        return None
    besoin = dict(LigneCommandeClient.objects.filter(
        commande__livreur_id=commande.livreur_id, commande__statut__in=STATUTS_COMMANDE_AFFECTEE,
        produit_id__in=list(hausses),
    ).values('produit_id').annotate(total=models.Sum('quantite')).values_list('produit_id', 'total'))
    stock = dict(ProductStock.objects.filter(warehouse=van, produit_id__in=list(hausses))
                 .values_list('produit_id', 'quantity'))

    def _q(v):
        return int(v) if v == int(v) else float(v)

    manques = []
    for pid, ligne in hausses.items():
        requis = besoin.get(pid) or ligne.quantite
        dispo = stock.get(pid, 0)
        if dispo < requis:
            manques.append(f"{ligne.produit.designation} : {_q(requis)} à livrer, {dispo} dans le van")
    if not manques:
        return None
    return (f"Stock du van {van.name} insuffisant pour livrer cette commande : " + ' ; '.join(manques)
            + '. Rechargez le van avant la livraison.')


class LivreurViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des livreurs de distribution"""
    queryset = LivreurDistribution.objects.all()
    serializer_class = LivreurSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return LivreurDetailSerializer
        return LivreurSerializer

    def get_queryset(self):
        # Livreurs de l'entreprise de l'utilisateur (avant : toutes les entreprises)
        from .tenant import filtrer_livreurs
        # Nombre de tournées actives annoté : une requête pour toute la liste (avant : 2 par livreur)
        return filtrer_livreurs(super().get_queryset(), self.request).select_related('user', 'entrepot').annotate(
            nb_tournees_actives=models.Count(
                'tournees', filter=models.Q(tournees__statut__in=['planifiee', 'en_cours']), distinct=True))

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """Livreur / prévendeur du compte connecté (mêmes champs qu'un élément de la liste).

        GET /API/distribution/livreurs/me/ → 200 {id, matricule, nom, ...} ; 404 si le compte
        n'est pas celui d'un livreur."""
        livreur = self.get_queryset().filter(user=request.user).first()
        if livreur is None:
            return Response({'error': 'Aucun livreur associé à cet utilisateur'},
                            status=status.HTTP_404_NOT_FOUND)
        return Response(LivreurSerializer(livreur, context=self.get_serializer_context()).data)

    def get_permissions(self):
        """
        Seuls les administrateurs peuvent créer ou supprimer des livreurs
        Les autres utilisateurs authentifiés peuvent lire
        """
        if self.action in ['create', 'destroy']:
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            nb_commandes = instance.commandes_prises.count()
            return Response(
                {'error': f"Impossible de supprimer ce livreur : {nb_commandes} commande(s) lui sont encore rattachée(s). "
                          f"Réaffectez d'abord ces commandes à un autre livreur."},
                status=status.HTTP_409_CONFLICT
            )

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

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Créer un livreur et son compte utilisateur automatiquement"""
        from django.contrib.auth.models import Group

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Sauvegarder le livreur
        # @transaction.atomic : si la création du compte User échoue après celle du
        # livreur (ex: username en double), tout est annulé plutôt que de laisser un
        # livreur orphelin sans compte, qui ferait échouer toutes les tentatives
        # suivantes avec la même erreur.
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
        """Tous les clients du planning de la semaine du prévendeur (choisis un par un ou via
        les secteurs du jour). Chaque client porte `jours_semaine` (1=lundi..7=dimanche).
        Même calcul que le téléphone et les tournées : les chiffres sont toujours identiques."""
        from API.models import Client
        from .distribution_serializers import ClientMobileSerializer
        from .distribution_prix_stock import jours_par_client
        livreur = self.get_object()
        jours = jours_par_client(livreur.id)
        clients = Client.objects.filter(pk__in=list(jours)).select_related('type_prix').order_by('nom', 'prenom')
        data = ClientMobileSerializer(clients, many=True).data
        for item in data:
            item['jours_semaine'] = sorted(jours.get(item['id'], ()))
        return Response({
            'livreur_id': livreur.id,
            'livreur_nom': livreur.nom,
            'clients': data,
            'nb_clients': len(data),
        })

    @action(detail=True, methods=['get'])
    def clients_du_jour(self, request, pk=None):
        """
        Récupérer les clients à visiter selon le planning hebdomadaire.
        Utilise ClientLivreurHebdo pour déterminer quels clients sont assignés
        pour le jour de la semaine.

        Paramètres optionnels:
        - date: Date spécifique (format YYYY-MM-DD). Si non fourni, utilise aujourd'hui.
        """
        from datetime import date, datetime
        from API.models import Client

        livreur = self.get_object()

        # Obtenir la date (paramètre ou aujourd'hui)
        date_param = request.query_params.get('date', None)
        if date_param:
            try:
                target_date = datetime.strptime(date_param, '%Y-%m-%d').date()
            except ValueError:
                target_date = date.today()
        else:
            target_date = date.today()

        # Obtenir le jour de la semaine (1=Lundi ... 7=Dimanche)
        # Python: weekday() retourne 0=Lundi, donc on ajoute 1
        jour_semaine = target_date.weekday() + 1  # 1=Lundi, 7=Dimanche

        # Planning de la semaine : clients choisis un par un + clients des secteurs du jour
        from .distribution_serializers import ClientMobileSerializer
        from .distribution_prix_stock import clients_planifies
        clients_data = []
        for rang, item in enumerate(clients_planifies(livreur.id, jour_semaine), start=1):
            client_data = ClientMobileSerializer(item['client']).data
            client_data['ordre_visite'] = item['ordre'] or rang
            client_data['source_planning'] = item['source']
            clients_data.append(client_data)

        return Response({
            'livreur_id': livreur.id,
            'livreur_nom': livreur.nom,
            'date': target_date.isoformat(),
            'jour_semaine': jour_semaine,
            'jour_nom': dict(ClientLivreurHebdo.JOURS_SEMAINE_CHOICES).get(jour_semaine, ''),
            'clients': clients_data,
            'nb_clients': len(clients_data)
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

    # ------------------------------------------------------------------
    # Planning de la semaine (sans dates) : par secteurs et/ou par clients
    # ------------------------------------------------------------------
    JOURS_NOMS = {1: 'Lundi', 2: 'Mardi', 3: 'Mercredi', 4: 'Jeudi', 5: 'Vendredi', 6: 'Samedi', 7: 'Dimanche'}

    @action(detail=False, methods=['get'], url_path='planning-clients')
    def planning_clients(self, request):
        """Vue d'ensemble du planning de la semaine de TOUS les prévendeurs de l'entreprise :
        {clients: {client_id: [{jour, livreur_id, livreur_nom}]},
         secteurs: {secteur_id: [{jour, livreur_id, livreur_nom}]}}.
        Sert aux cases L M M J V S D de l'écran Planning : un client pris le mardi par Karim
        reste affiché comme pris quand on sélectionne un autre prévendeur."""
        from .distribution_prix_stock import clients_planifies
        clients, secteurs = {}, {}
        livreurs = list(self.get_queryset().order_by('nom').values_list('id', 'nom'))
        noms = dict(livreurs)
        for lid, nom in livreurs:
            for jour in range(1, 8):
                for it in clients_planifies(lid, jour):
                    clients.setdefault(it['client'].id, []).append({'jour': jour, 'livreur_id': lid, 'livreur_nom': nom})
        for lid, jour, sid in PlanningHebdomadaire.objects.filter(
                livreur_id__in=noms, is_active=True, secteurs__isnull=False).values_list('livreur_id', 'jour_semaine', 'secteurs'):
            secteurs.setdefault(sid, []).append({'jour': jour, 'livreur_id': lid, 'livreur_nom': noms[lid]})
        return Response({'clients': clients, 'secteurs': secteurs})

    def _doublons_du_jour(self, livreur, jour, items):
        """Clients de ce jour qu'un AUTRE prévendeur visite aussi ce jour-là (anciennes données
        ou secteur donné à deux prévendeurs avant la vérification) : [{id, nom, chez: [noms]}]."""
        from .distribution_prix_stock import clients_planifies
        ids = {it['client'].id for it in items}
        if not ids:
            return []
        secteurs = {it['client'].secteur_id for it in items if it['client'].secteur_id}
        autres = set(ClientLivreurHebdo.objects.filter(jour_semaine=jour, is_active=True, client_id__in=ids)
                     .exclude(livreur=livreur).values_list('livreur_id', flat=True))
        if secteurs:
            autres |= set(PlanningHebdomadaire.objects.filter(jour_semaine=jour, is_active=True, secteurs__in=secteurs)
                          .exclude(livreur=livreur).values_list('livreur_id', flat=True))
        chez = {}
        for autre in LivreurDistribution.objects.filter(pk__in=autres).order_by('nom'):
            for it in clients_planifies(autre.id, jour):
                if it['client'].id in ids:
                    chez.setdefault(it['client'].id, []).append(autre.nom)
        noms = {it['client'].id: f"{it['client'].nom or ''} {it['client'].prenom or ''}".strip() for it in items}
        return [{'id': cid, 'nom': noms[cid], 'chez': n} for cid, n in sorted(chez.items(), key=lambda x: noms[x[0]])]

    def _company_planning(self, livreur):
        company = getattr(self.request, 'company', None)
        if company is None and livreur.entrepot_id:
            company = getattr(livreur.entrepot, 'company', None)
        return company

    @staticmethod
    def _jour_valide(valeur):
        try:
            jour = int(valeur)
        except (TypeError, ValueError):
            return None
        return jour if 1 <= jour <= 7 else None

    @action(detail=True, methods=['get'])
    def planning(self, request, pk=None):
        """Planning de la semaine du prévendeur : pour chaque jour, ses secteurs, ses clients
        choisis un par un et la liste complète des clients du jour (même calcul que le
        téléphone et les tournées)."""
        from API.models import Client, Secteur
        from .distribution_prix_stock import clients_planifies, secteurs_du_jour, exclusions_du_jour
        livreur = self.get_object()
        company = self._company_planning(livreur)
        secteurs_qs = Secteur.objects.filter(is_active=True)
        if company is not None:
            secteurs_qs = secteurs_qs.filter(models.Q(company=company) | models.Q(company__isnull=True))
        nb_par_secteur = dict(Client.objects.filter(secteur__in=secteurs_qs).values_list('secteur_id').annotate(n=models.Count('id')))
        secteurs_info = {s.id: {'id': s.id, 'nom': s.nom, 'code': s.code, 'couleur': s.couleur,
                                'nb_clients': nb_par_secteur.get(s.id, 0)} for s in secteurs_qs.order_by('nom')}

        def nom_client(c):
            return f"{c.nom or ''} {c.prenom or ''}".strip()

        jours, tous = [], set()
        for jour in range(1, 8):
            items = clients_planifies(livreur.id, jour)
            tous.update(it['client'].id for it in items)
            ids_secteurs = secteurs_du_jour(livreur.id, jour)
            exclusions = exclusions_du_jour(livreur.id, jour, ids_secteurs)
            exclus = [{'id': c.id, 'nom': nom_client(c), 'secteur_id': c.secteur_id, 'chez': exclusions[c.id]}
                      for c in Client.objects.filter(pk__in=exclusions).order_by('nom', 'prenom')]
            doublons = self._doublons_du_jour(livreur, jour, items)
            jours.append({
                'jour': jour,
                'nom': self.JOURS_NOMS[jour],
                'secteurs': [secteurs_info.get(sid) or {'id': sid, 'nom': f'Secteur {sid}', 'nb_clients': nb_par_secteur.get(sid, 0)}
                             for sid in ids_secteurs],
                'clients': [{'id': it['client'].id, 'nom': nom_client(it['client']),
                             'secteur_nom': getattr(it['client'].secteur, 'nom', '') if it['client'].secteur_id else ''}
                            for it in items if it['source'] == 'client'],
                'liste': [{'id': it['client'].id, 'nom': nom_client(it['client']), 'source': it['source'],
                           'secteur_id': it['client'].secteur_id,
                           'telephone': it['client'].telephone or '',
                           'secteur_nom': getattr(it['client'].secteur, 'nom', '') if it['client'].secteur_id else ''}
                          for it in items],
                'exclus': exclus,
                'doublons': doublons,
                'total': len(items),
            })
        # Anciennes affectations sans aucun jour de passage : à compléter ou retirer
        sans_jour = livreur.clients_assignes.exclude(pk__in=tous).order_by('nom')
        return Response({
            'livreur_id': livreur.id,
            'livreur_nom': livreur.nom,
            'jours': jours,
            'total_clients': len(tous),
            'clients_sans_jour': [{'id': c.id, 'nom': nom_client(c)} for c in sans_jour],
            'secteurs_disponibles': list(secteurs_info.values()),
        })

    @action(detail=True, methods=['post'], url_path='planning/secteurs')
    def planning_secteurs(self, request, pk=None):
        """Fixe les secteurs visités un jour de la semaine. Body : {jour, secteurs: [ids]}."""
        from API.models import Secteur
        livreur = self.get_object()
        jour = self._jour_valide(request.data.get('jour'))
        if jour is None:
            return Response({'error': 'Jour invalide (1 = lundi … 7 = dimanche)'}, status=status.HTTP_400_BAD_REQUEST)
        ids = request.data.get('secteurs') or []
        if not isinstance(ids, list):
            return Response({'error': 'secteurs doit être une liste'}, status=status.HTTP_400_BAD_REQUEST)
        company = self._company_planning(livreur)
        secteurs = Secteur.objects.filter(pk__in=ids)
        if company is not None:
            secteurs = secteurs.filter(models.Q(company=company) | models.Q(company__isnull=True))
        secteurs = list(secteurs)
        if len(secteurs) != len(set(ids)):
            return Response({'error': 'Secteur introuvable'}, status=status.HTTP_400_BAD_REQUEST)
        # Un secteur ne peut être visité que par UN prévendeur un jour donné (sinon ses clients
        # seraient chez deux prévendeurs le même jour). 409 sauf si transferer=true : il est alors
        # retiré au prévendeur qui l'avait ce jour-là.
        transferer = str(request.data.get('transferer', '')).lower() in ('1', 'true', 'oui', 'yes')
        autres_plannings = PlanningHebdomadaire.objects.filter(
            jour_semaine=jour, is_active=True, secteurs__in=secteurs,
        ).exclude(livreur=livreur).select_related('livreur').distinct()
        if company is not None:
            autres_plannings = autres_plannings.filter(models.Q(company=company) | models.Q(company__isnull=True))
        deja = set(PlanningHebdomadaire.objects.filter(livreur=livreur, jour_semaine=jour, is_active=True)
                   .values_list('secteurs', flat=True))
        ids_demandes = {s.id for s in secteurs} - deja   # seulement les secteurs ajoutés
        conflits = [{'secteur_id': s.id, 'secteur_nom': s.nom, 'livreur_id': p.livreur_id, 'livreur_nom': p.livreur.nom,
                     'jour': jour, 'jour_nom': self.JOURS_NOMS[jour]}
                    for p in autres_plannings for s in p.secteurs.filter(pk__in=ids_demandes)]
        if conflits and not transferer:
            return Response({'error': 'Ce secteur est déjà visité par un autre prévendeur ce jour-là',
                             'conflits': conflits}, status=status.HTTP_409_CONFLICT)
        with transaction.atomic():
            for p in autres_plannings:
                p.secteurs.remove(*[s for s in secteurs if s.id in ids_demandes])
            planning = PlanningHebdomadaire.objects.filter(livreur=livreur, jour_semaine=jour).order_by('-is_active', 'id').first()
            if planning is None:
                planning = PlanningHebdomadaire.objects.create(
                    livreur=livreur, jour_semaine=jour, company=company, is_active=True,
                    created_by=request.user if request.user.is_authenticated else None)
            elif not planning.is_active:
                planning.is_active = True
                planning.save(update_fields=['is_active'])
            planning.secteurs.set(secteurs)
            # Secteur ajouté (ou réaffecté) ou retiré de la journée : ses clients repartent de zéro.
            # Les clients qu'on avait retirés à la main de ce secteur reviennent avec lui.
            from API.models import Client
            changes = ids_demandes | ({sid for sid in deja if sid} - {s.id for s in secteurs})
            if changes:
                remis = list(Client.objects.filter(secteur_id__in=changes).values_list('id', flat=True))
                for p in PlanningHebdomadaire.objects.filter(livreur=livreur, jour_semaine=jour):
                    p.clients_exclus.remove(*remis)
        return Response({'message': f"{self.JOURS_NOMS[jour]} : {len(secteurs)} secteur(s)", 'jour': jour,
                         'secteurs': [s.id for s in secteurs]})

    @action(detail=True, methods=['post'], url_path='planning/ajouter-client')
    def planning_ajouter_client(self, request, pk=None):
        """Ajoute un client précis à un ou plusieurs jours. Body : {client_id, jours: [1..7],
        transferer: bool}. Si un autre prévendeur a déjà ce client ce jour-là : 409 avec la
        liste des conflits, sauf si transferer=true (le client lui est alors retiré)."""
        from API.models import Client
        livreur = self.get_object()
        jours = request.data.get('jours')
        if jours is None:
            jours = [request.data.get('jour')]
        jours = sorted({j for j in (self._jour_valide(v) for v in (jours if isinstance(jours, list) else [jours])) if j})
        if not jours:
            return Response({'error': 'Choisissez au moins un jour'}, status=status.HTTP_400_BAD_REQUEST)
        client = Client.objects.filter(pk=request.data.get('client_id')).first()
        if client is None:
            return Response({'error': 'Client introuvable'}, status=status.HTTP_404_NOT_FOUND)
        transferer = str(request.data.get('transferer', '')).lower() in ('1', 'true', 'oui', 'yes')
        company = self._company_planning(livreur)

        autres = list(ClientLivreurHebdo.objects.filter(client=client, jour_semaine__in=jours, is_active=True
                                                        ).exclude(livreur=livreur).select_related('livreur'))
        conflits = [{'jour': a.jour_semaine, 'jour_nom': self.JOURS_NOMS[a.jour_semaine],
                     'livreur_id': a.livreur_id, 'livreur_nom': a.livreur.nom, 'secteur_nom': None} for a in autres]
        # Client visité par un autre prévendeur via son secteur : il lui sera retiré automatiquement
        from .distribution_prix_stock import secteurs_du_jour, exclusions_du_jour, livreurs_du_secteur
        if client.secteur_id:
            deja = {(c['livreur_id'], c['jour']) for c in conflits}
            for autre in LivreurDistribution.objects.filter(pk__in=livreurs_du_secteur({client.secteur_id})).exclude(pk=livreur.pk):
                for jour in jours:
                    if (autre.id, jour) in deja:
                        continue
                    secteurs = secteurs_du_jour(autre.id, jour)
                    if client.secteur_id in secteurs and client.id not in exclusions_du_jour(autre.id, jour, secteurs):
                        conflits.append({'jour': jour, 'jour_nom': self.JOURS_NOMS[jour], 'livreur_id': autre.id,
                                         'livreur_nom': autre.nom, 'secteur_nom': client.secteur.nom})
        if conflits and not transferer:
            return Response({
                'error': 'Ce client est déjà chez un autre prévendeur',
                'conflits': conflits,
            }, status=status.HTTP_409_CONFLICT)
        ajoutes = []
        with transaction.atomic():
            for a in autres:
                a.delete()
            # S'il avait été retiré d'un secteur de ce prévendeur ces jours-là : on l'y remet
            for planning in PlanningHebdomadaire.objects.filter(livreur=livreur, jour_semaine__in=jours,
                                                                clients_exclus=client):
                planning.clients_exclus.remove(client)
            for jour in jours:
                ligne = ClientLivreurHebdo.objects.filter(client=client, livreur=livreur, jour_semaine=jour).first()
                if ligne is None:
                    # Même entreprise + même jour : la ligne d'un autre prévendeur bloquerait (unicité)
                    ClientLivreurHebdo.objects.filter(client=client, jour_semaine=jour, company=company).delete()
                    ordre = (ClientLivreurHebdo.objects.filter(livreur=livreur, jour_semaine=jour)
                             .aggregate(m=models.Max('ordre_passage'))['m'] or 0) + 1
                    ClientLivreurHebdo.objects.create(
                        client=client, livreur=livreur, jour_semaine=jour, company=company, is_active=True,
                        ordre_passage=ordre, created_by=request.user if request.user.is_authenticated else None)
                    ajoutes.append(jour)
                elif not ligne.is_active:
                    ligne.is_active = True
                    ligne.save(update_fields=['is_active'])
                    ajoutes.append(jour)
            # Liste utilisée pour les droits du prévendeur (encaissements…)
            livreur.clients_assignes.add(client)
            # Le client a pu être le dernier d'un secteur chez l'ancien prévendeur : secteur retiré
            from .distribution_prix_stock import retirer_secteurs_vides
            for c in conflits:
                if c.get('secteur_nom'):
                    retirer_secteurs_vides(c['livreur_id'], c['jour'])
        return Response({'message': f"{client.nom} ajouté : {', '.join(self.JOURS_NOMS[j] for j in jours)}",
                         'jours_ajoutes': ajoutes, 'transferes': len(conflits)})

    @action(detail=True, methods=['post'], url_path='planning/retirer-client')
    def planning_retirer_client(self, request, pk=None):
        """Retire un client précis d'un jour (ou de tous les jours si jour absent).
        Body : {client_id, jour?}. Un client qui vient d'un secteur est écarté de ce secteur
        ce jour-là (les autres clients du secteur restent visités)."""
        from API.models import Client
        from .distribution_prix_stock import secteurs_du_jour
        livreur = self.get_object()
        client = Client.objects.filter(pk=request.data.get('client_id')).first()
        if client is None:
            return Response({'error': 'Client introuvable'}, status=status.HTTP_404_NOT_FOUND)
        jour = self._jour_valide(request.data.get('jour'))
        lignes = ClientLivreurHebdo.objects.filter(client=client, livreur=livreur)
        if jour is not None:
            lignes = lignes.filter(jour_semaine=jour)
        from .distribution_prix_stock import retirer_secteurs_vides
        secteurs_retires = []
        with transaction.atomic():
            supprimees = lignes.count()
            lignes.delete()
            if not ClientLivreurHebdo.objects.filter(client=client, livreur=livreur).exists():
                livreur.clients_assignes.remove(client)
            ecartes = []
            if client.secteur_id:
                for j in ([jour] if jour is not None else range(1, 8)):
                    if client.secteur_id not in secteurs_du_jour(livreur.id, j):
                        continue
                    planning = PlanningHebdomadaire.objects.filter(livreur=livreur, jour_semaine=j,
                                                                   is_active=True).first()
                    if planning is not None:
                        planning.clients_exclus.add(client)
                        ecartes.append(j)
                        # Dernier client du secteur retiré : le secteur quitte la journée
                        secteurs_retires += retirer_secteurs_vides(livreur.id, j)
        message = f"{client.nom} retiré"
        if secteurs_retires:
            message += f" — plus aucun client dans « {', '.join(secteurs_retires)} » : secteur retiré du jour"
        elif ecartes:
            message += f" (les autres clients du secteur « {client.secteur.nom} » restent visités)"
        return Response({'message': message, 'supprimees': supprimees, 'ecarte_du_secteur': ecartes,
                         'secteurs_retires': secteurs_retires})

    @action(detail=True, methods=['post'], url_path='planning/remettre-client')
    def planning_remettre_client(self, request, pk=None):
        """Remet dans le secteur un client qui en avait été retiré ce jour-là (ou donné à un autre
        prévendeur : il lui est alors repris). Body : {client_id, jour}."""
        from API.models import Client
        livreur = self.get_object()
        client = Client.objects.filter(pk=request.data.get('client_id')).first()
        if client is None:
            return Response({'error': 'Client introuvable'}, status=status.HTTP_404_NOT_FOUND)
        jour = self._jour_valide(request.data.get('jour'))
        if jour is None:
            return Response({'error': 'Jour invalide (1 = lundi … 7 = dimanche)'}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            for planning in PlanningHebdomadaire.objects.filter(livreur=livreur, jour_semaine=jour, clients_exclus=client):
                planning.clients_exclus.remove(client)
            repris = ClientLivreurHebdo.objects.filter(client=client, jour_semaine=jour).exclude(livreur=livreur)
            nb_repris = repris.count()
            for ligne in repris:
                ligne.delete()
        return Response({'message': f"{client.nom} est de nouveau visité le {self.JOURS_NOMS[jour].lower()}",
                         'repris': nb_repris})

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
        from .distribution_prix_stock import TarifsMobile

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
        # Les produits supprimés dans le logiciel (suppression logique : is_active=False)
        # ne doivent plus apparaître dans l'app mobile.
        stocks = ProductStock.objects.filter(
            warehouse=livreur.entrepot,
            produit__is_active=True,
        ).select_related('produit', 'produit__categorie').prefetch_related('produit__conditionnements').order_by('produit__reference')

        # Filtrer les stocks vides si demandé
        hide_empty = request.query_params.get('hide_empty', 'false').lower() == 'true'
        if hide_empty:
            stocks = stocks.filter(quantity__gt=0)

        # Préparer les données
        stocks_data = []
        total_products = 0
        total_quantity = 0
        total_value = 0

        # Prix par type de client et promotions : chargés EN UNE FOIS pour tous les produits
        # du van (avant : 2 à 3 requêtes par produit et par type de prix)
        tarifs = TarifsMobile(company=livreur.entrepot.company_id, produits=stocks.values('produit_id'))
        code_prix_actif = tarifs.code_actif

        for stock in stocks:
            if stock.quantity > 0 or not hide_empty:
                # Prix de base du produit (fallback)
                prix_produit_base = float(stock.produit.prixU) if stock.produit.prixU else 0

                # Prix par type (DETAIL, SUPERETTE, GROS) avec promotions
                prix_par_type = tarifs.detail_par_type(stock.produit)

                # Utiliser le prix DETAIL comme prix de référence pour l'affichage
                prix_affichage = prix_par_type.get('DETAIL', {}).get('prix_original', prix_produit_base)
                product_value = float(stock.quantity * prix_affichage)

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
                    'image': stock.produit.image.url if stock.produit.image else None,  # URL de l'image
                    'quantite': stock.quantity,
                    'prix_unitaire': prix_affichage,  # Prix standard DETAIL (pas prixU)
                    'prix_par_type': prix_par_type,  # Prix par type de client avec promotions
                    'code_prix_actif': code_prix_actif.code if code_prix_actif else None,
                    'valeur': product_value,
                    'unite_mesure': stock.produit.get_unite_mesure_display(),
                    # Conditionnement : quantite toujours en unites, ce champ sert a
                    # afficher / saisir en cartons dans l'app mobile
                    'unites_par_carton': stock.produit.get_unites_par_carton(),
                    'cartons_par_colis': stock.produit.get_cartons_par_colis(),
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
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filtres
        livreur_id = self.request.query_params.get('livreur')
        assigned_to = self.request.query_params.get('assigned_to')
        date_tournee = self.request.query_params.get('date_tournee') or self.request.query_params.get('date')
        date_debut = self.request.query_params.get('date_tournee__gte') or self.request.query_params.get('date_debut')
        date_fin = self.request.query_params.get('date_tournee__lte') or self.request.query_params.get('date_fin')
        statut = self.request.query_params.get('statut')
        # Nouveau paramètre: inclure les tournées actives (non terminées)
        actives_only = self.request.query_params.get('actives_only', 'false').lower() == 'true'

        print(f"[TourneeViewSet] Params: livreur={livreur_id}, assigned_to={assigned_to}, actives_only={actives_only}, date_debut={date_debut}, date_fin={date_fin}")

        # Filtre spécial pour l'app mobile : assigned_to='me'
        if assigned_to == 'me':
            # Récupérer le livreur depuis l'utilisateur connecté
            if self.request.user and self.request.user.is_authenticated:
                try:
                    livreur = LivreurDistribution.objects.get(user=self.request.user)
                    queryset = queryset.filter(livreur=livreur)
                    print(f"[TourneeViewSet] Filtered by user's livreur: {livreur.id}")
                except LivreurDistribution.DoesNotExist:
                    # Si pas de livreur lié, retourner queryset vide
                    queryset = queryset.none()
                    print("[TourneeViewSet] No livreur found for user, returning empty")
            else:
                # Si pas authentifié, retourner queryset vide
                queryset = queryset.none()
                print("[TourneeViewSet] User not authenticated, returning empty")
        elif livreur_id:
            queryset = queryset.filter(livreur_id=livreur_id)
            print(f"[TourneeViewSet] Filtered by livreur_id={livreur_id}, count: {queryset.count()}")

        # Si actives_only=true, retourner toutes les tournées non terminées/clôturées
        # Sinon, filtrer par date si spécifiée
        if actives_only:
            # Retourner les tournées planifiées ou en cours (pas terminées, annulées ou clôturées)
            queryset = queryset.filter(statut__in=['planifiee', 'en_cours'])
        elif date_debut and date_fin:
            # Filtre par plage de dates
            queryset = queryset.filter(date_tournee__gte=date_debut, date_tournee__lte=date_fin)
            print(f"[TourneeViewSet] Filtered by date range {date_debut} to {date_fin}, count: {queryset.count()}")
        elif date_tournee:
            # Filtre par date exacte
            queryset = queryset.filter(date_tournee=date_tournee)

        if statut:
            queryset = queryset.filter(statut=statut)

        # ?depuis=YYYY-MM-DD : historique limité (tournées depuis cette date + celles encore
        # planifiées / en cours, quelle que soit leur date). Sans le paramètre : inchangé
        # (anciennes versions de l'application).
        depuis = self.request.query_params.get('depuis')
        if depuis:
            queryset = queryset.filter(
                models.Q(date_tournee__gte=_parse_date_param(depuis, 'depuis'))
                | models.Q(statut__in=['planifiee', 'en_cours']))

        return queryset.select_related(
            'livreur', 'code_prix', 'entrepot_depart', 'rapport_caisse'
        ).prefetch_related('arrets', 'arrets__client', 'ventes').order_by('-date_tournee', 'numero_tournee')

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

        # Au démarrage, la tournée charge les clients assignés au livreur pour ce jour (planning
        # hebdomadaire) qui n'y sont pas encore. Ajouts seulement : aucun arrêt n'est retiré.
        clients_ajoutes = 0
        try:
            from .distribution_prix_stock import synchroniser_arrets_tournee
            clients_ajoutes = synchroniser_arrets_tournee(tournee, clients_concernes=set())['ajoutes']
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Chargement des clients assignés au démarrage de la tournée %s", tournee.pk)

        return Response({
            'message': 'Tournée démarrée',
            'clients_ajoutes': clients_ajoutes,
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

    @action(detail=True, methods=['post'])
    def sync_arrets(self, request, pk=None):
        """Synchroniser les arrêts d'une tournée avec les clients assignés"""
        try:
            tournee = self.get_object()

            # Vérifier que la tournée n'est pas terminée ou clôturée
            if tournee.statut in ['terminee', 'cloturee', 'annulee']:
                return Response(
                    {'error': 'Impossible de synchroniser une tournée terminée ou clôturée'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Même logique que la synchronisation automatique (distribution_prix_stock) :
            # planning hebdomadaire du jour de la tournée, période de validité respectée.
            from .distribution_prix_stock import synchroniser_arrets_tournee
            with transaction.atomic():
                r = synchroniser_arrets_tournee(tournee)
            arrets_ajoutes, arrets_supprimes, arrets_mis_a_jour = r['ajoutes'], r['supprimes'], r['mis_a_jour']

            return Response({
                'message': 'Synchronisation terminée',
                'arrets_ajoutes': arrets_ajoutes,
                'arrets_supprimes': arrets_supprimes,
                'arrets_mis_a_jour': arrets_mis_a_jour,
                'total_arrets': tournee.arrets.count(),
                'tournee': TourneeSerializer(tournee).data
            })
        except Exception as e:
            import traceback
            return Response({
                'error': str(e),
                'traceback': traceback.format_exc()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def sync_all_en_cours(self, request):
        """Synchroniser toutes les tournées en cours avec les clients assignés"""
        tournees_en_cours = TourneeMobile.objects.filter(statut__in=['planifiee', 'en_cours'])

        tournees_synced = 0
        errors = []

        for tournee in tournees_en_cours:
            try:
                # Même logique que sync_arrets (ordre de passage sans collision)
                from .distribution_prix_stock import synchroniser_arrets_tournee
                with transaction.atomic():
                    synchroniser_arrets_tournee(tournee)

                tournees_synced += 1
            except Exception as e:
                errors.append({'tournee_id': tournee.id, 'error': str(e)})

        return Response({
            'message': f'{tournees_synced} tournée(s) synchronisée(s)',
            'tournees_synced': tournees_synced,
            'errors': errors if errors else None
        })

    @action(detail=False, methods=['get'])
    def historique_complet(self, request):
        """Retourne l'historique complet des tournées avec livreurs, ventes et arrêts"""
        from decimal import Decimal

        # Filtres
        date_debut = request.GET.get('date_debut')
        date_fin = request.GET.get('date_fin')
        livreur_id = request.GET.get('livreur_id')
        statut = request.GET.get('statut')

        # Query de base
        tournees = self.get_queryset()

        # Appliquer les filtres
        if date_debut:
            tournees = tournees.filter(date_tournee__gte=date_debut)
        if date_fin:
            tournees = tournees.filter(date_tournee__lte=date_fin)
        if livreur_id:
            tournees = tournees.filter(livreur_id=livreur_id)
        if statut:
            tournees = tournees.filter(statut=statut)

        # Limiter aux 100 dernières tournées par défaut
        tournees = tournees.select_related('livreur', 'rapport_caisse').prefetch_related(
            'arrets__client',
            'ventes__client'
        )[:100]

        # Construire la réponse
        data = []
        for tournee in tournees:
            # Calculer les statistiques de la tournée
            arrets = tournee.arrets.all()
            total_arrets = arrets.count()
            arrets_livres = arrets.filter(statut='livre').count()
            arrets_echec = arrets.filter(statut='echec').count()
            arrets_en_attente = arrets.filter(statut='en_attente').count()

            # Calculer le taux de réussite
            taux_reussite = round((arrets_livres / total_arrets) * 100, 2) if total_arrets > 0 else 0

            # Calculer le total des ventes et récupérer les informations
            ventes = tournee.ventes.all()
            total_ventes = sum(vente.montant_total for vente in ventes)
            ventes_list = []
            arrets_list = []

            # Ajouter les ventes si elles existent
            for vente in ventes:
                client_nom = ''
                client_prenom = ''
                client_tel = ''
                if vente.client:
                    client_nom = getattr(vente.client, 'nom', '')
                    client_prenom = getattr(vente.client, 'prenom', '')
                    client_tel = getattr(vente.client, 'telephone', '')

                ventes_list.append({
                    'id': vente.id,
                    'numero': vente.numero_vente or f"V-{vente.id}",
                    'client': {
                        'id': vente.client.id,
                        'nom': client_nom,
                        'prenom': client_prenom,
                        'telephone': client_tel
                    } if vente.client else None,
                    'date_vente': vente.date_vente.isoformat() if vente.date_vente else timezone.now().isoformat(),
                    'total_ttc': float(vente.montant_total),
                    'type_paiement': vente.type_paiement,
                    'statut': 'completed',
                    'statut_arret': 'livre'
                })

            # Ajouter les arrêts (clients visités) avec leurs informations
            for arret in arrets:
                if arret.client:
                    arrets_list.append({
                        'id': arret.id,
                        'ordre': arret.ordre_passage,
                        'client': {
                            'id': arret.client.id,
                            'nom': getattr(arret.client, 'nom', ''),
                            'prenom': getattr(arret.client, 'prenom', ''),
                            'telephone': getattr(arret.client, 'telephone', ''),
                            'adresse': getattr(arret.client, 'adresse', '')
                        },
                        'statut': arret.statut,
                        'heure_arrivee': arret.heure_arrivee.isoformat() if arret.heure_arrivee else None,
                        'heure_depart': arret.heure_depart.isoformat() if arret.heure_depart else None,
                        'notes': arret.notes or '',
                        'latitude': float(arret.latitude) if arret.latitude else None,
                        'longitude': float(arret.longitude) if arret.longitude else None
                    })

            # Récupérer le rapport de caisse s'il existe
            rapport_caisse = None
            if hasattr(tournee, 'rapport_caisse') and tournee.rapport_caisse:
                rapport = tournee.rapport_caisse
                rapport_caisse = {
                    'fonds_depart': float(rapport.fonds_depart),
                    'total_especes': float(rapport.total_especes),
                    'total_cartes': float(rapport.total_cartes),
                    'total_cheques': float(rapport.total_cheques),
                    'total_credits': float(rapport.total_credits),
                    'total_encaissements': float(rapport.total_encaissements),
                    'total_depenses': float(rapport.total_depenses),
                    'carburant': float(rapport.carburant),
                    'reparations': float(rapport.reparations),
                    'autres_depenses': float(rapport.autres_depenses),
                    'solde_final_theorique': float(rapport.solde_final_theorique),
                    'solde_final_reel': float(rapport.solde_final_reel),
                    'ecart': float(rapport.ecart),
                    'detail_billets': rapport.detail_billets if rapport.detail_billets else {},
                    'justification_ecart': rapport.justification_ecart,
                    'statut': rapport.statut,
                    'a_des_anomalies': rapport.a_des_anomalies,
                    'notes_anomalies': rapport.notes_anomalies
                }

            tournee_data = {
                'id': tournee.id,
                'numero': tournee.numero_tournee or f"T-{tournee.id}",
                'date': tournee.date_tournee.isoformat(),
                'statut': tournee.statut,
                'livreur': {
                    'id': tournee.livreur.id,
                    'nom': tournee.livreur.nom,
                    'prenom': '',
                    'telephone': tournee.livreur.telephone or '',
                    'vehicule_type': tournee.livreur.vehicule_marque or '',
                    'immatriculation': tournee.livreur.vehicule_immatriculation or ''
                } if tournee.livreur else None,
                'warehouse': None,
                'code_prix': None,
                'heure_depart_prevue': tournee.heure_debut.isoformat() if tournee.heure_debut else None,
                'heure_depart_reelle': tournee.heure_debut.isoformat() if tournee.heure_debut else None,
                'heure_retour_prevue': tournee.heure_fin.isoformat() if tournee.heure_fin else None,
                'heure_retour_reelle': tournee.heure_fin.isoformat() if tournee.heure_fin else None,
                'distance_km': float(tournee.distance_km) if tournee.distance_km else None,
                'commentaire': tournee.notes or '',
                'statistiques': {
                    'total_arrets': total_arrets,
                    'arrets_livres': arrets_livres,
                    'arrets_echec': arrets_echec,
                    'arrets_en_attente': arrets_en_attente,
                    'taux_reussite': taux_reussite,
                    'total_ventes': float(total_ventes)
                },
                'ventes': ventes_list,
                'arrets': arrets_list,
                'rapport_caisse': rapport_caisse,
                'created_at': tournee.created_at.isoformat(),
                'updated_at': tournee.updated_at.isoformat()
            }

            data.append(tournee_data)

        return Response({
            'count': len(data),
            'results': data
        })


class ArretTourneeViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des arrêts"""
    queryset = ArretTourneeMobile.objects.all()
    serializer_class = ArretTourneeSerializer
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='encaissements')
    def encaissements(self, request):
        """Argent reçu pendant les tournées d'un livreur (pour la caisse et l'historique du téléphone).

        GET /API/distribution/ventes/encaissements/?livreur=5
        Renvoie les règlements de crédits de ventes, les acomptes et paiements de commandes et
        les remboursements de dettes, chacun avec la tournée où l'argent a été reçu.
        """
        from .distribution_models import EncaissementVente, EncaissementCommande
        from API.models import PaiementSolde
        from .securite_encaissements import livreur_connecte, livreur_autorise
        # Un livreur ne voit que SES encaissements (le numéro envoyé est ignoré) ;
        # le bureau ne voit que les livreurs de son entreprise.
        moi = livreur_connecte(request.user)
        if moi is not None and not request.user.is_superuser:
            livreur_id = moi.pk
        else:
            livreur_id = request.query_params.get('livreur')
            if not livreur_id:
                return Response({'error': 'livreur est requis'}, status=status.HTTP_400_BAD_REQUEST)
            livreur = LivreurDistribution.objects.filter(pk=livreur_id).select_related('entrepot').first()                 if str(livreur_id).isdigit() else None
            if not livreur_autorise(request, livreur):
                return Response({'error': 'Livreur introuvable'}, status=status.HTTP_404_NOT_FOUND)

        def _client_nom(c):
            return ' '.join(x for x in [getattr(c, 'prenom', ''), getattr(c, 'nom', '')] if x).strip() if c else ''

        from .distribution_models import PaiementClient
        parents = list(PaiementClient.objects.filter(tournee__livreur_id=livreur_id).values_list('app_id', flat=True))

        def _parent(app_id):
            return next((p for p in parents if (app_id or '').startswith(p + '-')), None)

        res = []
        # Parts d'encaissements de compte sur des ventes du PC (PaiementVente n'a pas de tournée)
        for pc in PaiementClient.objects.filter(tournee__livreur_id=livreur_id).select_related('client'):
            for r in (pc.repartition or []):
                if r.get('type') == 'vente_pc':
                    res.append({'id': f"{pc.app_id}-{r['cle']}", 'parent': pc.app_id, 'type': 'vente_pc',
                                'ref_id': r['cle'], 'client_id': str(pc.client_id),
                                'client_nom': _client_nom(pc.client), 'reference': r.get('reference'),
                                'montant': r['montant'], 'mode': pc.mode_paiement, 'tournee_id': str(pc.tournee_id),
                                'date': pc.date_paiement.isoformat()})
        for e in EncaissementVente.objects.filter(tournee__livreur_id=livreur_id).select_related('vente', 'vente__client'):
            res.append({'id': e.app_id, 'parent': _parent(e.app_id), 'type': 'vente_credit', 'ref_id': e.vente.app_id or str(e.vente_id),
                        'client_id': str(e.vente.client_id), 'client_nom': _client_nom(e.vente.client),
                        'montant': float(e.montant), 'mode': e.type_paiement, 'tournee_id': str(e.tournee_id),
                        'date': e.date_paiement.isoformat()})
        for e in EncaissementCommande.objects.filter(tournee__livreur_id=livreur_id).select_related('commande', 'commande__client'):
            res.append({'id': e.app_id, 'parent': _parent(e.app_id), 'type': 'commande_acompte' if e.app_id.startswith('acompte-') else 'commande_livraison',
                        'ref_id': str(e.commande_id), 'client_id': str(e.commande.client_id),
                        'client_nom': _client_nom(e.commande.client), 'reference': e.commande.reference,
                        'montant': float(e.montant), 'mode': e.type_paiement, 'tournee_id': str(e.tournee_id),
                        'date': e.date_paiement.isoformat()})
        for p in PaiementSolde.objects.filter(tournee__livreur_id=livreur_id).select_related('client'):
            res.append({'id': p.app_id or f'paiement-solde-{p.pk}', 'parent': _parent(p.app_id), 'type': 'solde', 'ref_id': None,
                        'client_id': str(p.client_id), 'client_nom': _client_nom(p.client),
                        'montant': float(p.montant), 'mode': p.mode_paiement, 'tournee_id': str(p.tournee_id),
                        'date': p.date_paiement.isoformat()})
        return Response(res)

    @action(detail=False, methods=['post'], url_path='encaisser')
    def encaisser(self, request):
        """Règlement (total ou partiel) du crédit d'une vente faite sur le téléphone.

        POST /API/distribution/ventes/encaisser/
        { "app_id": "encaissement-...", "vente": "vente-1731...-12" (app_id) ou 32 (id),
          "montant": 500, "type_paiement": "especes", "date_paiement": "...", "tournee": 14 }

        Idempotent sur app_id. Refuse un montant supérieur au reste à payer.
        """
        from decimal import Decimal, InvalidOperation
        from django.db import IntegrityError, transaction
        from django.utils.dateparse import parse_datetime
        from .distribution_models import EncaissementVente, TourneeMobile

        data = request.data
        app_id = str(data.get('app_id') or '').strip()
        if not app_id:
            return Response({'error': 'app_id est requis'}, status=status.HTTP_400_BAD_REQUEST)

        def _reste(v):
            recu = (v.montant_paye or Decimal('0')) - (v.montant_rendu or Decimal('0'))
            return max(Decimal('0'), (v.montant_total or Decimal('0')) - recu)

        def _reponse(enc, deja):
            v = VenteTourneeMobile.objects.get(pk=enc.vente_id)
            return Response({
                'deja_enregistre': deja, 'encaissement_id': enc.id, 'vente_id': v.id,
                'montant': str(enc.montant), 'montant_paye': str(v.montant_paye),
                'reste_a_payer': str(_reste(v)),
            }, status=status.HTTP_200_OK if deja else status.HTTP_201_CREATED)

        existant = EncaissementVente.objects.filter(app_id=app_id).first()
        if existant:
            return _reponse(existant, True)

        ref = str(data.get('vente') or '').strip()
        vente = VenteTourneeMobile.objects.filter(app_id=ref).first() if ref else None
        if vente is None and ref.isdigit():
            vente = VenteTourneeMobile.objects.filter(pk=int(ref)).first()
        if vente is None:
            # La vente n'est peut-être pas encore arrivée : le téléphone renverra plus tard
            return Response({'error': f'Vente introuvable : {ref}'}, status=status.HTTP_404_NOT_FOUND)
        from .securite_encaissements import client_autorise, tournee_autorisee
        if not client_autorise(request, vente.client):
            # Vente d'une autre entreprise : on ne révèle pas qu'elle existe
            return Response({'error': f'Vente introuvable : {ref}'}, status=status.HTTP_404_NOT_FOUND)

        try:
            montant = Decimal(str(data.get('montant')))
        except (InvalidOperation, TypeError, ValueError):
            return Response({'error': 'Montant invalide'}, status=status.HTTP_400_BAD_REQUEST)
        if montant <= 0:
            return Response({'error': 'Le montant doit être supérieur à zéro'}, status=status.HTTP_400_BAD_REQUEST)

        type_paiement = data.get('type_paiement') or 'especes'
        if type_paiement not in ('especes', 'cheque'):
            return Response({'error': f'Type de paiement invalide : {type_paiement}'},
                            status=status.HTTP_400_BAD_REQUEST)
        date_paiement = parse_datetime(str(data.get('date_paiement') or '')) or timezone.now()
        tid = str(data.get('tournee') or '').strip()
        tournee = TourneeMobile.objects.filter(pk=int(tid)).select_related('livreur__entrepot').first() if tid.isdigit() else None
        if not tournee_autorisee(request, tournee):
            return Response({'error': "Cette tournée n'est pas la vôtre"}, status=status.HTTP_403_FORBIDDEN)

        try:
            with transaction.atomic():
                vente = VenteTourneeMobile.objects.select_for_update().get(pk=vente.pk)
                if montant > _reste(vente) + Decimal('0.01'):
                    return Response({'error': f'Montant ({montant}) supérieur au reste à payer ({_reste(vente)})'},
                                    status=status.HTTP_400_BAD_REQUEST)
                enc = EncaissementVente.objects.create(
                    vente=vente, app_id=app_id, montant=montant, type_paiement=type_paiement,
                    date_paiement=date_paiement, tournee=tournee,
                    enregistre_par=request.user if request.user.is_authenticated else None)
                vente.montant_paye = (vente.montant_paye or Decimal('0')) + montant
                vente.save(update_fields=['montant_paye'])
        except IntegrityError:
            existant = EncaissementVente.objects.filter(app_id=app_id).first()
            if existant:
                return _reponse(existant, True)
            raise
        return _reponse(enc, False)

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
        import logging
        logger = logging.getLogger(__name__)

        try:
            logger.info(f"[VenteTourneeViewSet] Données reçues: {request.data}")

            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                logger.error(f"[VenteTourneeViewSet] Erreurs de validation: {serializer.errors}")
                return Response({
                    'error': 'Données invalides',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            vente = serializer.save()

            # Retourner la vente créée
            return Response({
                'id': vente.id,
                'message': 'Vente créée avec succès',
                'montant_total': float(vente.montant_total) if vente.montant_total else 0
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception(f"[VenteTourneeViewSet] Erreur lors de la création de vente: {str(e)}")
            return Response({
                'error': 'Erreur serveur lors de la création de la vente',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_queryset(self):
        queryset = super().get_queryset()
        tournee_id = self.request.query_params.get('tournee')

        if tournee_id:
            queryset = queryset.filter(tournee_id=tournee_id)

        # ?livreur=<id>[&depuis=YYYY-MM-DD] : toutes les ventes des tournées du livreur en UNE
        # requête HTTP (le téléphone en faisait une par tournée de tout l'historique).
        # Sans « depuis » : 30 derniers jours. Un livreur ne reçoit que SES ventes.
        livreur_id = self.request.query_params.get('livreur')
        depuis = self.request.query_params.get('depuis')
        if livreur_id:
            from .securite_encaissements import livreur_connecte, livreur_autorise
            user = self.request.user
            moi = livreur_connecte(user)
            if moi is not None and not user.is_superuser:
                livreur_id = moi.pk
            elif not str(livreur_id).isdigit() or not livreur_autorise(
                    self.request, LivreurDistribution.objects.filter(pk=livreur_id).select_related('entrepot').first()):
                return queryset.none()
            queryset = queryset.filter(tournee__livreur_id=livreur_id)
            if not depuis:
                queryset = queryset.filter(date_vente__date__gte=timezone.localdate() - timedelta(days=30))
        if depuis:
            queryset = queryset.filter(date_vente__date__gte=_parse_date_param(depuis, 'depuis'))

        return queryset.select_related('client').prefetch_related(
            'lignes', 'lignes__produit', 'lignes__produit__conditionnements').order_by('-date_vente', '-id')

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

    @action(detail=True, methods=['patch'], url_path='update-line-price')
    def update_line_price(self, request, pk=None):
        """Mettre à jour le prix unitaire d'une ligne de vente mobile"""
        import logging
        from decimal import Decimal
        logger = logging.getLogger(__name__)

        vente = self.get_object()
        ligne_id = request.data.get('ligne_id')
        new_price = request.data.get('prix_unitaire')

        if not ligne_id:
            return Response({'error': 'ligne_id requis'}, status=status.HTTP_400_BAD_REQUEST)
        if new_price is None:
            return Response({'error': 'prix_unitaire requis'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_price = Decimal(str(new_price))
            if new_price < 0:
                return Response({'error': 'Le prix ne peut pas être négatif'}, status=status.HTTP_400_BAD_REQUEST)

            # Chercher la ligne dans LigneVenteTourneeMobile
            from .distribution_models import LigneVenteTourneeMobile
            ligne = LigneVenteTourneeMobile.objects.filter(id=ligne_id, vente=vente).first()
            if not ligne:
                return Response({'error': 'Ligne de vente non trouvée'}, status=status.HTTP_404_NOT_FOUND)

            # Mettre à jour le prix unitaire
            # La méthode save() recalculera automatiquement montant_ht, montant_tva, montant_ttc
            ligne.prix_unitaire = new_price
            ligne.save()  # save() recalcule automatiquement les montants

            # Recalculer les totaux de la vente
            from django.db.models import Sum
            totaux = vente.lignes.aggregate(
                total_ht=Sum('montant_ht'),
                total_tva=Sum('montant_tva'),
                total_ttc=Sum('montant_ttc')
            )
            vente.montant_ht = totaux['total_ht'] or Decimal('0')
            vente.montant_tva = totaux['total_tva'] or Decimal('0')
            vente.montant_total = totaux['total_ttc'] or Decimal('0')
            vente.save(update_fields=['montant_ht', 'montant_tva', 'montant_total'])

            logger.info(f"Prix de la ligne {ligne_id} mis à jour: {new_price}")

            # Retourner les données mises à jour
            return Response({
                'success': True,
                'ligne': {
                    'id': ligne.id,
                    'prix_unitaire': float(ligne.prix_unitaire),
                    'quantite': float(ligne.quantite),
                    'total': float(ligne.montant_ttc)
                },
                'vente': {
                    'total_ht': float(vente.montant_ht),
                    'total_ttc': float(vente.montant_total)
                }
            })
        except ValueError:
            return Response({'error': 'Format de prix invalide'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception('Erreur lors de la mise à jour du prix de la ligne: %s', e)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RapportCaisseViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des rapports de caisse"""
    queryset = RapportCaisseMobile.objects.all()
    serializer_class = RapportCaisseSerializer
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]

    def dispatch(self, request, *args, **kwargs):
        """Intercepter toutes les requêtes pour debug"""
        print(f"[DISPATCH] Method: {request.method}, Path: {request.path}")
        result = super().dispatch(request, *args, **kwargs)
        print(f"[DISPATCH] Action was: {self.action if hasattr(self, 'action') else 'N/A'}, Result status: {result.status_code if hasattr(result, 'status_code') else 'N/A'}")
        return result

    def get_serializer_class(self):
        """Utiliser CommandeClientCreateSerializer pour create et update depuis mobile"""
        print(f"[GET_SERIALIZER_CLASS] Action: {self.action}")
        if self.action in ['create', 'update', 'partial_update']:
            print(f"[GET_SERIALIZER_CLASS] Retourne CommandeClientCreateSerializer")
            return CommandeClientCreateSerializer
        print(f"[GET_SERIALIZER_CLASS] Retourne CommandeClientSerializer")
        return CommandeClientSerializer

    def update(self, request, *args, **kwargs):
        """Override update ET partial_update"""
        partial = kwargs.pop('partial', False)
        print(f"[VIEWSET UPDATE] ===== DÉBUT ===== (partial={partial})")
        print(f"[VIEWSET UPDATE] ID: {kwargs.get('pk')}")
        print(f"[VIEWSET UPDATE] Data: {request.data}")

        instance = self.get_object()

        # Changement de statut : mêmes règles que changer_statut / partial_update
        import logging
        logger = logging.getLogger(__name__)
        nouveau_statut = request.data.get('statut')
        if nouveau_statut == 'delivered' and instance.statut != 'delivered':
            return self._livrer_commande(instance, request.data.get('lignes'),
                                         request.data.get('date_livraison_reelle'), logger,
                                         tournee_livraison_id=request.data.get('tournee_livraison'),
                                         trop_percu=request.data.get('trop_percu'))
        refus = self._transition_interdite(instance, nouveau_statut)
        if refus is not None:
            return refus
        annulation = nouveau_statut == 'cancelled' and instance.statut != 'cancelled'
        statut_avant = instance.statut

        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        print(f"[VIEWSET UPDATE] Serializer class: {serializer.__class__.__name__}")

        if not serializer.is_valid():
            print(f"[VIEWSET UPDATE] Validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        print(f"[VIEWSET UPDATE] Validation OK, calling save()")
        self.perform_update(serializer)

        if annulation:
            CommandeClient.objects.filter(pk=instance.pk).update(statut=statut_avant)
            commande = self._annuler_commande(instance, logger)
            return Response(CommandeClientSerializer(commande).data)

        print(f"[VIEWSET UPDATE] ===== FIN =====")
        return Response(serializer.data)

    def perform_update(self, serializer):
        """Appelé par update() pour sauvegarder - TOUJOURS appelé"""
        print(f"[PERFORM_UPDATE] ===== APPELÉ =====")
        print(f"[PERFORM_UPDATE] Serializer class: {serializer.__class__.__name__}")
        print(f"[PERFORM_UPDATE] Validated data: {serializer.validated_data}")
        serializer.save()
        print(f"[PERFORM_UPDATE] ===== SAUVEGARDÉ =====")

    def old_partial_update(self, request, *args, **kwargs):
        """Ancienne méthode - ne devrait plus être appelée"""
        print(f"[OLD PARTIAL_UPDATE] ===== DÉBUT =====")
        print(f"[OLD PARTIAL_UPDATE] ID: {kwargs.get('pk')}")
        print(f"[OLD PARTIAL_UPDATE] Data: {request.data}")

        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)

        print(f"[VIEWSET PARTIAL_UPDATE] Serializer class: {serializer.__class__.__name__}")

        if not serializer.is_valid():
            print(f"[VIEWSET PARTIAL_UPDATE] Validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        print(f"[VIEWSET PARTIAL_UPDATE] Validation OK, calling save()")
        self.perform_update(serializer)

        print(f"[VIEWSET PARTIAL_UPDATE] ===== FIN =====")
        return Response(serializer.data)

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
        import logging
        logger = logging.getLogger(__name__)

        queryset = super().get_queryset()
        initial_count = queryset.count()

        # Option pour désactiver le filtre company (utile pour l'interface web)
        skip_company_filter = self.request.query_params.get('all_companies', 'false').lower() == 'true'

        # Filtrer par company de l'utilisateur OU commandes sans company assignée
        if not skip_company_filter and hasattr(self.request.user, 'company') and self.request.user.company:
            # Inclure les commandes de la company de l'utilisateur ET les commandes sans company
            queryset = queryset.filter(
                Q(company=self.request.user.company) | Q(company__isnull=True)
            )
            filtered_count = queryset.count()
            logger.info(f"[CommandeClient] Filtre company appliqué: {initial_count} -> {filtered_count} commandes (company={self.request.user.company.id})")
        else:
            logger.info(f"[CommandeClient] Pas de filtre company (skip={skip_company_filter}, total={initial_count})")

        # Filtres optionnels
        livreur_id = self.request.query_params.get('livreur')
        client_id = self.request.query_params.get('client')
        statut = self.request.query_params.get('statut')
        date_debut = self.request.query_params.get('date_debut')
        date_fin = self.request.query_params.get('date_fin')

        # Commandes passées par un vendeur (même affectées depuis à un autre livreur).
        # Anciennes commandes sans « passée par » : repli sur le livreur.
        passee_par_id = self.request.query_params.get('passee_par')

        if livreur_id:
            queryset = queryset.filter(livreur_id=livreur_id)

        if passee_par_id:
            queryset = queryset.filter(
                Q(passee_par_id=passee_par_id) | Q(passee_par__isnull=True, livreur_id=passee_par_id)
            )

        if client_id:
            queryset = queryset.filter(client_id=client_id)

        if statut:
            queryset = queryset.filter(statut=statut)

        if date_debut:
            queryset = queryset.filter(date_commande__gte=date_debut)

        if date_fin:
            queryset = queryset.filter(date_commande__lte=date_fin)

        return queryset.select_related('client', 'livreur', 'livreur__entrepot', 'passee_par').prefetch_related('lignes', 'lignes__produit', 'lignes__produit__conditionnements')

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

    def partial_update(self, request, *args, **kwargs):
        """
        Mise à jour partielle d'une commande
        Gère spécialement le cas de la livraison avec quantités ajustées
        """
        print(f"[PARTIAL_UPDATE] ===== DÉBUT =====")
        print(f"[PARTIAL_UPDATE] Request data: {request.data}")
        print(f"[PARTIAL_UPDATE] PK: {kwargs.get('pk')}")

        import logging
        logger = logging.getLogger(__name__)

        commande = self.get_object()
        nouveau_statut = request.data.get('statut')
        lignes_ajustees = request.data.get('lignes')
        date_livraison = request.data.get('date_livraison_reelle')

        print(f"[PARTIAL_UPDATE] Commande {commande.id}: statut={nouveau_statut}, lignes={'OUI' if lignes_ajustees else 'NON'}")
        if lignes_ajustees:
            print(f"[PARTIAL_UPDATE] Nombre de lignes reçues: {len(lignes_ajustees)}")

        if nouveau_statut == 'delivered':
            return self._livrer_commande(commande, lignes_ajustees, date_livraison, logger,
                                         tournee_livraison_id=request.data.get('tournee_livraison'),
                                         trop_percu=request.data.get('trop_percu'))

        refus = self._transition_interdite(commande, nouveau_statut)
        if refus is not None:
            return refus
        annulation = nouveau_statut == 'cancelled' and commande.statut != 'cancelled'
        statut_avant = commande.statut

        # Vérifier si on essaie d'ajuster les quantités d'une commande entièrement payée
        # Permettre l'ajustement pour paiements partiels (est_paye=False)
        if lignes_ajustees and commande.est_paye:
            print(f"[PARTIAL_UPDATE - WARNING] Tentative d'ajustement sur commande entièrement payée {commande.id}")
            return Response(
                {'error': 'Les quantités ne peuvent pas être ajustées pour une commande entièrement payée'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Cas normal: mise à jour standard (pas une livraison)
        # Utiliser le serializer pour gérer la mise à jour des champs et des lignes
        print(f"[PARTIAL_UPDATE] Cas normal (pas livraison), utilisation du serializer")
        serializer = self.get_serializer(commande, data=request.data, partial=True)

        if not serializer.is_valid():
            print(f"[PARTIAL_UPDATE] Erreurs de validation: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        print(f"[PARTIAL_UPDATE] Validation OK, appel de save()")
        serializer.save()
        if annulation:
            # Le serializer a enregistré « annulée » : on repasse par l'annulation complète
            CommandeClient.objects.filter(pk=commande.pk).update(statut=statut_avant)
            commande = self._annuler_commande(commande, logger)
            return Response(CommandeClientSerializer(commande).data)
        print(f"[PARTIAL_UPDATE] ===== FIN (sauvegardé via serializer) =====")
        return Response(serializer.data)

    def _transition_interdite(self, commande, nouveau_statut):
        """Changements de statut refusés quel que soit le chemin (PC, API). Renvoie une Response ou None."""
        if nouveau_statut and nouveau_statut != commande.statut and commande.statut == 'delivered':
            return Response(
                {'error': "Commande déjà livrée : son statut ne peut plus changer "
                          "(le stock du van a été déduit et l'argent compté dans la tournée)."},
                status=status.HTTP_409_CONFLICT)
        return None

    def _tournee_en_cours_du_livreur(self, commande):
        from .distribution_models import TourneeMobile
        if not commande.livreur_id:
            return None
        t = (TourneeMobile.objects.filter(livreur_id=commande.livreur_id, statut='en_cours')
             .order_by('-date_tournee', '-id').first())
        return t.id if t else None

    def _annuler_commande(self, commande, logger):
        """Annulation : l'argent déjà payé (acompte, encaissements) n'est pas perdu ; il passe en
        AVANCE sur le compte du client, utilisable sur ses prochains achats. Avant : la commande
        annulée gardait son acompte, invisible partout. Idempotent."""
        from decimal import Decimal
        from API.models import Client as ClientModel, PaiementSolde
        with transaction.atomic():
            commande = CommandeClient.objects.select_for_update().get(pk=commande.pk)
            if commande.statut == 'cancelled':
                return commande
            paye = commande.montant_paye or Decimal('0')
            commande.statut = 'cancelled'
            champs = ['statut']
            if paye > Decimal('0.01'):
                if not PaiementSolde.objects.filter(app_id=f'annulation-{commande.id}').exists():
                    client = ClientModel.objects.select_for_update().get(pk=commande.client_id)
                    avant = client.solde or Decimal('0')
                    client.solde = avant + paye          # solde positif = avance du client
                    client.save(update_fields=['solde'])
                    PaiementSolde.objects.create(
                        client=client, company=getattr(client, 'company', None), montant=paye,
                        mode_paiement='avoir', solde_avant=avant, solde_apres=client.solde,
                        notes=f'Commande {commande.reference} annulée : montant déjà payé gardé en avance',
                        enregistre_par=self.request.user if self.request.user.is_authenticated else None,
                        app_id=f'annulation-{commande.id}',
                    )
                commande.montant_paye = Decimal('0')
                commande.est_paye = False
                champs += ['montant_paye', 'est_paye']
                logger.info(f"[ANNULATION] Commande {commande.id} : {paye} DA passés en avance client")
            commande.save(update_fields=champs)
            return commande

    def _livrer_commande(self, commande, lignes_ajustees, date_livraison, logger, tournee_livraison_id=None,
                         trop_percu=None):
        """Livraison d'une commande (PATCH statut='delivered'), éventuellement avec des
        quantités ajustées.

        - Idempotente : l'application renvoie la même opération tant qu'elle n'a pas reçu
          de réponse (timeout, réseau coupé). Une commande déjà livrée est renvoyée telle
          quelle, sans toucher aux lignes ni au stock. Avant, ce renvoi passait par le
          serializer qui supprimait toutes les lignes.
        - Atomique : quantités, statut et déduction du stock du van sont validés ensemble.
          Avant, le statut était enregistré puis une erreur (logger non défini) empêchait
          la déduction : commande « livrée » sans sortie de stock.
        """
        from decimal import Decimal

        def _reponse(cmd, stock_info):
            data = CommandeClientSerializer(cmd).data
            data['stock_deduction'] = stock_info
            return Response(data)

        # Quantités demandées, indexées par id produit (entier)
        quantites = None
        if lignes_ajustees:
            try:
                quantites = {
                    int(l.get('produit')): Decimal(str(l.get('quantite', 0)))
                    for l in lignes_ajustees
                }
            except (TypeError, ValueError, ArithmeticError):
                return Response({'error': 'Lignes de livraison invalides'},
                                status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            commande = CommandeClient.objects.select_for_update().get(pk=commande.pk)

            if commande.statut == 'delivered':
                logger.info(f"[LIVRAISON] Commande {commande.id} déjà livrée : renvoi ignoré")
                return _reponse(commande, {
                    'success': True,
                    'message': 'Commande déjà livrée',
                    'mouvements_count': 0,
                    'deja_livree': True,
                })

            if commande.statut == 'cancelled':
                # Commande annulée (l'argent déjà payé est passé en avance client) : elle ne peut
                # plus être livrée, même si le téléphone, hors ligne, l'envoie après l'annulation.
                logger.warning(f"[LIVRAISON] Commande {commande.id} annulée : livraison refusée")
                return Response({'error': 'Livraison impossible : cette commande a été annulée.'},
                                status=status.HTTP_409_CONFLICT)

            lignes = {l.produit_id: l for l in commande.lignes.all()}

            # Quantités identiques à la commande : rien à ajuster (évite aussi de refuser
            # à vie la livraison d'une commande payée que l'app envoie avec ses lignes).
            if quantites is not None and all(
                pid in lignes and lignes[pid].quantite == q for pid, q in quantites.items()
            ):
                quantites = None

            if quantites is not None:
                # (Avant : refus si la commande était entièrement payée. Désormais une livraison
                # réduite est possible ; l'argent payé en trop est rendu ou gardé en avance, au
                # choix du livreur, voir « trop-payé » ci-dessous.)
                total_ht = Decimal('0')
                total_ttc = Decimal('0')
                for pid, ligne in lignes.items():
                    q = quantites.get(pid, ligne.quantite)
                    montant_ht = q * ligne.prix_unitaire_ht
                    montant_tva = montant_ht * (ligne.taux_tva / Decimal('100'))
                    montant_ttc = montant_ht + montant_tva
                    LigneCommandeClient.objects.filter(id=ligne.id).update(
                        quantite=q, montant_ht=montant_ht,
                        montant_tva=montant_tva, montant_ttc=montant_ttc,
                    )
                    total_ht += montant_ht
                    total_ttc += montant_ttc
                for pid in set(quantites) - set(lignes):
                    logger.error(f"[LIVRAISON] Commande {commande.id} : produit {pid} absent de la commande")
                CommandeClient.objects.filter(id=commande.id).update(
                    montant_total_ht=total_ht, montant_total_ttc=total_ttc
                )
                # Livraison augmentée sur une commande payée : elle n'est plus entièrement payée,
                # le reste à payer réapparaît (avant : elle restait « payée »)
                paye = commande.montant_paye or Decimal('0')
                if paye < total_ttc - Decimal('0.01'):
                    CommandeClient.objects.filter(id=commande.id).update(est_paye=False)

            # Historique : quantité juste avant la livraison et quantité livrée, ligne par ligne
            for pid, ligne in lignes.items():
                livree = quantites.get(pid, ligne.quantite) if quantites is not None else ligne.quantite
                LigneCommandeClient.objects.filter(id=ligne.id).update(
                    quantite_avant_livraison=ligne.quantite, quantite_livree=livree)

            commande.statut = 'delivered'
            commande.date_livraison_reelle = date_livraison or timezone.now()
            champs = ['statut', 'date_livraison_reelle']
            # Tournée de livraison envoyée par le téléphone (ignorée si inconnue ou d'un autre livreur)
            if tournee_livraison_id:
                from .distribution_models import TourneeMobile
                _tid = str(tournee_livraison_id).strip()
                t_liv = TourneeMobile.objects.filter(id=int(_tid)).first() if _tid.isdigit() else None
                if t_liv and (not t_liv.livreur_id or t_liv.livreur_id == commande.livreur_id):
                    commande.tournee_livraison = t_liv
                    champs.append('tournee_livraison')
            commande.save(update_fields=champs)
            commande.refresh_from_db()

            # TROP-PAYÉ : livraison réduite en dessous de ce que le client a déjà payé (ex. acompte
            # de 600 pour une livraison qui ne vaut plus que 500). Avant : la commande restait
            # « non payée » et les 100 DA n'étaient enregistrés nulle part. Le livreur choisit sur
            # le téléphone : « rendu » (rendu en espèces, retiré de la caisse de sa tournée) ou
            # « avance » (ajouté au solde du client ; choix par défaut, ex. livraison depuis le PC).
            trop = (commande.montant_paye or Decimal('0')) - (commande.montant_total_ttc or Decimal('0'))
            if trop > Decimal('0.01'):
                from .distribution_models import EncaissementCommande
                from API.models import Client as ClientModel, PaiementSolde
                commande.montant_paye = commande.montant_total_ttc
                commande.est_paye = True
                commande.save(update_fields=['montant_paye', 'est_paye'])
                if str(trop_percu or '').lower() == 'rendu':
                    EncaissementCommande.objects.get_or_create(
                        app_id=f'rendu-{commande.id}',
                        defaults=dict(commande=commande, montant=-trop, type_paiement='especes',
                                      date_paiement=timezone.now(), tournee=commande.tournee_livraison),
                    )
                    logger.info(f"[LIVRAISON] Commande {commande.id} : trop-payé {trop} rendu au client")
                elif not PaiementSolde.objects.filter(app_id=f'avance-{commande.id}').exists():
                    client = ClientModel.objects.select_for_update().get(pk=commande.client_id)
                    avant = client.solde or Decimal('0')
                    client.solde = avant + trop  # solde positif = avance du client
                    client.save(update_fields=['solde'])
                    PaiementSolde.objects.create(
                        client=client, company=getattr(client, 'company', None), montant=trop,
                        mode_paiement='avoir', solde_avant=avant, solde_apres=client.solde,
                        notes=f'Trop-payé sur la commande {commande.reference} (livraison réduite)',
                        enregistre_par=self.request.user if self.request.user.is_authenticated else None,
                        app_id=f'avance-{commande.id}',
                    )
                    logger.info(f"[LIVRAISON] Commande {commande.id} : trop-payé {trop} gardé en avance client")

            quantites_livrees = (
                {pid: int(q) for pid, q in quantites.items()} if quantites is not None else None
            )
            logger.info(f"[LIVRAISON] Déduction stock pour commande {commande.id}")
            resultat_stock = commande.livrer_et_deduire_stock_van(quantites_livrees)
            if not resultat_stock['success']:
                # Stock du van insuffisant, pas de livreur ou pas de van : la livraison est
                # REFUSÉE en entier (statut, quantités, trop-payé annulés). Avant : la commande
                # passait « livrée » sans aucune sortie de stock.
                transaction.set_rollback(True)
                logger.warning(f"[LIVRAISON] Commande {commande.id} refusée : {resultat_stock['message']}")
                message = resultat_stock['message'].replace('Erreur lors de la déduction du stock: ', '')
                return Response({
                    'error': f'Livraison impossible : {message}',
                    'stock_deduction': {'success': False, 'message': message, 'mouvements_count': 0},
                }, status=status.HTTP_409_CONFLICT)

        return _reponse(commande, {
            'success': resultat_stock['success'],
            'message': resultat_stock['message'],
            'mouvements_count': len(resultat_stock['mouvements']),
        })

    @action(detail=False, methods=['post'], url_path='encaisser')
    def encaisser(self, request):
        """
        Encaissement (total ou partiel) d'une commande par le livreur.

        POST /API/distribution/commandes/encaisser/
        {
            "app_id": "cmd-paiement-12-1731...",   # identifiant de l'opération (obligatoire)
            "commande_id": 12,
            "montant": 1500,
            "type_paiement": "especes",            # especes | carte | cheque | virement | credit
            "date_paiement": "2026-11-10T13:00:00Z"
        }

        Idempotent sur app_id : un renvoi renvoie 200 avec `deja_enregistre: true` sans
        ajouter le montant une deuxième fois.
        """
        from decimal import Decimal, InvalidOperation
        from django.db import IntegrityError
        from django.utils.dateparse import parse_datetime

        data = request.data
        app_id = str(data.get('app_id') or '').strip()
        if not app_id:
            return Response({'error': 'app_id est requis'}, status=status.HTTP_400_BAD_REQUEST)

        def _reponse(enc, deja):
            cmd = CommandeClient.objects.get(pk=enc.commande_id)
            return Response({
                'deja_enregistre': deja,
                'encaissement_id': enc.id,
                'commande_id': cmd.id,
                'montant': str(enc.montant),
                'montant_paye': str(cmd.montant_paye),
                'est_paye': cmd.est_paye,
                'reste_a_payer': str(max(cmd.montant_total_ttc - cmd.montant_paye, Decimal('0'))),
            }, status=status.HTTP_200_OK if deja else status.HTTP_201_CREATED)

        existant = EncaissementCommande.objects.filter(app_id=app_id).first()
        if existant:
            return _reponse(existant, True)

        try:
            montant = Decimal(str(data.get('montant')))
        except (InvalidOperation, TypeError, ValueError):
            return Response({'error': 'Montant invalide'}, status=status.HTTP_400_BAD_REQUEST)
        if montant <= 0:
            return Response({'error': 'Le montant doit être supérieur à zéro'},
                            status=status.HTTP_400_BAD_REQUEST)

        type_paiement = data.get('type_paiement') or 'especes'
        # « crédit » n'est pas un encaissement (aucun argent reçu) : refusé
        types_valides = {'especes', 'cheque'}  # un paiement reçu : espèces ou chèque
        if type_paiement not in types_valides:
            return Response({'error': f'Type de paiement invalide : {type_paiement}'},
                            status=status.HTTP_400_BAD_REQUEST)

        date_paiement = parse_datetime(str(data.get('date_paiement') or '')) or timezone.now()

        try:
            with transaction.atomic():
                # Restreint aux commandes visibles par l'utilisateur (entreprise, livreur)
                # of=('self',) : PostgreSQL refuse FOR UPDATE sur le côté nullable d'un
                # LEFT JOIN (select_related('livreur')).
                commande = self.get_queryset().select_for_update(of=('self',)).filter(
                    pk=data.get('commande_id')
                ).first()
                from .securite_encaissements import commande_autorisee, tournee_autorisee
                if commande is None or not commande_autorisee(request, commande):
                    return Response({'error': 'Commande introuvable'}, status=status.HTTP_404_NOT_FOUND)
                if commande.statut == 'cancelled':
                    return Response({'error': 'Commande annulée : encaissement impossible'},
                                    status=status.HTTP_409_CONFLICT)

                # Tournée pendant laquelle l'argent a été reçu (caisse de la tournée)
                _tid = str(data.get('tournee') or '').strip()
                from .distribution_models import TourneeMobile as _TM
                tournee_enc = _TM.objects.filter(pk=int(_tid)).select_related('livreur__entrepot').first() if _tid.isdigit() else None
                if not tournee_autorisee(request, tournee_enc):
                    return Response({'error': "Cette tournée n'est pas la vôtre"}, status=status.HTTP_403_FORBIDDEN)
                # Montant plafonné au reste dû (avant : n'importe quel montant était accepté,
                # ex. 10 000 DA sur une commande de 180 DA)
                reste_du = max((commande.montant_total_ttc or Decimal('0')) - (commande.montant_paye or Decimal('0')), Decimal('0'))
                if montant > reste_du + Decimal('0.01'):
                    return Response({'error': f'Montant ({montant}) supérieur au reste à payer ({reste_du})'},
                                    status=status.HTTP_400_BAD_REQUEST)
                enc = EncaissementCommande.objects.create(
                    commande=commande, app_id=app_id, montant=montant,
                    type_paiement=type_paiement, date_paiement=date_paiement,
                    tournee=tournee_enc,
                    enregistre_par=request.user,
                )
                commande.montant_paye = (commande.montant_paye or Decimal('0')) + montant
                commande.est_paye = commande.montant_paye >= commande.montant_total_ttc - Decimal('0.01')
                commande.type_paiement = type_paiement
                commande.date_paiement = date_paiement
                commande.save(update_fields=['montant_paye', 'est_paye', 'type_paiement', 'date_paiement'])
        except (ValueError, TypeError):
            return Response({'error': 'commande_id invalide'}, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError:
            # Deux envois simultanés de la même opération
            existant = EncaissementCommande.objects.filter(app_id=app_id).first()
            if existant:
                return _reponse(existant, True)
            raise

        return _reponse(enc, False)

    @action(detail=False, methods=['post'], url_path='modifier_lignes')
    def modifier_lignes(self, request):
        """
        Modification d'une commande par un prevendeur ou un livreur (le client change
        d'avis sur un produit ou une quantite) : ajouts, retraits, quantites a la hausse
        ou a la baisse. Regles dans API/commande_modification.py.

        POST /API/distribution/commandes/modifier_lignes/
        {
            "id": 12            # ou "app_id": "commande-..." (identifiant cree par l'application)
            "lignes": [{"produit": 5, "quantite": 10, "prix_unitaire_ht": 8.5}],
            "notes": "..."      # optionnel
        }
        200 : commande a jour + "modifications" ; 400 / 403 / 404 / 409 : {"detail": "..."}
        """
        from .commande_modification import ModificationRefusee, modifier_lignes_commande

        data = request.data if isinstance(request.data, dict) else {}
        ident = data.get('id') or data.get('commande_id')
        app_id = data.get('app_id')
        if not ident and not app_id:
            return Response({'detail': "Précisez la commande (« id » ou « app_id »)."},
                            status=status.HTTP_400_BAD_REQUEST)

        from .tenant import filtrer
        commandes = filtrer(CommandeClient.objects.all(), request)
        if ident:
            commande = commandes.filter(pk=ident).first() if str(ident).isdigit() else None
        else:
            commande = commandes.filter(app_id=str(app_id)).first()
        if commande is None:
            return Response({'detail': 'Commande introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        # Droits : administrateur, ou vendeur (prevendeur / livreur) actif.
        # La commande ne porte qu'un seul vendeur : apres affectation au livreur, le
        # prevendeur qui l'a prise n'y figure plus. On ne peut donc pas exiger que
        # l'auteur soit le vendeur de la commande ; l'auteur est trace dans la commande.
        user = request.user
        if not (user.is_staff or user.is_superuser):
            profil = LivreurDistribution.objects.filter(user=user).first()
            if profil is None:
                return Response({'detail': "Seul un vendeur ou un administrateur peut modifier une commande."},
                                status=status.HTTP_403_FORBIDDEN)
            if profil.statut != 'actif':
                return Response({'detail': "Votre compte vendeur n'est pas actif."},
                                status=status.HTTP_403_FORBIDDEN)

        # Commande déjà payée : modifiable seulement par son livreur (à la livraison) ou un administrateur
        autoriser_payee = bool(user.is_staff or user.is_superuser) or (
            commande.livreur_id is not None and commande.livreur_id == getattr(
                LivreurDistribution.objects.filter(user=user).first(), 'id', None))
        quantites_avant = {pid: q for pid, q in commande.lignes.values_list('produit_id', 'quantite')}
        try:
            commande, modifications = modifier_lignes_commande(
                commande, data.get('lignes'), user, notes=data.get('notes') if 'notes' in data else None,
                autoriser_payee=autoriser_payee)
        except ModificationRefusee as e:
            reponse = {'detail': e.message}
            if e.champ:
                reponse['champ'] = e.champ
            return Response(reponse, status=e.code)

        resultat = CommandeClientSerializer(
            CommandeClient.objects.select_related('client', 'livreur').prefetch_related('lignes', 'lignes__produit', 'lignes__produit__conditionnements')
            .get(pk=commande.pk)).data
        resultat['modifications'] = modifications
        # Commande déjà affectée (stock transféré dans le van) dont une quantité augmente : le
        # van peut manquer de stock à la livraison. Simple avertissement, aucun mouvement de stock.
        resultat['avertissement_stock_van'] = _avertissement_stock_van(commande, quantites_avant)
        return Response(resultat)

    @action(detail=True, methods=['patch'])
    def changer_statut(self, request, pk=None):
        """Changer le statut d'une commande"""
        commande = self.get_object()
        ancien_statut = commande.statut  # Stocker l'ancien statut pour éviter double déduction
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

        import logging
        logger = logging.getLogger(__name__)

        refus = self._transition_interdite(commande, nouveau_statut)
        if refus is not None:
            return refus

        # Livrée : même traitement que la livraison depuis le téléphone (stock du van, tournée
        # en cours du livreur, trop-payé gardé en avance). Avant : statut changé directement,
        # sans tournée, et « livrée » même si la sortie de stock échouait.
        if nouveau_statut == 'delivered' and ancien_statut != 'delivered':
            reponse = self._livrer_commande(
                commande, None, timezone.now(), logger,
                tournee_livraison_id=self._tournee_en_cours_du_livreur(commande))
            if reponse.status_code == 200:
                commande.refresh_from_db()
                return Response({
                    'message': f'Statut changé à {nouveau_statut}',
                    'stock_message': reponse.data.get('stock_deduction', {}).get('message', ''),
                    'commande': CommandeClientSerializer(commande).data,
                })
            return reponse

        if nouveau_statut == 'cancelled':
            commande = self._annuler_commande(commande, logger)
            return Response({
                'message': f'Statut changé à {nouveau_statut}',
                'commande': CommandeClientSerializer(commande).data,
            })

        commande.statut = nouveau_statut
        commande.save(update_fields=['statut'])
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

    @action(detail=True, methods=['post'])
    def affecter_livreur(self, request, pk=None):
        """
        Affecte une commande à un livreur et transfère automatiquement les produits
        de l'entrepôt vers le van du livreur.

        Body:
        {
            "livreur_id": int,           # ID du livreur
            "entrepot_source_id": int    # ID de l'entrepôt source (optionnel, prend l'entrepôt principal par défaut)
        }

        Returns:
        - 200: Commande affectée avec succès
        - 400: Erreur (rupture de stock, livreur sans van, etc.)
        """
        from .models import Warehouse
        from .distribution_models import LivreurDistribution

        print(f"[AFFECTER LIVREUR] Début - Commande ID: {pk}, User: {request.user.username}")
        print(f"[AFFECTER LIVREUR] Request data: {request.data}")

        commande = self.get_object()
        print(f"[AFFECTER LIVREUR] Commande récupérée: {commande.reference}, Statut: {commande.statut}, Lignes: {commande.lignes.count()}")

        livreur_id = request.data.get('livreur_id')
        entrepot_source_id = request.data.get('entrepot_source_id')

        # Validation des paramètres
        if not livreur_id:
            print(f"[AFFECTER LIVREUR] Erreur: livreur_id manquant")
            return Response(
                {'error': 'livreur_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Récupérer le livreur
        try:
            livreur = LivreurDistribution.objects.get(id=livreur_id)
            print(f"[AFFECTER LIVREUR] Livreur trouvé: {livreur.nom}, Van: {livreur.entrepot}")
        except LivreurDistribution.DoesNotExist:
            print(f"[AFFECTER LIVREUR] Erreur: Livreur ID {livreur_id} introuvable")
            return Response(
                {'error': f'Livreur avec ID {livreur_id} introuvable'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Récupérer l'entrepôt source :
        # 1) celui choisi dans la fenêtre « Affecter à un Livreur » ;
        # 2) sinon le dépôt par défaut des commandes mobiles (Paramètres > Général) ;
        # 3) sinon l'ancien choix automatique (premier dépôt actif hors van).
        from .models import SystemConfig
        if entrepot_source_id:
            try:
                entrepot_source = Warehouse.objects.get(id=int(entrepot_source_id))
                print(f"[AFFECTER LIVREUR] Entrepôt source spécifié: {entrepot_source.name} (ID: {entrepot_source.id})")
            except (Warehouse.DoesNotExist, ValueError, TypeError):
                print(f"[AFFECTER LIVREUR] Erreur: Entrepôt ID {entrepot_source_id} introuvable")
                return Response(
                    {'success': False, 'message': f'Entrepôt source #{entrepot_source_id} introuvable', 'ruptures': []},
                    status=status.HTTP_404_NOT_FOUND
                )
            if not entrepot_source.is_active:
                return Response({'success': False, 'message': f"L'entrepôt {entrepot_source.name} est inactif", 'ruptures': []},
                                status=status.HTTP_400_BAD_REQUEST)
            if 'van' in (entrepot_source.code or '').lower():
                return Response({'success': False, 'ruptures': [],
                                 'message': f"{entrepot_source.name} est un van : choisissez un dépôt comme entrepôt source"},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            entrepot_source = None
            # Paramètres de l'entreprise de la commande (chaque entreprise a les siens)
            cfg_company = commande.company or getattr(commande.client, 'company', None)
            depot_cfg = SystemConfig.get_solo(cfg_company).depot_commandes_mobile
            if depot_cfg and depot_cfg.is_active and 'van' not in (depot_cfg.code or '').lower():
                entrepot_source = depot_cfg
                print(f"[AFFECTER LIVREUR] Dépôt par défaut (paramètres): {entrepot_source.name}")

        if not entrepot_source:
            # Prendre l'entrepôt principal de la company
            # On cherche un entrepôt actif qui n'est pas un van
            print(f"[AFFECTER LIVREUR] Recherche d'un entrepôt source pour company: {commande.company}")

            # Essayer d'abord avec la company de la commande
            if commande.company:
                entrepot_source = Warehouse.objects.filter(
                    company=commande.company,
                    is_active=True
                ).exclude(
                    code__icontains='van'
                ).first()
                print(f"[AFFECTER LIVREUR] Recherche avec company: trouvé={entrepot_source}")
            else:
                entrepot_source = None

            # Si pas trouvé avec company, essayer avec la company du client
            if not entrepot_source and commande.client.company:
                print(f"[AFFECTER LIVREUR] Commande sans company, recherche avec company du client: {commande.client.company}")
                entrepot_source = Warehouse.objects.filter(
                    company=commande.client.company,
                    is_active=True
                ).exclude(
                    code__icontains='van'
                ).first()
                print(f"[AFFECTER LIVREUR] Recherche avec company du client: trouvé={entrepot_source}")

                # Mettre à jour la commande avec la company du client
                if entrepot_source:
                    commande.company = commande.client.company
                    commande.save(update_fields=['company'])
                    print(f"[AFFECTER LIVREUR] Company du client assignée à la commande")

            # Si toujours pas trouvé, chercher n'importe quel entrepôt actif non-van
            if not entrepot_source:
                print(f"[AFFECTER LIVREUR] Aucun entrepôt trouvé avec company, recherche globale...")
                entrepot_source = Warehouse.objects.filter(
                    is_active=True
                ).exclude(
                    code__icontains='van'
                ).first()
                print(f"[AFFECTER LIVREUR] Recherche globale: trouvé={entrepot_source}")

            if not entrepot_source:
                print(f"[AFFECTER LIVREUR] Erreur: Aucun entrepôt source trouvé dans le système")
                return Response(
                    {'error': 'Aucun entrepôt source trouvé. Veuillez créer un entrepôt ou spécifier entrepot_source_id.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            else:
                print(f"[AFFECTER LIVREUR] Entrepôt source auto-détecté: {entrepot_source.name} (ID: {entrepot_source.id})")

        # Effectuer l'affectation et le transfert de stock
        print(f"[AFFECTER LIVREUR] Appel affecter_livreur_et_preparer_stock...")
        try:
            resultat = commande.affecter_livreur_et_preparer_stock(
                livreur=livreur,
                entrepot_source=entrepot_source,
                user=request.user
            )
            print(f"[AFFECTER LIVREUR] Résultat: success={resultat['success']}, message={resultat['message']}")
        except Exception as e:
            print(f"[AFFECTER LIVREUR] Exception non gérée: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({
                'success': False,
                'error': f'Erreur inattendue: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if resultat['success']:
            print(f"[AFFECTER LIVREUR] Succès - Transfert: {resultat['transfert']}")
            return Response({
                'success': True,
                'message': resultat['message'],
                'commande': CommandeClientSerializer(commande).data,
                'transfert_numero': resultat['transfert'].numero if resultat['transfert'] else None,
                'entrepot_source': {'id': entrepot_source.id, 'nom': entrepot_source.name},
            }, status=status.HTTP_200_OK)
        else:
            # En cas de rupture de stock ou autre erreur
            print(f"[AFFECTER LIVREUR] Échec - Ruptures: {len(resultat.get('ruptures', []))}")
            return Response({
                'success': False,
                'message': resultat['message'],
                'ruptures': resultat['ruptures'],
                'entrepot_source': {'id': entrepot_source.id, 'nom': entrepot_source.name},
            }, status=status.HTTP_400_BAD_REQUEST)


class PlanningHebdomadaireViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des plannings hebdomadaires"""
    queryset = PlanningHebdomadaire.objects.all()
    serializer_class = PlanningHebdomadaireSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Utiliser PlanningHebdomadaireCreateSerializer pour create"""
        if self.action == 'create':
            return PlanningHebdomadaireCreateSerializer
        return PlanningHebdomadaireSerializer

    def get_queryset(self):
        from django.db.models import Q
        queryset = super().get_queryset()

        # Filtrer par company de l'utilisateur si applicable
        if hasattr(self.request, 'company') and self.request.company:
            queryset = queryset.filter(
                Q(company=self.request.company) | Q(company__isnull=True)
            )

        # Filtres optionnels
        livreur_id = self.request.query_params.get('livreur')
        jour_semaine = self.request.query_params.get('jour_semaine')
        is_active = self.request.query_params.get('is_active')

        if livreur_id:
            queryset = queryset.filter(livreur_id=livreur_id)

        if jour_semaine:
            queryset = queryset.filter(jour_semaine=jour_semaine)

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset.select_related('livreur', 'code_prix', 'created_by', 'company')

    def perform_create(self, serializer):
        """Attacher la company et le created_by lors de la création"""
        kwargs = {}
        if hasattr(self.request, 'company') and self.request.company:
            kwargs['company'] = self.request.company
        if hasattr(self.request, 'user'):
            kwargs['created_by'] = self.request.user
        serializer.save(**kwargs)

    @action(detail=False, methods=['post'])
    def generer_semaine(self, request):
        """Générer toutes les tournées pour une semaine donnée basées sur les plannings"""
        from datetime import datetime, timedelta

        date_debut_str = request.data.get('date_debut')
        if not date_debut_str:
            return Response(
                {'error': 'date_debut requise (format YYYY-MM-DD)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Format de date invalide. Utilisez YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # S'assurer que date_debut est un lundi
        if date_debut.weekday() != 0:  # 0 = lundi
            # Ajuster au lundi précédent
            date_debut = date_debut - timedelta(days=date_debut.weekday())

        # Générer les tournées
        company = self.request.company if hasattr(self.request, 'company') else None
        tournees_creees = PlanningHebdomadaire.generer_tournees_pour_semaine(date_debut, company)

        # Sérialiser les tournées créées
        from .distribution_serializers import TourneeSerializer
        serializer = TourneeSerializer(tournees_creees, many=True)

        return Response({
            'message': f'{len(tournees_creees)} tournée(s) générée(s) pour la semaine du {date_debut}',
            'date_debut': date_debut,
            'tournees': serializer.data
        })

    @action(detail=True, methods=['post'])
    def generer_tournee(self, request, pk=None):
        """Générer une tournée pour une date donnée basée sur ce planning"""
        from datetime import datetime

        planning = self.get_object()
        date_str = request.data.get('date')

        if not date_str:
            return Response(
                {'error': 'date requise (format YYYY-MM-DD)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Format de date invalide. Utilisez YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Générer la tournée
        tournee = planning.generer_tournee_pour_date(date)

        if not tournee:
            return Response(
                {'error': 'Impossible de générer la tournée pour cette date (planning inactif ou date invalide)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Sérialiser la tournée créée
        from .distribution_serializers import TourneeSerializer
        serializer = TourneeSerializer(tournee)

        return Response({
            'message': 'Tournée générée avec succès',
            'tournee': serializer.data
        })

    @action(detail=False, methods=['get'])
    def par_livreur(self, request):
        """Récupérer tous les plannings d'un livreur"""
        livreur_id = request.query_params.get('livreur_id')

        if not livreur_id:
            return Response(
                {'error': 'livreur_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        plannings = self.get_queryset().filter(livreur_id=livreur_id, is_active=True)
        serializer = self.get_serializer(plannings, many=True)

        return Response(serializer.data)


class ClientLivreurHebdoViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer la configuration hebdomadaire des clients par livreur"""
    queryset = ClientLivreurHebdo.objects.all()
    serializer_class = ClientLivreurHebdoSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['livreur', 'client', 'jour_semaine', 'is_active']
    search_fields = ['client__nom', 'livreur__nom']
    ordering_fields = ['jour_semaine', 'ordre_passage']
    ordering = ['jour_semaine', 'ordre_passage']

    # --- Entreprise de l'utilisateur (TenantMiddleware) ---------------------------------
    # Avant : request.user.company (inexistant) -> aucun filtre, les affectations, livreurs et
    # clients de TOUTES les entreprises sortaient dans la liste et les exports Excel.
    def _company(self):
        from .tenant import entreprise_de
        return entreprise_de(self.request)   # session web ou jeton du téléphone

    def _livreurs_entreprise(self):
        """Livreurs de l'entreprise (règles communes : API/tenant.py)."""
        from .tenant import filtrer_livreurs
        return filtrer_livreurs(LivreurDistribution.objects.all(), self.request)

    def _clients_entreprise(self):
        from .models import Client
        qs = Client.objects.all()
        company = self._company()
        if company is not None and not self.request.user.is_superuser:
            qs = qs.filter(company=company)
        return qs

    def get_queryset(self):
        queryset = super().get_queryset()
        company = self._company()
        if company is not None and not self.request.user.is_superuser:
            # Anciennes lignes sans entreprise : rattachées par l'entreprise du client
            queryset = queryset.filter(models.Q(company=company)
                                       | models.Q(company__isnull=True, client__company=company))
        return queryset.select_related('client', 'livreur', 'company', 'created_by')

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ClientLivreurHebdoCreateSerializer
        return ClientLivreurHebdoSerializer

    def perform_create(self, serializer):
        """Assigner automatiquement la company et created_by lors de la création"""
        kwargs = {}

        # Assigner created_by
        if self.request.user.is_authenticated:
            kwargs['created_by'] = self.request.user

            # Assigner company depuis l'utilisateur connecté
            if self._company() is not None:
                kwargs['company'] = self._company()

        self._verifier_entreprise(serializer)
        serializer.save(**kwargs)

    def _verifier_entreprise(self, serializer):
        """Refuse un client ou un livreur d'une autre entreprise."""
        from rest_framework.exceptions import ValidationError
        data = serializer.validated_data
        client, livreur = data.get('client'), data.get('livreur')
        if client is not None and not self._clients_entreprise().filter(pk=client.pk).exists():
            raise ValidationError({'client': 'Client introuvable'})
        if livreur is not None and not self._livreurs_entreprise().filter(pk=livreur.pk).exists():
            raise ValidationError({'livreur': 'Livreur introuvable'})

    def perform_update(self, serializer):
        """Ne pas modifier la company lors de la mise à jour"""
        self._verifier_entreprise(serializer)
        serializer.save()

    @action(detail=False, methods=['get'])
    def par_livreur(self, request):
        """Récupérer tous les clients d'un livreur pour un jour donné"""
        livreur_id = request.query_params.get('livreur_id')
        jour_semaine = request.query_params.get('jour_semaine')

        if not livreur_id:
            return Response(
                {'error': 'livreur_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        queryset = self.get_queryset().filter(livreur_id=livreur_id, is_active=True)

        if jour_semaine:
            queryset = queryset.filter(jour_semaine=jour_semaine)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def par_client(self, request):
        """Récupérer le livreur assigné à un client pour un jour donné"""
        client_id = request.query_params.get('client_id')
        jour_semaine = request.query_params.get('jour_semaine')

        if not client_id:
            return Response(
                {'error': 'client_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        queryset = self.get_queryset().filter(client_id=client_id, is_active=True)

        if jour_semaine:
            queryset = queryset.filter(jour_semaine=jour_semaine)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def assigner_clients(self, request):
        """Assigner plusieurs clients à un livreur pour un ou plusieurs jours"""
        livreur_id = request.data.get('livreur_id')
        clients_ids = request.data.get('clients_ids', [])
        jours_semaine = request.data.get('jours_semaine', [])

        if not livreur_id or not clients_ids or not jours_semaine:
            return Response(
                {'error': 'livreur_id, clients_ids et jours_semaine requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier que le livreur existe (dans l'entreprise de l'utilisateur)
        try:
            livreur = self._livreurs_entreprise().get(id=livreur_id)
        except LivreurDistribution.DoesNotExist:
            return Response(
                {'error': 'Livreur non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )

        company = self._company()
        created_assignments = []
        errors = []

        for client_id in clients_ids:
            try:
                from .models import Client
                client = self._clients_entreprise().get(id=client_id)

                for jour in jours_semaine:
                    # Vérifier si une assignation existe déjà (ou une ancienne ligne sans entreprise)
                    existing = ClientLivreurHebdo.objects.filter(
                        client=client,
                        jour_semaine=jour,
                        is_active=True
                    ).filter(
                        models.Q(company=company) | models.Q(company__isnull=True)
                    ).order_by(models.F('company').asc(nulls_last=True)).first()
                    if existing and existing.company_id is None and company is not None:
                        existing.company = company

                    if existing:
                        # Mettre à jour l'assignation existante
                        existing.livreur = livreur
                        existing.updated_by = request.user
                        existing.save()
                        created_assignments.append({
                            'client_id': client_id,
                            'jour_semaine': jour,
                            'action': 'updated'
                        })
                    else:
                        # Créer une nouvelle assignation
                        assignment = ClientLivreurHebdo.objects.create(
                            client=client,
                            livreur=livreur,
                            jour_semaine=jour,
                            company=company,
                            created_by=request.user
                        )
                        created_assignments.append({
                            'client_id': client_id,
                            'jour_semaine': jour,
                            'action': 'created',
                            'id': assignment.id
                        })

            except Client.DoesNotExist:
                errors.append(f'Client {client_id} non trouvé')
            except Exception as e:
                errors.append(f'Erreur pour client {client_id}: {str(e)}')

        return Response({
            'message': f'{len(created_assignments)} assignation(s) créée(s)/modifiée(s)',
            'assignments': created_assignments,
            'errors': errors
        })

    @action(detail=False, methods=['delete'])
    def supprimer_assignations(self, request):
        """Supprimer des assignations (désactiver)"""
        assignations_ids = request.data.get('assignations_ids', [])

        if not assignations_ids:
            return Response(
                {'error': 'assignations_ids requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        company = request.user.company if hasattr(request.user, 'company') else None

        assignations = self.get_queryset().filter(id__in=assignations_ids)
        count = assignations.count()

        # Désactiver au lieu de supprimer
        concernes = list(assignations.values_list('livreur_id', 'client_id'))
        # (le modèle n'a pas de champ updated_by : update(updated_by=...) plantait en 500)
        assignations.update(is_active=False, updated_at=timezone.now())
        # update() ne déclenche pas les signaux : retirer ici les arrêts « en attente » de ces
        # clients des tournées à venir
        from .distribution_prix_stock import planifier_sync_arrets
        planifier_sync_arrets({l for l, _ in concernes}, {c for _, c in concernes})

        return Response({
            'message': f'{count} assignation(s) désactivée(s)',
            'count': count
        })

    @action(detail=False, methods=['get'], url_path='export-excel')
    def export_excel(self, request):
        """
        Exporter les configurations clients-livreurs en Excel pour une semaine donnée.
        GET /API/distribution/clients-livreurs-hebdo/export-excel/?date_debut=2024-12-02&date_fin=2024-12-08
        """
        from django.http import HttpResponse
        import io
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        except ImportError:
            return Response(
                {'error': 'openpyxl est requis. Installez-le avec: pip install openpyxl'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        date_debut_str = request.query_params.get('date_debut')
        date_fin_str = request.query_params.get('date_fin')

        if not date_debut_str or not date_fin_str:
            return Response(
                {'error': 'date_debut et date_fin sont requis (format YYYY-MM-DD)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
            date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Format de date invalide. Utilisez YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Récupérer les configurations actives pour la période
        company = self._company()
        configs = self.get_queryset().filter(
            is_active=True
        ).filter(
            models.Q(date_debut__isnull=True) | models.Q(date_debut__lte=date_fin)
        ).filter(
            models.Q(date_fin__isnull=True) | models.Q(date_fin__gte=date_debut)
        ).select_related('client', 'livreur').order_by('livreur__nom', 'jour_semaine', 'ordre_passage')

        # Créer le workbook Excel
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Planning Semaine"

        # Styles
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="3B82F6", end_color="3B82F6", fill_type="solid")
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        # En-têtes
        jours_noms = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        headers = ['Livreur', 'Client ID', 'Client Nom', 'Client Prénom', 'Téléphone', 'Adresse', 'Secteur']
        headers.extend(jours_noms)

        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
            cell.border = border

        # Regrouper les configs par client
        clients_configs = {}
        for config in configs:
            key = (config.livreur_id, config.client_id)
            if key not in clients_configs:
                clients_configs[key] = {
                    'livreur': config.livreur.nom if config.livreur else '',
                    'client_id': config.client.id if config.client else '',
                    'client_nom': config.client.nom if config.client else '',
                    'client_prenom': config.client.prenom if config.client else '',
                    'telephone': config.client.telephone if config.client else '',
                    'adresse': config.client.adresse if config.client else '',
                    'secteur': config.client.secteur.nom if config.client and config.client.secteur else '',
                    'jours': {}
                }
            clients_configs[key]['jours'][config.jour_semaine] = config.ordre_passage or 'X'

        # Écrire les données
        row = 2
        for (livreur_id, client_id), data in clients_configs.items():
            ws.cell(row=row, column=1, value=data['livreur']).border = border
            ws.cell(row=row, column=2, value=data['client_id']).border = border
            ws.cell(row=row, column=3, value=data['client_nom']).border = border
            ws.cell(row=row, column=4, value=data['client_prenom']).border = border
            ws.cell(row=row, column=5, value=data['telephone']).border = border
            ws.cell(row=row, column=6, value=data['adresse']).border = border
            ws.cell(row=row, column=7, value=data['secteur']).border = border

            # Jours de la semaine (1=Lundi ... 7=Dimanche)
            for jour in range(1, 8):
                cell = ws.cell(row=row, column=7 + jour)
                if jour in data['jours']:
                    cell.value = data['jours'][jour]
                    cell.fill = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid")
                cell.border = border
                cell.alignment = Alignment(horizontal='center')

            row += 1

        # Ajuster la largeur des colonnes
        ws.column_dimensions['A'].width = 20  # Livreur
        ws.column_dimensions['B'].width = 10  # Client ID
        ws.column_dimensions['C'].width = 20  # Client Nom
        ws.column_dimensions['D'].width = 15  # Client Prénom
        ws.column_dimensions['E'].width = 15  # Téléphone
        ws.column_dimensions['F'].width = 30  # Adresse
        ws.column_dimensions['G'].width = 15  # Secteur
        for col in ['H', 'I', 'J', 'K', 'L', 'M', 'N']:  # Jours de la semaine
            ws.column_dimensions[col].width = 12

        # Créer la réponse HTTP
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=planning_semaine_{date_debut_str}_{date_fin_str}.xlsx'
        return response

    @action(detail=False, methods=['get'], url_path='template-excel')
    def template_excel(self, request):
        """
        Télécharger un template Excel avec les configurations existantes.
        GET /API/distribution/clients-livreurs-hebdo/template-excel/
        """
        from django.http import HttpResponse
        import io
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils.dataframe import dataframe_to_rows
        except ImportError:
            return Response(
                {'error': 'openpyxl est requis. Installez-le avec: pip install openpyxl'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        from .models import Client

        # Créer le workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Planning Import"

        # Styles
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="3B82F6", end_color="3B82F6", fill_type="solid")
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        # En-têtes avec noms complets
        headers = [
            'Livreur ID*', 'Livreur Nom', 'Client ID*', 'Client Nom Complet', 'Secteur',
            'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'
        ]

        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
            cell.border = border

        # Récupérer les données
        company = self._company()

        # Récupérer tous les livreurs
        livreurs = list(self._livreurs_entreprise().order_by('nom'))

        # Récupérer tous les clients
        clients_qs = self._clients_entreprise().order_by('nom', 'prenom')
        clients = list(clients_qs)

        # Récupérer toutes les configurations existantes
        configs_existantes = self.get_queryset().filter(is_active=True)

        # Regrouper les configurations par (livreur_id, client_id)
        configs_dict = {}
        for config in configs_existantes:
            key = (config.livreur_id, config.client_id)
            if key not in configs_dict:
                configs_dict[key] = {}
            configs_dict[key][config.jour_semaine] = config.ordre_passage or 'X'

        # Styles supplémentaires
        existing_fill = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid")  # Bleu clair - config existante
        new_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")  # Blanc - nouvelle ligne
        livreur_header_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")  # Jaune - en-tête livreur

        current_row = 2

        # Pour chaque livreur, afficher TOUS les clients
        for livreur in livreurs:
            # Ajouter une ligne d'en-tête pour ce livreur
            header_cell = ws.cell(row=current_row, column=1, value=f"▶ {livreur.nom} (ID: {livreur.id}) - {livreur.matricule or 'Sans matricule'}")
            header_cell.font = Font(bold=True, color="92400E")
            header_cell.fill = livreur_header_fill
            ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=12)
            for col in range(1, 13):
                ws.cell(row=current_row, column=col).border = border
                ws.cell(row=current_row, column=col).fill = livreur_header_fill
            current_row += 1

            # Afficher tous les clients pour ce livreur
            for client in clients:
                key = (livreur.id, client.id)
                jours_config = configs_dict.get(key, {})
                has_config = len(jours_config) > 0

                # Choisir le style selon si config existante ou non
                fill_style = existing_fill if has_config else new_fill

                # Livreur ID
                ws.cell(row=current_row, column=1, value=livreur.id).fill = fill_style
                ws.cell(row=current_row, column=1).border = border
                # Livreur Nom
                ws.cell(row=current_row, column=2, value=livreur.nom).fill = fill_style
                ws.cell(row=current_row, column=2).border = border
                # Client ID
                ws.cell(row=current_row, column=3, value=client.id).fill = fill_style
                ws.cell(row=current_row, column=3).border = border
                # Client Nom Complet
                client_nom = f"{client.nom} {client.prenom}".strip()
                ws.cell(row=current_row, column=4, value=client_nom).fill = fill_style
                ws.cell(row=current_row, column=4).border = border
                # Secteur
                secteur_nom = client.secteur.nom if client.secteur else ''
                ws.cell(row=current_row, column=5, value=secteur_nom).fill = fill_style
                ws.cell(row=current_row, column=5).border = border

                # Jours (1=Lundi ... 7=Dimanche) -> colonnes 6 à 12
                for jour in range(1, 8):
                    cell = ws.cell(row=current_row, column=5 + jour)
                    cell.value = jours_config.get(jour, '')
                    cell.fill = fill_style
                    cell.border = border
                    cell.alignment = Alignment(horizontal='center')

                current_row += 1

            # Ligne vide entre les livreurs
            current_row += 1

        # ========== FEUILLE LIVREURS ==========
        ws_livreurs = wb.create_sheet(title="Liste Livreurs")

        # En-têtes livreurs
        livreurs_headers = ['ID', 'Nom Complet', 'Matricule', 'Téléphone', 'Statut', 'Nb Clients Assignés']
        for col, header in enumerate(livreurs_headers, 1):
            cell = ws_livreurs.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = border

        # Données livreurs
        for row, livreur in enumerate(livreurs, 2):
            nb_clients = livreur.clients_assignes.count()
            ws_livreurs.cell(row=row, column=1, value=livreur.id).border = border
            ws_livreurs.cell(row=row, column=2, value=livreur.nom).border = border
            ws_livreurs.cell(row=row, column=3, value=livreur.matricule or '').border = border
            ws_livreurs.cell(row=row, column=4, value=livreur.telephone or '').border = border
            ws_livreurs.cell(row=row, column=5, value=livreur.statut or 'actif').border = border
            ws_livreurs.cell(row=row, column=6, value=nb_clients).border = border

        # Ajuster largeurs colonnes livreurs
        ws_livreurs.column_dimensions['A'].width = 8
        ws_livreurs.column_dimensions['B'].width = 25
        ws_livreurs.column_dimensions['C'].width = 15
        ws_livreurs.column_dimensions['D'].width = 15
        ws_livreurs.column_dimensions['E'].width = 12
        ws_livreurs.column_dimensions['F'].width = 18

        # ========== FEUILLE CLIENTS ==========
        ws_clients = wb.create_sheet(title="Liste Clients")

        # En-têtes clients
        clients_headers = ['ID', 'Nom', 'Prénom', 'Nom Complet', 'Téléphone', 'Email', 'Adresse', 'Secteur']
        for col, header in enumerate(clients_headers, 1):
            cell = ws_clients.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = border

        # Données clients
        for row, client in enumerate(clients, 2):
            nom_complet = f"{client.nom} {client.prenom}".strip()
            secteur_nom = client.secteur.nom if client.secteur else ''

            ws_clients.cell(row=row, column=1, value=client.id).border = border
            ws_clients.cell(row=row, column=2, value=client.nom).border = border
            ws_clients.cell(row=row, column=3, value=client.prenom or '').border = border
            ws_clients.cell(row=row, column=4, value=nom_complet).border = border
            ws_clients.cell(row=row, column=5, value=client.telephone or '').border = border
            ws_clients.cell(row=row, column=6, value=client.email or '').border = border
            ws_clients.cell(row=row, column=7, value=client.adresse or '').border = border
            ws_clients.cell(row=row, column=8, value=secteur_nom).border = border

        # Ajuster largeurs colonnes clients
        ws_clients.column_dimensions['A'].width = 8
        ws_clients.column_dimensions['B'].width = 20
        ws_clients.column_dimensions['C'].width = 15
        ws_clients.column_dimensions['D'].width = 30
        ws_clients.column_dimensions['E'].width = 15
        ws_clients.column_dimensions['F'].width = 25
        ws_clients.column_dimensions['G'].width = 30
        ws_clients.column_dimensions['H'].width = 15

        # ========== FEUILLE INSTRUCTIONS ==========
        ws_help = wb.create_sheet(title="Instructions")
        instructions = [
            "═══════════════════════════════════════════════════════════════",
            "           INSTRUCTIONS POUR L'IMPORT DU PLANNING",
            "═══════════════════════════════════════════════════════════════",
            "",
            "STRUCTURE DU FICHIER :",
            "  • Chaque livreur a une section avec TOUS les clients listés",
            "  • Les en-têtes jaunes indiquent le nom du livreur",
            "  • Modifiez les jours directement dans les cellules",
            "",
            "COLONNES JOURS (Lundi à Dimanche) :",
            "  • Mettre un numéro (1, 2, 3...) pour définir l'ordre de passage",
            "  • Mettre 'X' pour assigner sans ordre spécifique",
            "  • Laisser vide = pas de visite ce jour-là",
            "",
            "LÉGENDE COULEURS :",
            "  • 🟡 Jaune : En-tête du livreur (ne pas modifier)",
            "  • 🔵 Bleu clair : Configuration existante (déjà enregistrée)",
            "  • ⚪ Blanc : Pas encore configuré (ajoutez les jours souhaités)",
            "",
            "COMMENT UTILISER :",
            "  1. Repérez le livreur souhaité (en-tête jaune)",
            "  2. Trouvez le client dans la liste en dessous",
            "  3. Remplissez les colonnes des jours (1, 2, 3... ou X)",
            "  4. Sauvegardez le fichier Excel",
            "  5. Importez-le via le bouton 'Importer'",
            "",
            "EXEMPLE :",
            "┌──────────┬─────────────┬───────────┬────────────────┬───────┬───────┬──────────┐",
            "│Livreur ID│ Livreur Nom │ Client ID │ Client Nom     │ Lundi │ Mardi │ Mercredi │",
            "├──────────┼─────────────┼───────────┼────────────────┼───────┼───────┼──────────┤",
            "│    1     │ Ahmed Ben   │    101    │ Mohamed Ali    │   1   │       │    1     │",
            "│    1     │ Ahmed Ben   │    102    │ Karim Salah    │   2   │   1   │          │",
            "│    1     │ Ahmed Ben   │    103    │ Fatima Zahra   │       │       │          │",
            "└──────────┴─────────────┴───────────┴────────────────┴───────┴───────┴──────────┘",
            "",
            "  → Client 101 : visité Lundi (1er) et Mercredi (1er)",
            "  → Client 102 : visité Lundi (2ème) et Mardi (1er)",
            "  → Client 103 : pas de visite programmée",
            "",
            "NOTES :",
            "  • Les colonnes 'Livreur Nom' et 'Client Nom' sont informatives",
            "  • Seuls les IDs et les jours sont utilisés lors de l'import",
            "  • Supprimez les lignes inutiles pour alléger le fichier si besoin",
        ]

        for row, text in enumerate(instructions, 1):
            cell = ws_help.cell(row=row, column=1, value=text)
            if row <= 3:
                cell.font = Font(bold=True, size=12)
            elif text.startswith("COLONNES") or text.startswith("EXEMPLES") or text.startswith("LÉGENDE") or text.startswith("IMPORTANT"):
                cell.font = Font(bold=True, color="1D4ED8")

        ws_help.column_dimensions['A'].width = 80

        # Ajuster les largeurs de colonnes de la feuille principale
        ws.column_dimensions['A'].width = 12  # Livreur ID
        ws.column_dimensions['B'].width = 22  # Livreur Nom
        ws.column_dimensions['C'].width = 12  # Client ID
        ws.column_dimensions['D'].width = 25  # Client Nom Complet
        ws.column_dimensions['E'].width = 15  # Secteur
        # Jours de la semaine (colonnes F à L)
        for col in ['F', 'G', 'H', 'I', 'J', 'K', 'L']:
            ws.column_dimensions[col].width = 10

        # Créer la réponse
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=template_planning_clients_chauffeurs.xlsx'
        return response

    @action(detail=False, methods=['post'], url_path='preview-import')
    def preview_import(self, request):
        """
        Prévisualiser un fichier Excel avant import.
        POST /API/distribution/clients-livreurs-hebdo/preview-import/
        Body: FormData avec fichier 'file'
        """
        try:
            import openpyxl
        except ImportError:
            return Response(
                {'error': 'openpyxl est requis. Installez-le avec: pip install openpyxl'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        if 'file' not in request.FILES:
            return Response(
                {'error': 'Aucun fichier fourni'},
                status=status.HTTP_400_BAD_REQUEST
            )

        file = request.FILES['file']

        if not file.name.endswith(('.xlsx', '.xls')):
            return Response(
                {'error': 'Le fichier doit être au format Excel (.xlsx ou .xls)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            wb = openpyxl.load_workbook(file, data_only=True)
            ws = wb.active

            preview_data = []
            errors = []
            valid_count = 0

            company = self._company()

            from .models import Client

            # Nouveau format du template:
            # Col 0: Livreur ID, Col 1: Livreur Nom, Col 2: Client ID, Col 3: Client Nom
            # Col 4-10: Lundi à Dimanche

            # Sauter la première ligne (en-têtes)
            for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
                if not row or not any(row):
                    continue

                # Ignorer les lignes d'en-tête de livreur (commençant par ▶)
                first_cell = str(row[0]) if row[0] else ''
                if first_cell.startswith('▶') or first_cell.startswith('==='):
                    continue

                livreur_id = row[0]
                # Col 1 est le nom du livreur (ignoré)
                client_id = row[2]
                # Col 3 est le nom du client (ignoré)

                # Validation
                row_errors = []
                livreur = None
                client = None

                if not livreur_id:
                    continue  # Ligne vide, on passe
                else:
                    try:
                        livreur = self._livreurs_entreprise().get(id=int(livreur_id))
                    except (LivreurDistribution.DoesNotExist, ValueError):
                        row_errors.append(f'Livreur ID {livreur_id} invalide')

                if not client_id:
                    continue  # Ligne vide, on passe
                else:
                    try:
                        client = self._clients_entreprise().get(id=int(client_id))
                    except (Client.DoesNotExist, ValueError):
                        row_errors.append(f'Client ID {client_id} invalide')

                # Jours (colonnes 4 à 10, index 4-10) -> Lundi=1 à Dimanche=7
                jours_assignes = []
                ordres = {}
                for jour_idx in range(1, 8):  # 1=Lundi ... 7=Dimanche
                    col_idx = 3 + jour_idx  # Col 4=Lundi, Col 5=Mardi, etc.
                    if len(row) > col_idx and row[col_idx]:
                        val = row[col_idx]
                        if isinstance(val, str) and val.upper() == 'X':
                            jours_assignes.append(jour_idx)
                            ordres[jour_idx] = None
                        elif isinstance(val, (int, float)) and val > 0:
                            jours_assignes.append(jour_idx)
                            ordres[jour_idx] = int(val)

                # Si aucun jour n'est assigné, ignorer cette ligne
                if not jours_assignes:
                    continue

                row_data = {
                    'row': row_idx,
                    'livreur_id': int(livreur_id) if livreur_id else None,
                    'livreur_nom': livreur.nom if livreur else str(livreur_id),
                    'client_id': int(client_id) if client_id else None,
                    'client_nom': f"{client.nom} {client.prenom}".strip() if client else str(client_id),
                    'jours': jours_assignes,
                    'ordres': ordres,
                    'errors': row_errors,
                    'valid': len(row_errors) == 0
                }

                preview_data.append(row_data)

                if row_data['valid']:
                    valid_count += 1
                else:
                    errors.extend([f"Ligne {row_idx}: {e}" for e in row_errors])

            return Response({
                'total_rows': len(preview_data),
                'valid_rows': valid_count,
                'error_rows': len(preview_data) - valid_count,
                'preview': preview_data[:20],  # Limiter la preview
                'errors': errors[:50],  # Limiter les erreurs
                'can_import': valid_count > 0
            })

        except Exception as e:
            return Response(
                {'error': f'Erreur lors de la lecture du fichier: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'], url_path='import-excel')
    def import_excel(self, request):
        """
        Importer les configurations depuis un fichier Excel.
        POST /API/distribution/clients-livreurs-hebdo/import-excel/
        Body: FormData avec fichier 'file'
        """
        try:
            import openpyxl
        except ImportError:
            return Response(
                {'error': 'openpyxl est requis. Installez-le avec: pip install openpyxl'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        if 'file' not in request.FILES:
            return Response(
                {'error': 'Aucun fichier fourni'},
                status=status.HTTP_400_BAD_REQUEST
            )

        file = request.FILES['file']

        if not file.name.endswith(('.xlsx', '.xls')):
            return Response(
                {'error': 'Le fichier doit être au format Excel (.xlsx ou .xls)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        company = self._company()
        replace_existing = request.data.get('replace_existing', 'false').lower() == 'true'

        try:
            from .models import Client

            wb = openpyxl.load_workbook(file, data_only=True)
            ws = wb.active

            created_count = 0
            updated_count = 0
            skipped_count = 0
            errors = []

            # Nouveau format du template:
            # Col 0: Livreur ID, Col 1: Livreur Nom, Col 2: Client ID, Col 3: Client Nom
            # Col 4-10: Lundi à Dimanche

            with transaction.atomic():
                for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
                    if not row or not any(row):
                        continue

                    # Ignorer les lignes d'en-tête de livreur (commençant par ▶ ou ===)
                    first_cell = str(row[0]) if row[0] else ''
                    if first_cell.startswith('▶') or first_cell.startswith('==='):
                        continue

                    livreur_id = row[0]
                    # Col 1 est le nom du livreur (ignoré)
                    client_id = row[2] if len(row) > 2 else None
                    # Col 3 est le nom du client (ignoré)

                    if not livreur_id or not client_id:
                        continue  # Ligne vide

                    # Validation
                    try:
                        livreur = self._livreurs_entreprise().get(id=int(livreur_id))
                    except (LivreurDistribution.DoesNotExist, ValueError, TypeError):
                        errors.append(f'Ligne {row_idx}: Livreur ID {livreur_id} invalide')
                        skipped_count += 1
                        continue

                    try:
                        client = self._clients_entreprise().get(id=int(client_id))
                    except (Client.DoesNotExist, ValueError, TypeError):
                        errors.append(f'Ligne {row_idx}: Client ID {client_id} invalide')
                        skipped_count += 1
                        continue

                    # Traiter les jours (colonnes 4 à 10) -> Lundi=1 à Dimanche=7
                    has_any_day = False
                    for jour_idx in range(1, 8):  # 1=Lundi ... 7=Dimanche
                        col_idx = 3 + jour_idx  # Col 4=Lundi, Col 5=Mardi, etc.

                        if len(row) > col_idx and row[col_idx]:
                            val = row[col_idx]
                            ordre_passage = None

                            if isinstance(val, str) and val.upper() == 'X':
                                ordre_passage = 0
                                has_any_day = True
                            elif isinstance(val, (int, float)) and val > 0:
                                ordre_passage = int(val)
                                has_any_day = True
                            else:
                                continue

                            # Chercher une configuration existante
                            existing = ClientLivreurHebdo.objects.filter(
                                client=client, jour_semaine=jour_idx,
                            ).filter(
                                models.Q(company=company) | models.Q(company__isnull=True)
                            ).order_by(models.F('company').asc(nulls_last=True)).first()
                            if existing and existing.company_id is None and company is not None:
                                existing.company = company

                            if existing:
                                if replace_existing:
                                    existing.livreur = livreur
                                    existing.ordre_passage = ordre_passage
                                    existing.is_active = True
                                    existing.save()
                                    updated_count += 1
                                else:
                                    # Mise à jour seulement si même livreur
                                    if existing.livreur_id == livreur.id:
                                        existing.ordre_passage = ordre_passage
                                        existing.is_active = True
                                        existing.save()
                                        updated_count += 1
                                    else:
                                        skipped_count += 1
                            else:
                                ClientLivreurHebdo.objects.create(
                                    client=client,
                                    livreur=livreur,
                                    jour_semaine=jour_idx,
                                    ordre_passage=ordre_passage,
                                    company=company,
                                    is_active=True
                                )
                                created_count += 1

                    if not has_any_day:
                        skipped_count += 1

            return Response({
                'success': True,
                'message': f'Import terminé: {created_count} créé(s), {updated_count} mis à jour, {skipped_count} ignoré(s)',
                'created': created_count,
                'updated': updated_count,
                'skipped': skipped_count,
                'errors': errors[:20]
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {'error': f'Erreur lors de l\'import: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class SyncViewSet(viewsets.ViewSet):
    """ViewSet pour la synchronisation mobile"""
    permission_classes = [IsAuthenticated]

    def _get_livreur_for_request(self, request, livreur_id):
        """Retourne le LivreurDistribution autorisé pour cette requête, ou lève PermissionDenied."""
        from .tenant import filtrer_livreurs
        livreur = get_object_or_404(LivreurDistribution, id=livreur_id)
        if request.user.is_superuser:
            return livreur
        if request.user.is_staff:
            # Administrateur d'entreprise : seulement les livreurs de son entreprise
            if not filtrer_livreurs(LivreurDistribution.objects.filter(pk=livreur.pk), request).exists():
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("Ce livreur n'appartient pas à votre entreprise.")
            return livreur
        try:
            user_livreur = request.user.livreur_distribution_profile
        except LivreurDistribution.DoesNotExist:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Votre compte n'est pas lié à un profil livreur.")
        if user_livreur.id != livreur.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Vous ne pouvez synchroniser que vos propres données.")
        return livreur

    @action(detail=False, methods=['post'])
    def pull(self, request):
        """Pull: Récupérer les données depuis le serveur (Serveur -> Mobile)"""
        serializer = SyncDeltaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        livreur_id = serializer.validated_data['livreur_id']
        derniere_sync = serializer.validated_data.get('derniere_sync')

        livreur = self._get_livreur_for_request(request, livreur_id)

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
        livreur = self._get_livreur_for_request(request, livreur_id)

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

    queryset = Produit.objects.filter(is_active=True).prefetch_related('conditionnements').order_by('designation')
    serializer_class = ProduitMobileSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Pas de pagination pour l'app mobile

    def _company(self):
        # Le TenantMiddleware passe AVANT l'authentification JWT : request.company vaut None
        # pour le téléphone. Avant, la liste contenait alors les produits de TOUTES les
        # entreprises. L'entreprise est donc déduite du compte (profil, sinon van du livreur).
        if not hasattr(self, '_company_cache'):
            from .distribution_prix_stock import company_pour_mobile
            self._company_cache = company_pour_mobile(self.request)
        return self._company_cache

    def get_queryset(self):
        """Produits de l'entreprise de l'utilisateur + produits sans entreprise ;
        superutilisateur sans entreprise : tous."""
        from django.db.models import Q
        queryset = super().get_queryset().select_related('categorie')
        company, tout_voir = self._company()
        if company is not None:
            queryset = queryset.filter(Q(company=company) | Q(company__isnull=True))
        elif not tout_voir:
            queryset = queryset.filter(company__isnull=True)
        return queryset

    def get_serializer_context(self):
        """Stock dépôt et prix par type calculés UNE fois pour toute la liste
        (avant : 1 à 2 requêtes SQL par produit)."""
        from .distribution_prix_stock import TarifsMobile, stock_depot_par_produit
        context = super().get_serializer_context()
        company, tout_voir = self._company()
        context['stock_map'] = stock_depot_par_produit(company, tout_voir)
        context['tarifs'] = TarifsMobile(company=company, produits=self.get_queryset().values('id'))
        return context


############################
# Statistiques Livreurs    #
############################

from rest_framework.views import APIView
from django.db.models import Sum, Count, Q, F
from django.db.models.functions import TruncDate
from collections import defaultdict


class ObjectifVendeurViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    """
    Objectifs mensuels de CA des vendeurs (livreurs), avec suivi.

    GET /API/distribution/objectifs-vendeurs/?annee=2026&mois=9[&livreur=ID]
      -> liste des objectifs avec ca_realise, reste, taux_reussite, atteint
    GET /API/distribution/objectifs-vendeurs/synthese/?annee=2026&mois=9
      -> totaux du mois (objectifs, atteints, CA realise, taux moyen)
    Ecriture reservee aux administrateurs (is_staff).
    """
    from .distribution_models import ObjectifVendeur as _ObjectifVendeur
    from .distribution_serializers import ObjectifVendeurSerializer as _ObjectifVendeurSerializer

    queryset = _ObjectifVendeur.objects.select_related('livreur', 'entrepot', 'categorie', 'categorie__parent').all()
    serializer_class = _ObjectifVendeurSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    filterset_fields = ['livreur', 'annee', 'mois', 'type_perimetre', 'entrepot', 'categorie']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'])
    def synthese(self, request):
        objectifs = self.filter_queryset(self.get_queryset())
        data = self.get_serializer(objectifs, many=True).data
        nb = len(data)
        atteints = sum(1 for o in data if o['atteint'])
        total_objectif = sum(float(o['montant_objectif']) for o in data)
        total_realise = sum(o['ca_realise'] for o in data)
        taux = [o['taux_reussite'] for o in data if o['taux_reussite'] is not None]
        return Response({
            'nb_objectifs': nb,
            'nb_atteints': atteints,
            'total_objectif': round(total_objectif, 2),
            'total_realise': round(total_realise, 2),
            'taux_moyen': round(sum(taux) / len(taux), 1) if taux else None,
            'taux_global': round(total_realise / total_objectif * 100, 1) if total_objectif else None,
        })


def _argent_recu(ventes_qs, tournees_qs):
    """Argent réellement reçu sur un ensemble de ventes mobiles / tournées.

    - especes : ventes payées en espèces (payé - monnaie rendue, y compris l'acompte d'une vente
      à crédit) + paiements de commandes, règlements de crédits et remboursements de dettes
      en espèces reçus pendant ces tournées
    - cheques : idem en chèque
    - credits : reste à payer des ventes (argent non reçu)
    """
    from decimal import Decimal
    from django.db.models import Sum, F
    from .distribution_models import EncaissementCommande, EncaissementVente
    from API.models import PaiementSolde
    z = Decimal('0')
    recu = F('montant_paye') - F('montant_rendu')
    # payé - rendu au moment de la vente (les règlements de crédit ultérieurs, qui augmentent
    # montant_paye, sont comptés à part via EncaissementVente : pas de double comptage)
    q_esp = ventes_qs.exclude(type_paiement__in=['cheque', 'carte', 'virement'])
    q_chq = ventes_qs.filter(type_paiement='cheque')
    v_esp = (q_esp.aggregate(s=Sum(recu))['s'] or z) - (EncaissementVente.objects.filter(vente__in=q_esp).aggregate(s=Sum('montant'))['s'] or z)
    v_chq = (q_chq.aggregate(s=Sum(recu))['s'] or z) - (EncaissementVente.objects.filter(vente__in=q_chq).aggregate(s=Sum('montant'))['s'] or z)
    reste = ventes_qs.aggregate(s=Sum(F('montant_total') - (F('montant_paye') - F('montant_rendu'))))['s'] or z

    def _enc(mode_field, modes):
        t = 0
        t += EncaissementCommande.objects.filter(tournee__in=tournees_qs, type_paiement__in=modes).aggregate(s=Sum('montant'))['s'] or z
        t += EncaissementVente.objects.filter(tournee__in=tournees_qs, type_paiement__in=modes).aggregate(s=Sum('montant'))['s'] or z
        t += PaiementSolde.objects.filter(tournee__in=tournees_qs, mode_paiement__in=modes).aggregate(s=Sum('montant'))['s'] or z
        from .distribution_models import PaiementClient
        t += PaiementClient.objects.filter(tournee__in=tournees_qs, mode_paiement__in=modes).aggregate(s=Sum('montant_ventes_pc'))['s'] or z
        return t

    return {
        'especes': float(v_esp + _enc('type_paiement', ['especes', 'espece'])),
        'cheques': float(v_chq + _enc('type_paiement', ['cheque'])),
        'credits': float(max(reste, z)),
    }


class StatsLivreursAPIView(APIView):
    """
    API pour les statistiques détaillées des livreurs
    GET /API/distribution/stats-livreurs/?date_debut=YYYY-MM-DD&date_fin=YYYY-MM-DD&livreur_id=X
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Récupérer les paramètres
        date_debut_str = request.query_params.get('date_debut')
        date_fin_str = request.query_params.get('date_fin')
        livreur_id = request.query_params.get('livreur_id')

        # Validation des dates
        if not date_debut_str or not date_fin_str:
            return Response(
                {'error': 'date_debut et date_fin sont requis (format YYYY-MM-DD)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
            date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Format de date invalide. Utilisez YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Récupérer la company de l'utilisateur
        company = None
        if hasattr(request.user, 'company') and request.user.company:
            company = request.user.company

        # Filtrer les tournées
        tournees_qs = TourneeMobile.objects.filter(
            date_tournee__gte=date_debut,
            date_tournee__lte=date_fin
        )

        if company:
            tournees_qs = tournees_qs.filter(company=company)

        if livreur_id:
            tournees_qs = tournees_qs.filter(livreur_id=livreur_id)

        # Filtrer les ventes
        ventes_qs = VenteTourneeMobile.objects.filter(
            date_vente__date__gte=date_debut,
            date_vente__date__lte=date_fin
        )

        if company:
            ventes_qs = ventes_qs.filter(company=company)

        if livreur_id:
            ventes_qs = ventes_qs.filter(tournee__livreur_id=livreur_id)

        # Filtrer les arrêts
        arrets_qs = ArretTourneeMobile.objects.filter(
            tournee__date_tournee__gte=date_debut,
            tournee__date_tournee__lte=date_fin
        )

        if company:
            arrets_qs = arrets_qs.filter(company=company)

        if livreur_id:
            arrets_qs = arrets_qs.filter(tournee__livreur_id=livreur_id)

        # ========================================
        # RÉSUMÉ GLOBAL
        # ========================================
        # Argent réellement reçu (avant : montant vendu, même non payé, compté en espèces ;
        # paiements de commandes et remboursements de dettes ignorés)
        argent = _argent_recu(ventes_qs, tournees_qs)
        summary = {
            'total_clients': arrets_qs.filter(statut='livre').values('client').distinct().count(),
            'total_tournees': tournees_qs.count(),
            'total_especes': argent['especes'],
            'total_cheques': argent['cheques'],
            'total_credits': argent['credits'],
            'total_ventes': float(ventes_qs.aggregate(total=Sum('montant_total'))['total'] or 0),
        }

        # ========================================
        # STATISTIQUES PAR LIVREUR
        # ========================================
        livreurs_stats = []

        # Récupérer tous les livreurs concernés
        livreurs_ids = tournees_qs.values_list('livreur_id', flat=True).distinct()
        livreurs = LivreurDistribution.objects.filter(id__in=livreurs_ids)

        for livreur in livreurs:
            # Tournées du livreur
            tournees_livreur = tournees_qs.filter(livreur=livreur)

            # Ventes du livreur
            ventes_livreur = ventes_qs.filter(tournee__livreur=livreur)

            # Arrêts du livreur
            arrets_livreur = arrets_qs.filter(tournee__livreur=livreur)

            # Calculer les stats
            argent_l = _argent_recu(ventes_livreur, tournees_livreur)
            especes = argent_l['especes']
            cheques = argent_l['cheques']
            credits = argent_l['credits']

            total_arrets = arrets_livreur.count()
            arrets_livres = arrets_livreur.filter(statut='livre').count()
            arrets_echec = arrets_livreur.filter(statut='echec').count()

            livreurs_stats.append({
                'id': livreur.id,
                'nom': livreur.nom,
                'matricule': livreur.matricule,
                'tournees': tournees_livreur.count(),
                'clients_visites': arrets_livreur.filter(statut='livre').values('client').distinct().count(),
                'total_arrets': total_arrets,
                'arrets_livres': arrets_livres,
                'arrets_echec': arrets_echec,
                'especes': especes,
                'cheques': cheques,
                'credits': credits,
                'total': especes + cheques + credits,
            })

        # Trier par total décroissant
        livreurs_stats.sort(key=lambda x: x['total'], reverse=True)

        # ========================================
        # STATISTIQUES PAR JOUR
        # ========================================
        par_jour = []

        # Regrouper les ventes par jour
        ventes_par_jour = ventes_qs.annotate(
            jour=TruncDate('date_vente')
        ).values('jour').annotate(
            total=Sum('montant_total'),
            especes=Sum('montant_total', filter=Q(type_paiement='especes')),
            cheques=Sum('montant_total', filter=Q(type_paiement='cheque')),
            credits=Sum('montant_total', filter=Q(type_paiement='credit')),
            nb_ventes=Count('id')
        ).order_by('jour')

        # Pour chaque jour, récupérer les stats par livreur
        jours_data = {}
        for v in ventes_par_jour:
            jour = v['jour']
            if jour not in jours_data:
                jours_data[jour] = {
                    'date': jour,
                    'date_label': jour.strftime('%d/%m'),
                    'jour_semaine': ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'][jour.weekday()],
                    'total': float(v['total'] or 0),
                    'especes': float(v['especes'] or 0),
                    'cheques': float(v['cheques'] or 0),
                    'credits': float(v['credits'] or 0),
                    'nb_ventes': v['nb_ventes'],
                    'livreurs': []
                }

        # Ajouter les stats par livreur pour chaque jour
        for jour, data in jours_data.items():
            jour_ventes = ventes_qs.filter(date_vente__date=jour)
            jour_arrets = arrets_qs.filter(tournee__date_tournee=jour)

            livreurs_jour_ids = jour_ventes.values_list('tournee__livreur_id', flat=True).distinct()

            for lid in livreurs_jour_ids:
                try:
                    liv = LivreurDistribution.objects.get(id=lid)
                    liv_ventes = jour_ventes.filter(tournee__livreur_id=lid)
                    liv_arrets = jour_arrets.filter(tournee__livreur_id=lid)

                    data['livreurs'].append({
                        'id': liv.id,
                        'nom': liv.nom,
                        'clients': liv_arrets.values('client').distinct().count(),
                        'livres': liv_arrets.filter(statut='livre').count(),
                        'echecs': liv_arrets.filter(statut='echec').count(),
                        'especes': float(liv_ventes.filter(type_paiement='especes').aggregate(
                            total=Sum('montant_total'))['total'] or 0),
                        'cheques': float(liv_ventes.filter(type_paiement='cheque').aggregate(
                            total=Sum('montant_total'))['total'] or 0),
                        'credits': float(liv_ventes.filter(type_paiement='credit').aggregate(
                            total=Sum('montant_total'))['total'] or 0),
                        'total': float(liv_ventes.aggregate(total=Sum('montant_total'))['total'] or 0),
                    })
                except LivreurDistribution.DoesNotExist:
                    pass

        # Convertir en liste triée par date
        par_jour = sorted(jours_data.values(), key=lambda x: x['date'])

        # Convertir les dates en string pour JSON
        for jour in par_jour:
            jour['date'] = jour['date'].strftime('%Y-%m-%d')

        return Response({
            'date_debut': date_debut_str,
            'date_fin': date_fin_str,
            'summary': summary,
            'livreurs': livreurs_stats,
            'par_jour': par_jour,
        })


# ============================================
# ENDPOINTS LIVRAISONS COMPAT MOBILE
# ============================================

from rest_framework.views import APIView


class LivraisonConfirmerView(APIView):
    """
    Endpoint pour confirmer une livraison depuis l'app mobile.
    POST /API/livraisons/confirmer/
    {
        "arret_id": "123",
        "signature_base64": "...",
        "notes": "...",
        "ts_client": 1234567890
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        arret_id = request.data.get('arret_id')
        signature_base64 = request.data.get('signature_base64', '')
        notes = request.data.get('notes', '')
        nom_receptionnaire = request.data.get('nom_receptionnaire', '')

        if not arret_id:
            return Response({'error': 'arret_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            arret = ArretTourneeMobile.objects.get(id=arret_id)
        except ArretTourneeMobile.DoesNotExist:
            return Response({'error': 'Arret not found'}, status=status.HTTP_404_NOT_FOUND)

        if arret.tournee.est_cloturee:
            return Response({'error': 'La tournee est cloturee'}, status=status.HTTP_400_BAD_REQUEST)

        arret.statut = 'livre'
        arret.heure_arrivee = timezone.now()
        arret.heure_depart = timezone.now()
        arret.signature_base64 = signature_base64
        arret.nom_receptionnaire = nom_receptionnaire
        arret.notes = notes
        arret.save()

        return Response({
            'message': 'Livraison confirmee',
            'arret_id': arret.id,
            'statut': arret.statut
        })


class LivraisonEchecView(APIView):
    """
    Endpoint pour marquer une livraison comme echec depuis l'app mobile.
    POST /API/livraisons/echec/
    {
        "arret_id": "123",
        "motif": "Client absent",
        "notes": "...",
        "ts_client": 1234567890
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        arret_id = request.data.get('arret_id')
        motif = request.data.get('motif', '')
        notes = request.data.get('notes', '')

        if not arret_id:
            return Response({'error': 'arret_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            arret = ArretTourneeMobile.objects.get(id=arret_id)
        except ArretTourneeMobile.DoesNotExist:
            return Response({'error': 'Arret not found'}, status=status.HTTP_404_NOT_FOUND)

        if arret.tournee.est_cloturee:
            return Response({'error': 'La tournee est cloturee'}, status=status.HTTP_400_BAD_REQUEST)

        arret.statut = 'echec'
        arret.heure_arrivee = timezone.now()
        arret.motif_echec = motif
        arret.notes_echec = notes
        arret.save()

        return Response({
            'message': 'Echec enregistre',
            'arret_id': arret.id,
            'statut': arret.statut,
            'motif': motif
        })


class IndicateursPerformanceAPIView(APIView):
    """
    Indicateurs de performance par vendeur (prevendeurs et livreurs) :
    taux de visite, taux de reussite, taux de realisation (objectifs) et taux de
    livraison des commandes. Formules dans API/indicateurs.py.

    GET /API/distribution/indicateurs-performance/?date_debut=YYYY-MM-DD&date_fin=YYYY-MM-DD[&livreur_id=X]
    Sans dates : mois en cours.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .indicateurs import calculer_indicateurs

        aujourd_hui = timezone.localdate()
        date_debut_str = request.query_params.get('date_debut')
        date_fin_str = request.query_params.get('date_fin')
        try:
            date_debut = (datetime.strptime(date_debut_str, '%Y-%m-%d').date()
                          if date_debut_str else aujourd_hui.replace(day=1))
            date_fin = (datetime.strptime(date_fin_str, '%Y-%m-%d').date()
                        if date_fin_str else aujourd_hui)
        except ValueError:
            return Response({'error': 'Format de date invalide. Utilisez YYYY-MM-DD'},
                            status=status.HTTP_400_BAD_REQUEST)
        if date_debut > date_fin:
            return Response({'error': 'date_debut doit être antérieure ou égale à date_fin'},
                            status=status.HTTP_400_BAD_REQUEST)
        if (date_fin - date_debut).days > 731:
            return Response({'error': 'La période ne peut pas dépasser deux ans'},
                            status=status.HTTP_400_BAD_REQUEST)

        livreur_id = request.query_params.get('livreur_id') or None
        if livreur_id is not None and not str(livreur_id).isdigit():
            return Response({'error': 'livreur_id invalide'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(calculer_indicateurs(date_debut, date_fin, livreur_id=livreur_id))


class CAVendeursAPIView(APIView):
    """
    Chiffre d'affaires par vendeur, mois par mois, et CA du mois en cours.

    GET /API/distribution/ca-vendeurs/?annee=2026[&livreur_id=X]
    Sans annee : annee en cours. CA TTC = ventes de tournee + commandes prises hors annulees.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .indicateurs import calculer_ca_mensuel

        annee = request.query_params.get('annee') or timezone.localdate().year
        try:
            annee = int(annee)
            if not 2000 <= annee <= 2100:
                raise ValueError
        except (TypeError, ValueError):
            return Response({'error': 'annee invalide (ex. 2026)'}, status=status.HTTP_400_BAD_REQUEST)

        livreur_id = request.query_params.get('livreur_id') or None
        if livreur_id is not None and not str(livreur_id).isdigit():
            return Response({'error': 'livreur_id invalide'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(calculer_ca_mensuel(annee, livreur_id=livreur_id))


class EtatLivreursAPIView(APIView):
    """
    Etat des livreurs : « net », « écart » ou « à contrôler », avec le détail par tournée.
    Calcul dans API/etat_livreurs.py.

    GET /API/distribution/etat-livreurs/?date_debut=YYYY-MM-DD&date_fin=YYYY-MM-DD[&livreur_id=X]
    Sans dates : les 30 derniers jours.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .etat_livreurs import calculer_etat_livreurs

        aujourd_hui = timezone.localdate()
        try:
            date_fin = (datetime.strptime(request.query_params['date_fin'], '%Y-%m-%d').date()
                        if request.query_params.get('date_fin') else aujourd_hui)
            date_debut = (datetime.strptime(request.query_params['date_debut'], '%Y-%m-%d').date()
                          if request.query_params.get('date_debut') else date_fin - timedelta(days=29))
        except ValueError:
            return Response({'error': 'Format de date invalide. Utilisez YYYY-MM-DD'},
                            status=status.HTTP_400_BAD_REQUEST)
        if date_debut > date_fin:
            return Response({'error': 'date_debut doit être antérieure ou égale à date_fin'},
                            status=status.HTTP_400_BAD_REQUEST)
        if (date_fin - date_debut).days > 731:
            return Response({'error': 'La période ne peut pas dépasser deux ans'},
                            status=status.HTTP_400_BAD_REQUEST)

        livreur_id = request.query_params.get('livreur_id') or None
        if livreur_id is not None and not str(livreur_id).isdigit():
            return Response({'error': 'livreur_id invalide'}, status=status.HTTP_400_BAD_REQUEST)

        from .tenant import entreprise_de
        company = None if request.user.is_superuser else entreprise_de(request)
        return Response(calculer_etat_livreurs(date_debut, date_fin, company=company, livreur_id=livreur_id))



class ComptesClientsAPIView(APIView):
    """Comptes des clients d'une ou plusieurs tournées (écran « Comptes clients » du téléphone).

    GET /API/distribution/comptes-clients/?tournees=14,15   → clients des arrêts de ces tournées
    GET /API/distribution/comptes-clients/?clients=12,13
    Pour chaque client : dette (détail par document), avance, net, historique.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from API.models import Client
        from API.comptes_clients import compte
        ids = set()
        t = request.query_params.get('tournees') or ''
        c = request.query_params.get('clients') or ''
        t_ids = [int(x) for x in t.split(',') if x.strip().isdigit()]
        if t_ids:
            ids |= set(ArretTourneeMobile.objects.filter(tournee_id__in=t_ids).values_list('client_id', flat=True))
        ids |= {int(x) for x in c.split(',') if x.strip().isdigit()}
        if not ids:
            return Response({'error': 'tournees ou clients est requis'}, status=status.HTTP_400_BAD_REQUEST)
        return Response([compte(cl) for cl in Client.objects.filter(pk__in=ids).order_by('nom', 'prenom')])


class EncaisserCompteClientAPIView(APIView):
    """Encaisser sur le compte d'un client : le montant est réparti sur ses dettes, de la plus
    ancienne à la plus récente ; le surplus devient une avance.

    POST /API/distribution/comptes-clients/encaisser/
    { "app_id": "compte-...", "client": 12, "montant": 500, "mode_paiement": "especes" | "cheque",
      "tournee": 14, "date_paiement": "..." }
    Idempotent sur app_id.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from decimal import Decimal, InvalidOperation
        from django.utils.dateparse import parse_datetime
        from API.models import Client
        from API.comptes_clients import compte, encaisser
        from .distribution_models import TourneeMobile
        d = request.data
        app_id = str(d.get('app_id') or '').strip()
        if not app_id:
            return Response({'error': 'app_id est requis'}, status=status.HTTP_400_BAD_REQUEST)
        from API.securite_encaissements import client_autorise, tournee_autorisee
        client = Client.objects.filter(pk=d.get('client')).first() if str(d.get('client') or '').isdigit() else None
        if client is None or not client_autorise(request, client):
            return Response({'error': f"Client introuvable : {d.get('client')}"}, status=status.HTTP_404_NOT_FOUND)
        try:
            montant = Decimal(str(d.get('montant')))
        except (InvalidOperation, TypeError, ValueError):
            return Response({'error': 'Montant invalide'}, status=status.HTTP_400_BAD_REQUEST)
        if montant <= 0:
            return Response({'error': 'Le montant doit être supérieur à zéro'}, status=status.HTTP_400_BAD_REQUEST)
        mode = d.get('mode_paiement') or 'especes'
        mode = 'especes' if mode == 'espece' else mode
        if mode not in ('especes', 'cheque'):
            return Response({'error': f'Mode de paiement invalide : {mode} (espèces ou chèque)'},
                            status=status.HTTP_400_BAD_REQUEST)
        tid = str(d.get('tournee') or '').strip()
        tournee = TourneeMobile.objects.filter(pk=int(tid)).select_related('livreur__entrepot').first() if tid.isdigit() else None
        if not tournee_autorisee(request, tournee):
            return Response({'error': "Cette tournée n'est pas la vôtre"}, status=status.HTTP_403_FORBIDDEN)
        date_paiement = parse_datetime(str(d.get('date_paiement') or '')) or timezone.now()
        pc, deja = encaisser(client, app_id, montant, mode, tournee=tournee, date_paiement=date_paiement,
                             user=request.user if request.user.is_authenticated else None)
        return Response({'deja_enregistre': deja, 'app_id': pc.app_id, 'montant': float(pc.montant),
                         'repartition': pc.repartition,
                         'compte': compte(Client.objects.get(pk=client.pk), avec_historique=False)},
                        status=status.HTTP_200_OK if deja else status.HTTP_201_CREATED)
