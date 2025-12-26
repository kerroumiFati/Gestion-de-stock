# Stratégies de Déploiement

Ce guide explique les différentes stratégies de déploiement disponibles et comment choisir celle qui vous convient.

---

## 🎯 Cas d'utilisation : Plusieurs projets/entreprises

### Votre situation :

Vous travaillez sur **plusieurs projets** (plusieurs entreprises) dans le même repository ou avez besoin de **contrôler** quand déployer.

### ✅ Solutions recommandées :

| Stratégie | Description | Quand l'utiliser |
|-----------|-------------|------------------|
| **Déploiement manuel** | Vous décidez quand déployer | Plusieurs projets, contrôle total |
| **Déploiement sur release** | Déploie uniquement sur les versions | Production stable |
| **Déploiement par branche** | Branches différentes → VPS différents | Entreprise A sur branche A, B sur branche B |

---

## 🔧 Option 1 : Déploiement Manuel (RECOMMANDÉ pour vous)

### Fichier : `.github/workflows/deploy-manual-only.yml`

### Comment ça marche :

```
Vous pushez → Rien ne se passe automatiquement
Quand vous êtes prêt → Vous cliquez sur "Run workflow"
→ Déploiement lancé
```

### Comment déployer :

1. **Allez sur GitHub** :
   ```
   Votre repo → Actions → Deploy to VPS (Manual Only)
   ```

2. **Cliquez sur "Run workflow"**

3. **Choisissez les options** :
   - Environnement : production / staging
   - Créer sauvegarde : Oui / Non
   - Exécuter migrations : Oui / Non

4. **Cliquez "Run workflow"**

5. **Regardez le déploiement** en direct

### Avantages :

✅ Vous contrôlez QUAND déployer
✅ Vous pouvez pusher sans déclencher de déploiement
✅ Options personnalisables à chaque déploiement
✅ Parfait pour plusieurs projets

### Configuration :

```bash
# Renommez/supprimez les autres workflows
rm .github/workflows/deploy.yml
rm .github/workflows/deploy-with-tests.yml

# Gardez uniquement
.github/workflows/deploy-manual-only.yml
```

---

## 🏷️ Option 2 : Déploiement sur Release/Tag

### Fichier : `.github/workflows/deploy-on-release.yml`

### Comment ça marche :

```
Vous développez et pushez → Rien ne se passe
Vous créez un tag (v1.0.0) → Déploiement automatique
```

### Comment déployer :

#### Méthode 1 : Via tag Git

```bash
# Quand vous êtes prêt à déployer
git tag v1.0.0
git push origin v1.0.0

# Le déploiement se lance automatiquement
```

#### Méthode 2 : Via GitHub Release

```
1. GitHub → Releases → Create a new release
2. Tag version: v1.0.0
3. Release title: Version 1.0.0
4. Description: Liste des changements
5. Publish release
→ Déploiement automatique
```

### Avantages :

✅ Déploiements versionnés
✅ Historique clair des versions
✅ Sauvegardes avec numéro de version
✅ Professionnel

### Exemple de workflow :

```bash
# Développement normal
git add .
git commit -m "Add feature X"
git push origin main
# → Rien ne se déploie

# ... plus de développement ...

# Quand prêt pour production
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
# → Déploiement automatique de v1.0.0
```

---

## 🌲 Option 3 : Déploiement par Branche

### Scénario : Plusieurs entreprises/projets

```
main        → VPS Entreprise A (production)
entreprise-b → VPS Entreprise B
staging     → VPS de test
```

### Configuration :

Créez un workflow pour chaque environnement :

#### `.github/workflows/deploy-entreprise-a.yml`

```yaml
name: Deploy Entreprise A

on:
  push:
    branches:
      - main  # Branche pour entreprise A

jobs:
  deploy:
    # ... utiliser VPS_HOST_A, VPS_SSH_KEY_A, etc.
```

#### `.github/workflows/deploy-entreprise-b.yml`

```yaml
name: Deploy Entreprise B

on:
  push:
    branches:
      - entreprise-b  # Branche pour entreprise B

jobs:
  deploy:
    # ... utiliser VPS_HOST_B, VPS_SSH_KEY_B, etc.
```

### Secrets GitHub :

```
# Pour entreprise A
VPS_HOST_A
VPS_SSH_KEY_A
ENV_FILE_A

# Pour entreprise B
VPS_HOST_B
VPS_SSH_KEY_B
ENV_FILE_B
```

---

## 📊 Comparaison des stratégies

| Critère | Manuel | Release/Tag | Par branche |
|---------|--------|-------------|-------------|
| **Contrôle** | ⭐⭐⭐ Total | ⭐⭐ Bon | ⭐⭐ Bon |
| **Flexibilité** | ⭐⭐⭐ Maximum | ⭐⭐ Moyen | ⭐⭐⭐ Maximum |
| **Automatisation** | ⭐ Faible | ⭐⭐⭐ Élevé | ⭐⭐⭐ Élevé |
| **Multi-projets** | ⭐⭐⭐ Parfait | ⭐⭐ Bon | ⭐⭐⭐ Parfait |
| **Historique** | ⭐⭐ Moyen | ⭐⭐⭐ Excellent | ⭐⭐ Moyen |
| **Complexité** | ⭐ Simple | ⭐⭐ Moyen | ⭐⭐⭐ Complexe |

---

## 🎯 Recommandations par cas d'usage

### Vous travaillez sur plusieurs projets clients

