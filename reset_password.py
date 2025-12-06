"""
Script pour réinitialiser le mot de passe d'un livreur
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.distribution_models import LivreurDistribution
from django.contrib.auth.models import User

print("=" * 80)
print("RÉINITIALISATION DU MOT DE PASSE")
print("=" * 80)

# Trouver le livreur LIV004
try:
    livreur = LivreurDistribution.objects.get(matricule='LIV004')
    print(f"\n✅ Livreur trouvé : {livreur.nom} ({livreur.matricule})")

    if not livreur.user:
        print("❌ Pas de compte utilisateur lié !")
        exit(1)

    user = livreur.user
    print(f"✅ Username : {user.username}")

    # Réinitialiser le mot de passe
    new_password = "test1234"
    user.set_password(new_password)
    user.save()

    print(f"\n✅ Mot de passe réinitialisé avec succès !")
    print(f"\n📱 IDENTIFIANTS DE CONNEXION :")
    print(f"   Username: {user.username}")
    print(f"   Password: {new_password}")
    print(f"\n⚠️  IMPORTANT : Changez ce mot de passe après la première connexion !")

except LivreurDistribution.DoesNotExist:
    print("\n❌ Livreur LIV004 introuvable !")
    print("\nLivreurs disponibles :")
    for liv in LivreurDistribution.objects.filter(user__isnull=False):
        print(f"  - {liv.matricule} : {liv.nom}")
