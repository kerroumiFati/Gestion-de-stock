#!/usr/bin/env python3
"""
GestionStock MCP Server
Server MCP pour interagir avec l'application Django de gestion de stock
"""

import json
import sys
import os
from typing import Any, Optional
import urllib.request
import urllib.parse
import urllib.error

# Configuration
API_BASE_URL = os.getenv("DJANGO_API_URL", "http://192.168.0.150:8000")
API_USERNAME = os.getenv("DJANGO_USERNAME", "admin")
API_PASSWORD = os.getenv("DJANGO_PASSWORD", "admin")


class DjangoAPIClient:
    """Client HTTP avec authentification JWT pour l'API Django"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.access_token = None
        self.refresh_token = None

    def login(self, username: str, password: str) -> bool:
        """Authentification et obtention du token JWT"""
        if not username or not password:
            return False

        url = f"{self.base_url}/API/token/"
        data = json.dumps({"username": username, "password": password}).encode()

        try:
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode())
                self.access_token = result.get("access")
                self.refresh_token = result.get("refresh")
                return True
        except Exception as e:
            sys.stderr.write(f"Login error: {e}\n")
            sys.stderr.flush()
            return False

    def refresh_access_token(self) -> bool:
        """Rafraîchir le token d'accès"""
        if not self.refresh_token:
            return False

        url = f"{self.base_url}/API/token/refresh/"
        data = json.dumps({"refresh": self.refresh_token}).encode()

        try:
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode())
                self.access_token = result.get("access")
                return True
        except:
            return False

    def _get_headers(self) -> dict:
        """Obtenir les headers avec le token d'authentification"""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Requête GET avec authentification"""
        url = f"{self.base_url}{endpoint}"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        try:
            req = urllib.request.Request(url, headers=self._get_headers())
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 401:
                # Token expiré, essayer de rafraîchir
                if self.refresh_access_token():
                    return self.get(endpoint, params)
                # Sinon, essayer de se reconnecter
                if self.login(API_USERNAME, API_PASSWORD):
                    return self.get(endpoint, params)
            return {"error": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            return {"error": str(e)}

    def post(self, endpoint: str, data: dict) -> dict:
        """Requête POST avec authentification"""
        url = f"{self.base_url}{endpoint}"

        try:
            json_data = json.dumps(data).encode()
            req = urllib.request.Request(
                url,
                data=json_data,
                headers=self._get_headers(),
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 401:
                if self.refresh_access_token():
                    return self.post(endpoint, data)
                if self.login(API_USERNAME, API_PASSWORD):
                    return self.post(endpoint, data)
            try:
                error_body = e.read().decode()
                return {"error": f"HTTP {e.code}: {error_body}"}
            except:
                return {"error": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            return {"error": str(e)}


# Client API global
api_client = DjangoAPIClient(API_BASE_URL)

# Tentative de connexion au démarrage
if API_USERNAME and API_PASSWORD:
    if api_client.login(API_USERNAME, API_PASSWORD):
        sys.stderr.write("Authentication successful\n")
    else:
        sys.stderr.write("Authentication failed - API calls may fail\n")
    sys.stderr.flush()


# ============== OUTILS (TOOLS) ==============

def list_clients(filter_name: str = None, limit: int = 50) -> dict:
    """Lister tous les clients"""
    params = {}
    if filter_name:
        params["search"] = filter_name

    result = api_client.get("/API/clients/", params)

    if "error" in result:
        return result

    if isinstance(result, list):
        clients = result[:limit]
    elif isinstance(result, dict) and "results" in result:
        clients = result["results"][:limit]
    else:
        clients = result

    return {"clients": clients, "count": len(clients) if isinstance(clients, list) else 0}


def get_client(client_id: int) -> dict:
    """Obtenir les détails d'un client"""
    return api_client.get(f"/API/clients/{client_id}/")


def list_products(filter_name: str = None, category: str = None, limit: int = 50) -> dict:
    """Lister tous les produits"""
    params = {}
    if filter_name:
        params["search"] = filter_name
    if category:
        params["categorie"] = category

    result = api_client.get("/API/produits/", params)

    if "error" in result:
        return result

    if isinstance(result, list):
        products = result[:limit]
    elif isinstance(result, dict) and "results" in result:
        products = result["results"][:limit]
    else:
        products = result

    return {"products": products, "count": len(products) if isinstance(products, list) else 0}


