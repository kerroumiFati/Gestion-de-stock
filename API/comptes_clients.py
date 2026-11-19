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
