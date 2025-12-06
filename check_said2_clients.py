from API.distribution_models import LivreurDistribution, ClientAssignment
from API.models import Client

# Find SAID2 livreur
livreur = LivreurDistribution.objects.filter(username='SAID2').first() or \
          LivreurDistribution.objects.filter(matricule='SAID2').first()

if livreur:
    print(f'Livreur: {livreur.username}')
    print(f'Livreur ID: {livreur.id}')
    print(f'Matricule: {livreur.matricule}')

    # Get assigned clients
    assignments = ClientAssignment.objects.filter(livreur=livreur, is_active=True)

    print(f'\nClients assignes a SAID2:')
    for assignment in assignments:
        print(f'  - Client ID: {assignment.client.id}, Nom: {assignment.client.nom} {assignment.client.prenom}')

    print(f'\nTotal clients assignes: {assignments.count()}')
else:
    print('Livreur SAID2 not found')