def get_product(product_id: int) -> dict:
    """Obtenir les détails d'un produit"""
    return api_client.get(f"/API/produits/{product_id}/")


def list_drivers(status: str = None, limit: int = 50) -> dict:
    """Lister tous les livreurs/chauffeurs"""
    params = {}
    if status:
        params["statut"] = status

    result = api_client.get("/API/distribution/livreurs/", params)

    if "error" in result:
        return result

    if isinstance(result, list):
        drivers = result[:limit]
    elif isinstance(result, dict) and "results" in result:
        drivers = result["results"][:limit]
    else:
        drivers = result

    return {"drivers": drivers, "count": len(drivers) if isinstance(drivers, list) else 0}


def get_driver(driver_id: int) -> dict:
    """Obtenir les détails d'un livreur"""
    return api_client.get(f"/API/distribution/livreurs/{driver_id}/")


def list_routes(status: str = None, date: str = None, limit: int = 50) -> dict:
    """Lister toutes les tournées"""
    params = {}
    if status:
        params["statut"] = status
    if date:
        params["date_tournee"] = date

    result = api_client.get("/API/distribution/tournees/", params)

    if "error" in result:
        return result

    if isinstance(result, list):
        routes = result[:limit]
    elif isinstance(result, dict) and "results" in result:
        routes = result["results"][:limit]
    else:
        routes = result

    return {"routes": routes, "count": len(routes) if isinstance(routes, list) else 0}


def get_route(route_id: int) -> dict:
    """Obtenir les détails d'une tournée"""
    return api_client.get(f"/API/distribution/tournees/{route_id}/")


def list_warehouses(limit: int = 50) -> dict:
    """Lister tous les entrepôts"""
    result = api_client.get("/API/entrepots/")

    if "error" in result:
        return result

    if isinstance(result, list):
        warehouses = result[:limit]
    elif isinstance(result, dict) and "results" in result:
        warehouses = result["results"][:limit]
    else:
        warehouses = result

    return {"warehouses": warehouses, "count": len(warehouses) if isinstance(warehouses, list) else 0}


def get_stock(warehouse_id: int = None, product_id: int = None) -> dict:
    """Obtenir le stock (par entrepôt ou produit)"""
    params = {}
    if warehouse_id:
        params["entrepot"] = warehouse_id
    if product_id:
        params["produit"] = product_id

    result = api_client.get("/API/stocks/", params)

    if "error" in result:
        return result

    if isinstance(result, list):
        stocks = result
    elif isinstance(result, dict) and "results" in result:
        stocks = result["results"]
    else:
        stocks = result

    return {"stocks": stocks}


def list_categories(limit: int = 50) -> dict:
    """Lister toutes les catégories de produits"""
    result = api_client.get("/API/categories/")

    if "error" in result:
        return result

    if isinstance(result, list):
        categories = result[:limit]
    elif isinstance(result, dict) and "results" in result:
        categories = result["results"][:limit]
    else:
        categories = result

    return {"categories": categories, "count": len(categories) if isinstance(categories, list) else 0}


def get_sales(client_id: int = None, date_from: str = None, date_to: str = None, limit: int = 50) -> dict:
    """Obtenir les ventes"""
    params = {}
    if client_id:
        params["client"] = client_id
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to

    result = api_client.get("/API/ventes/", params)

    if "error" in result:
        return result

    if isinstance(result, list):
        sales = result[:limit]
    elif isinstance(result, dict) and "results" in result:
        sales = result["results"][:limit]
    else:
        sales = result

    return {"sales": sales, "count": len(sales) if isinstance(sales, list) else 0}


def get_weekly_config(driver_id: int = None, day: int = None) -> dict:
    """Obtenir la configuration hebdomadaire clients/livreurs"""
    params = {}
    if driver_id:
        params["livreur"] = driver_id
    if day:
        params["jour_semaine"] = day

    result = api_client.get("/API/distribution/clients-livreurs-hebdo/", params)

    if "error" in result:
        return result

    if isinstance(result, list):
        configs = result
    elif isinstance(result, dict) and "results" in result:
        configs = result["results"]
    else:
        configs = result

    return {"configurations": configs}


def authenticate(username: str, password: str) -> dict:
    """S'authentifier auprès de l'API"""
    global API_USERNAME, API_PASSWORD
    API_USERNAME = username
    API_PASSWORD = password

    if api_client.login(username, password):
        return {"success": True, "message": "Authentification réussie"}
    else:
        return {"success": False, "error": "Échec de l'authentification. Vérifiez vos identifiants."}


