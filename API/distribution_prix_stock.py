"""
Calculs partagés par l'API de l'application mobile (prévendeurs / livreurs) :

- entreprise de l'utilisateur connecté (le TenantMiddleware s'exécute AVANT l'authentification
  JWT de DRF : pour le téléphone, request.company vaut None) ;
- stock disponible au dépôt pour les prévendeurs (vans exclus, sans repli sur Produit.quantite) ;
- prix par type de client (Détail, Gros, ...) avec promotions, en quelques requêtes SQL
  quel que soit le nombre de produits (avant : 2 à 4 requêtes PAR produit et par type) ;
- synchronisation des arrêts des tournées à venir quand l'affectation des clients change.
"""
import logging
from decimal import Decimal

from django.db import models, transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Entreprise
# ---------------------------------------------------------------------------
def company_pour_mobile(request):
    """Entreprise de l'utilisateur, aussi pour les appels authentifiés par JWT.

    Retourne (company, tout_voir) : tout_voir=True pour un superutilisateur sans entreprise.
    Sans entreprise, s'il n'existe qu'UNE entreprise, c'est la sienne (même règle que
    SystemConfig.get_solo).
    """
    from .models import Company, SystemConfig
    user = getattr(request, 'user', None)
    company = getattr(request, 'company', None) or SystemConfig.company_of_user(user)
    if company is not None:
        return company, False
    if user is not None and getattr(user, 'is_superuser', False):
        return None, True
    entreprises = list(Company.objects.values_list('pk', flat=True)[:2])
    if len(entreprises) == 1:
        return Company.objects.get(pk=entreprises[0]), False
    return None, False


# ---------------------------------------------------------------------------
# Stock dépôt (prévendeurs)
# ---------------------------------------------------------------------------
def ids_entrepots_vans():
    """Sous-requête : entrepôts utilisés comme van par un livreur."""
    from .distribution_models import LivreurDistribution
    return LivreurDistribution.objects.filter(entrepot__isnull=False).values('entrepot_id')


def entrepots_stock_mobile(company, tout_voir=False):
    """Entrepôts dont le stock est proposé aux prévendeurs.

    - dépôt des commandes mobiles configuré (Paramètres) et actif : lui seul ;
    - sinon : entrepôts ACTIFS de l'entreprise (et sans entreprise), hors vans
      (code contenant « van » OU entrepôt rattaché à un livreur comme van).
    """
    from .models import SystemConfig, Warehouse
    if company is not None:
        cfg = SystemConfig.objects.filter(company=company).select_related('depot_commandes_mobile').first()
        depot = cfg.depot_commandes_mobile if cfg else None
        if depot is not None and depot.is_active:
            return Warehouse.objects.filter(pk=depot.pk)
    qs = Warehouse.objects.filter(is_active=True)
    if company is not None:
        qs = qs.filter(models.Q(company=company) | models.Q(company__isnull=True))
    elif not tout_voir:
        qs = qs.filter(company__isnull=True)
    return qs.exclude(code__icontains='van').exclude(pk__in=ids_entrepots_vans())


def stock_depot_par_produit(company, tout_voir=False, produit_ids=None):
    """{produit_id: quantité} en UNE requête agrégée (produits absents = 0)."""
    from .models import ProductStock
    qs = ProductStock.objects.filter(warehouse__in=entrepots_stock_mobile(company, tout_voir))
    if produit_ids is not None:
        qs = qs.filter(produit_id__in=produit_ids)
    return {pid: int(total or 0) for pid, total in
            qs.values('produit_id').annotate(total=models.Sum('quantity')).values_list('produit_id', 'total')}


