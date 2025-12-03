# GestionStock MCP Servers

Serveurs MCP (Model Context Protocol) pour interagir avec l'application Django de gestion de stock via Claude.

## Serveurs disponibles

### 1. gestion-stock (API Server)
Interagit avec l'API REST Django pour lire/écrire des données.

### 2. gestion-stock-ui (UI Test Server)
Automatise les tests de l'interface utilisateur avec Playwright (navigateur).

## Installation

### Prérequis

- Python 3.8+
- L'application Django doit être en cours d'exécution
- Pour le serveur UI : `pip install playwright && python -m playwright install chromium`

### Configuration dans Claude Code

La configuration est déjà dans `.mcp.json` à la racine du projet :

```json
{
  "mcpServers": {
    "gestion-stock": {
      "type": "stdio",
      "command": "python",
      "args": ["...\\mcp-server\\server.py"],
      "env": {
        "DJANGO_API_URL": "http://192.168.0.150:8000",
        "DJANGO_USERNAME": "admin",
        "DJANGO_PASSWORD": "admin"
      }
    },
    "gestion-stock-ui": {
      "type": "stdio",
      "command": "python",
      "args": ["...\\mcp-server\\ui_test_server.py"],
      "env": {
        "APP_URL": "http://192.168.0.150:8000",
        "APP_USERNAME": "admin",
        "APP_PASSWORD": "admin",
        "HEADLESS": "false"
      }
    }
  }
}
```

## Outils API (gestion-stock)

| Outil | Description |
|-------|-------------|
| `list_clients` | Lister tous les clients |
| `get_client` | Détails d'un client |
| `list_products` | Lister tous les produits |
| `get_product` | Détails d'un produit |
| `list_drivers` | Lister tous les livreurs |
| `get_driver` | Détails d'un livreur |
| `list_routes` | Lister toutes les tournées |
| `get_route` | Détails d'une tournée |
| `list_warehouses` | Lister tous les entrepôts |
| `get_stock` | État du stock |
| `list_categories` | Lister les catégories |
| `get_sales` | Obtenir les ventes |
| `get_weekly_config` | Configuration hebdomadaire clients/livreurs |

## Outils UI Test (gestion-stock-ui)

| Outil | Description |
|-------|-------------|
| `ui_login` | Se connecter à l'application |
| `ui_navigate` | Naviguer vers une page |
| `ui_click` | Cliquer sur un bouton/élément |
| `ui_fill_form` | Remplir un formulaire |
| `ui_submit_form` | Soumettre le formulaire |
| `ui_screenshot` | Prendre une capture d'écran |
| `ui_get_elements` | Lister les éléments interactifs |
| `ui_test_add_client` | Test: Ajouter un client |
| `ui_test_add_product` | Test: Ajouter un produit |
| `ui_test_promotions` | Test: Page promotions |
| `ui_test_commandes` | Test: Page commandes |
| `ui_test_tournees` | Test: Page tournées |
| `ui_run_full_test` | Exécuter tous les tests |
| `ui_close_browser` | Fermer le navigateur |

## Utilisation avec Claude

### API Server
```
"Liste tous les livreurs"
"Montre-moi les tournées du 2025-12-01"
"Quel est le stock du produit 5 ?"
```

### UI Test Server
```
"Connecte-toi à l'application"
"Va sur la page des clients et prends un screenshot"
"Teste l'ajout d'un nouveau produit"
"Clique sur le bouton Ajouter"
"Remplis le formulaire avec nom=Test et email=test@test.com"
"Exécute une suite de tests complète"
```

## Configuration

### Variables d'environnement - API Server

| Variable | Description | Défaut |
|----------|-------------|--------|
| `DJANGO_API_URL` | URL de l'API Django | `http://192.168.0.150:8000` |
| `DJANGO_USERNAME` | Nom d'utilisateur | `admin` |
| `DJANGO_PASSWORD` | Mot de passe | `admin` |

### Variables d'environnement - UI Server

| Variable | Description | Défaut |
|----------|-------------|--------|
| `APP_URL` | URL de l'application | `http://192.168.0.150:8000` |
| `APP_USERNAME` | Nom d'utilisateur | `admin` |
| `APP_PASSWORD` | Mot de passe | `admin` |
| `HEADLESS` | Mode sans interface | `false` |
| `SCREENSHOTS_DIR` | Dossier des captures | `./screenshots` |

## Screenshots

Les captures d'écran sont sauvegardées dans `mcp-server/screenshots/`.

## Dépannage

### Le serveur API ne retourne pas de données
- Vérifiez que l'utilisateur a une company associée avec des données
- Les endpoints avec `TenantFilterMixin` filtrent par company

### Le serveur UI ne se connecte pas
- Vérifiez que l'application Django est accessible
- Vérifiez les credentials dans les variables d'environnement

### Erreur Playwright
- Installez Chromium : `python -m playwright install chromium`
