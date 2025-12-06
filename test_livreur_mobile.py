import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from frontoffice.views import page

# Créer une requête de test
factory = RequestFactory()
user = User.objects.filter(is_staff=True).first()

if not user:
    print("Aucun utilisateur admin trouvé!")
else:
    print(f"Test avec l'utilisateur: {user.username}")
    request = factory.get('/page/livreur_mobile/')
    request.user = user

    try:
        response = page(request, 'livreur_mobile')
        print(f"✅ Status code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Page chargée avec succès!")
        else:
            print(f"⚠️  Status non-200: {response.status_code}")
    except Exception as e:
        print(f"❌ ERREUR: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        import traceback
        traceback.print_exc()
