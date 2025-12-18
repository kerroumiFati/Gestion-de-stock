# -*- coding: utf-8 -*-
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from datetime import date, timedelta
from decimal import Decimal
from API.models import CodePrix, TypePrix, PrixProduit, Produit, Client, Currency

print("\n" + "="*60)
print("GENERATION DE DONNEES DE TEST - PROMOTIONS")
print("="*60)

# ETAPE 1: Creer le code prix
print("\nETAPE 1 : Creation du Code Prix")
print("-"*60)

code_prix, created = CodePrix.objects.get_or_create(
    code='PROMO2025',
    defaults={
        'libelle': 'Promotion Janvier 2025',
        'description': 'Prix promotionnels pour janvier',
        'date_debut': date.today(),
        'date_fin': date.today() + timedelta(days=30),
        'is_active': True,
        'is_default': False,
        'ordre': 1
    }
)

if created:
    print(f"[OK] Code prix cree : {code_prix.code}")
else:
    code_prix.is_active = True
    code_prix.date_debut = date.today()
    code_prix.date_fin = date.today() + timedelta(days=30)
    code_prix.save()
    print(f"[OK] Code prix mis a jour : {code_prix.code}")

print(f"     Periode : {code_prix.date_debut} -> {code_prix.date_fin}")
print(f"     Actif : {code_prix.is_active}")

# ETAPE 2: Creer les types de prix
print("\nETAPE 2 : Creation des Types de Prix")
print("-"*60)

types_prix = {}
for code_name, libelle in [('DETAIL', 'Prix de detail'), ('SUPERETTE', 'Prix superette'), ('GROS', 'Prix de gros')]:
    tp, created = TypePrix.objects.get_or_create(
        code=code_name,
        defaults={
            'libelle': libelle,
            'is_active': True,
            'is_default': (code_name == 'DETAIL')
        }
    )
    types_prix[code_name] = tp
    status = "cree" if created else "existant"
    print(f"[OK] Type {code_name} : {status}")

# ETAPE 3: Creer les prix promotionnels
print("\nETAPE 3 : Creation des Prix Promotionnels")
print("-"*60)

produits = Produit.objects.all()[:10]

if not produits.exists():
    print("[ERREUR] Aucun produit trouve")
else:
    print(f"[OK] {produits.count()} produits trouves\n")

    currency = Currency.objects.first()
    created_count = 0

    reductions = {
        'DETAIL': 0.10,      # -10%
        'SUPERETTE': 0.15,   # -15%
        'GROS': 0.20         # -20%
    }

    for produit in produits:
        prix_base = float(produit.prixU)
        print(f"  {produit.designation[:40]} (Base: {prix_base:.2f} DZD)")

        for type_code, reduction in reductions.items():
            type_prix = types_prix[type_code]
            prix_promo = Decimal(str(prix_base * (1 - reduction)))

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

            reduction_pct = int(reduction*100)
            print(f"     [{type_code}] {prix_promo:.2f} DZD (-{reduction_pct}%)")

    print(f"\n[OK] {created_count} prix promotionnels crees")

# ETAPE 4: Assigner types de prix aux clients
print("\nETAPE 4 : Assignation des Types de Prix aux Clients")
print("-"*60)

clients = Client.objects.all()[:10]

if not clients.exists():
    print("[ERREUR] Aucun client trouve")
else:
    print(f"[OK] {clients.count()} clients trouves\n")

    updated_count = 0
    type_list = [types_prix['DETAIL'], types_prix['SUPERETTE'], types_prix['GROS']]

    for i, client in enumerate(clients):
        type_prix = type_list[i % 3]

        if client.type_prix != type_prix:
            client.type_prix = type_prix
            client.save()
            updated_count += 1

        print(f"  {client.nom} {client.prenom} -> {type_prix.code}")

    print(f"\n[OK] {updated_count} clients mis a jour")

# RESUME
print("\n" + "="*60)
print("RESUME DE LA CONFIGURATION")
print("="*60)

print(f"\nCode Prix Actif :")
print(f"  Code      : {code_prix.code}")
print(f"  Periode   : {code_prix.date_debut} -> {code_prix.date_fin}")
print(f"  Statut    : {'ACTIF' if code_prix.is_active else 'INACTIF'}")

nb_prix = PrixProduit.objects.filter(code_prix=code_prix, is_active=True).count()
print(f"\nPrix Promotionnels :")
print(f"  Total     : {nb_prix} prix configures")

for type_code in ['DETAIL', 'SUPERETTE', 'GROS']:
    type_prix = types_prix.get(type_code)
    if type_prix:
        nb = PrixProduit.objects.filter(
            code_prix=code_prix,
            type_prix=type_prix,
            is_active=True
        ).count()
        print(f"  {type_code:12s}: {nb} produits")

print(f"\nClients avec Type de Prix :")
for type_code in ['DETAIL', 'SUPERETTE', 'GROS']:
    type_prix = types_prix.get(type_code)
    if type_prix:
        nb = Client.objects.filter(type_prix=type_prix).count()
        print(f"  {type_code:12s}: {nb} clients")

nb_sans_type = Client.objects.filter(type_prix__isnull=True).count()
print(f"  Sans type   : {nb_sans_type} clients")

print("\n" + "="*60)
print("CONFIGURATION TERMINEE")
print("="*60)
print("\nProchaines etapes :")
print("  1. Testez l'API : http://localhost:8000/API/livreurs/1/stock_van/")
print("  2. Synchronisez l'application mobile")
print("  3. Selectionnez un client dans l'ecran Vente")
print("  4. Verifiez que les prix promotionnels s'affichent\n")
