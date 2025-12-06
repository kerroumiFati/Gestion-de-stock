# 📊 API d'Export de Rapports - Documentation

## Vue d'ensemble

Le système GestionStock propose maintenant des exports professionnels de rapports en formats **Excel (.xlsx)** et **PDF**. Ces rapports incluent des styles visuels, des tableaux structurés, et des résumés statistiques.

---

## 🎯 Endpoints Disponibles

### 1. Rapport de Valorisation du Stock

**Endpoint:** `GET /API/reports/stock-valuation/`

**Description:** Export complet de la valorisation du stock avec calcul de la valeur totale par produit.

**Query Parameters:**
- `format` (optionnel): Format d'export
  - `excel` (défaut): Fichier Excel (.xlsx)
  - `pdf`: Fichier PDF
- `warehouse` (optionnel): ID de l'entrepôt spécifique
  - Si non fourni, affiche tous les entrepôts

**Exemple d'utilisation:**
```bash
# Export Excel (tous les entrepôts)
GET /API/reports/stock-valuation/?format=excel

# Export PDF (entrepôt spécifique)
GET /API/reports/stock-valuation/?format=pdf&warehouse=1
```

**Contenu du rapport:**
- Référence produit
- Désignation
- Catégorie
- Quantité en stock
- Prix unitaire
- Valeur totale (Qté × Prix)
- Statut du stock (Normal, Alerte, Critique, Rupture)
- **Total général de la valorisation**

**Response:**
- Header: `Content-Disposition: attachment; filename="valorisation_stock_YYYYMMDD_HHMMSS.xlsx"`
- Content-Type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` (Excel) ou `application/pdf`

---

### 2. Rapport des Ventes

**Endpoint:** `GET /API/reports/sales/`

**Description:** Export détaillé des ventes avec totaux HT/TTC, statistiques de période.

**Query Parameters:**
- `format` (optionnel): Format d'export
  - `excel` (défaut)
  - `pdf`
- `start_date` (optionnel): Date de début (format YYYY-MM-DD)
- `end_date` (optionnel): Date de fin (format YYYY-MM-DD)

**Exemple d'utilisation:**
```bash
# Export Excel (toutes les ventes)
GET /API/reports/sales/?format=excel

# Export PDF (période spécifique)
GET /API/reports/sales/?format=pdf&start_date=2024-01-01&end_date=2024-12-31

# Export avec filtrage par dates
GET /API/reports/sales/?start_date=2025-01-01&end_date=2025-01-31
```

**Contenu du rapport:**
- Numéro de vente
- Date de vente
- Client (nom + prénom)
- Type de paiement (Espèces, Carte, Chèque, Virement, Crédit)
- Montant HT
- Montant TTC
- Remise appliquée (%)
- **Totaux généraux**
- **Statistiques:** Nombre de ventes, CA HT/TTC, Ticket moyen

**Response:**
- Header: `Content-Disposition: attachment; filename="rapport_ventes_YYYYMMDD_HHMMSS.xlsx"`
- Content-Type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` ou `application/pdf`

---

### 3. Rapport d'Inventaire Complet

**Endpoint:** `GET /API/reports/inventory/`

**Description:** Export exhaustif de tous les produits avec leurs caractéristiques et statuts.

**Query Parameters:**
- `format` (optionnel): Format d'export
  - `excel` (défaut)
  - `pdf`

**Exemple d'utilisation:**
```bash
# Export Excel
GET /API/reports/inventory/?format=excel

# Export PDF
GET /API/reports/inventory/?format=pdf
```

**Contenu du rapport:**
- Référence produit
- Code-barres
- Désignation complète
- Catégorie
- Fournisseur
- Quantité en stock
- Seuil d'alerte
- Prix unitaire
- Statut du stock
- **Statistiques:** Répartition des statuts (Rupture, Critique, Alerte, Normal)

**Response:**
- Header: `Content-Disposition: attachment; filename="inventaire_complet_YYYYMMDD_HHMMSS.xlsx"`
- Content-Type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` ou `application/pdf`

---

## 🔐 Authentification

**Tous les endpoints nécessitent une authentification.**

**Permission requise:** `IsAuthenticated`

**Headers requis:**
```http
Authorization: Token YOUR_AUTH_TOKEN
# OU
Cookie: sessionid=YOUR_SESSION_ID
```

---

## 📥 Exemples de Requêtes

### JavaScript (Fetch API)

```javascript
// Export Excel de la valorisation du stock
async function exportStockValuation() {
  const response = await fetch('/API/reports/stock-valuation/?format=excel', {
    method: 'GET',
    headers: {
      'Authorization': 'Token ' + localStorage.getItem('authToken')
    }
  });

  if (response.ok) {
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'valorisation_stock.xlsx';
    document.body.appendChild(a);
    a.click();
    a.remove();
  }
}

