"""
Script pour assigner la company par defaut a tous les entrepots, clients et utilisateurs
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.models import Warehouse, Client, Company
from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 70)
print("ASSIGNATION DE LA COMPANY PAR DEFAUT")
print("=" * 70)

# Recuperer ou creer la company par defaut
company, created = Company.objects.get_or_create(
    id=1,
    defaults={
        'name': 'Entreprise Par Defaut',
        'is_active': True
    }
)

if created:
    print(f"\nCompany creee: {company.name}")
else:
    print(f"\nCompany utilisee: {company.name} (ID: {company.id})")

# 1. Assigner la company aux entrepots sans company
print("\n1. ENTREPOTS")
print("-" * 70)
entrepots_sans_company = Warehouse.objects.filter(company__isnull=True)
print(f"Entrepots sans company: {entrepots_sans_company.count()}")

if entrepots_sans_company.count() > 0:
    count = entrepots_sans_company.update(company=company)
    print(f"  -> {count} entrepots mis a jour")

# 2. Assigner la company aux clients sans company
print("\n2. CLIENTS")
print("-" * 70)
clients_sans_company = Client.objects.filter(company__isnull=True)
print(f"Clients sans company: {clients_sans_company.count()}")

if clients_sans_company.count() > 0:
    count = clients_sans_company.update(company=company)
    print(f"  -> {count} clients mis a jour")

# 3. Utilisateurs - Verifier si le modele User a un champ company
print("\n3. UTILISATEURS")
print("-" * 70)
user_fields = [f.name for f in User._meta.get_fields()]
if 'company' in user_fields:
    users_sans_company = User.objects.filter(is_active=True, company__isnull=True)
    print(f"Utilisateurs actifs sans company: {users_sans_company.count()}")

    if users_sans_company.count() > 0:
        for user in users_sans_company:
            user.company = company
            user.save()
            print(f"  -> {user.username} assigne a {company.name}")
else:
    print(f"Le modele User n'a pas de champ 'company'")
    print(f"  -> Skipping user assignment")

# Verification finale
print("\n" + "=" * 70)
print("VERIFICATION FINALE")
print("=" * 70)

print(f"\nCompany: {company.name}")
print(f"  - Entrepots: {Warehouse.objects.filter(company=company).count()}")
print(f"  - Clients: {Client.objects.filter(company=company).count()}")

print("\n" + "=" * 70)
print("TERMINE!")
print("=" * 70)
print("\nActualisez la page web et tout devrait fonctionner correctement.")
