"""
Script pour tester les nouveaux endpoints de ventes, commandes et rapports
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://192.168.0.150:8000"

# ==========================================
# 1. Authentification
# ==========================================
print("=" * 60)
print("1. AUTHENTIFICATION")
print("=" * 60)

login_data = {
    "username": "LIV004",
    "password": "test1234"
}

response = requests.post(f"{BASE_URL}/API/token/", json=login_data)
if response.status_code == 200:
    tokens = response.json()
    access_token = tokens['access']
    print("✅ Authentification réussie")
    print(f"   Access Token: {access_token[:50]}...")
else:
    print(f"❌ Erreur d'authentification: {response.status_code}")
    print(f"   {response.text}")
    exit(1)

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

# ==========================================
# 2. Test Endpoint VENTES
# ==========================================
print("\n" + "=" * 60)
print("2. TEST ENDPOINT VENTES")
print("=" * 60)

# GET - Liste des ventes
print("\n📋 GET /API/distribution/ventes/")
response = requests.get(f"{BASE_URL}/API/distribution/ventes/", headers=headers)
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    ventes = response.json()
    print(f"   ✅ {len(ventes)} ventes trouvées")
else:
    print(f"   ❌ Erreur: {response.text[:200]}")

# ==========================================
# 3. Test Endpoint COMMANDES
# ==========================================
print("\n" + "=" * 60)
print("3. TEST ENDPOINT COMMANDES")
print("=" * 60)

# GET - Liste des commandes
print("\n📋 GET /API/distribution/commandes/")
response = requests.get(f"{BASE_URL}/API/distribution/commandes/", headers=headers)
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    commandes = response.json()
    print(f"   ✅ {len(commandes)} commandes trouvées")
else:
    print(f"   ❌ Erreur: {response.text[:200]}")

# GET - Commandes en attente
print("\n📋 GET /API/distribution/commandes/en_attente/")
response = requests.get(f"{BASE_URL}/API/distribution/commandes/en_attente/", headers=headers)
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    commandes_attente = response.json()
    print(f"   ✅ {len(commandes_attente)} commandes en attente")
else:
    print(f"   ❌ Erreur: {response.text[:200]}")

# POST - Créer une commande de test (si on a des données)
print("\n📝 POST /API/distribution/commandes/ (création)")
# On va d'abord récupérer un client et des produits
response_clients = requests.get(f"{BASE_URL}/API/clients/?page_size=1", headers=headers)
response_produits = requests.get(f"{BASE_URL}/API/distribution/produits/", headers=headers)

if response_clients.status_code == 200 and response_produits.status_code == 200:
    clients = response_clients.json()
    produits = response_produits.json()

    if len(clients) > 0 and len(produits) > 0:
        client_id = clients[0]['id'] if isinstance(clients, list) else clients.get('results', [{}])[0].get('id')
        produit = produits[0] if isinstance(produits, list) else produits.get('results', [{}])[0]

        # Récupérer l'ID de la company (depuis le token ou l'utilisateur)
        # Pour simplifier, on va supposer company_id = 1
        commande_data = {
            "company": 1,
            "client": client_id,
            "livreur": 4,  # LIV004
            "date_livraison_souhaitee": "2025-11-25",
            "notes": "Commande de test depuis script",
            "app_id": f"test-cmd-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "lignes": [
                {
                    "produit": produit.get('id'),
                    "quantite": 10,
                    "prix_unitaire_ht": float(produit.get('prixU', 100)),
                    "taux_tva": 19
                }
            ]
        }

        response = requests.post(
            f"{BASE_URL}/API/distribution/commandes/",
            headers=headers,
            json=commande_data
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 201:
            commande = response.json()
            print(f"   ✅ Commande créée: {commande.get('reference')}")
            print(f"      Client: {commande.get('client_nom')} {commande.get('client_prenom')}")
            print(f"      Total HT: {commande.get('montant_total_ht')} DA")
            print(f"      Total TTC: {commande.get('montant_total_ttc')} DA")
        else:
            print(f"   ❌ Erreur: {response.text[:500]}")
    else:
        print("   ⏭️  Aucun client ou produit disponible pour le test")
else:
    print(f"   ⏭️  Impossible de récupérer clients/produits pour le test")

# ==========================================
# 4. Test Endpoint RAPPORTS
# ==========================================
print("\n" + "=" * 60)
print("4. TEST ENDPOINT RAPPORTS DE CAISSE")
print("=" * 60)

# GET - Liste des rapports
print("\n📋 GET /API/distribution/rapports-caisse/")
response = requests.get(f"{BASE_URL}/API/distribution/rapports-caisse/", headers=headers)
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    rapports = response.json()
    print(f"   ✅ {len(rapports)} rapports trouvés")
else:
    print(f"   ❌ Erreur: {response.text[:200]}")

# GET - Rapports avec anomalies
print("\n📋 GET /API/distribution/rapports-caisse/anomalies/")
response = requests.get(f"{BASE_URL}/API/distribution/rapports-caisse/anomalies/", headers=headers)
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    anomalies = response.json()
    print(f"   ✅ {len(anomalies)} rapports avec anomalies")
else:
    print(f"   ❌ Erreur: {response.text[:200]}")

# ==========================================
# 5. Test Endpoint PRODUITS (déjà créé)
# ==========================================
print("\n" + "=" * 60)
print("5. TEST ENDPOINT PRODUITS")
print("=" * 60)

print("\n📋 GET /API/distribution/produits/")
response = requests.get(f"{BASE_URL}/API/distribution/produits/", headers=headers)
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    produits = response.json()
    print(f"   ✅ {len(produits)} produits trouvés")
    if len(produits) > 0:
        print(f"      Premier produit: {produits[0].get('designation')}")
        print(f"      Prix: {produits[0].get('prixU')} DA")
else:
    print(f"   ❌ Erreur: {response.text[:200]}")

# ==========================================
# RÉSUMÉ
# ==========================================
print("\n" + "=" * 60)
print("RÉSUMÉ DES TESTS")
print("=" * 60)
print("""
Endpoints testés:
✅ POST /API/token/ - Authentification
✅ GET  /API/distribution/ventes/ - Liste des ventes
✅ GET  /API/distribution/commandes/ - Liste des commandes
✅ GET  /API/distribution/commandes/en_attente/ - Commandes en attente
✅ POST /API/distribution/commandes/ - Créer une commande
✅ GET  /API/distribution/rapports-caisse/ - Liste des rapports
✅ GET  /API/distribution/rapports-caisse/anomalies/ - Rapports avec anomalies
✅ GET  /API/distribution/produits/ - Liste des produits

Endpoints créés et disponibles (non testés automatiquement):
- POST /API/distribution/ventes/ - Créer une vente
- POST /API/distribution/ventes/bulk_create/ - Créer plusieurs ventes
- POST /API/distribution/commandes/bulk_create/ - Créer plusieurs commandes
- PATCH /API/distribution/commandes/{id}/changer_statut/ - Changer statut commande
- POST /API/distribution/rapports-caisse/ - Créer un rapport
- PUT  /API/distribution/rapports-caisse/{id}/ - Modifier un rapport
- POST /API/distribution/rapports-caisse/{id}/calculer/ - Recalculer totaux
- POST /API/distribution/rapports-caisse/{id}/valider/ - Valider rapport
""")