# ---------------------------------------------------------------------------
# Prix par type de client
# ---------------------------------------------------------------------------
class TarifsMobile:
    """Prix par type de client pour un ensemble de produits, chargés en une fois.

    produits : None (tous), liste d'ids ou QuerySet de valeurs produit_id (sous-requête).
    Prix de base d'un type = PrixProduit actif du CodePrix par défaut (sinon sans code prix),
    sinon prixU. Promotions : CodePrix actif à la date du jour et Promotion « active »
    (même règle que l'ancien calcul de stock_van).
    """

    def __init__(self, company=None, produits=None, avec_promotions=True):
        from .models import CodePrix, PrixProduit, TypePrix, Promotion, Categorie
        today = timezone.localdate()
        now = timezone.now()
        self.types = list(TypePrix.objects.filter(is_active=True))
        self.type_defaut = next((t for t in self.types if t.is_default), None)
        self.code_defaut = CodePrix.get_default()
        code_actif = CodePrix.objects.filter(
            is_active=True, date_debut__lte=today, date_fin__gte=today).first() if avec_promotions else None
        self.code_actif = code_actif or self.code_defaut

        codes = {c.id for c in (self.code_defaut, self.code_actif) if c is not None}
        qs = PrixProduit.objects.filter(is_active=True).filter(
            models.Q(code_prix_id__in=codes) | models.Q(code_prix__isnull=True))
        if produits is not None:
            qs = qs.filter(produit_id__in=produits)
        self._prix = {}
        for pid, cid, tid, prix, qmin in qs.values_list('produit_id', 'code_prix_id', 'type_prix_id',
                                                       'prix', 'quantite_min'):
            self._prix[(pid, cid, tid)] = (prix, qmin or 1)

        self.promotions = []
        self._parents = {}
        if avec_promotions:
            promos = Promotion.objects.filter(statut='active', date_fin__gte=now)
            if company is not None:
                promos = promos.filter(models.Q(company=company) | models.Q(company__isnull=True))
            self.promotions = list(promos.order_by('-priorite'))
            if any(p.categorie_id for p in self.promotions):
                self._parents = dict(Categorie.objects.values_list('id', 'parent_id'))

    # -- prix de base ------------------------------------------------------
    def _ligne_standard(self, produit_id, type_prix_id):
        ligne = None
        if self.code_defaut is not None:
            ligne = self._prix.get((produit_id, self.code_defaut.id, type_prix_id))
        return ligne or self._prix.get((produit_id, None, type_prix_id))

    def prix_base(self, produit, type_prix_id=None):
        """Prix (Decimal) d'un produit pour un type de client (type par défaut si absent)."""
        if type_prix_id is None and self.type_defaut is not None:
            type_prix_id = self.type_defaut.id
        ligne = self._ligne_standard(produit.id, type_prix_id) if type_prix_id else None
        if ligne is not None:
            return Decimal(str(ligne[0]))
        return Decimal(str(produit.prixU or 0))

    # -- promotions ----------------------------------------------------------
    def _promotion(self, produit):
        """Promotion de plus haute priorité applicable au produit (sans requête SQL)."""
        for promo in self.promotions:
            if not promo.produit_id and not promo.categorie_id:
                return promo
            if promo.produit_id and promo.produit_id == produit.id:
                return promo
            if promo.categorie_id:
                cat, vus = produit.categorie_id, set()
                while cat and cat not in vus:
                    if cat == promo.categorie_id:
                        return promo
                    vus.add(cat)
                    cat = self._parents.get(cat)
        return None

    def detail_par_type(self, produit):
        """Format historique de stock_van : {code: {prix, prix_original, has_promotion,
        quantite_min, promo_code}} pour TOUS les types actifs (repli sur prixU)."""
        prix_produit = float(produit.prixU) if produit.prixU else 0
        promo = self._promotion(produit)
        res = {}
        for t in self.types:
            std = self._ligne_standard(produit.id, t.id)
            prix_base = float(std[0]) if std else prix_produit

            promo_codeprix = None
            if self.code_actif is not None and self.code_actif != self.code_defaut:
                promo_codeprix = self._prix.get((produit.id, self.code_actif.id, t.id))

            prix_nouvelle_promo, has_nouvelle_promo, qmin_promo, promo_code = prix_base, False, 1, None
            if promo is not None:
                calc = promo.calculer_prix_promotion(Decimal(str(prix_base)), 1)
                if float(calc) < prix_base:
                    prix_nouvelle_promo = float(calc)
                    has_nouvelle_promo = True
                    qmin_promo = promo.quantite_minimum
                    promo_code = promo.code

            prix_final, has_promotion, quantite_min = prix_base, False, 1
            if promo_codeprix and float(promo_codeprix[0]) < prix_base:
                prix_final = float(promo_codeprix[0])
                has_promotion = True
                quantite_min = promo_codeprix[1]
            if has_nouvelle_promo and prix_nouvelle_promo < prix_final:
                prix_final = prix_nouvelle_promo
                has_promotion = True
                quantite_min = qmin_promo

            res[t.code] = {
                'prix': prix_final,
                'prix_original': prix_base,
                'has_promotion': has_promotion,
                'quantite_min': quantite_min,
                'promo_code': promo_code if has_nouvelle_promo else None,
            }
        return res

    def prix_par_type(self, produit):
        """Catalogue prévendeur : {code_type: prix (nombre)} pour les seuls types ayant un
        PrixProduit actif (dictionnaire éventuellement vide → l'app utilise prixU)."""
        res = {}
        for t in self.types:
            ligne = self._ligne_standard(produit.id, t.id)
            if ligne is not None:
                res[t.code] = float(ligne[0])
        return res

    def promotions_par_type(self, produit):
        """{code_type: {prix, quantite_min, promo_code}} pour les types en promotion (sinon {})."""
        if not self.promotions and (self.code_actif is None or self.code_actif == self.code_defaut):
            return {}
        return {code: {'prix': d['prix'], 'quantite_min': d['quantite_min'], 'promo_code': d['promo_code']}
                for code, d in self.detail_par_type(produit).items() if d['has_promotion']}


