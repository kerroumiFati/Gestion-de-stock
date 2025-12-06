# 🌍 Guide du Système Multi-Devises et Taux de Change

## 📋 Vue d'ensemble

Le système multi-devises a été intégré dans votre application de gestion de stock pour permettre :
- Gestion de multiples devises
- Taux de change automatiques
- Conversions en temps réel
- Ventes dans différentes devises
- Calculs automatiques des totaux

## 🏗️ Architecture

### Modèles Django ajoutés :

#### Currency (Devise)
- **code** : Code ISO 4217 (EUR, USD, MAD, etc.)
- **name** : Nom complet de la devise
- **symbol** : Symbole (€, $, DH, etc.)
- **is_default** : Devise par défaut du système
- **is_active** : Devise active/inactive

#### ExchangeRate (Taux de Change)
- **from_currency** : Devise source
- **to_currency** : Devise destination
- **rate** : Taux de change (6 décimales)
- **date** : Date du taux
- **is_active** : Taux actif/inactif

### Modèles modifiés :

#### Produit
- **currency** : Devise du prix (optionnel, utilise devise par défaut si vide)
- Méthode `get_price_in_currency()` pour conversion automatique

#### Vente
- **currency** : Devise de la vente
- **exchange_rate_snapshot** : Taux figé au moment de la vente
- Méthode `recompute_totals()` avec gestion multi-devises
- Méthode `get_total_in_currency()` pour conversion

#### LigneVente
- **currency** : Devise du prix unitaire
- Méthode `get_total_in_sale_currency()` pour conversion

## 🚀 Fonctionnalités

### 1. Gestion des Devises

#### Devises pré-configurées :
- **EUR** (Euro) - Devise par défaut
- **USD** (Dollar américain)
- **MAD** (Dirham marocain)
- **GBP** (Livre sterling)
- **JPY** (Yen japonais)
- **CHF** (Franc suisse)
- **CAD** (Dollar canadien)

#### Actions disponibles :
- ✅ Ajouter de nouvelles devises
- ⭐ Définir la devise par défaut
- 🗑️ Supprimer des devises (sauf la devise par défaut)
- 👁️ Visualiser toutes les devises actives

### 2. Gestion des Taux de Change

#### Taux pré-configurés :
- EUR/USD : 1.10
- EUR/MAD : 10.80
- USD/EUR : 0.91
- USD/MAD : 9.80
- MAD/EUR : 0.093
- MAD/USD : 0.102
- *(et autres...)*

#### Fonctionnalités :
- ✅ Ajouter des taux manuellement
- 🔄 Conversion automatique (directe, inverse, ou via devise par défaut)
- 📅 Historique des taux par date
- 🗑️ Suppression des taux obsolètes

### 3. Convertisseur Intégré

#### Interface de conversion :
- Saisie du montant
- Sélection devise source
- Sélection devise destination
- Calcul instantané
- Affichage du taux utilisé

### 4. Ventes Multi-Devises

#### Nouveautés dans l'interface de vente :
- 💱 Sélecteur de devise pour la vente
- 🔄 Conversion automatique des prix produits
- 📊 Totaux calculés dans la devise de vente
- 💾 Sauvegarde des taux au moment de la vente

## 📍 Accès aux Fonctionnalités

### Interface de Vente (`/admindash/ventes`)

#### Onglet "Nouvelle Vente" :
1. **Sélecteur de devise** : Choisir la devise de la vente
2. **Conversion automatique** : Les prix des produits sont convertis automatiquement
3. **Totaux multi-devises** : Calculs dans la devise sélectionnée

#### Onglet "Devises & Taux" :
1. **Gestion des Devises** :
   - Ajouter : Code (3 lettres), Nom, Symbole
   - Définir par défaut : Bouton étoile
   - Supprimer : Bouton corbeille

2. **Gestion des Taux** :
   - Ajouter : Devise source, Devise destination, Taux
   - Supprimer : Bouton corbeille

3. **Convertisseur** :
   - Montant, Devise source, Devise destination
   - Résultat instantané avec taux utilisé

## 🔧 API Endpoints