# ============== DÉFINITION DES OUTILS ==============

TOOLS = [
    {
        "name": "authenticate",
        "description": "S'authentifier auprès de l'API Django. Requis avant d'utiliser les autres outils si les variables d'environnement DJANGO_USERNAME et DJANGO_PASSWORD ne sont pas configurées.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Nom d'utilisateur Django"
                },
                "password": {
                    "type": "string",
                    "description": "Mot de passe Django"
                }
            },
            "required": ["username", "password"]
        }
    },
    {
        "name": "list_clients",
        "description": "Lister tous les clients du système. Permet de filtrer par nom.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filter_name": {
                    "type": "string",
                    "description": "Filtrer les clients par nom (recherche partielle)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Nombre maximum de résultats (défaut: 50)"
                }
            }
        }
    },
    {
        "name": "get_client",
        "description": "Obtenir les détails d'un client spécifique par son ID",
        "inputSchema": {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "integer",
                    "description": "ID du client"
                }
            },
            "required": ["client_id"]
        }
    },
    {
        "name": "list_products",
        "description": "Lister tous les produits. Permet de filtrer par nom ou catégorie.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filter_name": {
                    "type": "string",
                    "description": "Filtrer par nom de produit"
                },
                "category": {
                    "type": "string",
                    "description": "Filtrer par catégorie"
                },
                "limit": {
                    "type": "integer",
                    "description": "Nombre maximum de résultats (défaut: 50)"
                }
            }
        }
    },
    {
        "name": "get_product",
        "description": "Obtenir les détails d'un produit spécifique par son ID",
        "inputSchema": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "integer",
                    "description": "ID du produit"
                }
            },
            "required": ["product_id"]
        }
    },
    {
        "name": "list_drivers",
        "description": "Lister tous les livreurs/chauffeurs",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filtrer par statut (actif, inactif)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Nombre maximum de résultats (défaut: 50)"
                }
            }
        }
    },
    {
        "name": "get_driver",
        "description": "Obtenir les détails d'un livreur spécifique",
        "inputSchema": {
            "type": "object",
            "properties": {
                "driver_id": {
                    "type": "integer",
                    "description": "ID du livreur"
                }
            },
            "required": ["driver_id"]
        }
    },
    {
        "name": "list_routes",
        "description": "Lister toutes les tournées de livraison",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filtrer par statut (planifiee, en_cours, terminee, annulee)"
                },
                "date": {
                    "type": "string",
                    "description": "Filtrer par date (format: YYYY-MM-DD)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Nombre maximum de résultats (défaut: 50)"
                }
            }
        }
    },
    {
        "name": "get_route",
        "description": "Obtenir les détails d'une tournée spécifique",
        "inputSchema": {
            "type": "object",
            "properties": {
                "route_id": {
                    "type": "integer",
                    "description": "ID de la tournée"
                }
            },
            "required": ["route_id"]
        }
    },
    {
        "name": "list_warehouses",
        "description": "Lister tous les entrepôts (y compris les vans)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Nombre maximum de résultats (défaut: 50)"
                }
            }
        }
    },
    {
        "name": "get_stock",
        "description": "Obtenir l'état du stock. Peut filtrer par entrepôt ou produit.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "warehouse_id": {
                    "type": "integer",
                    "description": "ID de l'entrepôt (optionnel)"
                },
                "product_id": {
                    "type": "integer",
                    "description": "ID du produit (optionnel)"
                }
            }
        }
    },
    {
        "name": "list_categories",
        "description": "Lister toutes les catégories de produits",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Nombre maximum de résultats (défaut: 50)"
                }
            }
        }
    },
    {
        "name": "get_sales",
        "description": "Obtenir les ventes. Peut filtrer par client et période.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "integer",
                    "description": "ID du client (optionnel)"
                },
                "date_from": {
                    "type": "string",
                    "description": "Date de début (format: YYYY-MM-DD)"
                },
                "date_to": {
                    "type": "string",
                    "description": "Date de fin (format: YYYY-MM-DD)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Nombre maximum de résultats (défaut: 50)"
                }
            }
        }
    },
    {
        "name": "get_weekly_config",
        "description": "Obtenir la configuration hebdomadaire des clients assignés aux livreurs par jour",
        "inputSchema": {
            "type": "object",
            "properties": {
                "driver_id": {
                    "type": "integer",
                    "description": "ID du livreur (optionnel)"
                },
                "day": {
                    "type": "integer",
                    "description": "Jour de la semaine (1=Lundi, 7=Dimanche)"
                }
            }
        }
    }
]