// Export PDF des ventes
async function exportSalesReport(startDate, endDate) {
  const params = new URLSearchParams({
    format: 'pdf',
    start_date: startDate,
    end_date: endDate
  });

  const response = await fetch(`/API/reports/sales/?${params}`, {
    method: 'GET',
    credentials: 'include' // Pour les sessions
  });

  if (response.ok) {
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    window.open(url); // Ouvre le PDF dans un nouvel onglet
  }
}
```

### Python (requests)

```python
import requests

# Configuration
BASE_URL = 'http://localhost:8000'
TOKEN = 'your_auth_token_here'

headers = {
    'Authorization': f'Token {TOKEN}'
}

# Export Excel - Valorisation du stock
response = requests.get(
    f'{BASE_URL}/API/reports/stock-valuation/',
    headers=headers,
    params={'format': 'excel'}
)

if response.status_code == 200:
    with open('valorisation_stock.xlsx', 'wb') as f:
        f.write(response.content)
    print("Export réussi!")

# Export PDF - Rapport de ventes avec dates
response = requests.get(
    f'{BASE_URL}/API/reports/sales/',
    headers=headers,
    params={
        'format': 'pdf',
        'start_date': '2025-01-01',
        'end_date': '2025-01-31'
    }
)

if response.status_code == 200:
    with open('rapport_ventes_janvier.pdf', 'wb') as f:
        f.write(response.content)
```

### cURL

```bash
# Export Excel - Inventaire complet
curl -X GET "http://localhost:8000/API/reports/inventory/?format=excel" \
  -H "Authorization: Token YOUR_TOKEN" \
  --output inventaire.xlsx

# Export PDF - Ventes (avec dates)
curl -X GET "http://localhost:8000/API/reports/sales/?format=pdf&start_date=2025-01-01&end_date=2025-12-31" \
  -H "Authorization: Token YOUR_TOKEN" \
  --output ventes_2025.pdf
```

---

## 📋 Structure des Fichiers Exportés

### Excel (.xlsx)

**Caractéristiques:**
- Styles professionnels (en-têtes bleus, bordures)
- Colonnes dimensionnées automatiquement
- Formats numériques avec séparateurs de milliers
- Ligne de total en gras
- Métadonnées (date, société)

**Sections:**
1. Titre du rapport (fusionné, centré)
2. Métadonnées (date génération, société)
3. En-tête de colonnes (fond bleu, texte blanc)
4. Données tabulaires
5. Ligne de total (si applicable)

### PDF

**Caractéristiques:**
- Orientation portrait ou paysage selon le rapport
- Tableau avec alternance de couleurs de lignes
- En-tête bleu marine
- Résumé statistique dans un encadré
- Marges professionnelles
- Police Helvetica

**Sections:**
1. Titre centré (police 16pt)
2. Métadonnées (date, période, société)
3. Tableau principal avec grille
4. Encadré de résumé (totaux, statistiques)

---

## 🎨 Personnalisation

### Modifier les styles Excel

Éditez `API/reports.py` dans la classe `ExcelReportGenerator`:

```python
# Changer la couleur d'en-tête
self.header_fill = PatternFill(
    start_color="366092",  # Bleu actuel
    end_color="366092",
    fill_type="solid"
)

