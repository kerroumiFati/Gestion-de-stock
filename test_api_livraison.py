"""
Test de l'API de livraison de commande avec ajustement de quantités
Simule exactement ce que fait l'application mobile
"""
import os
import sys
import django
import requests
import json

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.distribution_models import CommandeClient, LigneCommandeClient
from API.models import Client, Produit
from decimal import Decimal

def test_livraison_api():
    print("=" * 80)
    print("TEST API - LIVRAISON AVEC AJUSTEMENT DE QUANTITÉS")
    print("=" * 80)
    print()

    # 1. Créer une commande de test
    print("1. Création d'une commande de test...")

    # Récupérer un client et des produits
    client = Client.objects.first()
    produits = Produit.objects.all()[:2]  # 2 produits

    if not client or produits.count() < 2:
        print("❌ Pas assez de données (besoin d'au moins 1 client et 2 produits)")
        return

    # Créer la commande
    from API.distribution_models import LivreurDistribution
    livreur = LivreurDistribution.objects.first()

    if not livreur:
        print("❌ Aucun livreur trouvé")
        return

    commande = CommandeClient.objects.create(
        reference=f"TEST-API-{CommandeClient.objects.count() + 1}",
        client=client,
        livreur=livreur,
        statut='ready',
        montant_total_ht=Decimal('0'),
        montant_total_ttc=Decimal('0')
    )

    # Créer les lignes
    ligne1 = LigneCommandeClient.objects.create(
        commande=commande,
        produit=produits[0],
        quantite=Decimal('5'),
        prix_unitaire_ht=Decimal('100'),
        taux_tva=Decimal('0')
    )

    ligne2 = LigneCommandeClient.objects.create(
        commande=commande,
        produit=produits[1],
        quantite=Decimal('3'),
        prix_unitaire_ht=Decimal('50'),
        taux_tva=Decimal('0')
    )

    # Calculer les totaux initiaux
    commande.calculer_totaux()
    commande.refresh_from_db()

    print(f"✅ Commande créée: {commande.reference} (ID: {commande.id})")
    print(f"   Ligne 1: {produits[0].designation} - Qté: 5 x 100 = 500 DZD")
    print(f"   Ligne 2: {produits[1].designation} - Qté: 3 x 50 = 150 DZD")
    print(f"   Total initial: {commande.montant_total_ttc:.2f} DZD")
    print()

    # 2. Simuler la requête PATCH de l'application mobile
    print("2. Simulation de la requête PATCH (livraison avec ajustement)...")
    print("   Ajustement: Ligne 1 -> Qté 2 (au lieu de 5)")
    print("   Ajustement: Ligne 2 -> Qté 1 (au lieu de 3)")
    print()

    # Données envoyées par le mobile (comme dans les logs)
    payload = {
        'statut': 'delivered',
        'date_livraison_reelle': '2025-12-26T15:00:00Z',
        'lignes': [
            {
                'produit': produits[0].id,
                'quantite': 2,  # Ajusté de 5 à 2
                'prix_unitaire': 100,
                'taux_tva': 0
            },
            {
                'produit': produits[1].id,
                'quantite': 1,  # Ajusté de 3 à 1
                'prix_unitaire': 50,
                'taux_tva': 0
            }
        ]
    }

    print("   Payload envoyé:")
    print(json.dumps(payload, indent=2))
    print()

    # Envoyer la requête PATCH via l'API interne Django
    from django.test import RequestFactory
    from API.distribution_views import CommandeClientViewSet
    from rest_framework.test import force_authenticate
    from django.contrib.auth import get_user_model

    factory = RequestFactory()
    request = factory.patch(
        f'/API/distribution/commandes/{commande.id}/',
        data=json.dumps(payload),
        content_type='application/json'
    )

    # Authentifier la requête avec un utilisateur
    User = get_user_model()
    user = User.objects.first()
    if user:
        force_authenticate(request, user=user)

    # Appeler la vue
    view = CommandeClientViewSet.as_view({'patch': 'partial_update'})
    response = view(request, pk=commande.id)

    print(f"3. Réponse de l'API: Status {response.status_code}")
    print()

    # 4. Vérifier les résultats
    print("4. Vérification des résultats dans la base de données...")
    print()

    commande.refresh_from_db()
    ligne1.refresh_from_db()
    ligne2.refresh_from_db()

    # Calcul attendu
    total_attendu = (2 * 100) + (1 * 50)  # 200 + 50 = 250

    print(f"Ligne 1: Qté={ligne1.quantite}, HT={ligne1.montant_ht}, TTC={ligne1.montant_ttc}")
    print(f"Ligne 2: Qté={ligne2.quantite}, HT={ligne2.montant_ht}, TTC={ligne2.montant_ttc}")
    print()
    print(f"Total attendu: {total_attendu:.2f} DZD")
    print(f"Total stocké:  {commande.montant_total_ttc:.2f} DZD")
    print()

    # Vérification
    if abs(commande.montant_total_ttc - Decimal(str(total_attendu))) < Decimal('0.01'):
        print("✅ TEST RÉUSSI! Les totaux sont corrects!")
        print()
        print("=" * 80)
        print("Le problème est RÉSOLU!")
        print("=" * 80)
    else:
        print(f"❌ TEST ÉCHOUÉ! Différence: {abs(commande.montant_total_ttc - Decimal(str(total_attendu))):.2f} DZD")
        print()
        print("=" * 80)
        print("Le problème PERSISTE - Le serveur Django doit être redémarré")
        print("=" * 80)

    # Nettoyer la commande de test
    print()
    reponse = input("Voulez-vous supprimer la commande de test? (oui/non): ")
    if reponse.lower() in ['oui', 'o', 'yes', 'y']:
        commande.delete()
        print("✅ Commande de test supprimée")

if __name__ == '__main__':
    test_livraison_api()
