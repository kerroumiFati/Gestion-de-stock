"""Compte client : tout ce qu'un client doit, l'historique de ses crédits et paiements, et
l'encaissement d'un montant réparti automatiquement sur ses dettes.

Un client peut devoir de l'argent pour :
  - une dette antérieure (champ Client.solde négatif, ex. saisie sur le PC) ;
  - une vente à crédit faite sur le téléphone (VenteTourneeMobile) ;
  - une vente à crédit faite sur le PC (Vente, payée par PaiementVente) ;
  - une commande livrée pas entièrement payée (CommandeClient).

« Encaisser » répartit le montant reçu sur ces dettes, de la plus ancienne à la plus récente.
Chaque part est enregistrée sur son document (encaissement de vente, de commande, paiement de
vente PC, remboursement de dette) avec la tournée où l'argent a été reçu : la caisse de la
tournée et le reste à payer de chaque document restent justes. Le surplus devient une avance
(Client.solde positif).

Convention du modèle Client : solde POSITIF = avance du client, NÉGATIF = dette.
"""
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

Z = Decimal('0')
CENT = Decimal('0.01')


def _d(v):
    return Decimal(str(v or 0))


def _date_tri(dt):
    """Clé de tri : None (dette antérieure, sans date) passe en premier."""
    return (0, '') if dt is None else (1, dt.isoformat())


def documents_dus(client):
    """Dettes du client, de la plus ancienne à la plus récente. Chaque élément :
    cle (identifiant stable, aussi utilisé par le téléphone), type, libelle, reference,
    date (ISO ou None), total, reste."""
    from API.models import Vente
    from API.distribution_models import VenteTourneeMobile, CommandeClient

    docs = []
    solde = _d(client.solde)
    if solde < 0:
        docs.append({'cle': 'solde', 'type': 'dette_anterieure', 'libelle': 'Dette antérieure',
                     'reference': '', 'date': None, 'total': -solde, 'reste': -solde})

    for v in VenteTourneeMobile.objects.filter(client=client):
        recu = _d(v.montant_paye) - _d(v.montant_rendu)
        reste = _d(v.montant_total) - recu
        if reste > CENT:
            docs.append({'cle': f'vm-{v.app_id or v.pk}', 'type': 'vente', 'libelle': 'Vente',
                         'reference': v.numero_vente, 'date': v.date_vente,
                         'total': _d(v.montant_total), 'reste': reste, '_obj': v})

    for v in Vente.objects.filter(client=client, statut='completed'):
        reste = _d(v.get_reste_a_payer())
        if reste > CENT:
            docs.append({'cle': f'vpc-{v.pk}', 'type': 'vente_pc', 'libelle': 'Vente (bureau)',
                         'reference': v.numero, 'date': v.date_vente,
                         'total': _d(v.total_ttc), 'reste': reste, '_obj': v})

    for c in CommandeClient.objects.filter(client=client, statut='delivered'):
        reste = _d(c.montant_total_ttc) - _d(c.montant_paye)
        if reste > CENT:
            docs.append({'cle': f'cmd-{c.pk}', 'type': 'commande', 'libelle': 'Commande livrée',
                         'reference': c.reference, 'date': c.date_livraison_reelle or c.date_commande,
                         'total': _d(c.montant_total_ttc), 'reste': reste, '_obj': c})

    docs.sort(key=lambda d: _date_tri(d['date']))
    return docs


