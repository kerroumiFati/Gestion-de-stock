"""
Etat des livreurs : chaque livreur est-il « net » ou presente-t-il un ecart ?

Base : le rapport de caisse de fin de tournee (RapportCaisseMobile), qui compare
l'argent rapporte (solde reel) a l'argent attendu (solde theorique = fonds de depart
+ especes encaissees - depenses). Ecart = reel - theorique.

Etat d'un livreur sur la periode :
- « ecart »       : au moins une tournee avec un ecart au-dela de la tolerance ;
- « a_controler » : pas d'ecart, mais une tournee terminee sans rapport de caisse
                     (ou avec un rapport encore ouvert) : on ne peut pas dire qu'il est net ;
- « net »         : toutes les tournees terminees ont un rapport, sans ecart ;
- « aucune »      : aucune tournee terminee sur la periode.

La tolerance reprend le seuil d'anomalie du rapport de caisse (10 DA).
"""
from decimal import Decimal

TOLERANCE = Decimal('10')
STATUTS_FINIS = ('terminee', 'cloturee')

# Ordre d'affichage : ce qui demande une action d'abord
ORDRE_ETAT = {'ecart': 0, 'a_controler': 1, 'net': 2, 'aucune': 3}
LIBELLES = {
    'ecart': 'Écart',
    'a_controler': 'À contrôler',
    'net': 'Net',
    'aucune': 'Aucune tournée',
}


def _f(d):
    return float(d or 0)


def _detail_tournee(tournee):
    rapport = getattr(tournee, 'rapport_caisse', None)
    base = {
        'tournee_id': tournee.id,
        'numero': tournee.numero_tournee,
        'date': tournee.date_tournee.isoformat(),
        'statut_tournee': tournee.statut,
        'statut_tournee_libelle': tournee.get_statut_display(),
    }
    if rapport is None:
        base.update({'rapport': None, 'etat': 'a_controler',
                     'motif': 'Tournée terminée sans rapport de caisse.'})
        return base, Decimal('0')

    ecart = rapport.ecart or Decimal('0')
    if abs(ecart) > TOLERANCE:
        etat = 'ecart'
        motif = ('Manquant' if ecart < 0 else 'Excédent') + f" de {abs(ecart):.2f} DA.".replace('.', ',', 1)
    elif rapport.statut == 'ouvert':
        etat = 'a_controler'
        motif = "Rapport de caisse pas encore validé."
    else:
        etat = 'net'
        motif = ''
    base.update({
        'etat': etat,
        'motif': motif,
        'rapport': {
            'id': rapport.id,
            'statut': rapport.statut,
            'statut_libelle': rapport.get_statut_display(),
            'fonds_depart': _f(rapport.fonds_depart),
            'total_especes': _f(rapport.total_especes),
            'total_cartes': _f(rapport.total_cartes),
            'total_cheques': _f(rapport.total_cheques),
            'total_credits': _f(rapport.total_credits),
            'total_depenses': _f(rapport.total_depenses),
            'depenses': {
                'carburant': _f(rapport.carburant),
                'reparations': _f(rapport.reparations),
                'autres': _f(rapport.autres_depenses),
            },
            'solde_theorique': _f(rapport.solde_final_theorique),
            'solde_reel': _f(rapport.solde_final_reel),
            'ecart': _f(ecart),
            'justification': rapport.justification_ecart or '',
            'detail_billets': rapport.detail_billets or {},
            'valide_par': (rapport.valide_par.get_full_name() or rapport.valide_par.username) if rapport.valide_par_id else '',
            'date_validation': rapport.date_validation.isoformat() if rapport.date_validation else None,
        },
    })
    # Seuls les ecarts au-dela de la tolerance comptent dans le cumul
    return base, (ecart if etat == 'ecart' else Decimal('0'))


def calculer_etat_livreurs(date_debut, date_fin, company=None, livreur_id=None):
    from .distribution_models import LivreurDistribution, TourneeMobile

    livreurs = LivreurDistribution.objects.all().order_by('nom')
    tournees = (TourneeMobile.objects
                .filter(date_tournee__gte=date_debut, date_tournee__lte=date_fin, statut__in=STATUTS_FINIS)
                .select_related('rapport_caisse', 'rapport_caisse__valide_par')
                .order_by('-date_tournee', '-id'))
    if company is not None:
        # Le livreur n'a pas d'entreprise propre : on garde ceux qui ont des tournees de l'entreprise
        livreurs = livreurs.filter(tournees__company=company).distinct()
        tournees = tournees.filter(company=company)
    if livreur_id:
        livreurs = livreurs.filter(pk=livreur_id)
        tournees = tournees.filter(livreur_id=livreur_id)

    par_livreur = {}
    for t in tournees:
        par_livreur.setdefault(t.livreur_id, []).append(t)

    resultats = []
    for l in livreurs:
        details, manquant, excedent = [], Decimal('0'), Decimal('0')
        for t in par_livreur.get(l.id, []):
            detail, ecart = _detail_tournee(t)
            details.append(detail)
            if ecart < 0:
                manquant += -ecart
            elif ecart > 0:
                excedent += ecart
        etats = {d['etat'] for d in details}
        if not details:
            # Livreur inactif sans tournee : inutile de l'afficher
            if l.statut != 'actif':
                continue
            etat = 'aucune'
        elif 'ecart' in etats:
            etat = 'ecart'
        elif 'a_controler' in etats:
            etat = 'a_controler'
        else:
            etat = 'net'
        resultats.append({
            'livreur_id': l.id,
            'nom': l.nom,
            'matricule': l.matricule,
            'statut_livreur': l.statut,
            'etat': etat,
            'etat_libelle': LIBELLES[etat],
            'nb_tournees': len(details),
            'nb_ecarts': sum(1 for d in details if d['etat'] == 'ecart'),
            'nb_a_controler': sum(1 for d in details if d['etat'] == 'a_controler'),
            'manquant': _f(manquant),
            'excedent': _f(excedent),
            'ecart_net': _f(excedent - manquant),
            'derniere_tournee': details[0]['date'] if details else None,
            'tournees': details,
        })

    resultats.sort(key=lambda r: (ORDRE_ETAT[r['etat']], -abs(r['ecart_net']), r['nom']))
    synthese = {k: sum(1 for r in resultats if r['etat'] == k) for k in ORDRE_ETAT}
    synthese['manquant_total'] = _f(sum(Decimal(str(r['manquant'])) for r in resultats))
    synthese['excedent_total'] = _f(sum(Decimal(str(r['excedent'])) for r in resultats))
    return {
        'periode': {'debut': date_debut.isoformat(), 'fin': date_fin.isoformat()},
        'tolerance': _f(TOLERANCE),
        'synthese': synthese,
        'livreurs': resultats,
    }