def execute_tool(tool_name: str, arguments: dict) -> dict:
    """Exécuter un outil"""
    try:
        if tool_name == "authenticate":
            return authenticate(arguments["username"], arguments["password"])
        elif tool_name == "list_clients":
            return list_clients(
                filter_name=arguments.get("filter_name"),
                limit=arguments.get("limit", 50)
            )
        elif tool_name == "get_client":
            return get_client(arguments["client_id"])
        elif tool_name == "list_products":
            return list_products(
                filter_name=arguments.get("filter_name"),
                category=arguments.get("category"),
                limit=arguments.get("limit", 50)
            )
        elif tool_name == "get_product":
            return get_product(arguments["product_id"])
        elif tool_name == "list_drivers":
            return list_drivers(
                status=arguments.get("status"),
                limit=arguments.get("limit", 50)
            )
        elif tool_name == "get_driver":
            return get_driver(arguments["driver_id"])
        elif tool_name == "list_routes":
            return list_routes(
                status=arguments.get("status"),
                date=arguments.get("date"),
                limit=arguments.get("limit", 50)
            )
        elif tool_name == "get_route":
            return get_route(arguments["route_id"])
        elif tool_name == "list_warehouses":
            return list_warehouses(limit=arguments.get("limit", 50))
        elif tool_name == "get_stock":
            return get_stock(
                warehouse_id=arguments.get("warehouse_id"),
                product_id=arguments.get("product_id")
            )
        elif tool_name == "list_categories":
            return list_categories(limit=arguments.get("limit", 50))
        elif tool_name == "get_sales":
            return get_sales(
                client_id=arguments.get("client_id"),
                date_from=arguments.get("date_from"),
                date_to=arguments.get("date_to"),
                limit=arguments.get("limit", 50)
            )
        elif tool_name == "get_weekly_config":
            return get_weekly_config(
                driver_id=arguments.get("driver_id"),
                day=arguments.get("day")
            )
        else:
            return {"error": f"Outil inconnu: {tool_name}"}
    except Exception as e:
        return {"error": str(e)}


# ============== SERVEUR MCP (STDIO) ==============

def read_message() -> Optional[dict]:
    """Lire un message JSON depuis stdin"""
    try:
        line = sys.stdin.readline()
        if not line:
            return None
        line = line.strip()
        if not line:
            return {"method": "ping"}
        return json.loads(line)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"JSON decode error: {e}\n")
        sys.stderr.flush()
        return {"method": "ping"}
    except Exception as e:
        sys.stderr.write(f"Read error: {e}\n")
        sys.stderr.flush()
        return {"method": "ping"}


def write_message(message: dict):
    """Écrire un message JSON vers stdout"""
    try:
        output = json.dumps(message, ensure_ascii=False)
        sys.stdout.write(output + "\n")
        sys.stdout.flush()
    except Exception as e:
        sys.stderr.write(f"Write error: {e}\n")
        sys.stderr.flush()


def handle_request(request: dict) -> dict:
    """Traiter une requête MCP"""
    method = request.get("method", "")
    request_id = request.get("id")
    params = request.get("params", {})

    if method == "ping":
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "gestion-stock-mcp",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": {}
                }
            }
        }

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": TOOLS
            }
        }

    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        result = execute_tool(tool_name, arguments)

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2, ensure_ascii=False)
                    }
                ]
            }
        }

    elif method == "notifications/initialized":
        return None

    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"Méthode non supportée: {method}"
            }
        }


def main():
    """Point d'entrée principal du serveur MCP"""
    # Configurer stdout pour UTF-8
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    sys.stderr.write(f"GestionStock MCP Server started (API: {API_BASE_URL})\n")
    sys.stderr.flush()

    while True:
        try:
            message = read_message()
            if message is None:
                import time
                time.sleep(0.1)
                continue

            response = handle_request(message)
            if response is not None:
                write_message(response)

        except KeyboardInterrupt:
            sys.stderr.write("Server stopped by user\n")
            sys.stderr.flush()
            break
        except Exception as e:
            sys.stderr.write(f"Error: {e}\n")
            sys.stderr.flush()
            continue


if __name__ == "__main__":
    main()