def prix_unitaire_client(produit, client, tarifs=None):
    """Prix d'un produit pour un client (type de prix du client, sinon type par défaut ;
    sinon prixU). Utilisé quand le téléphone envoie une ligne sans prix (ou à 0)."""
    if tarifs is None:
        tarifs = TarifsMobile(produits=[produit.id], avec_promotions=False)
    type_id = getattr(client, 'type_prix_id', None) if client is not None else None
    return tarifs.prix_base(produit, type_id)


# ---------------------------------------------------------------------------
# Synchronisation des arrêts avec le planning (ClientLivreurHebdo)
# ---------------------------------------------------------------------------
def synchroniser_arrets_tournee(tournee, clients_concernes=None):
    """Aligne les arrêts d'une tournée sur le planning hebdomadaire de son livreur.

    - ajoute un arrêt pour chaque client planifié ce jour-là qui n'en a pas ;
    - met à jour les coordonnées GPS des arrêts existants ;
    - supprime les arrêts « en_attente » de clients qui ne sont plus planifiés :
      tous (clients_concernes=None, action manuelle sync_arrets) ou seulement ceux de
      clients_concernes (synchronisation automatique : on ne touche pas aux arrêts
      ajoutés à la main pour d'autres clients).
    Retourne {'ajoutes', 'supprimes', 'mis_a_jour'}.
    """
    from .distribution_models import ArretTourneeMobile, ClientLivreurHebdo

    date_tournee = tournee.date_tournee
    configs = list(ClientLivreurHebdo.objects.filter(
        livreur_id=tournee.livreur_id, jour_semaine=date_tournee.weekday() + 1, is_active=True,
    ).filter(
        models.Q(date_debut__isnull=True) | models.Q(date_debut__lte=date_tournee)
    ).filter(
        models.Q(date_fin__isnull=True) | models.Q(date_fin__gte=date_tournee)
    ).select_related('client').order_by('ordre_passage', 'id'))

    arrets = list(ArretTourneeMobile.objects.filter(tournee=tournee))
    existants = {a.client_id: a for a in arrets}
    planifies = {c.client_id for c in configs}
    ordres = {a.ordre_passage for a in arrets}
    ajoutes = supprimes = mis_a_jour = 0

    for config in configs:
        arret = existants.get(config.client_id)
        if arret is None:
            continue
        lat, lng = getattr(config.client, 'lat', None), getattr(config.client, 'lng', None)
        if lat is not None and lng is not None:
            cur = (float(arret.latitude) if arret.latitude is not None else None,
                   float(arret.longitude) if arret.longitude is not None else None)
            if cur != (float(lat), float(lng)):
                arret.latitude, arret.longitude = lat, lng
                arret.save(update_fields=['latitude', 'longitude'])
                mis_a_jour += 1

    for client_id, arret in existants.items():
        if client_id in planifies or arret.statut != 'en_attente':
            continue
        if clients_concernes is not None and client_id not in clients_concernes:
            continue
        ordres.discard(arret.ordre_passage)
        arret.delete()
        supprimes += 1

    ordre = 1
    for config in configs:
        if config.client_id in existants:
            continue
        while ordre in ordres:
            ordre += 1
        ArretTourneeMobile.objects.create(
            tournee=tournee, client=config.client, ordre_passage=ordre,
            latitude=getattr(config.client, 'lat', None), longitude=getattr(config.client, 'lng', None),
            statut='en_attente', notes=config.notes or '')
        ordres.add(ordre)
        ajoutes += 1

    return {'ajoutes': ajoutes, 'supprimes': supprimes, 'mis_a_jour': mis_a_jour}