def situations_clients(clients):
    """Situation de PLUSIEURS clients d'un coup (listes, tableau de bord), mêmes règles que
    documents_dus / compte, en 4 requêtes quel que soit le nombre de clients.
    Renvoie {client_id: {'dette', 'avance', 'net', 'nb_documents'}} (Decimal ; net > 0 = le client doit)."""
    from django.db.models import DecimalField, ExpressionWrapper, F, Sum, Value
    from django.db.models.functions import Coalesce
    from API.models import Vente
    from API.distribution_models import VenteTourneeMobile, CommandeClient

    dec = DecimalField(max_digits=14, decimal_places=2)
    zero = Value(Decimal('0'), output_field=dec)
    res = {}
    soldes = {}
    for cid, solde in clients.values_list('pk', 'solde'):
        soldes[cid] = _d(solde)
        res[cid] = {'dette': Z, 'avance': max(soldes[cid], Z), 'net': Z, 'nb_documents': 0}

    def ajouter(cid, reste):
        r = res.get(cid)
        if r is not None and reste > CENT:
            r['dette'] += reste
            r['nb_documents'] += 1

    for cid, solde in soldes.items():
        if solde < 0:
            ajouter(cid, -solde)

    ids = list(res)
    # Ventes du téléphone : reste = total - (payé - rendu)
    for cid, reste in (VenteTourneeMobile.objects.filter(client_id__in=ids)
                       .annotate(r=ExpressionWrapper(
                           Coalesce('montant_total', zero) - Coalesce('montant_paye', zero)
                           + Coalesce('montant_rendu', zero), output_field=dec))
                       .filter(r__gt=CENT).values_list('client_id', 'r')):
        ajouter(cid, _d(reste))
    # Ventes du PC validées : reste = total TTC - paiements
    for cid, reste in (Vente.objects.filter(client_id__in=ids, statut='completed')
                       .annotate(p=Coalesce(Sum('paiements__montant'), zero))
                       .annotate(r=ExpressionWrapper(Coalesce('total_ttc', zero) - F('p'), output_field=dec))
                       .filter(r__gt=CENT).values_list('client_id', 'r')):
        ajouter(cid, _d(reste))
    # Commandes livrées pas entièrement payées
    for cid, reste in (CommandeClient.objects.filter(client_id__in=ids, statut='delivered')
                       .annotate(r=ExpressionWrapper(
                           Coalesce('montant_total_ttc', zero) - Coalesce('montant_paye', zero), output_field=dec))
                       .filter(r__gt=CENT).values_list('client_id', 'r')):
        ajouter(cid, _d(reste))

    for r in res.values():
        r['net'] = r['dette'] - r['avance']
    return res


def historique(client, limite=60):
    """Mouvements du compte, du plus récent au plus ancien : ce qui a été dû (débit) et payé (crédit)."""
    from API.models import Vente, PaiementVente, PaiementSolde
    from API.distribution_models import (VenteTourneeMobile, CommandeClient, EncaissementCommande,
                                         EncaissementVente)
    ev = []

    def add(date, libelle, reference, du=Z, paye=Z, mode=''):
        ev.append({'date': date, 'libelle': libelle, 'reference': reference or '',
                   'du': du, 'paye': paye, 'mode': mode or ''})

    for v in VenteTourneeMobile.objects.filter(client=client):
        add(v.date_vente, 'Vente', v.numero_vente, du=_d(v.montant_total))
        recu_vente = _d(v.montant_paye) - _d(v.montant_rendu) - sum(
            (e.montant for e in v.encaissements.all()), Z)
        if recu_vente > CENT:
            add(v.date_vente, 'Payé à la vente', v.numero_vente, paye=recu_vente, mode=v.type_paiement)
        for e in v.encaissements.all():
            add(e.date_paiement, 'Paiement', v.numero_vente, paye=_d(e.montant), mode=e.type_paiement)

    for v in Vente.objects.filter(client=client, statut='completed'):
        add(v.date_vente, 'Vente (bureau)', v.numero, du=_d(v.total_ttc))
        for p in v.paiements.all():
            add(p.date_paiement, 'Paiement', v.numero, paye=_d(p.montant),
                mode={'cash': 'especes', 'check': 'cheque'}.get(p.moyen_paiement, p.moyen_paiement))

    for c in CommandeClient.objects.filter(client=client).exclude(statut='cancelled'):
        if c.statut == 'delivered':
            add(c.date_livraison_reelle or c.date_commande, 'Commande livrée', c.reference,
                du=_d(c.montant_total_ttc))
        for e in c.encaissements.all():
            if e.montant < 0:
                add(e.date_paiement, 'Rendu au client', c.reference, paye=_d(e.montant), mode=e.type_paiement)
            else:
                lib = 'Acompte' if e.app_id.startswith('acompte-') else 'Paiement'
                add(e.date_paiement, lib, c.reference, paye=_d(e.montant), mode=e.type_paiement)

    for p in PaiementSolde.objects.filter(client=client):
        lib = 'Avance (trop-payé)' if p.mode_paiement == 'avoir' else (
            'Avance' if (p.app_id or '').endswith('-avance') else 'Remboursement de dette')
        add(p.date_paiement, lib, '', paye=_d(p.montant), mode=p.mode_paiement)

    ev.sort(key=lambda e: _date_tri(e['date']), reverse=True)
    return ev[:limite]


