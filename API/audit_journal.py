"""
Journal d'audit lisible pour l'interface d'administration.

GET /API/audit-journal/          liste paginée et filtrée, avec libellés en français
    ?q=texte  &module=produit  &action=produit.delete  &acteur=<user id>
    &date_debut=AAAA-MM-JJ  &date_fin=AAAA-MM-JJ  &page=1  &page_size=50
GET /API/audit-journal/filtres/  valeurs disponibles pour les listes déroulantes

(L'ancienne route /API/audit-logs/ reste inchangée : la page Rapports s'en sert.)
"""
import csv
import json
import re
from datetime import datetime, time, timedelta

from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AuditLog

MODULES = {
    'produit': 'Produits',
    'prixproduit': 'Prix des produits',
    'promotion': 'Promotions',
    'codeprix': 'Codes prix',
    'typeprix': 'Types de prix',
    'client': 'Clients',
    'secteur': 'Secteurs',
    'vente': 'Ventes',
    'achat': 'Achats',
    'facture': 'Factures',
    'bonlivraison': 'Bons de livraison',
    'stockmove': 'Mouvements de stock',
    'mouvement': 'Mouvements de stock',
    'warehouse': 'Entrepôts',
    'inventorysession': 'Inventaires',
    'user': 'Utilisateurs',
    'group': 'Groupes',
    'role': 'Rôles & permissions',
    'currency': 'Devises',
    'exchange_rate': 'Taux de change',
    'report': 'Rapports',
    'benefices': 'Tableau des bénéfices',
}

# Libellés complets pour les actions particulières
ACTIONS = {
    'produit.delete': 'Produit supprimé (désactivé)',
    'produit.purge': 'Produit supprimé définitivement',
    'produit.restore': 'Produit réactivé',
    'facture.create_from_bl': 'Facture créée depuis un bon de livraison',
    'facture.issue': 'Facture émise',
    'facture.pay': 'Facture payée',
    'vente.complete': 'Vente validée',
    'vente.cancel': 'Vente annulée',
    'vente.update_line_price': "Prix d'une ligne de vente modifié",
    'bonlivraison.validate': 'Bon de livraison validé',
    'stockmove.transfer': 'Transfert de stock',
    'mouvement.return': 'Retour de stock',
    'inventorysession.export': 'Inventaire exporté',
    'inventorysession.saisie_masse': 'Inventaire : saisie en masse',
    'user.password_reset': 'Mot de passe réinitialisé',
    'role.update_permissions': 'Permissions du rôle modifiées',
    'currency.set_default': 'Devise par défaut changée',
    'exchange_rate.upsert': 'Taux de change enregistré',
    'client.paiement_solde': 'Paiement du solde client',
    'client.config_created': 'Configuration client créée',
    'report.export_inventory': "Export du rapport d'inventaire",
    'report.export_sales': 'Export du rapport des ventes',
    'report.export_profit': 'Export du rapport des bénéfices',
    'report.export_stock_valuation': 'Export de la valorisation du stock',
    'benefices.deverrouille': 'Tableau des bénéfices déverrouillé',
    'benefices.pin_defini': 'Code PIN des bénéfices défini',
    'benefices.pin_refuse': 'Code PIN des bénéfices refusé',
    'benefices.pin_change_refuse': 'Changement de PIN des bénéfices refusé',
}

# Nature de l'action -> (verbe, catégorie utilisée pour la couleur du badge)
VERBES = {
    'create': ('Création', 'create'),
    'update': ('Modification', 'update'),
    'delete': ('Suppression', 'delete'),
    'purge': ('Suppression définitive', 'delete'),
    'restore': ('Réactivation', 'create'),
    'cancel': ('Annulation', 'delete'),
    'export': ('Export', 'export'),
}

