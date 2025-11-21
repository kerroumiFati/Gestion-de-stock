# 🏢 Système Multi-Tenancy - GestionStock

## Vue d'ensemble

Le système multi-tenancy permet à plusieurs entreprises d'utiliser la même application tout en gardant leurs données **complètement isolées** les unes des autres. Chaque entreprise (ou "tenant") a ses propres clients, produits, ventes, etc.

## 📋 Fonctionnalités

✅ **Isolation complète des données** : Chaque entreprise ne voit que ses propres données
✅ **Gestion multi-utilisateurs** : Plusieurs utilisateurs par entreprise avec différents rôles
✅ **Filtrage automatique** : Les données sont filtrées automatiquement par entreprise
✅ **Sécurité renforcée** : Impossible d'accéder aux données d'une autre entreprise

## 🏗️ Architecture

### Nouveaux modèles

#### 1. **Company (Entreprise)**
Représente une organisation/entreprise utilisant le système.

```python
- name: Nom de l'entreprise
- code: Code unique (ex: "ACME", "SHOP123")
- email: Email de contact
- telephone: Téléphone
- adresse: Adresse physique
- tax_id: Numéro fiscal (ICE, SIREN, etc.)
- is_active: Si l'entreprise est active
```

#### 2. **UserProfile (Profil Utilisateur)**
Lie chaque utilisateur Django à une entreprise.

```python
- user: Utilisateur Django (OneToOne)
- company: Entreprise de l'utilisateur
- role: Rôle dans l'entreprise (admin, manager, employee)
```

### Modèles modifiés

Tous les modèles métier ont maintenant un champ `company` :
- Produit
- Client
- Fournisseur
- Categorie
- Achat
- Vente
- BonLivraison
- Facture
- Warehouse
- InventorySession

## 🚀 Configuration initiale

### 1. Appliquer les migrations (déjà fait)

```bash
python manage.py makemigrations
python manage.py migrate
```

### 2. Configurer le multi-tenancy

**Avec le script automatique :**
```bash
python manage.py setup_multitenancy
```

Ce script va :
- Créer une entreprise par défaut "Entreprise Par Défaut" (code: DEFAULT)
- Assigner tous les utilisateurs existants à cette entreprise
- Assigner toutes les données existantes à cette entreprise

**Options du script :**
```bash
# Avec un nom personnalisé
python manage.py setup_multitenancy --company-name "Ma Société" --company-code "MASOC"
```

## 📖 Utilisation

### Créer une nouvelle entreprise

**Via Django Admin :**
1. Connectez-vous à `/admin/`
2. Allez dans **API > Companies**
3. Cliquez sur "Ajouter Company"
4. Remplissez les informations (nom, code unique, etc.)
5. Sauvegardez

**Via API (exemple avec Python) :**
```python
from API.models import Company

company = Company.objects.create(
    name="Nouvelle Entreprise",
    code="NEWCO",
    email="contact@newco.com",
    telephone="0123456789",
    is_active=True
)
```

### Assigner un utilisateur à une entreprise

**Lors de la création d'un utilisateur :**
```python
from django.contrib.auth import get_user_model
from API.models import Company, UserProfile

User = get_user_model()
company = Company.objects.get(code="NEWCO")

# Créer l'utilisateur
user = User.objects.create_user(
    username="employe1",
    email="employe1@newco.com",
    password="password123"
)

# Créer son profil lié à l'entreprise
profile = UserProfile.objects.create(
    user=user,
    company=company,
    role="employee"
)
```

**Pour un utilisateur existant :**
```python
from API.models import UserProfile, Company

user = User.objects.get(username="john")
company = Company.objects.get(code="NEWCO")

# Si le profil n'existe pas
profile = UserProfile.objects.create(
    user=user,
    company=company,
    role="admin"
)
```

### Rôles disponibles

- **admin** : Administrateur de l'entreprise (tous les droits)
- **manager** : Gestionnaire (gestion courante)
- **employee** : Employé (accès limité)

## 🔒 Sécurité et isolation

### Comment fonctionne l'isolation ?

1. **Middleware TenantMiddleware** :
   - S'exécute pour chaque requête
   - Récupère l'entreprise de l'utilisateur connecté
   - La stocke dans `request.company`

