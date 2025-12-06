"""
Script pour assigner une company aux produits et catégories qui n'en ont pas.
Exécuter avec: python manage.py shell < fix_company_data.py
Ou: python fix_company_data.py (si Django est configuré)
"""
import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from API.models import Company, Categorie, Produit, Client, Fournisseur, UserProfile, Warehouse
from django.contrib.auth.models import User

def fix_data():
    # Vérifier s'il existe une company
    companies = Company.objects.all()

    if not companies.exists():
        print("Aucune entreprise trouvée. Création d'une entreprise par défaut...")
        company = Company.objects.create(
            name="Entreprise Principale",
            code="MAIN",
            email="contact@entreprise.com",
            is_active=True
        )
        print(f"Entreprise créée: {company}")
    else:
        company = companies.first()
        print(f"Entreprise existante: {company}")

    # Assigner la company aux catégories sans company
    categories_sans_company = Categorie.objects.filter(company__isnull=True)
    count_cat = categories_sans_company.count()
    if count_cat > 0:
        categories_sans_company.update(company=company)
        print(f"{count_cat} catégorie(s) mise(s) à jour avec la company '{company.name}'")
    else:
        print("Toutes les catégories ont déjà une company")

    # Assigner la company aux produits sans company
    produits_sans_company = Produit.objects.filter(company__isnull=True)
    count_prod = produits_sans_company.count()
    if count_prod > 0:
        produits_sans_company.update(company=company)
        print(f"{count_prod} produit(s) mis à jour avec la company '{company.name}'")
    else:
        print("Tous les produits ont déjà une company")

    # Assigner la company aux clients sans company
    try:
        clients_sans_company = Client.objects.filter(company__isnull=True)
        count_cli = clients_sans_company.count()
        if count_cli > 0:
            clients_sans_company.update(company=company)
            print(f"{count_cli} client(s) mis à jour avec la company '{company.name}'")
        else:
            print("Tous les clients ont déjà une company")
    except Exception as e:
        print(f"Clients: {e}")

    # Assigner la company aux fournisseurs sans company
    try:
        fournisseurs_sans_company = Fournisseur.objects.filter(company__isnull=True)
        count_four = fournisseurs_sans_company.count()
        if count_four > 0:
            fournisseurs_sans_company.update(company=company)
            print(f"{count_four} fournisseur(s) mis à jour avec la company '{company.name}'")
        else:
            print("Tous les fournisseurs ont déjà une company")
    except Exception as e:
        print(f"Fournisseurs: {e}")

    # Assigner la company aux entrepôts (warehouses) sans company
    try:
        warehouses_sans_company = Warehouse.objects.filter(company__isnull=True)
        count_wh = warehouses_sans_company.count()
        if count_wh > 0:
            warehouses_sans_company.update(company=company)
            print(f"{count_wh} entrepôt(s) mis à jour avec la company '{company.name}'")
        else:
            print("Tous les entrepôts ont déjà une company")
    except Exception as e:
        print(f"Entrepôts: {e}")

    # Vérifier les utilisateurs sans profil
    users_sans_profil = User.objects.filter(profile__isnull=True)
    count_users = users_sans_profil.count()
    if count_users > 0:
        print(f"\n{count_users} utilisateur(s) sans profil trouvé(s):")
        for user in users_sans_profil:
            print(f"  - {user.username}")
            UserProfile.objects.create(user=user, company=company, role='admin')
            print(f"    -> Profil créé avec company '{company.name}'")
    else:
        print("\nTous les utilisateurs ont un profil")

    print("\n=== Résumé ===")
    print(f"Catégories totales: {Categorie.objects.count()}")
    print(f"Produits totaux: {Produit.objects.count()}")
    print(f"Produits actifs: {Produit.objects.filter(is_active=True).count()}")
    print(f"Catégories actives: {Categorie.objects.filter(is_active=True).count()}")

if __name__ == '__main__':
    fix_data()
