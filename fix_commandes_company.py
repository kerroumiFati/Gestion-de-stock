"""
Script pour corriger les commandes clients sans company assignée
"""
import os
import sys
import django

# Configurer Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from API.distribution_models import CommandeClient
from API.models import Company

def fix_commandes_sans_company():
    """Corrige les commandes qui n'ont pas de company assignée"""

    # Trouver les commandes sans company
    commandes_sans_company = CommandeClient.objects.filter(company__isnull=True)
    count = commandes_sans_company.count()

    print(f"Commandes sans company: {count}")

    if count == 0:
        print("Aucune commande à corriger!")
        return

    # Récupérer la company par défaut
    default_company = Company.objects.first()
    if not default_company:
        print("ERREUR: Aucune company trouvée dans la base de données!")
        return

    print(f"Company par défaut: {default_company.name} (ID: {default_company.id})")

    # Corriger chaque commande
    fixed_count = 0
    for commande in commandes_sans_company:
        # Essayer d'utiliser la company du client
        if commande.client and hasattr(commande.client, 'company') and commande.client.company:
            commande.company = commande.client.company
            print(f"  - Commande {commande.reference}: company assignée depuis le client ({commande.client.company.name})")
        else:
            # Sinon utiliser la company par défaut
            commande.company = default_company
            print(f"  - Commande {commande.reference}: company par défaut assignée ({default_company.name})")

        commande.save(update_fields=['company'])
        fixed_count += 1

    print(f"\n{fixed_count} commande(s) corrigée(s) avec succès!")

def show_commandes_status():
    """Affiche le statut des commandes"""
    total = CommandeClient.objects.count()
    with_company = CommandeClient.objects.exclude(company__isnull=True).count()
    without_company = CommandeClient.objects.filter(company__isnull=True).count()

    print("\n=== Statut des commandes ===")
    print(f"Total: {total}")
    print(f"Avec company: {with_company}")
    print(f"Sans company: {without_company}")

    # Afficher par company
    print("\nPar company:")
    for company in Company.objects.all():
        count = CommandeClient.objects.filter(company=company).count()
        print(f"  - {company.name}: {count} commande(s)")

    # Commandes sans company
    if without_company > 0:
        print(f"\n  - (Sans company): {without_company} commande(s)")

if __name__ == '__main__':
    print("=== Correction des commandes sans company ===\n")
    show_commandes_status()

    response = input("\nVoulez-vous corriger les commandes sans company? (o/n): ")
    if response.lower() in ['o', 'oui', 'y', 'yes']:
        fix_commandes_sans_company()
        show_commandes_status()
    else:
        print("Opération annulée.")
