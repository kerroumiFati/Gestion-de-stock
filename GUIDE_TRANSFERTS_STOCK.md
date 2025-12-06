# 📦 Guide d'Utilisation - Interface Admin de Gestion des Transferts de Stock

## 🎯 Vue d'ensemble

Cette interface admin vous permet de gérer facilement les transferts de stock entre entrepôts, notamment pour charger les vans de distribution.

## 🚀 Installation et Configuration

### 1. Appliquer les migrations

```bash
cd C:\Users\KB\Documents\autre\GestionStock-django-master\GestionStock-django-master
python manage.py migrate
```

### 2. Créer un superutilisateur (si nécessaire)

```bash
python manage.py createsuperuser
```

### 3. Démarrer le serveur

```bash
python manage.py runserver
```

### 4. Accéder à l'admin

Ouvrez votre navigateur et allez sur : `http://localhost:8000/admin/`

---

## 📋 Fonctionnalités Disponibles

### 1️⃣ **Tableau de Bord des Vans**

📍 **URL** : `/admin/API/transfertstock/stock-dashboard/`

**Fonctionnalités** :
- Vue d'ensemble de tous les vans
- Stock de chaque van en temps réel
- Valeur totale du stock par van
- Livreur assigné à chaque van
- Top 10 des produits par van

**Comment y accéder** :
1. Connectez-vous à l'admin Django
2. Allez dans **API** → **Transferts de stock**
3. En haut, vous verrez l'URL personnalisée pour le tableau de bord

---

### 2️⃣ **Charger un Van Rapidement**

📍 **URL** : `/admin/API/transfertstock/charger-van/`

**Fonctionnalités** :
- Formulaire simple pour charger un van
- Validation automatique du transfert
- Vérification du stock disponible
- Création automatique des mouvements de stock

**Mode d'emploi** :

1. **Sélectionner le van** (entrepôt mobile)
2. **Choisir l'entrepôt source** (d'où provient le stock)
3. **Lister les produits** au format :
   ```
   PROD-001,50
   PROD-002,30
   PROD-003,100
   ```

4. **Cliquer sur "Charger le van"**

Le système va :
- ✅ Créer un transfert avec numéro automatique
- ✅ Vérifier le stock disponible
- ✅ Valider automatiquement le transfert
- ✅ Créer les mouvements de stock (sortie source + entrée van)
- ✅ Mettre à jour les quantités

---

### 3️⃣ **Gestion Complète des Transferts**

📍 **URL** : `/admin/API/transfertstock/`

**Liste des transferts avec** :
- Numéro de transfert auto-généré (TRANS-YYYYMMDD-NNNN)
- Date de création
- Entrepôt source → Entrepôt destination
- Statut coloré (Brouillon, Validé, Annulé)
- Nombre de lignes et de produits
- Demandeur

**Actions en masse disponibles** :
1. ✅ **Valider les transferts** - Valide plusieurs transferts en une fois
2. ❌ **Annuler les transferts** - Annule les transferts sélectionnés
3. 📊 **Exporter en CSV** - Exporte la liste des transferts

**Filtres disponibles** :
- Par statut
- Par date
- Par entrepôt source
- Par entrepôt destination

---

### 4️⃣ **Créer un Transfert Manuel**

**Étapes** :

1. Allez dans **API** → **Transferts de stock** → **Ajouter**

2. **Remplissez les champs** :
   - **Entrepôt source** : L'entrepôt d'origine
   - **Entrepôt destination** : Le van ou autre entrepôt
   - **Notes** : Informations complémentaires

3. **Ajoutez des produits** (lignes de transfert) :
   - Cliquez sur "Ajouter une ligne de transfert"
   - Sélectionnez le produit (recherche par référence)
   - Indiquez la quantité
   - Le stock disponible s'affiche automatiquement

4. **Sauvegardez** en tant que brouillon

5. **Validez le transfert** :
   - Option 1 : Utilisez l'action "Valider les transferts"
   - Option 2 : Validation automatique lors de la création via "Charger van"

---

## 🗂️ Modèles de Données

### **TransfertStock**

| Champ | Description |
|-------|-------------|
| `numero` | Numéro auto-généré (TRANS-20250118-0001) |
| `entrepot_source` | Entrepôt d'origine |
| `entrepot_destination` | Van ou entrepôt de destination |
| `statut` | brouillon, validé, en_transit, réceptionné, annulé |
| `demandeur` | Utilisateur qui a créé le transfert |
| `valideur` | Utilisateur qui a validé |
| `date_creation` | Date de création |
| `date_validation` | Date de validation |

