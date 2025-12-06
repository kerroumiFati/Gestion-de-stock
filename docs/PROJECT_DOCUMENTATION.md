# GestionStock - Documentation complète

Cette documentation couvre l'architecture, l'installation, la configuration, les modèles de données, les APIs, l'interface front, les flux métier (achats, bons de livraison, factures), la sécurité et le dépannage.

Sommaire
- Présentation
- Architecture (Django + DRF + Front jQuery)
- Installation et configuration
  - Environnement (Python/venv)
  - Dépendances
  - Base de données (SQLite par défaut, MySQL en option)
  - Démarrage
- Modèles (domaine)
  - Fournisseur, Produit, Client, Achat
  - BonLivraison, LigneLivraison
  - Facture, LigneFacture
- API REST (endpoints)
- Frontoffice (UI) et scripts
- Flux métier
  - Achats (vente au client)
  - Bons de livraison
  - Factures (émission, paiement)
- Sécurité (CSRF, Auth, Permissions)
- Dépannage (troubleshooting)
- Roadmap / Améliorations

## Présentation
Application de gestion de stock basée sur Django et Django REST Framework avec une interface front légère (jQuery + DataTables + Bootstrap). Elle permet de gérer les fournisseurs, produits, clients, achats, bons de livraison (BL) et factures clients.

## Architecture
- Backend: Django 4.2 LTS
  - Apps: `API` (REST), `frontoffice` (pages/templates)
  - DRF + django-filter pour API et filtrage
- Front: jQuery, DataTables, Bootstrap via `static/`
- Templates: dans `templates/frontoffice/`
- Routage global: `Gestion_stock/urls.py`

## Installation et configuration
### Prérequis
- Python 3.10+ (testé avec 3.13)
- pip

Optionnel mais recommandé: environnement virtuel
- Windows: `python -m venv .venv && .venv\\Scripts\\activate`
- macOS/Linux: `python -m venv .venv && source .venv/bin/activate`

### Dépendances
```
pip install "django>=4.2,<5.0" djangorestframework django-filter
```

### Base de données
- Par défaut: SQLite (fichier `db.sqlite3`) configuré dans `Gestion_stock/settings.py`.
- MySQL (option): installer `mysqlclient` et configurer `DATABASES`:
```
DATABASES = {
  'default': {
    'ENGINE': 'django.db.backends.mysql',
    'NAME': 'gestionstockdjango',
    'USER': 'root',
    'PASSWORD': '...',
    'HOST': 'localhost',
    'PORT': '3306',
    'OPTIONS': {'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"}
  }
}
```

Appliquer les migrations:
```
python manage.py migrate
```
Créer un superuser (optionnel):
```
python manage.py createsuperuser
```

Démarrer:
```
python manage.py runserver
```
- API: http://localhost:8000/API/
- Dashboard: http://localhost:8000/admindash/

### Réglages utiles
- `DEBUG=True` pour le dev, `False` en prod
- `ALLOWED_HOSTS` à configurer en prod
- `DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'` (réglé)

## Modèles (domaine)
### Fournisseur
- `libelle`, `telephone`, `email`, `adresse`

### Produit
- `reference` (unique), `designation`, `prixU`, `quantite`, `fournisseur`

### Client
- `nom`, `prenom`, `email`, `telephone`, `adresse`

### Achat
- `date_Achat`, `quantite`, `client`, `produit`
- Utilisé par l'UI Achats pour enregistrer une vente simple et décrémenter le stock.

### BonLivraison
- `numero` (unique), `date_creation`, `client`, `statut` (draft/validated/canceled), `observations`
- Lignes: `LigneLivraison(bon, produit, quantite, prixU_snapshot)`
- Action `valider`: vérifie le stock de chaque produit et décrémente en cas de validation.

### Facture
- `numero` (unique), `date_emission`, `client`, `bon_livraison` (optionnel), `statut` (draft/issued/paid/canceled)
- `tva_rate`, `total_ht`, `total_tva`, `total_ttc`
- Lignes: `LigneFacture(facture, produit, designation, quantite, prixU_snapshot)`
- Méthode `recompute_totals()` pour calculer HT/TVA/TTC.

