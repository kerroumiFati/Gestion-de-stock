#!/usr/bin/env python
"""
Script automatique pour récupérer les produits disparus
Version automatisée sans interaction utilisateur
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.models import Produit, Company

print("=" * 80)
print("RÉCUPÉRATION AUTOMATIQUE DES PRODUITS")
print("=" * 80)

# 1. Réactiver TOUS les produits inactifs
produits_inactifs = Produit.objects.filter(is_active=False)
if produits_inactifs.exists():
    print(f"\n🔧 Réactivation de {produits_inactifs.count()} produit(s) inactif(s)...")
    for p in produits_inactifs:
        company_str = f"{p.company.name}" if p.company else "AUCUNE"
        print(f"   ✓ [{p.id}] {p.reference} - {p.designation} (Société: {company_str})")

    count = produits_inactifs.update(is_active=True)
    print(f"\n   ✅ {count} produit(s) réactivé(s) avec succès!")
else:
    print("\n   ✓ Aucun produit inactif")

# 2. Gérer les produits sans société
produits_sans_company = Produit.objects.filter(company__isnull=True)
if produits_sans_company.exists():
    print(f"\n🔧 Traitement de {produits_sans_company.count()} produit(s) sans société...")

    # Utiliser la première société active
    company = Company.objects.filter(is_active=True).first()
    if not company:
        print("   ⚠️ Aucune société active trouvée!")
    else:
        print(f"   Société cible: {company.name}")

        for p in produits_sans_company:
            # Vérifier conflit
            existing = Produit.objects.filter(company=company, reference=p.reference).exclude(id=p.id).first()

            if existing:
                # Renommer au lieu de supprimer (pour éviter ProtectedError)
                old_ref = p.reference
                p.reference = f"{p.reference}-DOUBLON-{p.id}"
                p.company = company
                p.is_active = False  # Désactiver les doublons
                p.save()
                print(f"   ⚠️ CONFLIT: [{p.id}] {old_ref} → {p.reference} (désactivé)")
            else:
                p.company = company
                p.save()
                print(f"   ✓ [{p.id}] {p.reference} - {p.designation} → assigné à {company.name}")
else:
    print("\n   ✓ Aucun produit sans société")

# 3. Résumé final
print("\n" + "=" * 80)
print("✅ RÉCUPÉRATION TERMINÉE")
print("=" * 80)

total = Produit.objects.count()
actifs = Produit.objects.filter(is_active=True).count()
avec_company = Produit.objects.filter(company__isnull=False).count()

print(f"\n📊 ÉTAT FINAL:")
print(f"   Total produits: {total}")
print(f"   Produits actifs: {actifs}")
print(f"   Produits avec société: {avec_company}")

print("\n🔄 PROCHAINES ÉTAPES:")
print("   1. Rechargez votre navigateur avec Ctrl+Shift+R")
print("   2. Vérifiez que vos produits (eau, coca, chips) apparaissent maintenant")
print("\n" + "=" * 80)