### **LigneTransfertStock**

| Champ | Description |
|-------|-------------|
| `transfert` | Transfert parent |
| `produit` | Produit à transférer |
| `quantite` | Quantité à transférer |
| `quantite_recue` | Quantité effectivement reçue |
| `notes` | Notes sur cette ligne |

---

## 📊 Workflows Recommandés

### **Workflow Quotidien : Chargement d'un Van**

#### **Matin - Préparation**

1. **Accéder au tableau de bord**
   - `/admin/API/transfertstock/stock-dashboard/`
   - Vérifier l'état actuel du stock de chaque van

2. **Charger le van**
   - `/admin/API/transfertstock/charger-van/`
   - Sélectionner le van (ex: VAN-001)
   - Entrepôt source : ENTREPOT-PRINCIPAL
   - Lister les produits :
     ```
     PROD-COLA,50
     PROD-EAU,100
     PROD-CHIPS,30
     ```
   - Valider

3. **Vérification**
   - Le transfert est créé et validé automatiquement
   - Le stock du van est mis à jour
   - Les mouvements sont enregistrés

#### **Soir - Retour**

Pour retourner le stock invendu :

1. Créer un nouveau transfert
2. **Source** : VAN-001
3. **Destination** : ENTREPOT-PRINCIPAL
4. Ajouter les produits invendus
5. Valider

---

### **Workflow Hebdomadaire : Transfert entre Entrepôts**

1. **Créer un transfert**
   - Source : Entrepôt principal
   - Destination : Entrepôt secondaire

2. **Ajouter les produits**
   - Rechercher par référence
   - Vérifier le stock disponible (affiché en vert/rouge)

3. **Valider**
   - Le stock est automatiquement transféré
   - Les mouvements sont tracés

---

## 🔍 Suivi et Traçabilité

### **Mouvements de Stock**

Chaque validation de transfert crée **automatiquement** :

1. **Mouvement de SORTIE** dans l'entrepôt source
   - Source : TRANS
   - Delta : négatif (-quantité)
   - Note : "Transfert vers [code destination]"

2. **Mouvement d'ENTRÉE** dans l'entrepôt destination
   - Source : TRANS
   - Delta : positif (+quantité)
   - Note : "Transfert depuis [code source]"

### **Vérification du Stock**

Pour vérifier le stock d'un produit dans un entrepôt :

1. Allez dans **API** → **Product stocks**
2. Filtrez par :
   - Produit
   - Entrepôt (warehouse)

Vous verrez :
- Quantité actuelle
- Statut (OK, Alerte, Critique, Rupture)

---

## ⚠️ Règles de Validation

### **Lors de la validation d'un transfert** :

✅ **Vérifications automatiques** :
1. Le transfert doit être en statut "brouillon"
2. Le transfert doit contenir au moins une ligne
3. **Stock suffisant** dans l'entrepôt source pour chaque produit
4. Si stock insuffisant → Erreur avec détails

✅ **Actions automatiques** :
1. Changement du statut → "validé"
2. Enregistrement du valideur et de la date
3. Décrémentation du stock source
4. Incrémentation du stock destination
5. Création des mouvements de stock

❌ **Impossible de** :
- Valider un transfert déjà validé
- Annuler un transfert réceptionné
- Transférer plus que le stock disponible

---

## 🎨 Interface Utilisateur

### **Codes Couleur des Statuts**

| Statut | Couleur | Signification |
|--------|---------|---------------|
| 🟦 Brouillon | Gris | En cours de création |
| 🟢 Validé | Vert | Transfert effectué |
| 🔵 En transit | Bleu | En cours de transport |
| 🟢 Réceptionné | Vert foncé | Réception confirmée |
| 🔴 Annulé | Rouge | Transfert annulé |

### **Codes Couleur du Stock**

| Niveau | Couleur | Condition |
|--------|---------|-----------|
| ✅ OK | Vert | Stock > seuil_alerte |
| ⚠️ Alerte | Jaune | Stock ≤ seuil_alerte |
| 🚨 Critique | Orange | Stock ≤ seuil_critique |
| ❌ Rupture | Rouge | Stock = 0 |

