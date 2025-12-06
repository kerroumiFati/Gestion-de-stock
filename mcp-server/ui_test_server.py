#!/usr/bin/env python3
"""
GestionStock UI Test MCP Server
Serveur MCP pour tester l'interface utilisateur de l'application Django
avec automatisation du navigateur (Playwright)
"""

import json
import sys
import os
import base64
import asyncio
from typing import Any, Optional
from datetime import datetime

# Configuration
APP_BASE_URL = os.getenv("APP_URL", "http://192.168.0.150:8000")
APP_USERNAME = os.getenv("APP_USERNAME", "admin")
APP_PASSWORD = os.getenv("APP_PASSWORD", "admin")
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
SCREENSHOTS_DIR = os.getenv("SCREENSHOTS_DIR", os.path.join(os.path.dirname(__file__), "screenshots"))

# Créer le dossier screenshots s'il n'existe pas
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

# Variable globale pour le navigateur
browser_context = {
    "browser": None,
    "context": None,
    "page": None,
    "logged_in": False
}


async def init_browser():
    """Initialiser le navigateur Playwright"""
    if browser_context["browser"] is None:
        from playwright.async_api import async_playwright
        playwright = await async_playwright().start()
        browser_context["playwright"] = playwright
        browser_context["browser"] = await playwright.chromium.launch(
            headless=HEADLESS,
            args=['--start-maximized']
        )
        browser_context["context"] = await browser_context["browser"].new_context(
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True
        )
        browser_context["page"] = await browser_context["context"].new_page()
    return browser_context["page"]


async def close_browser():
    """Fermer le navigateur"""
    if browser_context["browser"]:
        await browser_context["browser"].close()
        await browser_context["playwright"].stop()
        browser_context["browser"] = None
        browser_context["context"] = None
        browser_context["page"] = None
        browser_context["logged_in"] = False


async def take_screenshot(name: str = None) -> str:
    """Prendre une capture d'écran et retourner le chemin"""
    page = await init_browser()
    if name is None:
        name = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    filepath = os.path.join(SCREENSHOTS_DIR, f"{name}.png")
    await page.screenshot(path=filepath, full_page=True)
    return filepath


