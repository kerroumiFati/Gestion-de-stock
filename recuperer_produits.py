#!/usr/bin/env python
"""
Script pour récupérer les produits disparus
Affiche tous les produits et leur statut, puis permet de les réassigner à une société
Version améliorée avec gestion des contraintes UNIQUE
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.models import Produit, Company, UserProfile
from django.contrib.auth.models import User
from django.db import transaction

print("=" * 80)
print("RÉCUPÉRATION DES PRODUITS DISPARUS")
print("=" * 80)

# 1. Afficher toutes les sociétés
print("\n📋 SOCIÉTÉS DISPONIBLES:")
companies = Company.objects.all()
if companies.exists():
    for idx, company in enumerate(companies, 1):
        print(f"   {idx}. {company.name} ({company.code}) - Active: {company.is_active}")
else:
    print("   ⚠️ Aucune société trouvée!")
    print("   Créez une société avec: python setup_local_user.py")
    exit(1)

# 2. Afficher TOUS les produits (même inactifs, même sans société)
print("\n📦 TOUS LES PRODUITS (incluant inactifs et sans société):")
all_products = Produit.objects.all()
if all_products.exists():
    print(f"\n   Total: {all_products.count()} produits\n")
    for p in all_products:
        company_str = f"{p.company.name}" if p.company else "⚠️ AUCUNE SOCIÉTÉ"
        active_str = "✓ Actif" if p.is_active else "✗ Inactif"
        print(f"   [{p.id}] {p.reference} - {p.designation}")
        print(f"        Société: {company_str} | État: {active_str}")
        print()
else:
    print("   ⚠️ Aucun produit trouvé dans la base de données!")
    exit(0)

# 3. Trouver les produits problématiques
print("\n🔍 PRODUITS PROBLÉMATIQUES:")
produits_sans_company = Produit.objects.filter(company__isnull=True)
produits_inactifs = Produit.objects.filter(is_active=False)

if produits_sans_company.exists():
    print(f"\n   ⚠️ {produits_sans_company.count()} produit(s) SANS SOCIÉTÉ:")
    for p in produits_sans_company:
        print(f"      - [{p.id}] {p.reference} - {p.designation}")

if produits_inactifs.exists():
    print(f"\n   ⚠️ {produits_inactifs.count()} produit(s) INACTIF(S):")
    for p in produits_inactifs:
        company_str = f"{p.company.name}" if p.company else "AUCUNE"
        print(f"      - [{p.id}] {p.reference} - {p.designation} (Société: {company_str})")

if not produits_sans_company.exists() and not produits_inactifs.exists():
    print("   ✓ Tous les produits ont une société et sont actifs!")
    print("\n   Le problème vient probablement du cache du navigateur.")
    print("   Appuyez sur Ctrl+Shift+R pour forcer le rechargement.")
    exit(0)

# 4. ÉTAPE 1: Réactiver les produits inactifs (PRIORITAIRE)
print("\n" + "=" * 80)
print("ÉTAPE 1: RÉACTIVATION DES PRODUITS INACTIFS")
print("=" * 80)

if produits_inactifs.exists():
    print(f"\n⚠️ {produits_inactifs.count()} produit(s) inactif(s) trouvé(s).")
    print("Ces produits ont probablement été désactivés par erreur lors de modifications.")
    print("\nListe des produits à réactiver:")
    for p in produits_inactifs:
        company_str = f"{p.company.name}" if p.company else "AUCUNE SOCIÉTÉ"
        print(f"   - [{p.id}] {p.reference} - {p.designation} (Société: {company_str})")

    reponse_activer = input(f"\nVoulez-vous réactiver ces {produits_inactifs.count()} produit(s)? (o/n): ").strip().lower()
    if reponse_activer == 'o':
        count = produits_inactifs.update(is_active=True)
        print(f"   ✓ {count} produit(s) réactivé(s)")
        print("\n💡 Ces produits devraient maintenant apparaître dans votre interface!")
        print("   Rechargez la page avec Ctrl+Shift+R pour vider le cache.")
    else:
        print("   → Produits inactifs non réactivés")
else:
    print("\n   ✓ Aucun produit inactif à réactiver")

# 5. ÉTAPE 2: Gérer les produits sans société (avec gestion des conflits)
print("\n" + "=" * 80)
print("ÉTAPE 2: ATTRIBUTION DE SOCIÉTÉ AUX PRODUITS ORPHELINS")
print("=" * 80)

if produits_sans_company.exists():
    print(f"\n⚠️ {produits_sans_company.count()} produit(s) sans société trouvé(s).")

    # Choisir la société à assigner
    if companies.count() == 1:
        company = companies.first()
        print(f"\n✓ Utilisation de la seule société disponible: {company.name}")
    else:
        print("\nChoisissez la société à assigner aux produits:")
        for idx, comp in enumerate(companies, 1):
            print(f"   {idx}. {comp.name} ({comp.code})")

        choix = input("\nNuméro de la société: ").strip()
        try:
            company = companies[int(choix) - 1]
        except (ValueError, IndexError):
            print("❌ Choix invalide!")
            exit(1)

    print(f"\n📝 Attribution de la société '{company.name}' aux produits sans société...")

    # Traiter chaque produit individuellement pour gérer les conflits
    success_count = 0
    conflict_count = 0
    conflicts = []

    for p in produits_sans_company:
        # Vérifier si un produit avec la même référence existe déjà dans cette société
        existing = Produit.objects.filter(company=company, reference=p.reference).exclude(id=p.id).first()

        if existing:
            conflict_count += 1
            conflicts.append({
                'orphan': p,
                'existing': existing
            })
            print(f"   ⚠️ CONFLIT: Référence '{p.reference}' existe déjà dans {company.name}")
            print(f"      - Produit orphelin: [{p.id}] {p.reference} - {p.designation}")
            print(f"      - Produit existant: [{existing.id}] {existing.reference} - {existing.designation}")
        else:
            # Pas de conflit, on peut assigner la société
            p.company = company
            p.save()
            success_count += 1
            print(f"   ✓ [{p.id}] {p.reference} - {p.designation} → assigné à {company.name}")

    print(f"\n📊 Résultats:")
    print(f"   ✓ {success_count} produit(s) assigné(s) avec succès")
    if conflict_count > 0:
        print(f"   ⚠️ {conflict_count} conflit(s) détecté(s)")

        print("\n❓ Que faire avec les produits en conflit?")
        print("   1. Supprimer les produits orphelins (recommandé si doublons)")
        print("   2. Renommer les produits orphelins (ajouter suffixe -OLD)")
        print("   3. Supprimer les produits existants (DANGER!)")
        print("   4. Ignorer (laisser les orphelins sans société)")

        choix_conflit = input("\nVotre choix (1-4): ").strip()

        if choix_conflit == '1':
            print("\n🗑️ Suppression des produits orphelins en conflit...")
            for conf in conflicts:
                orphan = conf['orphan']
                orphan.delete()
                print(f"   ✓ Supprimé: [{orphan.id}] {orphan.reference} - {orphan.designation}")
            print(f"   ✓ {len(conflicts)} produit(s) orphelin(s) supprimé(s)")

        elif choix_conflit == '2':
            print("\n✏️ Renommage des produits orphelins...")
            for conf in conflicts:
                orphan = conf['orphan']
                old_ref = orphan.reference
                orphan.reference = f"{orphan.reference}-OLD"
                orphan.company = company
                orphan.save()
                print(f"   ✓ Renommé: {old_ref} → {orphan.reference} et assigné à {company.name}")
            print(f"   ✓ {len(conflicts)} produit(s) renommé(s) et assigné(s)")

        elif choix_conflit == '3':
            confirm = input("⚠️ ATTENTION: Supprimer les produits EXISTANTS? Tapez 'CONFIRMER' pour continuer: ")
            if confirm == 'CONFIRMER':
                print("\n🗑️ Suppression des produits existants...")
                for conf in conflicts:
                    existing = conf['existing']
                    orphan = conf['orphan']
                    existing.delete()
                    orphan.company = company
                    orphan.save()
                    print(f"   ✓ Supprimé produit existant [{existing.id}], orphelin [{orphan.id}] assigné")
                print(f"   ✓ {len(conflicts)} produit(s) existant(s) supprimé(s)")
            else:
                print("   → Suppression annulée")

        else:
            print("   → Conflits ignorés, produits orphelins laissés sans société")

else:
    print("\n   ✓ Aucun produit sans société")

# 6. Résumé final
print("\n" + "=" * 80)
print("✅ CORRECTION TERMINÉE")
print("=" * 80)

print("\n📊 ÉTAT FINAL:")
total = Produit.objects.count()
actifs = Produit.objects.filter(is_active=True).count()
avec_company = Produit.objects.filter(company__isnull=False).count()
sans_company = Produit.objects.filter(company__isnull=True).count()
inactifs = Produit.objects.filter(is_active=False).count()

print(f"   Total produits: {total}")
print(f"   Produits actifs: {actifs}")
print(f"   Produits inactifs: {inactifs}")
print(f"   Produits avec société: {avec_company}")
print(f"   Produits sans société: {sans_company}")

print("\n🔄 PROCHAINES ÉTAPES:")
print("   1. Rechargez la page dans votre navigateur")
print("   2. Appuyez sur Ctrl+Shift+R pour vider le cache")
print("   3. Vérifiez que les produits apparaissent maintenant")
print("   4. Si les produits n'apparaissent toujours pas, vérifiez:")
print("      - Que vous êtes connecté avec le bon utilisateur")
print("      - Que votre utilisateur a une société assignée (python setup_local_user.py)")
print("\n" + "=" * 80)
