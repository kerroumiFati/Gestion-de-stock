# GestionStock – Documentation complète du logiciel

Ce document présente une vue d’ensemble fonctionnelle et technique du logiciel GestionStock, ainsi que des guides d’installation, de configuration, d’utilisation et de dépannage. Il consolide et complète les informations présentes dans les fichiers README, docs/* et le code source.

---

## 1. Présentation générale

GestionStock est une application web de gestion des stocks, des produits, des achats, des ventes, des entrepôts et des documents (bons de livraison, factures). Elle propose :
- Gestion du catalogue produits (catégories, fournisseurs, prix, devises, seuils d’alerte)
- Suivi des achats et des ventes (lignes, totaux, snapshots de prix)
- Entrepôts et mouvements de stock (transferts, pertes, inventaires)
- Devises et taux de change avec conversions
- Tableau de bord, statistiques, alertes stock
- Administration (utilisateurs, rôles, permissions, audit)

Stack :
- Backend : Django + Django REST Framework
- Frontoffice : templates Django + JS (fetch API), DataTables, Bootstrap
- Base de données : SQLite (dev), compatible Postgres/MySQL
- Déploiement : guides Railway/Vercel (voir fichiers Railway/Vercel), Procfile (gunicorn)

---

## 2. Architecture et composants

- Gestion_stock/ (projet Django)
  - settings.py, urls.py, wsgi/asgi.py
- API/ (app Django)
  - models.py : modèles (Produit, Categorie, Fournisseur, Achat, Vente, Currency, ExchangeRate, Warehouse, StockMove, Inventaire, BonLivraison, Facture, etc.)
  - serializers.py : sérialise les modèles pour l’API REST
  - views.py : ViewSets DRF + APIView pour endpoints spéciaux (statistiques, alertes…)
  - urls.py : routes API (/API/…)
  - migrations/ : schéma base
  - audit.py : journalisation d’actions
- frontoffice/
  - views.py : vues HTML, authentification, administration simple
  - templates/frontoffice/… : pages UI (master_page, produit, achat, vente, inventaire, mouvements, facture…)
  - static/script/*.js : scripts front (produit.js, achat.js, …)

Flux général :
- Le front charge des fragments HTML (templates) et utilise fetch() pour appeler l’API REST.
- L’API DRF expose des ViewSets pour CRUD et des endpoints dédiés pour rapports/agrégats.

---

## 3. Installation et lancement (développement)

Prérequis :
- Python 3.10+
- pip / venv
- (Optionnel) Node/npm si vous modifiez les assets

Étapes :
1) Créer et activer un environnement virtuel
   - Windows : `py -m venv .venv && .venv\\Scripts\\activate`
   - Unix/Mac : `python3 -m venv .venv && source .venv/bin/activate`
2) Installer les dépendances Python
   - `pip install -r requirements.txt`
3) Configurer l’environnement
   - Dupliquer `.env.example` en `.env` et ajuster si nécessaire
4) Appliquer les migrations
   - `python manage.py migrate`
5) Démarrer le serveur
   - `python manage.py runserver`
6) Accéder à l’app
   - Frontoffice : `http://127.0.0.1:8000/` (login)
   - API REST : `http://127.0.0.1:8000/API/`

Comptes : créez un superuser si besoin : `python manage.py createsuperuser`.

---

## 4. Configuration

- Fichier `Gestion_stock/settings.py` : base de données, sécurité, apps installées.
- Devises : définir une devise par défaut (Currency.is_default = True). Voir API Currency/ExchangeRate.
- Permissions : certaines vues API sont publiques (AllowAny) pour le chargement front (catégories, fournisseurs, produits, statistiques, alertes). Adaptez selon votre politique de sécurité.

---

## 5. Modèles de données (principaux)

- Categorie(nom, parent, is_active, couleur, icone)
  - Arbre de catégories, helpers get_full_path, get_all_children.
- Fournisseur(libelle, téléphone, email, adresse)
- Currency(code, name, symbol, is_default, is_active)
- ExchangeRate(from_currency, to_currency, rate, date)
  - Méthodes : get_rate, convert_amount
- Produit(reference, code_barre, designation, description, categorie, prixU, currency, quantite, seuils, unite_mesure, fournisseur)
  - Helpers sur le stock : statut, classes, pourcentages, suggestion de réassort
  - Conversion prix vers autre devise
- Client(nom, prenom, …)
- Achat(date_Achat, date_expiration, quantite, prix_achat, client, produit)
  - Total calculable: prix_achat × quantite
- BonLivraison(numero, date, client, statut) + LigneLivraison(produit, quantite, prixU_snapshot)
- Facture(numero, date, client, tva, totaux) + LigneFacture(produit, designation, quantite, prixU_snapshot)
- Warehouse(name, code) + ProductStock(produit, warehouse, quantity)
- StockMove(produit, warehouse?, delta, source, ref_id, date, note)
- InventorySession(numero, date, statut, …) + InventoryLine(produit, counted_qty, snapshot_qty, …)
- Vente(numero, date_vente, client, type_paiement, statut, currency, exchange_rate_snapshot, total_ht, total_ttc, remise, observations) + LigneVente(produit, designation, quantite, prixU_snapshot, currency)
- AuditLog(actor, action, target, metadata, …)

---

## 6. API REST (principaux endpoints)

Base : `/API/`
- Catégories : `/categories/` (CRUD, +actions tree/roots/products)
- Fournisseurs : `/fournisseurs/` (CRUD)
- Produits : `/produits/` (CRUD) + `/produits/{id}/stock/`
- Clients : `/clients/` (CRUD)
- Achats : `/achats/` (CRUD)
- BL : `/bons/` (CRUD) + `POST /bons/{id}/valider/`
- Factures : `/factures/` (CRUD)
  - `POST /factures/from_bl/`, `/factures/{id}/issue/`, `/factures/{id}/pay/`, `/factures/{id}/printable/`
- Inventaires : `/inventaires/` (CRUD) + `POST /inventaires/{id}/validate/`
- Mouvements : `/mouvements/` (CRUD) + `POST /mouvements/transfer/`, `POST /mouvements/loss/`, `POST /mouvements/outflow/`
- Devises : `/currencies/` (CRUD), `/exchange-rates/` (CRUD)
- Statistiques/Alertes/Comptes : `/statistics/charts/`, `/alerts/`, `/prod/count/`
- Administration sécurité : `/users/`, `/roles/`, `/permissions/`, `/audit-logs/`

Notes :
- Tous les endpoints renvoient du JSON (DRF). Trailing slash requis.
- Certains endpoints sont publics pour permettre le rendu du front sans authentification stricte. Ajustez `permission_classes` selon vos besoins.

---

## 7. Interface Utilisateur (frontoffice)

- Layout principal : `templates/frontoffice/master_page.html`
  - Sidebar de navigation
  - Injection des pages via `show(name)` (scripts front `redirect.js`)
- Pages clés :
  - Produits : `templates/frontoffice/page/produit.html`
    - Formulaire : référence, code-barres, désignation, catégorie, fournisseur, Prix U
    - Tableau produits (CRUD) – script `static/script/produit.js`
  - Achats : `templates/frontoffice/page/achat.html`
    - Quantité, Prix d’achat unitaire, Total auto (readonly), client, filtre produit (référence/code-barres)
    - Table Achats (CRUD) – script `static/script/achat.js`
  - Ventes, Factures, Inventaires, Mouvements, Entrepôts, Statistiques – pages dédiées + scripts correspondants

Comportements front importants :
- Les listes Catégories/Fournisseurs sont chargées via fetch sur `/API/categories/` et `/API/fournisseurs/`.
- Le script produit inclut des garde-fous pour éviter les doublons d’initialisation (utile si le contenu est injecté dynamiquement).

---

## 8. Gestion des devises et taux de change

- Chaque produit peut avoir une devise propre (sinon la devise par défaut du système est utilisée).
- ExchangeRate gère les conversions (directes, inverses ou via la devise par défaut).
- Ventes : les lignes conservent un snapshot de prix et une devise; les totaux de vente sont recomputés dans la devise de la vente, avec conversion si nécessaire.
- Achats : le prix d’achat unitaire + total sont manipulés dans la devise du produit (symbole exposé côté API pour affichage front). 

---

## 9. Achats – logique de calcul

- Champs : quantite, prix_achat, date_Achat, date_expiration, client, produit
- L’API sérialise `total_achat = prix_achat × quantite` et expose `currency_symbol` du produit.
- Front : champ “Total (auto)” readonly, calculé dynamiquement côté JS lors de la saisie.

---

## 10. Entrepôts et mouvements

- ProductStock par entrepôt, cumulé en Produit.quantite pour compatibilité.
- Mouvements (StockMove) : entrées/sorties, transfert, pertes/casse/expiration.
- Inventaire : sessions, lignes avec counted_qty vs snapshot, validation qui génère des mouvements d’écart si nécessaire.

---

## 11. Sécurité, rôles et audit

- Authentification : Django auth (utilisateurs, groupes)
- Permissions DRF :
  - APIView sans queryset (alerts, charts, counts) : AllowAny par défaut (ajustable)
  - ViewSets produits/fournisseurs/catégories : AllowAny pour alimentation front (ajustable)
- Administration : pages front simples pour gérer utilisateurs et rôles (frontoffice/views.py)
- Audit : chaque action clé (create/update/delete/validate) est journalisée via AuditLog

---

## 12. Déploiement

- Railway/Vercel : voir RAILWAY_*.md, VERCEL_*.md, `railway.json`, `vercel.json`, `Procfile`.
- Variables d’environnement : configurez la DB, debug, hôte, etc.
- Static files : servez les fichiers statiques via le service d’hébergement ou un CDN.

---

## 13. Dépannage (Troubleshooting)

- Boucles de requêtes front (selects vides, fetch en rafale)
  - Vérifiez que les scripts ne sont pas inclus deux fois
  - Garde-fous présents dans `static/script/produit.js` : `window.__rovodev_produit_loaded`, `__rovodev_inited`
  - Si contenu injecté dynamiquement, un `MutationObserver` appelle `init()` une seule fois
- Erreur DB `OperationalError: table API_achat has no column named prix_achat`
  - Appliquer les migrations (`python manage.py migrate`)
  - Une migration ajoute `prix_achat` sur `Achat`
- DjangoModelPermissions assertion sur APIView
  - Définit `permission_classes = [AllowAny]` (ou autre) sur APIView sans queryset
- Listes Catégories/Fournisseurs vides
  - Vérifier permissions API + fetch côté front
  - Vérifier qu’il existe des données en base

---

## 14. Bonnes pratiques et TODO

- Valider côté backend les champs obligatoires (ex : Prix U) et bornes (min/max)
- Uniformiser les permissions (publique vs authentifiée) selon votre contexte
- Ajouter des tests unitaires DRF pour les endpoints critiques (ventes, inventaires, conversions devises)
- Documenter les webhooks/exports si ajoutés ultérieurement

---

## 15. Journal des changements (extraits récents)

- Ajout migration `prix_achat` sur `Achat`
- Correction doublon “Date d’expiration” dans Achats
- Ajout champ “Prix U” (UI) dans Produits + support JS
- Corrections permissions APIView (alerts, charts, counts)
- Garde-fous anti-boucle d’initialisation dans `produit.js`

---

## 16. Annexes

- Endpoints de conversion devise (ExchangeRate)
- Exemples de payloads (POST/PUT) pour Produits, Achats, Ventes
- Règles de calcul des totaux (Vente: recompute_totals, Facture: recompute_totals)

---

Besoin d’aide supplémentaire ?
- Vous pouvez créer un ticket (Jira) pour suivre les TODO/évolutions.
- Je peux aussi publier cette documentation dans Confluence ou préparer une Pull Request pour l’intégrer au dépôt principal.