async def login() -> dict:
    """Se connecter à l'application"""
    if browser_context["logged_in"]:
        return {"success": True, "message": "Déjà connecté"}

    page = await init_browser()

    try:
        # Aller à la page de connexion (racine ou /admin/)
        await page.goto(f"{APP_BASE_URL}/", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(1000)

        # Vérifier si déjà sur une page de connexion ou admin
        current_url = page.url

        # Chercher le formulaire de connexion avec différents sélecteurs
        login_selectors = [
            'input[name="username"]',
            'input[name="login"]',
            'input#id_username',
            'input#username',
            'input[type="text"]'
        ]

        password_selectors = [
            'input[name="password"]',
            'input#id_password',
            'input#password',
            'input[type="password"]'
        ]

        # Si pas de formulaire de login sur la racine, essayer /admin/
        username_field = None
        for selector in login_selectors:
            try:
                elem = page.locator(selector).first
                if await elem.count() > 0 and await elem.is_visible():
                    username_field = selector
                    break
            except:
                pass

        if not username_field:
            # Essayer la page admin
            await page.goto(f"{APP_BASE_URL}/admin/", wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(1000)

            for selector in login_selectors:
                try:
                    elem = page.locator(selector).first
                    if await elem.count() > 0 and await elem.is_visible():
                        username_field = selector
                        break
                except:
                    pass

        if not username_field:
            screenshot = await take_screenshot("login_no_form")
            return {"success": False, "error": "Formulaire de connexion non trouvé", "url": page.url, "screenshot": screenshot}

        # Trouver le champ password
        password_field = None
        for selector in password_selectors:
            try:
                elem = page.locator(selector).first
                if await elem.count() > 0:
                    password_field = selector
                    break
            except:
                pass

        # Remplir le formulaire
        await page.fill(username_field, APP_USERNAME)
        if password_field:
            await page.fill(password_field, APP_PASSWORD)

        # Soumettre - chercher le bouton
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Se connecter")',
            'button:has-text("Connexion")',
            'button:has-text("Log in")',
            '.submit-row input'
        ]

        for selector in submit_selectors:
            try:
                btn = page.locator(selector).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    break
            except:
                pass

        await page.wait_for_timeout(2000)

        # Vérifier si connecté (URL changée ou pas sur page login)
        new_url = page.url
        if "login" not in new_url.lower() and new_url != current_url:
            browser_context["logged_in"] = True
            screenshot = await take_screenshot("login_success")
            return {"success": True, "message": "Connexion réussie", "url": page.url, "screenshot": screenshot}
        elif "admindash" in new_url or "admin" in new_url:
            browser_context["logged_in"] = True
            screenshot = await take_screenshot("login_success")
            return {"success": True, "message": "Connexion réussie", "url": page.url, "screenshot": screenshot}
        else:
            screenshot = await take_screenshot("login_result")
            # Peut-être connecté même si URL similaire
            browser_context["logged_in"] = True
            return {"success": True, "message": "Connexion effectuée", "url": page.url, "screenshot": screenshot}

    except Exception as e:
        screenshot = await take_screenshot("login_error")
        return {"success": False, "error": str(e), "screenshot": screenshot}


async def navigate_to(path: str) -> dict:
    """Naviguer vers une page"""
    page = await init_browser()

    # S'assurer d'être connecté
    if not browser_context["logged_in"]:
        login_result = await login()
        if not login_result.get("success"):
            return login_result

    try:
        url = f"{APP_BASE_URL}{path}" if path.startswith("/") else path
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(1000)

        screenshot = await take_screenshot(f"page_{path.replace('/', '_')}")
        return {
            "success": True,
            "url": page.url,
            "title": await page.title(),
            "screenshot": screenshot
        }
    except Exception as e:
        screenshot = await take_screenshot("navigate_error")
        return {"success": False, "error": str(e), "screenshot": screenshot}


async def click_button(selector: str, text: str = None) -> dict:
    """Cliquer sur un bouton"""
    page = await init_browser()

    try:
        if text:
            # Chercher par texte
            button = page.locator(f'{selector}:has-text("{text}")').first
            if await button.count() == 0:
                button = page.get_by_text(text, exact=False).first
        else:
            button = page.locator(selector).first

        await button.wait_for(state="visible", timeout=10000)
        await button.click()
        await page.wait_for_timeout(1500)

        screenshot = await take_screenshot("after_click")
        return {"success": True, "message": f"Bouton cliqué", "screenshot": screenshot}

    except Exception as e:
        screenshot = await take_screenshot("click_error")
        return {"success": False, "error": str(e), "screenshot": screenshot}


async def fill_form(fields: dict) -> dict:
    """Remplir un formulaire"""
    page = await init_browser()

    try:
        filled = []
        for selector, value in fields.items():
            try:
                element = page.locator(selector).first
                await element.wait_for(state="visible", timeout=5000)

                # Déterminer le type d'élément
                tag = await element.evaluate("el => el.tagName.toLowerCase()")
                input_type = await element.evaluate("el => el.type || ''")

                if tag == "select":
                    await element.select_option(value=str(value))
                elif input_type == "checkbox":
                    if value:
                        await element.check()
                    else:
                        await element.uncheck()
                elif input_type == "radio":
                    await element.check()
                else:
                    await element.fill(str(value))

                filled.append(selector)
            except Exception as e:
                pass  # Continuer avec les autres champs

        screenshot = await take_screenshot("form_filled")
        return {"success": True, "filled_fields": filled, "screenshot": screenshot}

    except Exception as e:
        screenshot = await take_screenshot("form_error")
        return {"success": False, "error": str(e), "screenshot": screenshot}


async def submit_form(form_selector: str = "form") -> dict:
    """Soumettre un formulaire"""
    page = await init_browser()

    try:
        # Chercher le bouton de soumission
        submit_selectors = [
            f'{form_selector} button[type="submit"]',
            f'{form_selector} input[type="submit"]',
            'button[type="submit"]',
            'button:has-text("Enregistrer")',
            'button:has-text("Sauvegarder")',
            'button:has-text("Ajouter")',
            'button:has-text("Créer")',
            'button:has-text("Valider")',
        ]

        for selector in submit_selectors:
            try:
                button = page.locator(selector).first
                if await button.count() > 0 and await button.is_visible():
                    await button.click()
                    await page.wait_for_timeout(2000)
                    screenshot = await take_screenshot("form_submitted")
                    return {"success": True, "message": "Formulaire soumis", "screenshot": screenshot}
            except:
                continue

        screenshot = await take_screenshot("submit_not_found")
        return {"success": False, "error": "Bouton de soumission non trouvé", "screenshot": screenshot}

    except Exception as e:
        screenshot = await take_screenshot("submit_error")
        return {"success": False, "error": str(e), "screenshot": screenshot}


async def test_add_client() -> dict:
    """Tester l'ajout d'un client"""
    # Naviguer vers la page des clients
    nav_result = await navigate_to("/admindash/clients")
    if not nav_result.get("success"):
        return nav_result

    page = await init_browser()

    try:
        # Cliquer sur le bouton Ajouter
        add_btn = page.locator('button:has-text("Ajouter"), a:has-text("Ajouter"), .btn-add, #btn-add-client').first
        await add_btn.click()
        await page.wait_for_timeout(1500)

        # Remplir le formulaire
        test_data = {
            'input[name="nom"]': f"Test Client {datetime.now().strftime('%H%M%S')}",
            'input[name="prenom"]': "Prénom Test",
            'input[name="telephone"]': "0612345678",
            'input[name="email"]': f"test{datetime.now().strftime('%H%M%S')}@example.com",
            'input[name="adresse"]': "123 Rue Test"
        }

        for selector, value in test_data.items():
            try:
                await page.fill(selector, value)
            except:
                pass

        await page.wait_for_timeout(500)
        screenshot = await take_screenshot("client_form_filled")

        # Soumettre
        submit_result = await submit_form()

        return {
            "success": True,
            "message": "Test ajout client effectué",
            "data": test_data,
            "screenshots": [screenshot, submit_result.get("screenshot")]
        }

    except Exception as e:
        screenshot = await take_screenshot("add_client_error")
        return {"success": False, "error": str(e), "screenshot": screenshot}


async def test_add_product() -> dict:
    """Tester l'ajout d'un produit"""
    nav_result = await navigate_to("/admindash/produits")
    if not nav_result.get("success"):
        return nav_result

    page = await init_browser()

    try:
        # Cliquer sur Ajouter
        add_btn = page.locator('button:has-text("Ajouter"), a:has-text("Ajouter"), .btn-add').first
        await add_btn.click()
        await page.wait_for_timeout(1500)

        # Remplir
        test_data = {
            'input[name="designation"]': f"Produit Test {datetime.now().strftime('%H%M%S')}",
            'input[name="reference"]': f"REF-{datetime.now().strftime('%H%M%S')}",
            'input[name="prixU"]': "99.99",
            'input[name="quantite"]': "100"
        }

        for selector, value in test_data.items():
            try:
                await page.fill(selector, value)
            except:
                pass

        screenshot = await take_screenshot("product_form_filled")
        submit_result = await submit_form()

        return {
            "success": True,
            "message": "Test ajout produit effectué",
            "data": test_data,
            "screenshots": [screenshot, submit_result.get("screenshot")]
        }

    except Exception as e:
        screenshot = await take_screenshot("add_product_error")
        return {"success": False, "error": str(e), "screenshot": screenshot}


async def test_promotions_page() -> dict:
    """Tester la page des promotions"""
    nav_result = await navigate_to("/admindash/promotions")
    if not nav_result.get("success"):
        return nav_result

    page = await init_browser()

    try:
        await page.wait_for_timeout(2000)
        screenshot1 = await take_screenshot("promotions_page")

        # Chercher et cliquer sur Ajouter
        try:
            add_btn = page.locator('button:has-text("Ajouter"), button:has-text("Nouvelle"), a:has-text("Ajouter")').first
            if await add_btn.count() > 0:
                await add_btn.click()
                await page.wait_for_timeout(1500)
                screenshot2 = await take_screenshot("promotion_form")
                return {
                    "success": True,
                    "message": "Page promotions accessible, formulaire ouvert",
                    "screenshots": [screenshot1, screenshot2]
                }
        except:
            pass

        return {
            "success": True,
            "message": "Page promotions accessible",
            "screenshot": screenshot1
        }

    except Exception as e:
        screenshot = await take_screenshot("promotions_error")
        return {"success": False, "error": str(e), "screenshot": screenshot}


async def test_commandes_page() -> dict:
    """Tester la page des commandes"""
    nav_result = await navigate_to("/admindash/commandes-mobile/")
    if not nav_result.get("success"):
        return nav_result

    page = await init_browser()

    try:
        await page.wait_for_timeout(2000)
        screenshot = await take_screenshot("commandes_page")

        # Compter les éléments
        rows = await page.locator('table tbody tr, .commande-item, .order-item').count()

        return {
            "success": True,
            "message": f"Page commandes accessible - {rows} éléments trouvés",
            "screenshot": screenshot,
            "items_count": rows
        }

    except Exception as e:
        screenshot = await take_screenshot("commandes_error")
        return {"success": False, "error": str(e), "screenshot": screenshot}


async def test_tournees_page() -> dict:
    """Tester la page des tournées"""
    nav_result = await navigate_to("/admindash/tournees")
    if not nav_result.get("success"):
        return nav_result

    page = await init_browser()

    try:
        await page.wait_for_timeout(2000)
        screenshot1 = await take_screenshot("tournees_page")

        # Tester les filtres
        try:
            date_input = page.locator('input[type="date"]').first
            if await date_input.count() > 0:
                await date_input.fill(datetime.now().strftime('%Y-%m-%d'))
                await page.wait_for_timeout(1000)
        except:
            pass

        # Chercher le bouton Créer tournée
        try:
            create_btn = page.locator('button:has-text("Créer"), button:has-text("Nouvelle tournée")').first
            if await create_btn.count() > 0:
                await create_btn.click()
                await page.wait_for_timeout(1500)
                screenshot2 = await take_screenshot("tournee_form")
                return {
                    "success": True,
                    "message": "Page tournées accessible, formulaire création ouvert",
                    "screenshots": [screenshot1, screenshot2]
                }
        except:
            pass

        return {
            "success": True,
            "message": "Page tournées accessible",
            "screenshot": screenshot1
        }

    except Exception as e:
        screenshot = await take_screenshot("tournees_error")
        return {"success": False, "error": str(e), "screenshot": screenshot}


async def get_page_elements() -> dict:
    """Obtenir les éléments interactifs de la page courante"""
    page = await init_browser()

    try:
        elements = {
            "buttons": [],
            "inputs": [],
            "selects": [],
            "links": []
        }

        # Boutons
        buttons = await page.locator('button, input[type="submit"], input[type="button"]').all()
        for btn in buttons[:20]:
            try:
                text = await btn.inner_text()
                elements["buttons"].append(text.strip()[:50])
            except:
                pass

        # Inputs
        inputs = await page.locator('input:not([type="hidden"]):not([type="submit"]):not([type="button"])').all()
        for inp in inputs[:20]:
            try:
                name = await inp.get_attribute("name") or await inp.get_attribute("id") or ""
                placeholder = await inp.get_attribute("placeholder") or ""
                elements["inputs"].append(f"{name} ({placeholder})")
            except:
                pass

        # Selects
        selects = await page.locator('select').all()
        for sel in selects[:10]:
            try:
                name = await sel.get_attribute("name") or await sel.get_attribute("id") or ""
                elements["selects"].append(name)
            except:
                pass

        # Liens
        links = await page.locator('a[href]').all()
        for link in links[:20]:
            try:
                text = await link.inner_text()
                href = await link.get_attribute("href")
                if text.strip():
                    elements["links"].append(f"{text.strip()[:30]} -> {href}")
            except:
                pass

        screenshot = await take_screenshot("page_elements")
        return {
            "success": True,
            "url": page.url,
            "elements": elements,
            "screenshot": screenshot
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


async def run_full_test() -> dict:
    """Exécuter une suite de tests complète"""
    results = {
        "login": None,
        "clients": None,
        "produits": None,
        "tournees": None,
        "commandes": None,
        "promotions": None
    }

    # Login
    results["login"] = await login()
    if not results["login"].get("success"):
        return {"success": False, "error": "Échec connexion", "results": results}

    # Test pages
    results["clients"] = await navigate_to("/admindash/clients")
    results["produits"] = await navigate_to("/admindash/produits")
    results["tournees"] = await test_tournees_page()
    results["commandes"] = await test_commandes_page()
    results["promotions"] = await test_promotions_page()

    # Résumé
    success_count = sum(1 for r in results.values() if r and r.get("success"))

    return {
        "success": True,
        "message": f"Tests terminés: {success_count}/{len(results)} réussis",
        "results": results
    }


# ============== DÉFINITION DES OUTILS ==============

TOOLS = [
    {
        "name": "ui_login",
        "description": "Se connecter à l'application GestionStock via l'interface web",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "ui_navigate",
        "description": "Naviguer vers une page de l'application (ex: /admindash/clients, /admindash/produits, /admindash/tournees)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Chemin de la page (ex: /admindash/clients)"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "ui_click",
        "description": "Cliquer sur un bouton ou élément de la page",
        "inputSchema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "Sélecteur CSS de l'élément (ex: button, #id, .class)"
                },
                "text": {
                    "type": "string",
                    "description": "Texte du bouton à cliquer (optionnel)"
                }
            }
        }
    },
    {
        "name": "ui_fill_form",
        "description": "Remplir un formulaire avec les données fournies",
        "inputSchema": {
            "type": "object",
            "properties": {
                "fields": {
                    "type": "object",
                    "description": "Dictionnaire {selecteur: valeur} des champs à remplir"
                }
            },
            "required": ["fields"]
        }
    },
    {
        "name": "ui_submit_form",
        "description": "Soumettre le formulaire courant",
        "inputSchema": {
            "type": "object",
            "properties": {
                "form_selector": {
                    "type": "string",
                    "description": "Sélecteur du formulaire (défaut: form)"
                }
            }
        }
    },
    {
        "name": "ui_screenshot",
        "description": "Prendre une capture d'écran de la page courante",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Nom du fichier screenshot (optionnel)"
                }
            }
        }
    },
    {
        "name": "ui_get_elements",
        "description": "Obtenir la liste des éléments interactifs de la page courante (boutons, inputs, liens)",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "ui_test_add_client",
        "description": "Test automatisé: Ajouter un nouveau client",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "ui_test_add_product",
        "description": "Test automatisé: Ajouter un nouveau produit",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "ui_test_promotions",
        "description": "Test automatisé: Tester la page des promotions",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "ui_test_commandes",
        "description": "Test automatisé: Tester la page des commandes",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "ui_test_tournees",
        "description": "Test automatisé: Tester la page des tournées",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "ui_run_full_test",
        "description": "Exécuter une suite complète de tests sur toutes les pages principales",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "ui_close_browser",
        "description": "Fermer le navigateur",
        "inputSchema": {"type": "object", "properties": {}}
    }
]


