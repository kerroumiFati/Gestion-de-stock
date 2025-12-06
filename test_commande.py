# -*- coding: utf-8 -*-
"""
Script de test pour creer une commande via l'API mobile
"""
import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

def test_commande():
    print("=" * 50)
    print("TEST DE CREATION DE COMMANDE")
    print("=" * 50)

    # 1. Authentification
    print("\n1. Authentification...")
    auth_url = f"{BASE_URL}/API/token/"

    # Utiliser les credentials d'un livreur existant
    credentials = {
        "username": "livreur1",
        "password": "livreur123"
    }

    try:
        response = requests.post(auth_url, json=credentials)
        if response.status_code != 200:
            print(f"   Erreur auth avec livreur1, essai avec admin...")
            credentials = {"username": "admin", "password": "admin"}
            response = requests.post(auth_url, json=credentials)

        if response.status_code == 200:
            tokens = response.json()
            access_token = tokens.get('access')
            print(f"   [OK] Authentification reussie!")
        else:
            print(f"   [ERREUR] Erreur d'authentification: {response.status_code}")
            print(f"   Reponse: {response.text}")
            print("\n   Essai avec d'autres credentials...")

            # Essayer de lister les utilisateurs via Django
            credentials = {"username": "kerroumi", "password": "kerroumi123"}
            response = requests.post(auth_url, json=credentials)
            if response.status_code == 200:
                tokens = response.json()
                access_token = tokens.get('access')
                print(f"   [OK] Authentification reussie avec kerroumi!")
            else:
                print("   [ERREUR] Impossible de s'authentifier")
                return
    except Exception as e:
        print(f"   [ERREUR] {e}")
        return

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # 2. Recuperer les clients
    print("\n2. Recuperation des clients...")
    client = None

    # Essayer plusieurs endpoints pour les clients
    client_endpoints = [
        f"{BASE_URL}/API/clients/",
        f"{BASE_URL}/API/distribution/clients/",
    ]

    for clients_url in client_endpoints:
        try:
            response = requests.get(clients_url, headers=headers)
            if response.status_code == 200:
                clients = response.json()
                if isinstance(clients, dict) and 'results' in clients:
                    clients = clients['results']
                if clients:
                    client = clients[0]
                    print(f"   [OK] {len(clients)} clients trouves via {clients_url}")
                    print(f"   Premier client: {client.get('nom', 'N/A')} {client.get('prenom', 'N/A')} (ID: {client.get('id')})")
                    break
        except Exception as e:
            continue

    if not client:
        print(f"   [ERREUR] Aucun client trouve")

    # 3. Recuperer les produits
    print("\n3. Recuperation des produits...")
    produit = None

    # Essayer plusieurs endpoints
    endpoints = [
        f"{BASE_URL}/API/distribution/produits/",
        f"{BASE_URL}/API/produits/",
        f"{BASE_URL}/API/distribution/produits-mobile/",
        f"{BASE_URL}/API/distribution/stock-van/"
    ]

    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, headers=headers)
            if response.status_code == 200:
                produits = response.json()
                if isinstance(produits, dict) and 'results' in produits:
                    produits = produits['results']
                if produits:
                    produit = produits[0]
                    print(f"   [OK] Produit trouve via {endpoint}")
                    print(f"   Produit: {produit.get('designation', produit.get('produit_nom', 'N/A'))}")
                    print(f"   Prix: {produit.get('prixU', produit.get('prix_unitaire', 0))} DZD")
                    break
        except Exception as e:
            continue

    if not produit:
        print("   [ERREUR] Aucun produit trouve")

    if not client or not produit:
        print("\n[ERREUR] Impossible de creer une commande sans clients ou produits")
        print("\nVerification de l'API...")

        # Lister les endpoints disponibles
        try:
            response = requests.get(f"{BASE_URL}/API/distribution/", headers=headers)
            print(f"   Endpoints distribution: {response.text[:500]}")
        except:
            pass
        return

    # 4. Creer une commande
    print("\n4. Creation de la commande...")
    commande_url = f"{BASE_URL}/API/distribution/commandes/"

    # Preparer les donnees de la commande
    date_livraison = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    prix_str = produit.get('prixU', produit.get('prix_unitaire', '100'))
    prix = float(prix_str) if isinstance(prix_str, str) else prix_str
    produit_id = produit.get('id', produit.get('produit_id'))

    # Recuperer company et livreur
    print("\n   Recuperation de la company...")
    company_id = 1  # Par defaut
    try:
        response = requests.get(f"{BASE_URL}/API/companies/", headers=headers)
        if response.status_code == 200:
            companies = response.json()
            if isinstance(companies, dict) and 'results' in companies:
                companies = companies['results']
            if companies:
                company_id = companies[0].get('id', 1)
                print(f"   Company ID: {company_id}")
    except Exception as e:
        print(f"   Utilisation company par defaut: {company_id}")

    print("   Recuperation du livreur...")
    livreur_id = None
    try:
        response = requests.get(f"{BASE_URL}/API/distribution/livreurs/", headers=headers)
        if response.status_code == 200:
            livreurs = response.json()
            if isinstance(livreurs, dict) and 'results' in livreurs:
                livreurs = livreurs['results']
            if livreurs:
                livreur_id = livreurs[0].get('id')
                print(f"   Livreur ID: {livreur_id}")
    except Exception as e:
        print(f"   [ERREUR] Impossible de recuperer les livreurs: {e}")

    quantite = 5
    montant_ligne = quantite * prix

    commande_data = {
        "app_id": f"test-commande-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "client": client.get('id'),
        "company": company_id,
        "livreur": livreur_id,
        "lignes": [
            {
                "produit": produit_id,
                "quantite": quantite,
                "prix_unitaire_ht": prix,
                "montant_ligne": montant_ligne
            }
        ],
        "notes": "Commande de test creee via script",
        "date_livraison_souhaitee": date_livraison
    }

    print(f"   Donnees envoyees:")
    print(f"   {json.dumps(commande_data, indent=2)}")

    try:
        response = requests.post(commande_url, json=commande_data, headers=headers)
        print(f"\n   Status: {response.status_code}")

        if response.status_code in [200, 201]:
            result = response.json()
            print(f"\n   [SUCCES] COMMANDE CREEE!")
            print(f"   ID: {result.get('id', 'N/A')}")
            print(f"   Client: {client.get('nom', '')} {client.get('prenom', '')}")
            print(f"   Total: {result.get('total', 'N/A')} DZD")
            print(f"   Date livraison: {date_livraison}")
        else:
            print(f"   [ERREUR] {response.status_code}")
            print(f"   Reponse: {response.text}")
    except Exception as e:
        print(f"   [ERREUR] {e}")

    print("\n" + "=" * 50)
    print("FIN DU TEST")
    print("=" * 50)


if __name__ == "__main__":
    test_commande()