## API REST (endpoints)
Base: `/API/`
- Fournisseurs: `/fournisseurs/`
- Produits: `/produits/`
  - Filtrage: `?quantite__gte=1`
  - `GET /produits/{id}/stock/` -> {book_quantity, moves_sum, delta}
- Clients: `/clients/`
- Achats: `/achats/`
- Bons de livraison: `/bons/`
  - `POST /bons/{id}/valider/`
- Factures: `/factures/`
  - `POST /factures/from_bl/` (créer depuis BL validé)
  - `POST /factures/{id}/issue/` (émettre)
  - `POST /factures/{id}/pay/` (payer)
  - `GET  /factures/{id}/printable/` (HTML imprimable)
- Inventaires: `/inventaires/` (CRUD)
  - `POST /inventaires/{id}/validate/` (valider et créer les écarts)
- Mouvements: `/mouvements/` (lecture seule)
  - Filtres: `?produit=<id>&source=BL|...&date_after=<ISO>&date_before=<ISO>`

Tous les endpoints DRF utilisent des trailing slashes `/` et renvoient du JSON; ajouter `?format=json` côté front si besoin.

## Frontoffice (UI) et scripts
- Layout: `templates/frontoffice/master_page.html` (sidebar, #main-content)
- Navigation dynamique: `static/script/redirect.js`
- Pages:
  - Produits: `templates/frontoffice/page/produit.html` (+ `static/script/produit.js`)
  - Achats: `templates/frontoffice/page/achat.html` (+ `static/script/achat.js`)
  - Factures: `templates/frontoffice/page/facture.html` (+ `static/script/facture.js`)
- Inventaires: `templates/frontoffice/page/inventaire.html` (+ `static/script/inventaire.js`)
- Mouvements: `templates/frontoffice/page/mouvements.html` (+ `static/script/mouvements.js`)

Scripts (extraits):
- `produit.js`: CRUD produits, sélecteur fournisseurs, gestion risk (endpoint à améliorer)
- `achat.js`: DataTables tachat, POST achat, décrémentation produit via PUT
- `facture.js`: liste factures, création depuis BL, issue/pay, printable

CSRF: ajouter l'en-tête X-CSRFToken pour POST/PUT/DELETE. Exemple:
```
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
const csrftoken = getCookie('csrftoken');
$.ajaxSetup({headers: {'X-CSRFToken': csrftoken}});
```

## Flux métier

### Stock source de vérité
- Le stock fiable est la somme des `StockMove.delta` par produit.
- Le champ `Produit.quantite` est maintenu pour compatibilité UI et mis à jour lors des opérations métier (BL, inventaire...).
- Endpoint `GET /API/produits/{id}/stock/` expose book vs mouvements.

### Achats (vente)
- Création d'un `Achat` décrémente le stock du `Produit` (via logique front existante);
  une implémentation côté serveur via signaux ou services est recommandée pour fiabilité.

### Bons de livraison
- Création BL (draft) + lignes
- Validation BL: contrôle de stock, décrémentation, statut -> validated

### Factures
- Création manuelle ou depuis BL (`from_bl`): lignes préremplies, totaux recalculés
- Issue: statut -> issued (verrouille les modifications)
- Pay: statut -> paid
- Printable: export imprimable HTML

## Sécurité
- Auth Django (login UI à corriger pour appeler `login(request, user)`).
- Permissions DRF: à ajouter selon besoin (IsAuthenticated, IsAdminUser...)
- CSRF obligatoire pour les requêtes d'écriture via AJAX (voir ci-dessus)

## Dépannage
- DataTables AJAX error: vérifier l'URL (trailing slash), statut HTTP en console, serveur démarré
- Migrations: `python manage.py makemigrations` puis `python manage.py migrate`
- Static: en prod, collectstatic et servir via le serveur HTTP

## Roadmap / Améliorations
- Export PDF serveur (WeasyPrint/xhtml2pdf)
- UI création/édition ligne facture sans BL
- Numérotation séquentielle par année
- Mouvement de stock (journal) + inventaires
- Rôles/permissions fine-grained
- Tests unitaires et d'intégration