---

## 📱 Intégration Mobile

### **API Endpoints pour l'App Mobile**

Les livreurs peuvent consulter leur stock via l'API :

```javascript
// 1. Récupérer le profil livreur
GET /API/distribution/livreurs/me/
// Retourne : { id, nom, entrepot: { id, code, name }, ... }

// 2. Consulter le stock du van
GET /API/stocks/?warehouse={warehouse_id}
// Retourne : [{ produit: {...}, quantity: 50 }, ...]

// 3. Vendre depuis le van
POST /API/distribution/ventes/
// Le stock du van diminue automatiquement
```

---

## 🛠️ Dépannage

### **Problème : "Stock insuffisant"**

**Cause** : Le stock disponible dans l'entrepôt source est inférieur à la quantité demandée.

**Solution** :
1. Vérifier le stock actuel : **API** → **Product stocks**
2. Filtrer par produit et entrepôt source
3. Ajuster la quantité du transfert

### **Problème : "Le transfert doit contenir au moins une ligne"**

**Cause** : Aucun produit n'a été ajouté au transfert.

**Solution** :
1. Modifier le transfert
2. Ajouter au moins une ligne de transfert
3. Sauvegarder puis valider

### **Problème : "Entrepôt non trouvé"**

**Cause** : Le van n'existe pas encore comme entrepôt.

**Solution** :
1. Créer l'entrepôt : **API** → **Warehouses** → **Ajouter**
2. Code : VAN-001 (doit commencer par "VAN")
3. Nom : Van - VAN-001
4. Activer : ✅
5. Sauvegarder

---

## 🎓 Exemples Pratiques

### **Exemple 1 : Chargement Quotidien d'un Van**

```
Van : VAN-001
Entrepôt source : ENTREPOT-PRINCIPAL

Produits à charger :
COLA-500ML,50
EAU-1L,100
CHIPS-NATURE,30
CHIPS-BBQ,25
BONBONS-MIXTE,40
```

**Résultat** :
- Transfert : TRANS-20250118-0001
- Statut : ✅ Validé
- Stock VAN-001 : +245 unités

### **Exemple 2 : Retour d'Invendus**

```
Van : VAN-001
Entrepôt destination : ENTREPOT-PRINCIPAL

Produits invendus :
COLA-500ML,15
CHIPS-NATURE,8
```

**Résultat** :
- Transfert : TRANS-20250118-0002
- Statut : ✅ Validé
- Stock ENTREPOT-PRINCIPAL : +23 unités

---

## 📈 Rapports et Statistiques

### **Rapports Disponibles**

1. **Tableau de bord des vans**
   - Stock total par van
   - Valeur du stock
   - Nombre de produits

2. **Export CSV des transferts**
   - Historique complet
   - Filtrable par période
   - Incluant tous les détails

3. **Mouvements de stock**
   - Traçabilité complète
   - Par produit
   - Par entrepôt
   - Par période

---

## 🔐 Permissions et Sécurité

### **Rôles Recommandés**

| Rôle | Permissions |
|------|-------------|
| **Admin** | Tout |
| **Manager** | Créer, valider, annuler transferts |
| **Préparateur** | Créer transferts (brouillon uniquement) |
| **Livreur** | Lecture seule (via app mobile) |

### **Traçabilité**

Chaque action est tracée :
- Qui a créé le transfert (`demandeur`)
- Qui a validé (`valideur`)
- Qui a réceptionné (`recepteur`)
- Dates de chaque action

---

## 📞 Support

Pour toute question ou problème :
1. Vérifiez les logs : `/admin/API/auditlog/` (si activé)
2. Consultez les mouvements de stock
3. Vérifiez les transferts en cours

---

## 🎉 Bonnes Pratiques

✅ **À FAIRE** :
- Valider les transferts quotidiennement
- Vérifier le stock avant de créer un transfert
- Utiliser le tableau de bord pour une vue d'ensemble
- Exporter régulièrement l'historique en CSV
- Retourner les invendus le soir même

❌ **À ÉVITER** :
- Créer des transferts sans validation
- Laisser des transferts en brouillon trop longtemps
- Transférer sans vérifier le stock disponible
- Annuler un transfert déjà réceptionné

---

**Version** : 1.0
**Date** : 18 Janvier 2025
**Auteur** : Système de Gestion de Stock
