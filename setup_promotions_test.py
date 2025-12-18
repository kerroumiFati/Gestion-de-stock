#!/usr/bin/env python
"""
Script de génération de données de test pour le système de promotions
Crée automatiquement :
- 1 CodePrix actif
- Prix promotionnels pour les produits existants
- Assigne des type_prix aux clients
"""

import os
import sys
import django
from datetime import date, timedelta
from decimal import Decimal

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GestionStock.settings')
django.setup()

from API.models import CodePrix, TypePrix, PrixProduit, Produit, Client, Currency

def create_code_prix():
    """Crée un code prix promotionnel actif"""
    print("\n" + "="*60)
    print("📋 ÉTAPE 1 : Création du Code Prix")
    print("="*60)

    # Vérifier si existe déjà
    code_prix, created = CodePrix.objects.get_or_create(
        code='PROMO2025',
        defaults={
            'libelle': 'Promotion Janvier 2025',
            'description': 'Prix promotionnels pour le mois de janvier',
            'date_debut': date.today(),
            'date_fin': date.today() + timedelta(days=30),
            'is_active': True,
            'is_default': False,
            'ordre': 1
        }
    )

    if created:
        print(f"✅ Code prix créé : {code_prix.code} - {code_prix.libelle}")
    else:
        print(f"ℹ️  Code prix existant : {code_prix.code}")
        # Mettre à jour pour être sûr qu'il est actif
        code_prix.is_active = True
        code_prix.date_debut = date.today()
        code_prix.date_fin = date.today() + timedelta(days=30)
        code_prix.save()
        print(f"✅ Code prix mis à jour et activé")

    print(f"   📅 Période : {code_prix.date_debut} → {code_prix.date_fin}")
    print(f"   ✓ Actif : {code_prix.is_active}")

    return code_prix


def create_prix_produits(code_prix):
    """Crée des prix promotionnels pour les produits"""
    print("\n" + "="*60)
    print("💰 ÉTAPE 2 : Création des Prix Promotionnels")
    print("="*60)

    # Récupérer les types de prix
    types_prix = {
        'DETAIL': TypePrix.objects.filter(code='DETAIL').first(),
        'SUPERETTE': TypePrix.objects.filter(code='SUPERETTE').first(),
        'GROS': TypePrix.objects.filter(code='GROS').first()
    }

    # Vérifier que les types existent
    for code, type_prix in types_prix.items():
        if not type_prix:
            print(f"⚠️  Type de prix '{code}' non trouvé, création...")
            type_prix = TypePrix.objects.create(
                code=code,
                libelle=f'Prix de {code.lower()}',
                is_active=True,
                is_default=(code == 'DETAIL')
            )
            types_prix[code] = type_prix

    # Récupérer les 10 premiers produits
    produits = Produit.objects.all()[:10]

    if not produits.exists():
        print("❌ Aucun produit trouvé dans la base de données")
        print("   Veuillez d'abord créer des produits")
        return 0

    print(f"\n📦 {produits.count()} produit(s) trouvé(s)\n")

    # Devise par défaut
    currency = Currency.objects.first()

    created_count = 0

    for produit in produits:
        prix_base = float(produit.prixU)

        print(f"   {produit.designation} (Prix de base: {prix_base:.2f} DZD)")

        # Créer 3 prix : DETAIL (-10%), SUPERETTE (-15%), GROS (-20%)
        reductions = {
            'DETAIL': 0.10,      # -10%
            'SUPERETTE': 0.15,   # -15%
            'GROS': 0.20         # -20%
        }

        for type_code, reduction in reductions.items():
            type_prix = types_prix[type_code]
            if not type_prix:
                continue

            prix_promo = Decimal(str(prix_base * (1 - reduction)))

            # Créer ou mettre à jour
            prix_produit, created = PrixProduit.objects.update_or_create(
                produit=produit,
                code_prix=code_prix,
                type_prix=type_prix,
                defaults={
                    'prix': prix_promo,
                    'quantite_min': 1,
                    'currency': currency,
                    'is_active': True
                }
            )

            if created:
                created_count += 1
                print(f"      ✓ {type_code}: {prix_promo:.2f} DZD (-{int(reduction*100)}%)")
            else:
                print(f"      ↻ {type_code}: {prix_promo:.2f} DZD (mis à jour)")

    print(f"\n✅ {created_count} prix promotionnels créés/mis à jour")
    return created_count