# Clés de métadonnées -> libellé français
CHAMPS = {
    'id': 'ID', 'reference': 'Référence', 'designation': 'Désignation', 'nom': 'Nom',
    'code': 'Code', 'numero': 'Numéro', 'montant': 'Montant', 'total': 'Total',
    'produit': 'Produit', 'warehouse': 'Entrepôt', 'username': 'Utilisateur',
    'quantite': 'Quantité', 'delta': 'Quantité', 'prix': 'Prix', 'statut': 'Statut',
    'client': 'Client', 'format': 'Format', 'role': 'Rôle',
    'creees': 'Créées', 'mises_a_jour': 'Mises à jour', 'supprimees': 'Supprimées',
    'stock_supprime': 'Stock supprimé', 'detail_stock': 'Détail du stock',
    'documents_conserves': 'Documents conservés',
}


def _module(action):
    return (action or '').split('.', 1)[0]


def libelle_action(action):
    if action in ACTIONS:
        return ACTIONS[action]
    module, _, verbe = (action or '').partition('.')
    nom_verbe = VERBES.get(verbe, (verbe.replace('_', ' ').capitalize() or 'Action', ''))[0]
    nom_module = MODULES.get(module, module.capitalize())
    return f'{nom_verbe} — {nom_module}'


def categorie_action(action):
    verbe = (action or '').partition('.')[2]
    if verbe.startswith('export'):
        return 'export'
    if action.endswith('refuse'):
        return 'delete'
    return VERBES.get(verbe, ('', 'autre'))[1]


def details_lisibles(metadata):
    """Transforme le JSON des métadonnées en liste [{label, valeur}]."""
    if not metadata:
        return []
    try:
        data = json.loads(metadata)
    except (TypeError, ValueError):
        return [{'label': 'Détails', 'valeur': str(metadata)}]
    if not isinstance(data, dict):
        return [{'label': 'Détails', 'valeur': json.dumps(data, ensure_ascii=False)}]
    out = []
    for k, v in data.items():
        if v in (None, '', [], {}):
            continue
        if isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False)
        out.append({'label': CHAMPS.get(k, k.replace('_', ' ').capitalize()), 'valeur': str(v)})
    return out


def appareil(user_agent):
    """Résumé court du navigateur / appareil."""
    ua = user_agent or ''
    if not ua:
        return ''
    if 'okhttp' in ua or 'Expo' in ua or 'ReactNative' in ua:
        return 'Application mobile'
    nav = next((n for pat, n in (
        (r'Edg/', 'Edge'), (r'OPR/|Opera', 'Opera'), (r'Chrome/', 'Chrome'),
        (r'Firefox/', 'Firefox'), (r'Safari/', 'Safari'),
    ) if re.search(pat, ua)), 'Navigateur')
    sys = next((n for pat, n in (
        (r'Android', 'Android'), (r'iPhone|iPad', 'iOS'), (r'Windows', 'Windows'),
        (r'Mac OS', 'macOS'), (r'Linux', 'Linux'),
    ) if re.search(pat, ua)), '')
    return f'{nav} · {sys}' if sys else nav


def _cible_depuis_metadata(metadata):
    """Élément concerné quand l'objet n'existe plus (ex. produit supprimé définitivement)."""
    try:
        data = json.loads(metadata or '{}')
    except (TypeError, ValueError):
        return ''
    if not isinstance(data, dict):
        return ''
    morceaux = [str(data[k]) for k in ('reference', 'designation', 'nom', 'numero') if data.get(k)]
    return ' - '.join(morceaux)


def serialiser(log):
    acteur = log.actor
    nom_acteur = ''
    if acteur:
        nom_acteur = (acteur.get_full_name() or '').strip() or acteur.username
    return {
        'id': log.id,
        'date': log.created_at,
        'acteur_id': acteur.id if acteur else None,
        'acteur': nom_acteur or 'Système',
        'acteur_username': acteur.username if acteur else '',
        'action': log.action,
        'action_label': libelle_action(log.action),
        'module': _module(log.action),
        'module_label': MODULES.get(_module(log.action), _module(log.action).capitalize()),
        'categorie': categorie_action(log.action),
        'cible': log.target_repr or _cible_depuis_metadata(log.metadata),
        'cible_id': log.target_id or '',
        'details': details_lisibles(log.metadata),
        'ip': log.ip_address or '',
        'appareil': appareil(log.user_agent),
        'user_agent': log.user_agent or '',
    }


def _parse_date(value):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None