2. **Mixins de filtrage** :
   - `TenantFilterMixin` : Filtre automatiquement les modèles par `company`
   - `WarehouseRelatedTenantMixin` : Pour les modèles liés via `warehouse`

3. **ViewSets** :
   - Tous les ViewSets utilisent les mixins
   - Filtre automatique : `queryset.filter(company=request.company)`
   - Création automatique : `obj.company = request.company`

### Que se passe-t-il quand un utilisateur accède aux données ?

```python
# L'utilisateur voit uniquement les produits de son entreprise
# Requête : GET /api/produits/

# Le ViewSet fait automatiquement :
queryset = Produit.objects.filter(company=request.company)

# Impossible d'accéder aux produits d'une autre entreprise !
```

## 📊 Gestion des données

### Transférer des données entre entreprises

⚠️ **Attention** : Le transfert de données entre entreprises doit être fait avec précaution !

```python
from API.models import Produit, Company

# Récupérer les entreprises
source_company = Company.objects.get(code="OLDCO")
target_company = Company.objects.get(code="NEWCO")

# Transférer un produit
produit = Produit.objects.get(id=123, company=source_company)
produit.company = target_company
produit.save()
```

### Supprimer une entreprise

⚠️ **Attention** : Supprimer une entreprise supprime **toutes ses données** !

```python
company = Company.objects.get(code="OLDCO")
company.delete()  # Supprime l'entreprise ET toutes ses données liées
```

## 🧪 Tests et vérification

### Vérifier l'isolation

```python
# Se connecter avec un utilisateur de l'entreprise A
# Essayer d'accéder aux données de l'entreprise B via l'API
# → Doit retourner aucun résultat ou erreur 403

# Vérifier manuellement
from django.contrib.auth import get_user_model
from API.models import UserProfile, Produit

user = get_user_model().objects.get(username="user_entrepriseA")
company = user.profile.company

# Ces produits sont visibles
produits_visibles = Produit.objects.filter(company=company)
print(f"Produits visibles : {produits_visibles.count()}")

# Vérifier qu'on ne voit pas les produits des autres entreprises
tous_les_produits = Produit.objects.all()
print(f"Total produits : {tous_les_produits.count()}")
# → Devrait être différent si plusieurs entreprises existent
```

## 🐛 Dépannage

### Problème : L'utilisateur ne voit aucune donnée

**Cause** : L'utilisateur n'a pas de profil ou son profil n'est pas lié à une entreprise.

**Solution** :
```python
from API.models import UserProfile, Company
user = get_user_model().objects.get(username="problematic_user")

# Vérifier le profil
if not hasattr(user, 'profile'):
    company = Company.objects.first()
    UserProfile.objects.create(user=user, company=company, role="employee")
```

### Problème : Les données existantes ne sont pas visibles

**Cause** : Les données n'ont pas été assignées à une entreprise.

**Solution** :
```bash
python manage.py setup_multitenancy
```

### Problème : Erreur "company cannot be null"

**Cause** : Tentative de créer un objet sans company.

**Solution** : S'assurer que l'utilisateur est authentifié et a un profil avec une entreprise.

## 📝 Notes importantes

1. **Superusers** : Les superusers Django doivent aussi avoir un UserProfile pour accéder aux données
2. **Migrations futures** : Tous les nouveaux modèles métier doivent avoir un champ `company`
3. **Performance** : L'ajout d'index sur les champs `company` peut améliorer les performances
4. **Backup** : Toujours sauvegarder la base de données avant des opérations de transfert/suppression

## 🎯 Prochaines étapes recommandées

1. ✅ Créer vos entreprises
2. ✅ Assigner les utilisateurs aux entreprises
3. ✅ Tester l'isolation des données
4. 🔄 Ajouter des utilisateurs à chaque entreprise
5. 🔄 Configurer les rôles et permissions spécifiques
6. 🔄 Personnaliser les paramètres par entreprise (devise par défaut, etc.)

## 💬 Support

Pour toute question ou problème, consultez :
- Les logs Django : `python manage.py runserver` affiche les logs du TenantMiddleware
- Django Admin : `/admin/` pour gérer les entreprises et profils
- Code source : `API/models.py`, `API/mixins.py`, `Gestion_stock/middleware.py`

---

🎉 **Félicitations !** Votre système multi-tenancy est maintenant opérationnel !
