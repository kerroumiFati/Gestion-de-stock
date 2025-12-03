"""
Vue de la carte GPS des livreurs et clients
"""
import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .distribution_models import LivreurDistribution
from .models import Client, Secteur


@login_required
def livreurs_map_view(request):
    """Vue de la carte des livreurs et clients en temps réel"""

    # Récupérer la company de l'utilisateur si disponible
    company = getattr(request, 'company', None)

    # Récupérer tous les livreurs qui ont une position GPS
    livreurs_qs = LivreurDistribution.objects.filter(
        current_lat__isnull=False,
        current_lng__isnull=False
    ).select_related('user').prefetch_related('clients_assignes')

    # Récupérer tous les livreurs (même sans GPS) pour le filtre
    all_livreurs = LivreurDistribution.objects.all().order_by('nom')

    # Récupérer tous les secteurs
    secteurs_qs = Secteur.objects.filter(is_active=True)
    if company:
        secteurs_qs = secteurs_qs.filter(company=company)
    secteurs_qs = secteurs_qs.order_by('nom')

    # Récupérer tous les clients avec position GPS
    clients_qs = Client.objects.filter(
        lat__isnull=False,
        lng__isnull=False
    ).select_related('secteur')
    if company:
        clients_qs = clients_qs.filter(company=company)

    # Préparer les données des livreurs pour le template
    livreurs_data = []
    for livreur in livreurs_qs:
        # Récupérer les IDs des clients assignés
        clients_ids = list(livreur.clients_assignes.values_list('id', flat=True))
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
            'clients_assignes_ids': clients_ids,
        })

    # Préparer les données des clients pour le template
    clients_data = []
    for client in clients_qs:
        # Trouver les livreurs assignés à ce client
        livreurs_ids = list(client.livreurs_assignes.values_list('id', flat=True))
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
            'livreurs_ids': livreurs_ids,
        })

    # Préparer les données des secteurs
    secteurs_data = []
    for secteur in secteurs_qs:
        secteurs_data.append({
            'id': secteur.id,
            'code': secteur.code,
            'nom': secteur.nom,
            'couleur': secteur.couleur,
            'clients_count': secteur.clients.filter(lat__isnull=False, lng__isnull=False).count(),
        })

    # Préparer la liste de tous les livreurs pour le filtre
    all_livreurs_data = []
    for livreur in all_livreurs:
        all_livreurs_data.append({
            'id': livreur.id,
            'nom': livreur.nom,
            'matricule': livreur.matricule,
            'statut': livreur.statut,
            'clients_count': livreur.clients_assignes.count(),
        })

    return render(request, 'api/livreurs_map.html', {
        'livreurs_json': json.dumps(livreurs_data),
        'clients_json': json.dumps(clients_data),
        'secteurs_json': json.dumps(secteurs_data),
        'all_livreurs_json': json.dumps(all_livreurs_data),
        'livreurs_count': len(livreurs_data),
        'clients_count': len(clients_data),
        'secteurs_count': len(secteurs_data),
    })
