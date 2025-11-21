"""
Script pour creer ou mettre a jour les profils utilisateurs avec la company par defaut
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.models import Company, UserProfile
from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 70)
print("CREATION/MISE A JOUR DES PROFILS UTILISATEURS")
print("=" * 70)

# Recuperer la company par defaut
try:
    company = Company.objects.get(id=1)
    print(f"\nCompany par defaut: {company.name} (ID: {company.id})")
except Company.DoesNotExist:
    print("\nERREUR: Company par defaut (ID=1) non trouvee!")
    exit(1)

# Parcourir tous les utilisateurs actifs
users = User.objects.filter(is_active=True)
print(f"\nUtilisateurs actifs: {users.count()}")

created_count = 0
updated_count = 0

for user in users:
    # Verifier si l'utilisateur a un profil
    if hasattr(user, 'profile'):
        # Mettre a jour le profil si pas de company
        if user.profile.company is None:
            user.profile.company = company
            user.profile.save()
            print(f"  [MAJ] {user.username} -> {company.name}")
            updated_count += 1
        else:
            print(f"  [OK]  {user.username} -> {user.profile.company.name}")
    else:
        # Creer un profil avec la company par defaut
        profile = UserProfile.objects.create(
            user=user,
            company=company
        )
        print(f"  [NEW] {user.username} -> {company.name}")
        created_count += 1

print("\n" + "=" * 70)
print("RESUME")
print("=" * 70)
print(f"\nProfils crees: {created_count}")
print(f"Profils mis a jour: {updated_count}")
print(f"\nTotal utilisateurs avec company: {UserProfile.objects.filter(company=company).count()}")

print("\n" + "=" * 70)
print("TERMINE!")
print("=" * 70)
print("\nActualisez la page web et reconnectez-vous pour que les changements prennent effet.")
