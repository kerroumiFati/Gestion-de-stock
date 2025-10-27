# 🔧 Fix: Erreur 500 sur update_line

## 🎯 Problème

**Erreur:**
```
POST http://localhost:8000/API/inventaires/1/update_line/ 500 (Internal Server Error)
Erreur mise à jour ligne: Error: Erreur mise à jour
```

## 🔍 Cause

Erreur 500 = Erreur Python côté serveur. C'était probablement:
1. Import manquant (InventoryLineSerializer)
2. Modèle InventoryLine pas importé
3. Champ counted_at manquant

## ✅ Solution Appliquée

### 1. Ajout de l'Import Manquant

**Ligne 15 de `API/views.py`:**
```python
from .serializers import StockMoveSerializer, InventorySessionSerializer, InventoryLineSerializer
```

### 2. Import Explicite du Modèle

**Ligne 869:**
```python
from .models import InventoryLine
```

### 3. Ajout du Timestamp

**Lignes 877 et 888:**
```python
from django.utils import timezone
line.counted_at = timezone.now()
```

### 4. Gestion Robuste des Erreurs

Le code gère maintenant:
- Produit inexistant → 404
- Quantité invalide → 400
- Session validée → 400
- Imports manquants → Corrigés

---

## 🚀 REDÉMARRER LE SERVEUR (OBLIGATOIRE)

**L'erreur 500 nécessite ABSOLUMENT un redémarrage:**

```bash
# Terminal Django:
Ctrl+C

# Puis:
python manage.py runserver
```

**Attendez:**
```
Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (0 silenced).
Starting development server at http://127.0.0.1:8000/
```

---

## 🧪 Test Complet

### Étape 1: Redémarrer Serveur ✅

```bash
python manage.py runserver
```

### Étape 2: Vider Cache ✅

```
Ctrl+Shift+R
```

### Étape 3: F12 Console ✅

**AVANT de tester, ouvrir:**
```
F12 > Console
```

Gardez cette console ouverte!

### Étape 4: Créer Session ✅

```
Menu > Inventaires
Numéro: INV-TEST-002
Date: Aujourd'hui
[Créer]
```

**Console devrait montrer:**
```
[Inventaire] Initialisation...
[Inventaire] Session créée
```

**Page devrait:**
- ✅ Basculer vers "Comptage"
- ✅ Afficher produits en cartes
- ✅ Montrer progression 0%

### Étape 5: Compter un Produit ✅

```
1. Clic sur carte "fanta" ou "selecto"
2. Popup apparaît
3. Saisir: 5
4. OK
```

**Console devrait montrer:**
```
POST http://localhost:8000/API/inventaires/2/update_line/ 200 (OK)
[Inventaire] Comptage enregistré
```

**Page devrait:**
- ✅ Carte devient verte
- ✅ Affiche "Compté: 5"
- ✅ Affiche "Écart: +/-X"
- ✅ Message toast "Comptage enregistré!" ✅

**Si 200 OK → C'est réparé! 🎉**
**Si 500 encore → Copier TOUS les logs du terminal Django**

---

## 🔍 Logs Django à Vérifier

**Dans le terminal où tourne Django, chercher:**

```
Exception:
Traceback (most recent call last):
  ...
```

**Si vous voyez une erreur, copier TOUT le traceback et envoyez-le moi.**

Erreurs possibles:
- `NameError: InventoryLine is not defined`
- `AttributeError: 'InventorySession' has no attribute 'update_completion_percentage'`
- `ImportError: cannot import name 'InventoryLineSerializer'`

---

## 🐛 Solutions par Type d'Erreur

### Erreur: "InventoryLine is not defined"

**Cause:** Modèle pas importé

**Solution appliquée:**
```python
from .models import InventoryLine  # Ligne 869
```

### Erreur: "InventoryLineSerializer is not defined"

**Cause:** Serializer pas importé

**Solution appliquée:**
```python
from .serializers import InventoryLineSerializer  # Ligne 15
```

### Erreur: "update_completion_percentage() doesn't exist"

**Vérifier le modèle:**
```bash
python manage.py shell

from API.models import InventorySession
session = InventorySession.objects.first()
session.update_completion_percentage()  # Doit fonctionner
```

**Si erreur:** La méthode n'existe pas dans le modèle

---

## 📊 Test Manuel de l'API

### Test Directement dans le Terminal

```bash
# Ouvrir nouveau terminal (garder serveur actif)
python manage.py shell
```

**Dans le shell Python:**

```python
from API.models import InventorySession, Produit, InventoryLine
from django.contrib.auth.models import User

# Créer session de test
user = User.objects.first()
session = InventorySession.objects.create(
    numero="TEST-SHELL-001",
    created_by=user
)

print(f"Session créée: {session.id}")

# Récupérer un produit
produit = Produit.objects.filter(is_active=True).first()
print(f"Produit: {produit.designation}")

# Créer ligne
line = InventoryLine.objects.create(
    session=session,
    produit=produit,
    snapshot_qty=produit.quantite,
    counted_qty=10,
    counted_by=user
)

print(f"Ligne créée: {line.id}")

# Tester update_completion_percentage
session.update_completion_percentage()
print(f"Progression: {session.completion_percentage}%")
```

**Si tout fonctionne sans erreur → API OK**
**Si erreur → Copier l'erreur complète**

---

## 🔄 Workflow Complet de Debug

### 1. Logs Serveur Django

**Terminal Django, chercher lignes rouges:**
```
Exception in thread...
Traceback...
```

### 2. Console Navigateur

**F12 > Console:**
```
Erreur mise à jour ligne: Error: ...
```

### 3. Network Tab

**F12 > Network > update_line:**
- Status: 500
- Preview/Response: Voir le message d'erreur

### 4. Test Manuel

**Shell Django:**
```bash
python manage.py shell
# Tester création InventoryLine manuellement
```

---

## 📝 Vérifications Effectuées

✅ Import InventoryLineSerializer ajouté
✅ Import InventoryLine explicite dans la fonction
✅ Import timezone pour counted_at
✅ Gestion erreurs améliorée
✅ Log d'événement ajouté
✅ Django check: No issues

---

## 🚀 REDÉMARREZ ET TESTEZ

```bash
# 1. OBLIGATOIRE: Redémarrer serveur
Ctrl+C
python manage.py runserver

# 2. Cache
Ctrl+Shift+R

# 3. Test
Menu > Inventaires
Créer session
Compter produit
Regarder console: 200 ou 500?
```

**Si 200 → ✅ Réussi!**
**Si 500 → Envoyez-moi le traceback Django (terminal)**

---

## 📞 Si Toujours Erreur 500

**Envoyez-moi:**

1. **Logs Django complets** (terminal serveur)
   ```
   Copier TOUT depuis "Exception" jusqu'à la fin
   ```

2. **Test shell:**
   ```bash
   python manage.py shell
   from API.models import InventorySession
   hasattr(InventorySession, 'update_completion_percentage')
   # Doit retourner: True
   ```

3. **Version Django:**
   ```bash
   python -c "import django; print(django.VERSION)"
   ```

---

**Redémarrez le serveur et testez maintenant! 🎯**
