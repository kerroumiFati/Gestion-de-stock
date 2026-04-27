"""
Vue de la carte GPS des livreurs et clients
"""
import json
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .distribution_models import LivreurDistribution
from .models import Client, Secteur


def _build_map_data(company):
    """Construit les données livreurs/clients/secteurs pour la carte."""
    livreurs_qs = LivreurDistribution.objects.filter(
        current_lat__isnull=False,
        current_lng__isnull=False
    ).select_related('user').prefetch_related('clients_assignes')

    secteurs_qs = Secteur.objects.filter(is_active=True)
    clients_qs = Client.objects.filter(lat__isnull=False, lng__isnull=False).select_related('secteur')
    all_livreurs = LivreurDistribution.objects.all().order_by('nom')

    if company:
        secteurs_qs = secteurs_qs.filter(company=company)
        clients_qs = clients_qs.filter(company=company)

    livreurs_data = []
    for livreur in livreurs_qs:
        livreurs_data.append({
            'id': livreur.id,
            'nom': livreur.nom,
            'matricule': livreur.matricule,
            'lat': float(livreur.current_lat),
            'lng': float(livreur.current_lng),
            'last_update': livreur.last_location_update.isoformat() if livreur.last_location_update else None,
            'statut': livreur.statut,
            'vehicule': livreur.vehicule_immatriculation or '',
            'telephone': livreur.telephone or '',
            'clients_assignes_ids': list(livreur.clients_assignes.values_list('id', flat=True)),
        })

    clients_data = []
    for client in clients_qs:
        clients_data.append({
            'id': client.id,
            'nom': f"{client.nom} {client.prenom}".strip(),
            'adresse': client.adresse or '',
            'telephone': client.telephone or '',
            'email': client.email or '',
            'lat': float(client.lat),
            'lng': float(client.lng),
            'secteur_id': client.secteur_id,
            'secteur_nom': client.secteur.nom if client.secteur else None,
            'secteur_couleur': client.secteur.couleur if client.secteur else '#6b7280',
            'livreurs_ids': list(client.livreurs_assignes.values_list('id', flat=True)),
        })

    secteurs_data = []
    for secteur in secteurs_qs.order_by('nom'):
        secteurs_data.append({
            'id': secteur.id,
            'code': secteur.code,
            'nom': secteur.nom,
            'couleur': secteur.couleur,
            'clients_count': secteur.clients.filter(lat__isnull=False, lng__isnull=False).count(),
        })

    all_livreurs_data = []
    for livreur in all_livreurs:
        all_livreurs_data.append({
            'id': livreur.id,
            'nom': livreur.nom,
            'matricule': livreur.matricule,
            'statut': livreur.statut,
            'clients_count': livreur.clients_assignes.count(),
        })

    return livreurs_data, clients_data, secteurs_data, all_livreurs_data


@login_required
def livreurs_map_view(request):
    """Vue de la carte des livreurs et clients en temps réel"""
    company = getattr(request, 'company', None)
    livreurs_data, clients_data, secteurs_data, all_livreurs_data = _build_map_data(company)

    return render(request, 'api/livreurs_map.html', {
        'livreurs_json': json.dumps(livreurs_data),
        'clients_json': json.dumps(clients_data),
        'secteurs_json': json.dumps(secteurs_data),
        'all_livreurs_json': json.dumps(all_livreurs_data),
        'livreurs_count': len(livreurs_data),
        'clients_count': len(clients_data),
        'secteurs_count': len(secteurs_data),
    })


@login_required
def livreurs_map_data_view(request):
    """Endpoint JSON pour le rafraîchissement AJAX de la carte (sans rechargement de page)."""
    company = getattr(request, 'company', None)
    livreurs_data, clients_data, secteurs_data, all_livreurs_data = _build_map_data(company)

    return JsonResponse({
        'livreurs': livreurs_data,
        'clients': clients_data,
        'secteurs': secteurs_data,
        'all_livreurs': all_livreurs_data,
    })