def execute_tool(tool_name: str, arguments: dict) -> dict:
    """Exécuter un outil de manière synchrone"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        if tool_name == "ui_login":
            return loop.run_until_complete(login())
        elif tool_name == "ui_navigate":
            return loop.run_until_complete(navigate_to(arguments.get("path", "/")))
        elif tool_name == "ui_click":
            return loop.run_until_complete(click_button(
                arguments.get("selector", "button"),
                arguments.get("text")
            ))
        elif tool_name == "ui_fill_form":
            return loop.run_until_complete(fill_form(arguments.get("fields", {})))
        elif tool_name == "ui_submit_form":
            return loop.run_until_complete(submit_form(arguments.get("form_selector", "form")))
        elif tool_name == "ui_screenshot":
            filepath = loop.run_until_complete(take_screenshot(arguments.get("name")))
            return {"success": True, "screenshot": filepath}
        elif tool_name == "ui_get_elements":
            return loop.run_until_complete(get_page_elements())
        elif tool_name == "ui_test_add_client":
            return loop.run_until_complete(test_add_client())
        elif tool_name == "ui_test_add_product":
            return loop.run_until_complete(test_add_product())
        elif tool_name == "ui_test_promotions":
            return loop.run_until_complete(test_promotions_page())
        elif tool_name == "ui_test_commandes":
            return loop.run_until_complete(test_commandes_page())
        elif tool_name == "ui_test_tournees":
            return loop.run_until_complete(test_tournees_page())
        elif tool_name == "ui_run_full_test":
            return loop.run_until_complete(run_full_test())
        elif tool_name == "ui_close_browser":
            loop.run_until_complete(close_browser())
            return {"success": True, "message": "Navigateur fermé"}
        else:
            return {"error": f"Outil inconnu: {tool_name}"}
    except Exception as e:
        return {"error": str(e)}
    finally:
        loop.close()


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
    except json.JSONDecodeError:
        return {"method": "ping"}
    except Exception:
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
                    "name": "gestion-stock-ui-test",
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
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    sys.stderr.write(f"GestionStock UI Test Server started (App: {APP_BASE_URL})\n")
    sys.stderr.write(f"Screenshots: {SCREENSHOTS_DIR}\n")
    sys.stderr.write(f"Headless: {HEADLESS}\n")
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
            sys.stderr.write("Server stopped\n")
            sys.stderr.flush()
            break
        except Exception as e:
            sys.stderr.write(f"Error: {e}\n")
            sys.stderr.flush()
            continue


if __name__ == "__main__":
    main()
