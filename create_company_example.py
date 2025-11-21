"""
Script exemple pour créer une entreprise et assigner des utilisateurs
via le shell Django
"""

# Pour exécuter ce script :
# python manage.py shell < create_company_example.py

from django.contrib.auth import get_user_model
from API.models import Company, UserProfile

User = get_user_model()

# Exemple 1 : Créer un Hotel
print("=== Création d'une entreprise Hotel ===")
hotel = Company.objects.create(
    name="Hotel Bella Vista",
    code="HOTEL01",
    email="contact@bellavista.com",
    telephone="+212 5XX-XXXXXX",
    adresse="123 Avenue Mohamed V, Casablanca",
    tax_id="ICE000123456789",
    is_active=True
)
print(f"✓ Hotel créé : {hotel.name} ({hotel.code})")

# Exemple 2 : Créer un Restaurant
print("\n=== Création d'une entreprise Restaurant ===")
restaurant = Company.objects.create(
    name="Restaurant Le Gourmet",
    code="RESTO01",
    email="contact@legourmet.ma",
    telephone="+212 6XX-XXXXXX",
    adresse="456 Boulevard Zerktouni, Rabat",
    tax_id="ICE000987654321",
    is_active=True
)
print(f"✓ Restaurant créé : {restaurant.name} ({restaurant.code})")

# Exemple 3 : Assigner des utilisateurs
print("\n=== Assignation des utilisateurs ===")

# Créer ou récupérer un utilisateur pour l'hotel
hotel_user, created = User.objects.get_or_create(
    username="manager_hotel",
    defaults={
        'email': "manager@bellavista.com",
        'first_name': "Ahmed",
        'last_name': "Benali"
    }
)
if created:
    hotel_user.set_password("password123")  # Changez ce mot de passe !
    hotel_user.save()
    print(f"✓ Utilisateur créé : {hotel_user.username}")

# Créer le profil pour l'utilisateur hotel
hotel_profile, created = UserProfile.objects.get_or_create(
    user=hotel_user,
    defaults={
        'company': hotel,
        'role': 'admin'
    }
)
if created:
    print(f"✓ Profil créé : {hotel_user.username} → {hotel.name} (admin)")
else:
    print(f"! Profil existant : {hotel_user.username}")

# Créer ou récupérer un utilisateur pour le restaurant
resto_user, created = User.objects.get_or_create(
    username="manager_resto",
    defaults={
        'email': "manager@legourmet.ma",
        'first_name': "Fatima",
        'last_name': "Zahra"
    }
)
if created:
    resto_user.set_password("password123")  # Changez ce mot de passe !
    resto_user.save()
    print(f"✓ Utilisateur créé : {resto_user.username}")

# Créer le profil pour l'utilisateur restaurant
resto_profile, created = UserProfile.objects.get_or_create(
    user=resto_user,
    defaults={
        'company': restaurant,
        'role': 'admin'
    }
)
if created:
    print(f"✓ Profil créé : {resto_user.username} → {restaurant.name} (admin)")
else:
    print(f"! Profil existant : {resto_user.username}")

# Résumé
print("\n=== Résumé ===")
print(f"Entreprises créées : {Company.objects.count()}")
print(f"Utilisateurs avec profils : {UserProfile.objects.count()}")
print("\nEntreprises :")
for company in Company.objects.all():
    users_count = company.users.count()
    print(f"  - {company.name} ({company.code}) : {users_count} utilisateur(s)")

print("\n✅ Terminé !")
print("\nVous pouvez maintenant vous connecter avec :")
print("  - username: manager_hotel / password: password123")
print("  - username: manager_resto / password: password123")
print("\n⚠️  N'oubliez pas de changer les mots de passe en production !")
