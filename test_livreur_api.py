"""
Script pour tester l'endpoint livreurs et vérifier le champ 'nom'
"""
import requests
import json

BASE_URL = "http://192.168.0.150:8000"

print("=" * 80)
print("TEST DE L'ENDPOINT LIVREURS")
print("=" * 80)

# 1. Connexion
print("\n1. Connexion avec LIV004...")
try:
    response = requests.post(
        f"{BASE_URL}/API/token/",
        json={"username": "LIV004", "password": "test1234"}
    )
    response.raise_for_status()
    tokens = response.json()
    access_token = tokens['access']
    print(f"✅ Token obtenu")
except Exception as e:
    print(f"❌ Erreur de connexion : {e}")
    exit(1)

# 2. Tester l'endpoint livreurs
print("\n2. Test de l'endpoint /API/distribution/livreurs/...")
headers = {"Authorization": f"Bearer {access_token}"}

try:
    response = requests.get(
        f"{BASE_URL}/API/distribution/livreurs/",
        headers=headers
    )
    response.raise_for_status()
    data = response.json()

    print(f"✅ Endpoint accessible !")
    print(f"\n📊 Réponse brute :")
    print(json.dumps(data, indent=2, ensure_ascii=False))

    # Vérifier la structure
    livreurs = data if isinstance(data, list) else data.get('results', [])
    print(f"\n📋 Nombre de livreurs : {len(livreurs)}")

    # Chercher LIV004
    print(f"\n🔍 Recherche de LIV004...")
    for liv in livreurs:
        if liv.get('matricule') == 'LIV004' or liv.get('username') == 'LIV004':
            print(f"\n✅ Livreur trouvé !")
            print(f"   ID: {liv.get('id')}")
            print(f"   Matricule: {liv.get('matricule')}")
            print(f"   Username: {liv.get('username')}")
            print(f"   Nom: {liv.get('nom')}")
            print(f"   Prénom: {liv.get('prenom', 'N/A')}")
            print(f"   Statut: {liv.get('statut')}")

            if not liv.get('nom'):
                print(f"\n⚠️  ATTENTION : Le champ 'nom' est vide ou manquant !")
            break
    else:
        print(f"❌ LIV004 non trouvé dans la liste")
        print(f"\nLivreurs disponibles :")
        for liv in livreurs[:5]:
            print(f"  - {liv.get('matricule', 'N/A')} : {liv.get('nom', 'N/A')}")

except requests.exceptions.HTTPError as e:
    print(f"❌ Erreur HTTP {e.response.status_code}")
    print(f"   Réponse : {e.response.text}")
except Exception as e:
    print(f"❌ Erreur : {e}")

print("\n" + "=" * 80)