def _json(v):
    if isinstance(v, Decimal):
        return float(v)
    if hasattr(v, 'isoformat'):
        return v.isoformat()
    return v


def compte(client, avec_historique=True):
    docs = documents_dus(client)
    dette = sum((d['reste'] for d in docs), Z)
    avance = max(_d(client.solde), Z)
    net = dette - avance
    res = {
        'client_id': client.pk,
        'client_nom': ' '.join(x for x in [client.prenom, client.nom] if x).strip(),
        'dette': float(dette),
        'avance': float(avance),
        'net': float(net),
        'situation': 'Dette' if net > CENT else ('Avance' if net < -CENT else 'À jour'),
        'documents': [{k: _json(v) for k, v in d.items() if not k.startswith('_')} for d in docs],
    }
    if avec_historique:
        res['historique'] = [{k: _json(v) for k, v in e.items()} for e in historique(client)]
    return res


def encaisser(client, app_id, montant, mode, tournee=None, date_paiement=None, user=None):
    """Encaisse `montant` (espèces ou chèque) et le répartit sur les dettes du client, de la
    plus ancienne à la plus récente ; le surplus devient une avance. Idempotent sur app_id.
    Renvoie (paiement_client, deja_enregistre)."""
    from API.models import Client, PaiementVente, PaiementSolde
    from API.distribution_models import (PaiementClient, EncaissementCommande, EncaissementVente,
                                         VenteTourneeMobile, CommandeClient)

    existant = PaiementClient.objects.filter(app_id=app_id).first()
    if existant:
        return existant, True

    montant = _d(montant)
    date_paiement = date_paiement or timezone.now()
    try:
        with transaction.atomic():
            client = Client.objects.select_for_update().get(pk=client.pk)
            pc = PaiementClient.objects.create(client=client, app_id=app_id, montant=montant,
                                               mode_paiement=mode, tournee=tournee,
                                               date_paiement=date_paiement, enregistre_par=user)
            reste_a_repartir = montant
            repartition = []
            montant_ventes_pc = Z
            for d in documents_dus(client):
                if reste_a_repartir <= 0:
                    break
                part = min(reste_a_repartir, d['reste'])
                cle_op = f'{app_id}-{d["cle"]}'
                if d['type'] == 'dette_anterieure':
                    avant = _d(client.solde)
                    client.solde = avant + part
                    client.save(update_fields=['solde'])
                    PaiementSolde.objects.create(client=client, company=getattr(client, 'company', None),
                                                 montant=part, mode_paiement=mode, solde_avant=avant,
                                                 solde_apres=client.solde, notes=f'Encaissement {app_id}',
                                                 enregistre_par=user, app_id=cle_op, tournee=tournee,
                                                 date_paiement=date_paiement)
                elif d['type'] == 'vente':
                    v = VenteTourneeMobile.objects.select_for_update().get(pk=d['_obj'].pk)
                    EncaissementVente.objects.create(vente=v, app_id=cle_op, montant=part, type_paiement=mode,
                                                     date_paiement=date_paiement, tournee=tournee,
                                                     enregistre_par=user)
                    v.montant_paye = _d(v.montant_paye) + part
                    v.save(update_fields=['montant_paye'])
                elif d['type'] == 'vente_pc':
                    PaiementVente.objects.create(vente=d['_obj'], montant=part, date_paiement=date_paiement,
                                                 moyen_paiement={'especes': 'cash', 'cheque': 'check'}[mode],
                                                 reference=cle_op[:100], notes=f'Encaissement {app_id}',
                                                 created_by=user)
                    montant_ventes_pc += part
                elif d['type'] == 'commande':
                    c = CommandeClient.objects.select_for_update().get(pk=d['_obj'].pk)
                    EncaissementCommande.objects.create(commande=c, app_id=cle_op, montant=part,
                                                        type_paiement=mode, date_paiement=date_paiement,
                                                        tournee=tournee, enregistre_par=user)
                    c.montant_paye = _d(c.montant_paye) + part
                    c.est_paye = c.montant_paye >= _d(c.montant_total_ttc) - CENT
                    c.date_paiement = date_paiement
                    c.save(update_fields=['montant_paye', 'est_paye', 'date_paiement'])
                repartition.append({'cle': d['cle'], 'type': d['type'], 'reference': d['reference'],
                                    'montant': float(part)})
                reste_a_repartir -= part

            if reste_a_repartir > CENT:  # surplus : avance du client
                avant = _d(client.solde)
                client.solde = avant + reste_a_repartir
                client.save(update_fields=['solde'])
                PaiementSolde.objects.create(client=client, company=getattr(client, 'company', None),
                                             montant=reste_a_repartir, mode_paiement=mode, solde_avant=avant,
                                             solde_apres=client.solde, notes=f'Avance - encaissement {app_id}',
                                             enregistre_par=user, app_id=f'{app_id}-avance', tournee=tournee,
                                             date_paiement=date_paiement)
                repartition.append({'cle': 'avance', 'type': 'avance', 'reference': '',
                                    'montant': float(reste_a_repartir)})

            pc.repartition = repartition
            pc.montant_ventes_pc = montant_ventes_pc
            pc.save(update_fields=['repartition', 'montant_ventes_pc'])
            return pc, False
    except IntegrityError:
        existant = PaiementClient.objects.filter(app_id=app_id).first()
        if existant:
            return existant, True
        raise


