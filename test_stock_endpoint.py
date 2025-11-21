"""
Script pour tester l'endpoint stock_van
"""
import requests
import json

BASE_URL = "http://192.168.0.150:8000"

print("=" * 80)
print("TEST DE L'ENDPOINT STOCK_VAN")
print("=" * 80)

# 1. Connexion pour obtenir le token
print("\n1. Connexion avec LIV004...")
try:
    response = requests.post(
        f"{BASE_URL}/API/token/",
        json={"username": "LIV004", "password": "test1234"}
    )
    response.raise_for_status()
    tokens = response.json()
    access_token = tokens['access']
    print(f"✅ Token obtenu : {access_token[:20]}...")
except Exception as e:
    print(f"❌ Erreur de connexion : {e}")
    exit(1)

# 2. Tester l'endpoint stock_van
print("\n2. Test de l'endpoint stock_van...")
headers = {"Authorization": f"Bearer {access_token}"}

try:
    response = requests.get(
        f"{BASE_URL}/API/distribution/livreurs/4/stock_van/",
        headers=headers
    )
    response.raise_for_status()
    stock_data = response.json()

    print(f"✅ Endpoint accessible !")
    print(f"\n📊 Données reçues :")
    print(json.dumps(stock_data, indent=2, ensure_ascii=False))

    # Vérifier la structure
    if 'stock' in stock_data:
        print(f"\n✅ Nombre de produits en stock : {len(stock_data['stock'])}")
        for item in stock_data['stock'][:3]:  # Afficher les 3 premiers
            print(f"   - {item.get('produit_nom', 'N/A')}: {item.get('quantite', 0)} unités")

except requests.exceptions.HTTPError as e:
    print(f"❌ Erreur HTTP {e.response.status_code}")
    print(f"   Réponse : {e.response.text}")
except Exception as e:
    print(f"❌ Erreur : {e}")

print("\n" + "=" * 80)
