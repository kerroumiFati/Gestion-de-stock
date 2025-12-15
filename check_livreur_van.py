import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.distribution_models import LivreurDistribution
from API.models import Warehouse

print("\n" + "="*70)
print("DIAGNOSTIC: LIVREURS ET VANS ASSIGNÉS")
print("="*70)

# Afficher tous les livreurs
livreurs = LivreurDistribution.objects.all()
print(f"\nNombre total de livreurs: {livreurs.count()}")

if livreurs.count() == 0:
    print("\n⚠️  Aucun livreur trouvé dans la base de données!")
else:
    print("\nDétail des livreurs:")
    print("-" * 70)
    for livreur in livreurs:
        print(f"\n🚚 Livreur: {livreur.nom}")
        print(f"   ID: {livreur.id}")
        print(f"   Matricule: {livreur.matricule}")
        print(f"   Téléphone: {livreur.telephone}")
        print(f"   Statut: {livreur.statut}")

        if livreur.entrepot:
            print(f"   ✅ Van assigné: {livreur.entrepot.name}")
            print(f"      - Code: {livreur.entrepot.code}")
            print(f"      - ID: {livreur.entrepot.id}")
        else:
            print(f"   ❌ PAS DE VAN ASSIGNÉ!")
            print(f"      👉 Pour corriger: aller dans 'Distribution > Gestion des Livreurs'")

# Afficher tous les entrepôts disponibles
print("\n" + "="*70)
print("ENTREPÔTS DISPONIBLES")
print("="*70)

entrepots = Warehouse.objects.all()
print(f"\nNombre total d'entrepôts: {entrepots.count()}")

if entrepots.count() == 0:
    print("\n⚠️  Aucun entrepôt trouvé!")
    print("   Vous devez d'abord créer un entrepôt dans:")
    print("   📍 Stocks > Entrepôts > Nouveau")
else:
    print("\nListe des entrepôts:")
    print("-" * 70)
    for entrepot in entrepots:
        # Vérifier si cet entrepôt est assigné à un livreur
        livreur_assigne = LivreurDistribution.objects.filter(entrepot=entrepot).first()

        print(f"\n🏢 Entrepôt: {entrepot.name}")
        print(f"   Code: {entrepot.code}")
        print(f"   ID: {entrepot.id}")

        if livreur_assigne:
            print(f"   ✅ Assigné à: {livreur_assigne.nom} (ID: {livreur_assigne.id})")
        else:
            print(f"   ⚪ Disponible (non assigné)")

print("\n" + "="*70)
print("SOLUTION POUR ASSIGNER UN VAN")
print("="*70)
print("""
Pour assigner un van à un livreur:

1. 📍 Allez dans le menu: Distribution > Gestion des Livreurs
   URL: http://localhost:8000/page/livreurs

2. ✏️  Cliquez sur 'Modifier' (icône crayon) pour le livreur concerné

3. 🏢 Dans le formulaire, trouvez le champ "Van/Entrepôt assigné"
   et sélectionnez un van dans la liste déroulante

4. 💾 Cliquez sur "Enregistrer"

Si aucun entrepôt n'est disponible dans la liste:
1. 📍 Allez dans: Stocks > Entrepôts
2. ➕ Créez un nouvel entrepôt
3. 🏷️  Donnez-lui un nom comme "Van Livraison X"
4. 💾 Enregistrez
5. 🔄 Retournez assigner cet entrepôt au livreur
""")
print("="*70)