def suivi_bons(clients, du=None, au=None):
    """Suivi des paiements, bon par bon : tous les bons des clients (payés ou non) dont la date
    est dans la période [du, au] (dates, bornes incluses). Mêmes documents et même calcul du
    reste que documents_dus (ventes téléphone, ventes bureau validées, commandes livrées).
    Renvoie {'bons': [...], 'clients': {id: {...}}} ; la dette antérieure (sans date) et la
    situation globale du client sont données à part, sans filtre de période."""
    from django.db.models import Max
    from API.models import Vente
    from API.distribution_models import VenteTourneeMobile, CommandeClient

    infos = {c['id']: c for c in clients.values('id', 'nom', 'prenom', 'telephone', 'solde')}
    ids = list(infos)

    def periode(qs, champ):
        if du:
            qs = qs.filter(**{f'{champ}__date__gte': du})
        if au:
            qs = qs.filter(**{f'{champ}__date__lte': au})
        return qs

    def etat(total, reste):
        if reste <= CENT:
            return 'paye'
        return 'partiel' if reste < total - CENT else 'non_paye'

    bons = []

    def ajouter(cle, type_, libelle, reference, client_id, date, vendeur, total, paye, dernier_paiement, mode):
        total = _d(total)
        if total <= CENT:  # bon à 0 DA (tout offert, annulé à zéro) : rien à suivre
            return
        paye = max(_d(paye), Z)
        reste = max(total - paye, Z)
        bons.append({'cle': cle, 'type': type_, 'libelle': libelle, 'reference': reference or '',
                     'client_id': client_id, 'date': date, 'vendeur': vendeur or '',
                     'total': total, 'paye': min(paye, total), 'reste': reste,
                     'etat': etat(total, reste), 'dernier_paiement': dernier_paiement, 'mode': mode or ''})

    # Ventes faites sur le téléphone (payé - rendu = argent gardé)
    for v in (periode(VenteTourneeMobile.objects.filter(client_id__in=ids), 'date_vente')
              .select_related('tournee__livreur').annotate(der=Max('encaissements__date_paiement'))):
        recu = _d(v.montant_paye) - _d(v.montant_rendu)
        livreur = v.tournee.livreur.nom if v.tournee_id and v.tournee.livreur_id else ''
        ajouter(f'vm-{v.pk}', 'vente', 'Vente directe', v.numero_vente, v.client_id, v.date_vente, livreur,
                v.montant_total, recu, v.der or (v.date_vente if recu > CENT else None), v.type_paiement)

    # Ventes faites au bureau (validées)
    modes_pc = {'cash': 'especes', 'check': 'cheque', 'card': 'carte', 'transfer': 'virement', 'credit': 'credit'}
    for v in (periode(Vente.objects.filter(client_id__in=ids, statut='completed'), 'date_vente')
              .prefetch_related('paiements')):
        paiements = list(v.paiements.all())
        paye = sum((_d(p.montant) for p in paiements), Z)
        der = max((p.date_paiement for p in paiements), default=None)
        ajouter(f'vpc-{v.pk}', 'vente_pc', 'Vente (bureau)', v.numero, v.client_id, v.date_vente, '',
                v.total_ttc, paye, der, modes_pc.get(v.type_paiement, v.type_paiement))

    # Commandes livrées (date = date de livraison, sinon date de commande)
    from django.db.models.functions import Coalesce
    cmds = (CommandeClient.objects.filter(client_id__in=ids, statut='delivered')
            .annotate(jour=Coalesce('date_livraison_reelle', 'date_commande'))
            .select_related('passee_par', 'livreur').annotate(der=Max('encaissements__date_paiement')))
    for c in periode(cmds, 'jour'):
        vendeur = (c.passee_par or c.livreur).nom if (c.passee_par_id or c.livreur_id) else ''
        ajouter(f'cmd-{c.pk}', 'commande', 'Commande livrée', c.reference, c.client_id, c.jour, vendeur,
                c.montant_total_ttc, c.montant_paye,
                (c.der or c.date_paiement or c.jour) if _d(c.montant_paye) > CENT else None,
                c.type_paiement)

    bons.sort(key=lambda b: _date_tri(b['date']), reverse=True)

    sit = situations_clients(clients)
    res_clients = {}
    for cid, c in infos.items():
        solde = _d(c.get('solde'))
        s = sit.get(cid, {'net': Z})
        res_clients[cid] = {'id': cid, 'nom': ' '.join(x for x in [c.get('prenom'), c.get('nom')] if x).strip(),
                            'telephone': c.get('telephone') or '',
                            'dette_anterieure': -solde if solde < 0 else Z,
                            'avance': solde if solde > 0 else Z,
                            'situation': s['net']}
    return {'bons': bons, 'clients': res_clients}


