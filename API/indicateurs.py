"""
Indicateurs de performance des vendeurs (prevendeurs et livreurs).

Memes formules pour tous, sans notion de role : un prevendeur realise son activite par
des commandes, un livreur par des ventes / livraisons de tournee, et les deux canaux
sont comptes pour chaque personne.

Unite de comptage : le couple (jour, client). Un client vu deux fois le meme jour
compte pour une visite.

- Taux de visite      = clients planifies visites / clients planifies
    planifie  : client au planning hebdomadaire du jour (ClientLivreurHebdo actif et dans
                sa periode de validite) OU arret de la tournee du jour.
                Les jours posterieurs a aujourd'hui ne sont pas comptes.
    visite    : visite enregistree, arret livre ou en echec, vente ou commande du jour.
- Taux de reussite    = visites fructueuses / visites effectuees
    fructueuse : visite avec vente ou commande, arret livre, vente ou commande du jour.
- Taux de realisation = CA realise / objectifs mensuels (ObjectifVendeur) des mois couverts
- Taux de livraison   = montant des commandes livrees / montant des commandes prises
"""
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone


def _taux(numerateur, denominateur):
    """Pourcentage arrondi a 0,1 ; None si le denominateur est nul."""
    if not denominateur:
        return None
    return round(float(numerateur) / float(denominateur) * 100, 1)


def _mois_couverts(date_debut, date_fin):
    """Liste des (annee, mois) touches par la periode."""
    mois = []
    a, m = date_debut.year, date_debut.month
    while (a, m) <= (date_fin.year, date_fin.month):
        mois.append((a, m))
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)
    return mois


def calculer_indicateurs_vendeur(livreur, date_debut, date_fin, aujourd_hui=None):
    """Calcule les indicateurs d'un vendeur sur [date_debut, date_fin]."""
    from .distribution_models import (
        ArretTourneeMobile, ClientLivreurHebdo, CommandeClient, ObjectifVendeur,
        VenteTourneeMobile, VisiteClient,
    )

    aujourd_hui = aujourd_hui or timezone.localdate()
    fin_planning = min(date_fin, aujourd_hui)

    planifies, visites, fructueuses = set(), set(), set()

    # --- Planning hebdomadaire ---
    par_jour = defaultdict(list)
    for cid, js, dd, df in ClientLivreurHebdo.objects.filter(livreur=livreur, is_active=True).values_list(
            'client_id', 'jour_semaine', 'date_debut', 'date_fin'):
        par_jour[js].append((cid, dd, df))
    jour = date_debut
    while jour <= fin_planning:
        for cid, dd, df in par_jour.get(jour.isoweekday(), []):   # 1 = lundi ... 7 = dimanche
            if (dd is None or dd <= jour) and (df is None or df >= jour):
                planifies.add((jour, cid))
        jour += timedelta(days=1)

    # --- Arrets de tournee (planifies ; visites si livres ou en echec) ---
    for jour, cid, statut in ArretTourneeMobile.objects.filter(
            tournee__livreur=livreur, tournee__date_tournee__range=(date_debut, date_fin)
    ).values_list('tournee__date_tournee', 'client_id', 'statut'):
        if jour <= fin_planning:
            planifies.add((jour, cid))
        if statut in ('livre', 'echec'):
            visites.add((jour, cid))
        if statut == 'livre':
            fructueuses.add((jour, cid))

    # --- Visites enregistrees ---
    for jour, cid, resultat in VisiteClient.objects.filter(
            livreur=livreur, date_visite__range=(date_debut, date_fin)
    ).values_list('date_visite', 'client_id', 'resultat'):
        visites.add((jour, cid))
        if resultat in ('vente', 'commande'):
            fructueuses.add((jour, cid))

    # --- Ventes de tournee ---
    for jour, cid in VenteTourneeMobile.objects.filter(
            tournee__livreur=livreur, date_vente__date__range=(date_debut, date_fin)
    ).values_list('date_vente__date', 'client_id'):
        visites.add((jour, cid))
        fructueuses.add((jour, cid))

    # --- Commandes prises (hors annulees) ---
    commandes = CommandeClient.objects.filter(
        livreur=livreur, date_commande__date__range=(date_debut, date_fin)
    ).exclude(statut='cancelled')
    for jour, cid in commandes.values_list('date_commande__date', 'client_id'):
        visites.add((jour, cid))
        fructueuses.add((jour, cid))

    planifies_visites = visites & planifies

    # --- Realisation des objectifs (mensuels) ---
    total_objectif = Decimal('0')
    total_realise = Decimal('0')
    nb_objectifs = 0
    for annee, mois in _mois_couverts(date_debut, date_fin):
        for objectif in ObjectifVendeur.objects.filter(livreur=livreur, annee=annee, mois=mois).select_related(
                'entrepot', 'categorie'):
            nb_objectifs += 1
            total_objectif += objectif.montant_objectif or Decimal('0')
            total_realise += objectif.calculer_ca_realise()

    # --- Livraison des commandes ---
    montant_pris = commandes.aggregate(t=Sum('montant_total_ttc'))['t'] or Decimal('0')
    livrees = commandes.filter(statut='delivered')
    montant_livre = livrees.aggregate(t=Sum('montant_total_ttc'))['t'] or Decimal('0')
    nb_commandes = commandes.count()
    nb_livrees = livrees.count()

    # CA de la periode (ventes de tournee + commandes prises)
    ca_ventes = VenteTourneeMobile.objects.filter(
        tournee__livreur=livreur, date_vente__date__range=(date_debut, date_fin)
    ).aggregate(t=Sum('montant_total'))['t'] or Decimal('0')

    return {
        'id': livreur.id,
        'nom': livreur.nom,
        'matricule': livreur.matricule,
        'statut': livreur.statut,
        # Taux de visite
        'clients_planifies': len(planifies),
        'clients_planifies_visites': len(planifies_visites),
        'visites_hors_planning': len(visites - planifies),
        'taux_visite': _taux(len(planifies_visites), len(planifies)),
        # Taux de reussite
        'visites': len(visites),
        'visites_fructueuses': len(fructueuses),
        'taux_reussite': _taux(len(fructueuses), len(visites)),
        # Taux de realisation (objectifs)
        'nb_objectifs': nb_objectifs,
        'objectif_ca': float(total_objectif),
        'ca_realise_objectifs': float(total_realise),
        'taux_realisation': _taux(total_realise, total_objectif),
        # Taux de livraison des commandes
        'commandes_prises': nb_commandes,
        'commandes_livrees': nb_livrees,
        'montant_commandes_prises': float(montant_pris),
        'montant_commandes_livrees': float(montant_livre),
        'taux_livraison': _taux(montant_livre, montant_pris),
        # CA de la periode
        'ca_ventes': float(ca_ventes),
        'ca_commandes': float(montant_pris),
        'ca_periode': float(ca_ventes + montant_pris),
    }


