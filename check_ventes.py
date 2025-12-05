import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.models import Vente, Company

# Compter toutes les ventes
total_ventes = Vente.objects.count()
print(f"Nombre total de ventes dans la base: {total_ventes}")

# Ventes sans company
ventes_sans_company = Vente.objects.filter(company__isnull=True)
count_no_company = ventes_sans_company.count()
print(f"Ventes sans company: {count_no_company}")

if count_no_company > 0:
    # Assigner la company DEFAULT
    default_company = Company.objects.get(code='DEFAULT')
    print(f"\nAssignation de la company '{default_company}' aux {count_no_company} ventes...")
    updated = ventes_sans_company.update(company=default_company)
    print(f"{updated} ventes mises à jour!")

# Vérification finale
print(f"\nAprès correction:")
print(f"  - Company DEFAULT: {Vente.objects.filter(company__code='DEFAULT').count()}")
print(f"  - Sans company: {Vente.objects.filter(company__isnull=True).count()}")