def detail_bon(cle, clients):
    """Contenu d'un bon du suivi des paiements (clé « cmd-12 », « vm-3 », « vpc-40 ») : en-tête,
    produits et paiements. None si le bon n'existe pas ou si son client n'est pas dans `clients`."""
    from API.models import Vente
    from API.distribution_models import VenteTourneeMobile, CommandeClient

    try:
        prefixe, pk = str(cle).split('-', 1)
        pk = int(pk)
    except (ValueError, TypeError):
        return None
    MODES_PC = {'cash': 'especes', 'check': 'cheque', 'card': 'carte', 'transfer': 'virement', 'credit': 'credit'}

    def ligne(produit, designation, quantite, prix, montant):
        return {'designation': designation or (produit.designation if produit else ''),
                'reference': produit.reference if produit else '',
                'unites_par_carton': produit.get_unites_par_carton() if produit else 1,
                'quantite': _d(quantite), 'prix_unitaire': _d(prix), 'montant': _d(montant)}

    if prefixe == 'cmd':
        c = (CommandeClient.objects.filter(pk=pk, client__in=clients)
             .select_related('client', 'passee_par', 'livreur').first())
        if c is None:
            return None
        lignes = [ligne(l.produit, '', l.quantite, l.prix_unitaire_ht, l.montant_ttc)
                  for l in c.lignes.select_related('produit').order_by('id')]
        paiements = [{'date': e.date_paiement, 'montant': _d(e.montant), 'mode': e.type_paiement}
                     for e in c.encaissements.order_by('date_paiement')]
        paye = _d(c.montant_paye)
        if not paiements and paye > CENT:  # payé à la livraison, sans encaissement séparé
            paiements = [{'date': c.date_paiement or c.date_livraison_reelle, 'montant': paye, 'mode': c.type_paiement}]
        vendeur = c.passee_par or c.livreur
        res = {'type': 'commande', 'libelle': 'Commande livrée', 'reference': c.reference, 'client': c.client,
               'date': c.date_livraison_reelle or c.date_commande, 'date_commande': c.date_commande,
               'vendeur': vendeur.nom if vendeur else '',
               'livreur': c.livreur.nom if c.livreur_id and c.passee_par_id and c.livreur_id != c.passee_par_id else '',
               'total_ht': _d(c.montant_total_ht), 'total': _d(c.montant_total_ttc), 'paye': paye,
               'notes': c.notes or '', 'prix_ht': True}
    elif prefixe == 'vm':
        v = (VenteTourneeMobile.objects.filter(pk=pk, client__in=clients)
             .select_related('client', 'tournee__livreur').first())
        if v is None:
            return None
        lignes = [ligne(l.produit, '', l.quantite, l.prix_unitaire, l.montant_ttc)
                  for l in v.lignes.select_related('produit').order_by('id')]
        encs = list(v.encaissements.order_by('date_paiement'))
        recu = _d(v.montant_paye) - _d(v.montant_rendu)
        a_la_vente = recu - sum((e.montant for e in encs), Z)
        paiements = ([{'date': v.date_vente, 'montant': a_la_vente, 'mode': v.type_paiement}] if a_la_vente > CENT else []) + [
            {'date': e.date_paiement, 'montant': _d(e.montant), 'mode': e.type_paiement} for e in encs]
        res = {'type': 'vente', 'libelle': 'Vente directe (van)', 'reference': v.numero_vente, 'client': v.client,
               'date': v.date_vente, 'date_commande': None,
               'vendeur': v.tournee.livreur.nom if v.tournee_id and v.tournee.livreur_id else '', 'livreur': '',
               'total_ht': _d(v.montant_ht), 'total': _d(v.montant_total), 'paye': recu,
               'notes': v.notes or '', 'prix_ht': True}
    elif prefixe == 'vpc':
        v = Vente.objects.filter(pk=pk, client__in=clients, statut='completed').select_related('client').first()
        if v is None:
            return None
        lignes = [ligne(l.produit, l.designation, l.quantite, l.prixU_snapshot, l.get_total_in_sale_currency())
                  for l in v.lignes.select_related('produit').order_by('id')]
        paiements = [{'date': p.date_paiement, 'montant': _d(p.montant),
                      'mode': MODES_PC.get(p.moyen_paiement, p.moyen_paiement)} for p in v.paiements.order_by('date_paiement')]
        res = {'type': 'vente_pc', 'libelle': 'Vente au bureau', 'reference': v.numero, 'client': v.client,
               'date': v.date_vente, 'date_commande': None, 'vendeur': '', 'livreur': '',
               'total_ht': _d(v.total_ht), 'total': _d(v.total_ttc), 'paye': sum((p['montant'] for p in paiements), Z),
               'notes': v.observations or '', 'prix_ht': False}
    else:
        return None

    client = res.pop('client')
    res['paye'] = min(max(res['paye'], Z), res['total'])
    res['reste'] = max(res['total'] - res['paye'], Z)
    res['etat'] = 'paye' if res['reste'] <= CENT else ('partiel' if res['paye'] > CENT else 'non_paye')
    res['cle'] = cle
    res['client'] = {'id': client.pk, 'nom': ' '.join(x for x in [client.prenom, client.nom] if x).strip(),
                     'telephone': client.telephone or '', 'adresse': getattr(client, 'adresse', '') or ''}
    res['lignes'] = lignes
    res['paiements'] = paiements
    return res
