"""
Script pour créer VOTRE hotel
Modifiez les informations ci-dessous selon vos besoins
"""

from django.contrib.auth import get_user_model
from API.models import Company, UserProfile

User = get_user_model()

print("=== Creation de votre Hotel ===\n")

# ========================================
# MODIFIEZ ICI LES INFORMATIONS DE VOTRE HOTEL
# ========================================

HOTEL_NAME = "Mon Hotel"  # Changez ici
HOTEL_CODE = "HOTEL_KB"   # Code unique (majuscules, pas d'espaces)
HOTEL_EMAIL = "contact@monhotel.com"
HOTEL_PHONE = "+212 5XX-XXXXXX"
HOTEL_ADDRESS = "Adresse de votre hotel"
HOTEL_TAX_ID = "ICE000000000"  # Votre numero fiscal

# Utilisateur administrateur de l'hotel
ADMIN_USERNAME = "admin_hotel"
ADMIN_PASSWORD = "MotDePasse123!"  # CHANGEZ CE MOT DE PASSE !
ADMIN_EMAIL = "admin@monhotel.com"
ADMIN_FIRST_NAME = "Prenom"
ADMIN_LAST_NAME = "Nom"

# ========================================
# FIN DE LA CONFIGURATION
# ========================================

# Créer l'hotel
hotel, created = Company.objects.get_or_create(
    code=HOTEL_CODE,
    defaults={
        'name': HOTEL_NAME,
        'email': HOTEL_EMAIL,
        'telephone': HOTEL_PHONE,
        'adresse': HOTEL_ADDRESS,
        'tax_id': HOTEL_TAX_ID,
        'is_active': True
    }
)

if created:
    print(f"✓ Hotel cree : {hotel.name} ({hotel.code})")
else:
    print(f"! Hotel existe deja : {hotel.name} ({hotel.code})")

# Créer l'utilisateur administrateur
user, created = User.objects.get_or_create(
    username=ADMIN_USERNAME,
    defaults={
        'email': ADMIN_EMAIL,
        'first_name': ADMIN_FIRST_NAME,
        'last_name': ADMIN_LAST_NAME,
        'is_staff': True  # Accès à l'admin Django
    }
)

if created:
    user.set_password(ADMIN_PASSWORD)
    user.save()
    print(f"✓ Utilisateur cree : {user.username}")
else:
    print(f"! Utilisateur existe deja : {user.username}")

# Créer le profil
profile, created = UserProfile.objects.get_or_create(
    user=user,
    defaults={
        'company': hotel,
        'role': 'admin'
    }
)

if created:
    print(f"✓ Profil cree : {user.username} -> {hotel.name} (admin)")
else:
    print(f"! Profil existe deja")

# Résumé
print("\n" + "="*50)
print("✅ VOTRE HOTEL EST PRET !")
print("="*50)
print(f"\nHotel : {hotel.name}")
print(f"Code  : {hotel.code}")
print(f"\nConnexion :")
print(f"  URL      : http://localhost:8000/")
print(f"  Username : {ADMIN_USERNAME}")
print(f"  Password : {ADMIN_PASSWORD}")
print("\n⚠️  IMPORTANT : Changez le mot de passe apres la premiere connexion !")
print("\nVous pouvez maintenant :")
print("  1. Creer des produits pour votre hotel")
print("  2. Creer des clients")
print("  3. Faire des ventes")
print("  4. Tout est separe des autres entreprises !")