def tournees_a_synchroniser(livreur_id):
    """Tournées planifiées ou en cours du livreur, d'aujourd'hui ou à venir."""
    from .distribution_models import TourneeMobile
    return TourneeMobile.objects.filter(
        livreur_id=livreur_id, statut__in=['planifiee', 'en_cours'],
        date_tournee__gte=timezone.localdate())


def synchroniser_arrets_livreur(livreur_id, clients_concernes=None):
    """Synchronise les tournées à venir d'un livreur (erreurs journalisées, jamais levées :
    l'affectation des clients a déjà réussi)."""
    total = {'tournees': 0, 'ajoutes': 0, 'supprimes': 0, 'mis_a_jour': 0}
    if not livreur_id:
        return total
    for tournee in tournees_a_synchroniser(livreur_id):
        if getattr(tournee, 'est_cloturee', False):
            continue
        try:
            with transaction.atomic():
                r = synchroniser_arrets_tournee(tournee, clients_concernes)
        except Exception:
            logger.exception('Synchronisation des arrêts de la tournée %s impossible', tournee.pk)
            continue
        total['tournees'] += 1
        for k in ('ajoutes', 'supprimes', 'mis_a_jour'):
            total[k] += r[k]
    return total


def planifier_sync_arrets(livreur_ids, clients_concernes=None):
    """Synchronise les tournées à venir des livreurs après validation de la transaction en
    cours (immédiatement hors transaction). Les demandes d'une même transaction (ex. import
    Excel de 500 lignes) sont regroupées : une seule synchronisation par livreur.
    clients_concernes : ids des clients dont l'affectation a changé (arrêts « en_attente »
    retirables) ; None = aucun retrait, seulement des ajouts."""
    ids = {int(i) for i in livreur_ids if i}
    if not ids:
        return
    conn = transaction.get_connection()
    attente = getattr(conn, '_sync_arrets_attente', None)
    # Le regroupement n'est valable que si notre callback est encore enregistré
    # (un rollback le retire de la liste des callbacks)
    if attente is None or not any(item[1] is attente['flush'] for item in conn.run_on_commit):
        attente = {'livreurs': {}}

        def _flush(attente=attente):
            if getattr(conn, '_sync_arrets_attente', None) is attente:
                conn._sync_arrets_attente = None
            for lid, concernes in attente['livreurs'].items():
                synchroniser_arrets_livreur(lid, concernes)

        attente['flush'] = _flush
        conn._sync_arrets_attente = attente
        enregistrer = True
    else:
        enregistrer = False
    for lid in ids:
        attente['livreurs'].setdefault(lid, set()).update(clients_concernes or ())
    if enregistrer:
        transaction.on_commit(attente['flush'])


# ---------------------------------------------------------------------------
# Signaux : toute modification d'affectation (API, import Excel, admin, création d'un
# client depuis le téléphone...) met à jour les arrêts des tournées à venir.
# ---------------------------------------------------------------------------
def _hebdo_pre_save(sender, instance, **kwargs):
    instance._sync_ancien_livreur_id = None
    if instance.pk:
        instance._sync_ancien_livreur_id = sender.objects.filter(pk=instance.pk).values_list(
            'livreur_id', flat=True).first()


def _hebdo_post_save(sender, instance, raw=False, **kwargs):
    if raw:
        return
    planifier_sync_arrets({instance.livreur_id, getattr(instance, '_sync_ancien_livreur_id', None)},
                          {instance.client_id})


def _hebdo_post_delete(sender, instance, **kwargs):
    planifier_sync_arrets({instance.livreur_id}, {instance.client_id})


def _clients_assignes_changed(sender, instance, action, reverse, pk_set, **kwargs):
    if action not in ('post_add', 'post_remove', 'post_clear'):
        return
    livreurs = set(pk_set or ()) if reverse else {instance.pk}
    planifier_sync_arrets(livreurs)


def connecter_signaux():
    from django.db.models.signals import pre_save, post_save, post_delete, m2m_changed
    from .distribution_models import ClientLivreurHebdo, LivreurDistribution
    uid = 'distribution_prix_stock'
    pre_save.connect(_hebdo_pre_save, sender=ClientLivreurHebdo, dispatch_uid=uid + '_pre')
    post_save.connect(_hebdo_post_save, sender=ClientLivreurHebdo, dispatch_uid=uid + '_post')
    post_delete.connect(_hebdo_post_delete, sender=ClientLivreurHebdo, dispatch_uid=uid + '_del')
    m2m_changed.connect(_clients_assignes_changed, sender=LivreurDistribution.clients_assignes.through,
                        dispatch_uid=uid + '_m2m')