def _a_de_l_activite(ind):
    return any(ind[k] for k in ('clients_planifies', 'visites', 'nb_objectifs', 'commandes_prises'))


def calculer_indicateurs(date_debut, date_fin, livreur_id=None, aujourd_hui=None):
    """Indicateurs de tous les vendeurs (actifs ou ayant de l'activite) + total global."""
    from .distribution_models import LivreurDistribution

    livreurs = LivreurDistribution.objects.all().order_by('nom')
    if livreur_id:
        livreurs = livreurs.filter(id=livreur_id)

    vendeurs = []
    for livreur in livreurs:
        ind = calculer_indicateurs_vendeur(livreur, date_debut, date_fin, aujourd_hui=aujourd_hui)
        if livreur_id or livreur.statut == 'actif' or _a_de_l_activite(ind):
            vendeurs.append(ind)

    somme = lambda cle: sum(v[cle] for v in vendeurs)
    global_ = {
        'clients_planifies': somme('clients_planifies'),
        'clients_planifies_visites': somme('clients_planifies_visites'),
        'taux_visite': _taux(somme('clients_planifies_visites'), somme('clients_planifies')),
        'visites': somme('visites'),
        'visites_fructueuses': somme('visites_fructueuses'),
        'taux_reussite': _taux(somme('visites_fructueuses'), somme('visites')),
        'objectif_ca': round(somme('objectif_ca'), 2),
        'ca_realise_objectifs': round(somme('ca_realise_objectifs'), 2),
        'taux_realisation': _taux(somme('ca_realise_objectifs'), somme('objectif_ca')),
        'montant_commandes_prises': round(somme('montant_commandes_prises'), 2),
        'montant_commandes_livrees': round(somme('montant_commandes_livrees'), 2),
        'taux_livraison': _taux(somme('montant_commandes_livrees'), somme('montant_commandes_prises')),
    }
    return {
        'periode': {'date_debut': date_debut.isoformat(), 'date_fin': date_fin.isoformat()},
        'definitions': {
            'taux_visite': "Clients planifiés visités / clients planifiés (planning hebdomadaire et arrêts de tournée, jusqu'à aujourd'hui)",
            'taux_reussite': "Visites ayant donné une vente ou une commande / visites effectuées",
            'taux_realisation': "CA réalisé / objectifs mensuels des mois couverts par la période",
            'taux_livraison': "Montant des commandes livrées / montant des commandes prises",
        },
        'vendeurs': vendeurs,
        'global': global_,
    }


# ---------------------------------------------------------------------------
# Chiffre d'affaires par vendeur, mois par mois
# ---------------------------------------------------------------------------
MOIS_LIBELLES = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août',
                 'Septembre', 'Octobre', 'Novembre', 'Décembre']