# Modifier la police des titres
self.title_font = Font(bold=True, size=14)
```

### Modifier les styles PDF

Éditez `API/reports.py` dans la classe `PDFReportGenerator`:

```python
# Changer la couleur du tableau
('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),

# Modifier la taille de page
pagesize = landscape(A4)  # ou portrait(A4), letter, etc.
```

---

## 🔧 Traçabilité (Audit)

Tous les exports de rapports sont **automatiquement enregistrés** dans le système d'audit (`AuditLog`).

**Informations enregistrées:**
- Utilisateur qui a exporté
- Type de rapport
- Format (Excel/PDF)
- Paramètres (dates, entrepôt)
- Timestamp
- Adresse IP
- User-Agent

**Requête d'audit:**
```bash
GET /API/audit-logs/?action__startswith=report.
```

---

## 🐛 Gestion des Erreurs

### Erreur 400 - Format de date invalide

```json
{
  "error": "Format de date invalide: time data '2025-13-01' does not match format '%Y-%m-%d'"
}
```

**Solution:** Utiliser le format YYYY-MM-DD

### Erreur 404 - Entrepôt non trouvé

Si `warehouse=999` n'existe pas:
```python
DoesNotExist: Warehouse matching query does not exist.
```

### Erreur 500 - Erreur interne

```json
{
  "error": "Détails de l'erreur..."
}
```

**Vérifier:** Les logs Django pour plus de détails

---

## 📊 Exemples de Rapports Générés

### 1. Valorisation du Stock (Excel)

| Référence | Désignation | Catégorie | Qté Stock | Prix Unit. | Valeur Stock | Statut |
|-----------|-------------|-----------|-----------|------------|--------------|--------|
| PROD-001 | Laptop Dell XPS 15 | Informatique | 25 | 1200.00 | 30,000.00 | Normal |
| PROD-002 | Souris Logitech | Accessoires | 3 | 25.00 | 75.00 | Critique |
| ... | ... | ... | ... | ... | ... | ... |
| **TOTAL** | | | **145** | | **125,450.50** | |

### 2. Rapport des Ventes (PDF)

**Période:** 01/01/2025 - 31/01/2025

| N° Vente | Date | Client | Type Paiement | Montant HT | Montant TTC |
|----------|------|--------|---------------|------------|-------------|
| V-0001 | 05/01/2025 | Jean Dupont | Carte | 1,500.00 | 1,800.00 |
| V-0002 | 07/01/2025 | Marie Martin | Espèces | 320.00 | 384.00 |

**Résumé:**
- Nombre de ventes: 145
- CA HT: 125,450.00 €
- CA TTC: 150,540.00 €
- Ticket moyen: 1,038.21 €

---

## 🚀 Intégration Frontend

### Bouton d'export dans votre interface

```html
<div class="export-buttons">
  <button onclick="exportReport('stock-valuation', 'excel')">
    📊 Export Stock (Excel)
  </button>
  <button onclick="exportReport('stock-valuation', 'pdf')">
    📄 Export Stock (PDF)
  </button>

  <button onclick="exportReport('sales', 'excel')">
    💰 Export Ventes (Excel)
  </button>
  <button onclick="exportReport('sales', 'pdf')">
    💰 Export Ventes (PDF)
  </button>
</div>

<script>
async function exportReport(type, format) {
  const endpoints = {
    'stock-valuation': '/API/reports/stock-valuation/',
    'sales': '/API/reports/sales/',
    'inventory': '/API/reports/inventory/'
  };

  const url = `${endpoints[type]}?format=${format}`;

  try {
    const response = await fetch(url, {
      credentials: 'include'
    });

    if (response.ok) {
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;

      // Extraire le nom de fichier du header Content-Disposition
      const contentDisposition = response.headers.get('Content-Disposition');
      const filename = contentDisposition
        ? contentDisposition.split('filename=')[1].replace(/"/g, '')
        : `rapport.${format === 'pdf' ? 'pdf' : 'xlsx'}`;

      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);

      alert('Export réussi!');
    } else {
      const error = await response.json();
      alert('Erreur: ' + error.error);
    }
  } catch (e) {
    alert('Erreur réseau: ' + e.message);
  }
}
</script>
```

---

## 📦 Dépendances

Les bibliothèques suivantes ont été ajoutées au projet:

```txt
openpyxl>=3.1.0      # Génération Excel
reportlab>=4.0.0     # Génération PDF
```

**Installation:**
```bash
pip install -r requirements.txt
```

---

## 🎓 Notes Techniques

### Performance

- Les rapports sont générés **à la demande** (pas de cache)
- Pour de gros volumes (>10,000 produits), prévoir 2-5 secondes de génération
- Les fichiers sont streamés directement (pas de stockage temporaire sur disque)

### Mémoire

- Les buffers `BytesIO` sont utilisés pour éviter l'écriture sur disque
- Libération automatique de la mémoire après envoi

### Sécurité

- Authentification obligatoire
- Audit automatique de tous les exports
- Pas d'injection SQL possible (utilise l'ORM Django)

### Limites

- Pas de limite sur le nombre de lignes exportées
- Format Excel: ~1 million de lignes max (limite OpenPyXL)
- Format PDF: Recommandé jusqu'à 1000 lignes pour lisibilité

---

## 📞 Support

Pour toute question ou problème:
1. Vérifier les logs Django
2. Consulter `/API/audit-logs/` pour tracer les exports
3. Tester avec cURL d'abord pour isoler les problèmes

---

**Version:** 1.0
**Dernière mise à jour:** 2025-01-27