def assign_type_prix_to_clients():
    """Assigne des type_prix aux clients de test"""
    print("\n" + "="*60)
    print("👥 ÉTAPE 3 : Assignation des Types de Prix aux Clients")
    print("="*60)

    # Récupérer les types de prix
    type_detail = TypePrix.objects.filter(code='DETAIL').first()
    type_superette = TypePrix.objects.filter(code='SUPERETTE').first()
    type_gros = TypePrix.objects.filter(code='GROS').first()

    # Récupérer les 10 premiers clients
    clients = Client.objects.all()[:10]

    if not clients.exists():
        print("❌ Aucun client trouvé dans la base de données")
        print("   Veuillez d'abord créer des clients")
        return 0

    print(f"\n👤 {clients.count()} client(s) trouvé(s)\n")

    # Répartir les clients
    updated_count = 0
    types = [type_detail, type_superette, type_gros]

    for i, client in enumerate(clients):
        # Alterner les types de prix
        type_prix = types[i % 3]

        if client.type_prix != type_prix:
            client.type_prix = type_prix
            client.save()
            updated_count += 1
            print(f"   ✓ {client.nom} {client.prenom} → {type_prix.code}")
        else:
            print(f"   = {client.nom} {client.prenom} → {type_prix.code} (déjà assigné)")

    print(f"\n✅ {updated_count} client(s) mis à jour")
    return updated_count


def display_summary(code_prix):
    """Affiche un résumé des données créées"""
    print("\n" + "="*60)
    print("📊 RÉSUMÉ DE LA CONFIGURATION")
    print("="*60)

    print(f"\n🏷️  Code Prix Actif :")
    print(f"   Code      : {code_prix.code}")
    print(f"   Libellé   : {code_prix.libelle}")
    print(f"   Période   : {code_prix.date_debut} → {code_prix.date_fin}")
    print(f"   Statut    : {'✅ Actif' if code_prix.is_active else '❌ Inactif'}")

    # Compter les prix produits
    nb_prix = PrixProduit.objects.filter(code_prix=code_prix, is_active=True).count()
    print(f"\n💰 Prix Promotionnels :")
    print(f"   Total     : {nb_prix} prix configurés")

    # Par type
    for type_code in ['DETAIL', 'SUPERETTE', 'GROS']:
        type_prix = TypePrix.objects.filter(code=type_code).first()
        if type_prix:
            nb = PrixProduit.objects.filter(
                code_prix=code_prix,
                type_prix=type_prix,
                is_active=True
            ).count()
            print(f"   {type_code:12s}: {nb} produits")

    # Compter les clients par type
    print(f"\n👥 Clients avec Type de Prix :")
    for type_code in ['DETAIL', 'SUPERETTE', 'GROS']:
        type_prix = TypePrix.objects.filter(code=type_code).first()
        if type_prix:
            nb = Client.objects.filter(type_prix=type_prix).count()
            print(f"   {type_code:12s}: {nb} clients")

    nb_sans_type = Client.objects.filter(type_prix__isnull=True).count()
    print(f"   Sans type   : {nb_sans_type} clients")

    print("\n" + "="*60)
    print("✅ CONFIGURATION TERMINÉE")
    print("="*60)
    print("\n📱 Prochaines étapes :")
    print("   1. Testez l'API : http://localhost:8000/API/livreurs/1/stock_van/")
    print("   2. Synchronisez l'application mobile")
    print("   3. Sélectionnez un client dans l'écran Vente")
    print("   4. Vérifiez que les prix promotionnels s'affichent avec le badge 🏷️ PROMO")
    print("")


def main():
    """Fonction principale"""
    print("\n" + "="*60)
    print("🚀 GÉNÉRATION DE DONNÉES DE TEST - PROMOTIONS")
    print("="*60)

    try:
        # Étape 1 : Créer le code prix
        code_prix = create_code_prix()

        # Étape 2 : Créer les prix promotionnels
        create_prix_produits(code_prix)

        # Étape 3 : Assigner les types de prix aux clients
        assign_type_prix_to_clients()

        # Afficher le résumé
        display_summary(code_prix)

    except Exception as e:
        print(f"\n❌ ERREUR : {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