def calculer_ca_mensuel(annee, livreur_id=None, aujourd_hui=None):
    """
    CA TTC de chaque vendeur pour chacun des 12 mois de `annee`.
    Meme definition que les objectifs et le taux de realisation : ventes de tournee
    (date de vente) + commandes prises hors annulees (date de commande). Livrer une
    commande ne cree pas de vente : pas de double comptage.
    Deux requetes groupees, quel que soit le nombre de vendeurs.
    """
    from django.db.models.functions import ExtractMonth
    from .distribution_models import CommandeClient, LivreurDistribution, VenteTourneeMobile

    aujourd_hui = aujourd_hui or timezone.localdate()

    ventes = VenteTourneeMobile.objects.filter(date_vente__year=annee, tournee__livreur__isnull=False)
    commandes = CommandeClient.objects.filter(date_commande__year=annee).exclude(statut='cancelled')
    if livreur_id:
        ventes = ventes.filter(tournee__livreur_id=livreur_id)
        commandes = commandes.filter(livreur_id=livreur_id)

    # (vendeur, mois) -> montants
    ca_ventes, ca_commandes = defaultdict(Decimal), defaultdict(Decimal)
    nb_ventes, nb_commandes = defaultdict(int), defaultdict(int)
    from django.db.models import Count
    for r in ventes.annotate(m=ExtractMonth('date_vente')).values('tournee__livreur_id', 'm').annotate(
            total=Sum('montant_total'), n=Count('id')):
        ca_ventes[(r['tournee__livreur_id'], r['m'])] = r['total'] or Decimal('0')
        nb_ventes[(r['tournee__livreur_id'], r['m'])] = r['n']
    for r in commandes.annotate(m=ExtractMonth('date_commande')).values('livreur_id', 'm').annotate(
            total=Sum('montant_total_ttc'), n=Count('id')):
        ca_commandes[(r['livreur_id'], r['m'])] = r['total'] or Decimal('0')
        nb_commandes[(r['livreur_id'], r['m'])] = r['n']

    ids_actifs = {k[0] for k in ca_ventes} | {k[0] for k in ca_commandes}
    livreurs = LivreurDistribution.objects.all().order_by('nom')
    if livreur_id:
        livreurs = livreurs.filter(id=livreur_id)

    mois_courant = aujourd_hui.month if aujourd_hui.year == int(annee) else None

    def cellule(lid, m):
        v, c = ca_ventes[(lid, m)], ca_commandes[(lid, m)]
        return {'mois': m, 'ventes': float(v), 'commandes': float(c), 'total': float(v + c),
                'nb_ventes': nb_ventes[(lid, m)], 'nb_commandes': nb_commandes[(lid, m)]}

    vendeurs = []
    for livreur in livreurs:
        if not (livreur_id or livreur.statut == 'actif' or livreur.id in ids_actifs):
            continue
        mois = [cellule(livreur.id, m) for m in range(1, 13)]
        courant = mois[mois_courant - 1] if mois_courant else None
        vendeurs.append({
            'id': livreur.id, 'nom': livreur.nom, 'matricule': livreur.matricule, 'statut': livreur.statut,
            'mois': mois,
            'total_ventes': round(sum(c['ventes'] for c in mois), 2),
            'total_commandes': round(sum(c['commandes'] for c in mois), 2),
            'total_annee': round(sum(c['total'] for c in mois), 2),
            'ca_mois_courant': courant['total'] if courant else None,
            'ca_mois_courant_ventes': courant['ventes'] if courant else None,
            'ca_mois_courant_commandes': courant['commandes'] if courant else None,
        })
    vendeurs.sort(key=lambda v: (-v['total_annee'], v['nom'].lower()))

    totaux_mois = []
    for m in range(1, 13):
        totaux_mois.append({
            'mois': m,
            'ventes': round(sum(v['mois'][m - 1]['ventes'] for v in vendeurs), 2),
            'commandes': round(sum(v['mois'][m - 1]['commandes'] for v in vendeurs), 2),
            'total': round(sum(v['mois'][m - 1]['total'] for v in vendeurs), 2),
        })
    courant = totaux_mois[mois_courant - 1] if mois_courant else None

    return {
        'annee': int(annee),
        'mois_libelles': MOIS_LIBELLES,
        'mois_courant': mois_courant,
        'definition': "CA TTC = ventes de tournée + commandes prises (hors annulées)",
        'vendeurs': vendeurs,
        'totaux_mois': totaux_mois,
        'total_annee': round(sum(t['total'] for t in totaux_mois), 2),
        'mois_en_cours': {
            'mois': mois_courant,
            'libelle': f"{MOIS_LIBELLES[mois_courant - 1]} {annee}" if mois_courant else None,
            'total': courant['total'] if courant else None,
            'ventes': courant['ventes'] if courant else None,
            'commandes': courant['commandes'] if courant else None,
        },
    }