→ **Déploiement Manuel** (`.github/workflows/deploy-manual-only.yml`)

**Workflow** :
```bash
# Projet Client A
git checkout client-a
# ... développement ...
git push
# Pas de déploiement

# Quand prêt → GitHub Actions → Run workflow

# Projet Client B
git checkout client-b
# ... développement ...
git push
# Pas de déploiement

# Quand prêt → GitHub Actions → Run workflow
```

### Vous gérez une application avec versions stables

→ **Déploiement sur Release** (`.github/workflows/deploy-on-release.yml`)

**Workflow** :
```bash
# Développement
git add .
git commit -m "Features"
git push
# Pas de déploiement

# Version stable
git tag v1.0.0
git push origin v1.0.0
# → Déploiement automatique
```

### Vous avez plusieurs VPS (dev, staging, prod)

→ **Déploiement par Branche**

**Workflow** :
```bash
# Développement
git checkout develop
git push origin develop
# → Déploie sur VPS de dev

# Staging
git checkout staging
git merge develop
git push origin staging
# → Déploie sur VPS de staging

# Production
git checkout main
git merge staging
git push origin main
# → Déploie sur VPS de production
```

---

## 🛠️ Configuration recommandée pour vous

### Étape 1 : Nettoyer les workflows automatiques

```bash
# Supprimer les workflows automatiques
rm .github/workflows/deploy.yml
rm .github/workflows/deploy-with-tests.yml

# Garder uniquement le manuel
# .github/workflows/deploy-manual-only.yml est déjà créé
```

### Étape 2 : Configurer les secrets GitHub

Un seul ensemble de secrets suffit :

```
VPS_HOST       = IP de votre VPS
VPS_USERNAME   = gestionstock
VPS_PORT       = 22
VPS_SSH_KEY    = Votre clé SSH privée
ENV_FILE       = Contenu de votre .env
```

### Étape 3 : Workflow de travail

```bash
# 1. Développer normalement
git add .
git commit -m "Add feature"
git push origin main
# → Rien ne se déploie automatiquement

# 2. Quand prêt à déployer
# Allez sur GitHub → Actions → Deploy to VPS (Manual Only)
# Cliquez "Run workflow"
# Choisissez les options
# Cliquez "Run workflow"

# 3. Le déploiement se lance
# Vous pouvez voir les logs en temps réel

# 4. Fini ! 🎉
```

---

## 🔄 Migration depuis déploiement automatique

Si vous avez déjà un workflow automatique et voulez passer au manuel :

```bash
# 1. Renommer l'ancien workflow
mv .github/workflows/deploy.yml .github/workflows/deploy-auto-backup.yml.bak

# 2. Commit et push
git add .
git commit -m "Switch to manual deployment"
git push

# 3. Désormais, les push ne déclenchent plus de déploiement
# 4. Déployez manuellement quand vous voulez
```

---

## 📱 Déploiement depuis votre téléphone

Avec le déploiement manuel, vous pouvez déployer depuis n'importe où :

1. **Via l'app GitHub** (iOS/Android)
   ```
   Repository → Actions → Deploy to VPS (Manual Only)
   → Run workflow
   ```

2. **Via navigateur mobile**
   ```
   github.com/votre-repo/actions
   → Deploy to VPS (Manual Only)
   → Run workflow
   ```

---

## 🐛 Questions fréquentes

### Q : Je peux quand même pusher normalement ?

**R** : Oui ! Avec le déploiement manuel, vous pouvez pusher autant que vous voulez. Le déploiement ne se lancera que si vous cliquez manuellement.

### Q : Combien de temps prend un déploiement manuel ?

**R** : ~2-3 minutes, comme un déploiement automatique.

### Q : Je peux déployer une branche spécifique ?

**R** : Oui ! Lors du déploiement manuel :
1. Allez sur la branche que vous voulez déployer
2. Actions → Run workflow
3. Sélectionnez la branche
4. Run workflow

### Q : Je peux annuler un déploiement en cours ?

**R** : Oui ! Sur la page du workflow en cours, cliquez sur "Cancel workflow".

### Q : Comment voir l'historique des déploiements ?

**R** : GitHub → Actions → Vous verrez tous les déploiements avec dates, qui l'a lancé, etc.

---

## 📚 Fichiers créés pour vous

```
.github/workflows/
├── deploy-manual-only.yml      ← Déploiement manuel (RECOMMANDÉ)
├── deploy-on-release.yml       ← Déploiement sur tag/release
├── deploy.yml                  ← Déploiement automatique (à supprimer)
└── deploy-with-tests.yml       ← Déploiement auto avec tests (à supprimer)
```

---

## ✅ Récapitulatif pour votre cas

Vous avez dit : *"je veux pas que chaque fois je push le vps soit à jour, possible que je push pour un autre entreprise"*

**Solution parfaite** : Déploiement Manuel

```bash
# 1. Utilisez ce workflow
.github/workflows/deploy-manual-only.yml

# 2. Supprimez les autres
rm .github/workflows/deploy.yml
rm .github/workflows/deploy-with-tests.yml

# 3. Pushez normalement
git push  # → Rien ne se déploie

# 4. Déployez quand VOUS voulez
GitHub → Actions → Run workflow
```

**Avantages pour vous** :
- ✅ Pushez autant que vous voulez
- ✅ Travaillez sur plusieurs projets
- ✅ Déployez uniquement quand prêt
- ✅ Contrôle total sur les déploiements

---

Besoin d'aide pour configurer une stratégie spécifique ?