def filtrer(request):
    qs = AuditLog.objects.select_related('actor').order_by('-created_at', '-id')
    p = request.query_params

    module = p.get('module')
    if module:
        qs = qs.filter(action__startswith=module + '.')
    action = p.get('action')
    if action:
        qs = qs.filter(action=action)
    acteur = p.get('acteur')
    if acteur:
        qs = qs.filter(actor_id=None) if acteur == 'systeme' else qs.filter(actor_id=acteur)

    tz = timezone.get_current_timezone()
    debut = _parse_date(p.get('date_debut'))
    if debut:
        qs = qs.filter(created_at__gte=timezone.make_aware(datetime.combine(debut, time.min), tz))
    fin = _parse_date(p.get('date_fin'))
    if fin:
        qs = qs.filter(created_at__lt=timezone.make_aware(datetime.combine(fin + timedelta(days=1), time.min), tz))

    q = (p.get('q') or '').strip()
    if q:
        qs = qs.filter(
            Q(action__icontains=q) | Q(target_repr__icontains=q) | Q(metadata__icontains=q)
            | Q(actor__username__icontains=q) | Q(actor__first_name__icontains=q)
            | Q(actor__last_name__icontains=q) | Q(ip_address__icontains=q)
        )
    return qs


class AuditJournalView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        qs = filtrer(request)

        if request.query_params.get('export') == 'csv':
            return self._csv(qs)

        try:
            page_size = max(10, min(int(request.query_params.get('page_size', 50)), 200))
        except ValueError:
            page_size = 50
        total = qs.count()
        pages = max(1, (total + page_size - 1) // page_size)
        try:
            page = max(1, min(int(request.query_params.get('page', 1)), pages))
        except ValueError:
            page = 1
        debut = (page - 1) * page_size
        logs = qs[debut:debut + page_size]

        # Statistiques de la sélection
        now = timezone.localtime()
        debut_jour = now.replace(hour=0, minute=0, second=0, microsecond=0)
        stats = {
            'total': total,
            'aujourdhui': qs.filter(created_at__gte=debut_jour).count(),
            'suppressions': qs.filter(
                Q(action__endswith='.delete') | Q(action__endswith='.purge')).count(),
            'utilisateurs': qs.exclude(actor=None).values('actor').distinct().count(),
        }
        return Response({
            'page': page, 'pages': pages, 'page_size': page_size, 'count': total,
            'stats': stats,
            'results': [serialiser(l) for l in logs],
        })

    def _csv(self, qs):
        resp = HttpResponse(content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = 'attachment; filename="journal_audit.csv"'
        resp.write('﻿')  # BOM pour Excel
        w = csv.writer(resp, delimiter=';')
        w.writerow(['Date', 'Utilisateur', 'Module', 'Action', 'Élément', 'Détails', 'Adresse IP', 'Appareil'])
        for log in qs[:10000]:
            d = serialiser(log)
            w.writerow([
                timezone.localtime(log.created_at).strftime('%d/%m/%Y %H:%M:%S'),
                d['acteur'], d['module_label'], d['action_label'], d['cible'],
                ' | '.join(f"{x['label']}: {x['valeur']}" for x in d['details']),
                d['ip'], d['appareil'],
            ])
        return resp


class AuditJournalFiltresView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        actions = (AuditLog.objects.values('action').annotate(n=Count('id')).order_by('action'))
        modules = {}
        liste_actions = []
        for a in actions:
            m = _module(a['action'])
            modules[m] = modules.get(m, 0) + a['n']
            liste_actions.append({'value': a['action'], 'label': libelle_action(a['action']),
                                  'module': m, 'count': a['n']})
        acteur_ids = AuditLog.objects.exclude(actor=None).values_list('actor', flat=True).distinct()
        acteurs = [
            {'value': u.id, 'label': (u.get_full_name() or '').strip() or u.username}
            for u in User.objects.filter(id__in=acteur_ids).order_by('username')
        ]
        return Response({
            'modules': sorted(
                [{'value': m, 'label': MODULES.get(m, m.capitalize()), 'count': n} for m, n in modules.items()],
                key=lambda x: x['label']),
            'actions': liste_actions,
            'acteurs': acteurs,
        })