### Devises
| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/API/currencies/` | GET | Liste des devises |
| `/API/currencies/` | POST | Créer une devise |
| `/API/currencies/{id}/` | PUT/DELETE | Modifier/Supprimer |
| `/API/currencies/default/` | GET | Devise par défaut |
| `/API/currencies/{id}/set_default/` | POST | Définir par défaut |

### Taux de Change
| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/API/exchange-rates/` | GET | Liste des taux |
| `/API/exchange-rates/` | POST | Créer un taux |
| `/API/exchange-rates/{id}/` | DELETE | Supprimer un taux |
| `/API/exchange-rates/convert/` | GET | Convertir un montant |
| `/API/exchange-rates/rates_matrix/` | GET | Matrice complète |

### Paramètres de conversion
- `amount` : Montant à convertir
- `from_currency` : ID devise source
- `to_currency` : ID devise destination
- `date` : Date du taux (optionnel, format YYYY-MM-DD)

## 💡 Exemples d'utilisation

### 1. Conversion via API
```bash
GET /API/exchange-rates/convert/?amount=100&from_currency=1&to_currency=2
```
Résultat :
```json
{
  "original_amount": 100.0,
  "converted_amount": 110.0,
  "from_currency": "EUR",
  "to_currency": "USD",
  "exchange_rate": 1.1,
  "date": "2025-10-23"
}
```

### 2. Vente multi-devise
1. Client français → Devise EUR
2. Client américain → Devise USD
3. Produits automatiquement convertis
4. Totaux calculés dans la bonne devise

### 3. Gestion des stocks
- Produits avec prix en devise originale
- Conversion automatique lors de l'affichage
- Cohérence des calculs multi-devises

## ⚙️ Configuration Avancée

### Ajouter une nouvelle devise
```python
Currency.objects.create(
    code='CNY',
    name='Yuan chinois',
    symbol='¥',
    is_active=True
)
```

### Ajouter un taux de change
```python
ExchangeRate.objects.create(
    from_currency=eur,
    to_currency=cny,
    rate=7.85,
    date=timezone.now().date()
)
```

### Conversion programmatique
```python
# Convertir 100 EUR en USD
converted = ExchangeRate.convert_amount(
    Decimal('100.00'), eur, usd
)
```

## 🔐 Sécurité et Validation

### Validations implémentées :
- Code devise : 3 caractères exactement
- Une seule devise par défaut
- Taux de change positifs
- Devises source/destination différentes
- Gestion des erreurs de conversion

### Gestion des erreurs :
- Taux manquant → Recherche taux inverse
- Pas de taux direct → Conversion via devise par défaut
- Erreurs réseau → Messages utilisateur explicites

## 📊 Rapports et Statistiques

### Statistiques multi-devises :
- CA par devise
- Conversion en devise par défaut pour totaux globaux
- Historique des taux utilisés

### Exports :
- Ventes avec devises originales
- Conversions automatiques pour reporting
- Cohérence des données historiques

## 🔄 Maintenance

### Mise à jour des taux :
1. **Manuelle** : Via l'interface web
2. **API** : Endpoint dédié pour imports
3. **Automatique** : Intégration services externes (à développer)

### Sauvegarde :
- Taux historiques conservés
- Snapshots dans les ventes
- Traçabilité complète

## 🎯 Roadmap

### Fonctionnalités futures :
- 🔄 Synchronisation automatique des taux (API externes)
- 📈 Graphiques d'évolution des taux
- 💹 Alertes de variation de taux
- 🌐 Support de plus de devises
- 📱 Application mobile
- 🔗 Intégration systèmes comptables

---

## ✅ Système Multi-Devises Opérationnel !

Le système complet de gestion des devises et taux de change est maintenant **pleinement fonctionnel** et intégré dans votre application de gestion de stock.

**Avantages :**
- ✅ Ventes internationales simplifiées
- ✅ Conversions automatiques précises
- ✅ Interface utilisateur intuitive
- ✅ API complète pour intégrations
- ✅ Historique et traçabilité
- ✅ Extensibilité pour futures devises

*Votre système de gestion de stock est maintenant prêt pour les opérations internationales !* 🌍💱