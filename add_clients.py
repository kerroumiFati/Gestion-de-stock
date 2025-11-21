import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.models import Client

# Liste de clients à créer
clients_data = [
    {'nom': 'Bouzid', 'prenom': 'Ahmed', 'email': 'ahmed.bouzid@email.dz', 'telephone': '0555123456', 'adresse': 'Rue des Martyrs, Alger'},
    {'nom': 'Khelifi', 'prenom': 'Fatima', 'email': 'fatima.khelifi@email.dz', 'telephone': '0666234567', 'adresse': 'Avenue de la Liberté, Oran'},
    {'nom': 'Mansouri', 'prenom': 'Karim', 'email': 'karim.mansouri@email.dz', 'telephone': '0777345678', 'adresse': 'Boulevard Mohamed V, Constantine'},
    {'nom': 'Amrani', 'prenom': 'Sarah', 'email': 'sarah.amrani@email.dz', 'telephone': '0555456789', 'adresse': 'Rue Didouche Mourad, Alger'},
    {'nom': 'Cherif', 'prenom': 'Malik', 'email': 'malik.cherif@email.dz', 'telephone': '0666567890', 'adresse': 'Place 1er Novembre, Annaba'},
    {'nom': 'Belkacem', 'prenom': 'Nadia', 'email': 'nadia.belkacem@email.dz', 'telephone': '0777678901', 'adresse': 'Rue Larbi Ben M\'hidi, Blida'},
    {'nom': 'Hamdi', 'prenom': 'Youcef', 'email': 'youcef.hamdi@email.dz', 'telephone': '0555789012', 'adresse': 'Avenue de l\'ALN, Sétif'},
    {'nom': 'Mekki', 'prenom': 'Amina', 'email': 'amina.mekki@email.dz', 'telephone': '0666890123', 'adresse': 'Rue de la République, Tlemcen'},
    {'nom': 'Saidi', 'prenom': 'Rachid', 'email': 'rachid.saidi@email.dz', 'telephone': '0777901234', 'adresse': 'Boulevard Zighoud Youcef, Batna'},
    {'nom': 'Djaballah', 'prenom': 'Leila', 'email': 'leila.djaballah@email.dz', 'telephone': '0555012345', 'adresse': 'Rue Emir Abdelkader, Béjaïa'},
    {'nom': 'Meziane', 'prenom': 'Sofiane', 'email': 'sofiane.meziane@email.dz', 'telephone': '0666123457', 'adresse': 'Avenue Houari Boumediene, Tizi Ouzou'},
    {'nom': 'Boudiaf', 'prenom': 'Samira', 'email': 'samira.boudiaf@email.dz', 'telephone': '0777234568', 'adresse': 'Rue du 8 Mai 1945, Skikda'},
    {'nom': 'Taleb', 'prenom': 'Hichem', 'email': 'hichem.taleb@email.dz', 'telephone': '0555345679', 'adresse': 'Place de la Victoire, Mostaganem'},
    {'nom': 'Rahmouni', 'prenom': 'Yasmine', 'email': 'yasmine.rahmouni@email.dz', 'telephone': '0666456780', 'adresse': 'Boulevard de la Soummam, Bordj Bou Arreridj'},
    {'nom': 'Lahmar', 'prenom': 'Bilal', 'email': 'bilal.lahmar@email.dz', 'telephone': '0777567891', 'adresse': 'Rue Ahmed Bey, Médéa'},
]

print("Création de clients non assignés...\n")
print("="*60)

created_count = 0
for client_data in clients_data:
    # Vérifier si le client existe déjà
    existing = Client.objects.filter(
        nom=client_data['nom'],
        prenom=client_data['prenom']
    ).first()

    if existing:
        print(f"⚠️  Client existe déjà: {client_data['nom']} {client_data['prenom']}")
        continue

    # Créer le client
    client = Client.objects.create(**client_data)
    created_count += 1
    print(f"✅ Client créé: {client.nom} {client.prenom} - {client.telephone}")

print("="*60)
print(f"\n✅ {created_count} clients créés avec succès!")

# Afficher le résumé
total_clients = Client.objects.count()
print(f"\n📊 RÉSUMÉ:")
print(f"   Total de clients dans la base: {total_clients}")

# Vérifier combien sont assignés
from API.distribution_models import LivreurDistribution
clients_assignes_count = 0
for livreur in LivreurDistribution.objects.all():
    clients_assignes_count += livreur.clients_assignes.count()

print(f"   Clients assignés à des livreurs: {clients_assignes_count}")
print(f"   Clients NON assignés: {total_clients - clients_assignes_count}")
