"""
Script pour ajouter le champ company aux modeles de distribution
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from django.db import connection

print("=" * 80)
print("AJOUT DU CHAMP company AUX MODELES DE DISTRIBUTION")
print("=" * 80)

# Tables a modifier
tables_to_update = [
    ('distribution_tournee_mobile', 'TourneeMobile'),
    ('distribution_arret_tournee', 'ArretTourneeMobile'),
    ('distribution_vente_tournee', 'VenteTourneeMobile'),
    ('distribution_ligne_vente_tournee', 'LigneVenteTourneeMobile'),
    ('distribution_rapport_caisse', 'RapportCaisseMobile'),
    ('distribution_bon_livraison_van', 'BonLivraisonVan'),
    ('distribution_ligne_bon_livraison_van', 'LigneBonLivraisonVan'),
    ('distribution_livreur', 'LivreurDistribution'),
    ('distribution_ligne_commande_client', 'LigneCommandeClient'),
]

# Recuperer la company par defaut (ID=1)
company_id = 1

with connection.cursor() as cursor:
    for table_name, model_name in tables_to_update:
        print(f"\n{model_name} ({table_name}):")

        # Verifier si la table existe
        cursor.execute(f"""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='{table_name}'
        """)

        if not cursor.fetchone():
            print(f"  ⚠️  Table {table_name} n'existe pas")
            continue

        # Verifier si le champ company existe deja
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in cursor.fetchall()]

        if 'company_id' in columns:
            print(f"  ✓ Champ company_id existe deja")

            # Mettre a jour les lignes NULL
            cursor.execute(f"""
                UPDATE {table_name}
                SET company_id = {company_id}
                WHERE company_id IS NULL
            """)
            updated = cursor.rowcount
            if updated > 0:
                print(f"    → {updated} ligne(s) mise(s) a jour")
        else:
            print(f"  ⚠️  Champ company_id n'existe pas - Creation requise via migration Django")
            print(f"    → Utilisez: python manage.py makemigrations")

print("\n" + "=" * 80)
print("TERMINE!")
print("=" * 80)
print("\nPour appliquer completement:")
print("  1. Ajoutez 'company = models.ForeignKey(Company, ...)' aux modeles")
print("  2. Executez: python manage.py makemigrations")
print("  3. Executez: python manage.py migrate")
