"""
Vue de la carte GPS des livreurs
"""
import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .distribution_models import LivreurDistribution


@login_required
def livreurs_map_view(request):
    """Vue de la carte des livreurs en temps réel"""
    # Récupérer tous les livreurs qui ont une position GPS
    livreurs = LivreurDistribution.objects.filter(
        current_lat__isnull=False,
        current_lng__isnull=False
    ).select_related('user')

    # Préparer les données pour le template
    livreurs_data = []
    for livreur in livreurs:
        livreurs_data.append({
            'id': livreur.id,
            'nom': livreur.nom,
            'matricule': livreur.matricule,
            'lat': float(livreur.current_lat),
            'lng': float(livreur.current_lng),
            'last_update': livreur.last_location_update.isoformat() if livreur.last_location_update else None,
            'statut': livreur.statut,
        })

    return render(request, 'api/livreurs_map.html', {
        'livreurs_json': json.dumps(livreurs_data),
        'livreurs_count': len(livreurs_data)
    })
