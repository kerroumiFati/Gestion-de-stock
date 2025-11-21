"""
Script pour verifier le filtrage par company
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.models import Warehouse, Client, Company
from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 70)
print("VERIFICATION DU FILTRAGE PAR COMPANY (TENANT)")
print("=" * 70)

# Recuperer tous les utilisateurs
users = User.objects.filter(is_active=True, is_staff=True)[:5]

if not users.exists():
    print("\nAucun utilisateur admin trouve!")
else:
    for user in users:
        print(f"\nUtilisateur: {user.username}")

        # Verifier la company de l'utilisateur
        if hasattr(user, 'company'):
            company = user.company
            print(f"  Company: {company.name} (ID: {company.id})")

            # Compter les entrepots de cette company
            entrepots_company = Warehouse.objects.filter(company=company)
            print(f"  Entrepots de cette company: {entrepots_company.count()}")

            # Compter les clients de cette company
            clients_company = Client.objects.filter(company=company)
            print(f"  Clients de cette company: {clients_company.count()}")
        else:
            print(f"  Pas de company associee!")

# Verifier toutes les companies
print("\n" + "=" * 70)
print("TOUTES LES COMPANIES")
print("=" * 70)

companies = Company.objects.all()
print(f"\nTotal companies: {companies.count()}")

for company in companies:
    entrepots_count = Warehouse.objects.filter(company=company).count()
    clients_count = Client.objects.filter(company=company).count()
    print(f"\n{company.name} (ID: {company.id})")
    print(f"  - Entrepots: {entrepots_count}")
    print(f"  - Clients: {clients_count}")

# Verifier les entrepots sans company
print("\n" + "=" * 70)
print("ENTREPOTS SANS COMPANY")
print("=" * 70)

entrepots_sans_company = Warehouse.objects.filter(company__isnull=True)
print(f"\nTotal: {entrepots_sans_company.count()}")
if entrepots_sans_company.count() > 0:
    for e in entrepots_sans_company:
        print(f"  - {e.code} - {e.name}")

# Verifier les clients sans company
print("\n" + "=" * 70)
print("CLIENTS SANS COMPANY")
print("=" * 70)

clients_sans_company = Client.objects.filter(company__isnull=True)
print(f"\nTotal: {clients_sans_company.count()}")
if clients_sans_company.count() > 0:
    for c in clients_sans_company[:10]:
        print(f"  - {c.nom} {c.prenom}")

print("\n" + "=" * 70)
