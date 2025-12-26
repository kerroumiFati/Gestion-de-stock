# Guide de Déploiement CI/CD

## 🚀 Qu'est-ce que le CI/CD ?

**CI/CD** (Continuous Integration / Continuous Deployment) permet de déployer automatiquement votre application à chaque modification du code.

### Avantages :

✅ **Déploiement automatique** - Push sur Git → Déploiement automatique
✅ **Plus sécurisé** - Pas besoin de Git sur le VPS
✅ **Traçabilité** - Historique de tous les déploiements
✅ **Tests automatisés** - Vérifications avant déploiement
✅ **Rollback facile** - Retour à une version précédente simple

---

## 📋 Vue d'ensemble du processus

```
1. Vous modifiez le code localement
2. Vous faites un git push
3. GitHub Actions / GitLab CI détecte le push
4. Tests automatiques (optionnel)
5. Construction de l'application
6. Déploiement automatique sur le VPS via SSH
7. Redémarrage de l'application
```

---

## Option 1 : GitHub Actions (Recommandé)

### Prérequis

1. Repository GitHub (privé recommandé)
2. Accès SSH au VPS configuré

### Étape 1 : Générer une clé SSH pour le déploiement

Sur votre **machine locale** :

```bash
# Générer une paire de clés dédiée au déploiement
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_deploy_key

# Cela créera :
# ~/.ssh/github_deploy_key (clé privée)
# ~/.ssh/github_deploy_key.pub (clé publique)
```

### Étape 2 : Ajouter la clé publique au VPS

```bash
# Copier la clé publique sur le VPS
cat ~/.ssh/github_deploy_key.pub | ssh root@VOTRE_IP_VPS "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"

# Ou manuellement :
# 1. Affichez la clé publique
cat ~/.ssh/github_deploy_key.pub

# 2. Connectez-vous au VPS
ssh root@VOTRE_IP_VPS

# 3. Ajoutez la clé
nano ~/.ssh/authorized_keys
# Collez la clé publique
# Sauvegardez
```

### Étape 3 : Configurer les secrets GitHub

1. Allez sur votre repository GitHub
2. **Settings** → **Secrets and variables** → **Actions**
3. Cliquez sur **New repository secret**
4. Ajoutez les secrets suivants :

| Nom du secret | Valeur | Comment obtenir |
|--------------|--------|-----------------|
| `VPS_HOST` | `123.45.67.89` | IP de votre VPS |
| `VPS_USERNAME` | `root` ou `gestionstock` | Utilisateur SSH |
| `VPS_SSH_KEY` | Contenu de `~/.ssh/github_deploy_key` | Clé privée SSH |
| `VPS_PORT` | `22` | Port SSH (22 par défaut) |
| `ENV_FILE` | Contenu complet de votre `.env` | Variables d'environnement |

Pour obtenir la clé privée :
```bash
cat ~/.ssh/github_deploy_key
# Copiez TOUT le contenu (y compris BEGIN et END)
```

### Étape 4 : Créer le workflow GitHub Actions

Créez le fichier `.github/workflows/deploy.yml` dans votre projet :

```bash
mkdir -p .github/workflows
```

Créez le fichier de workflow (voir ci-dessous).

### Étape 5 : Push et déploiement automatique

```bash
git add .
git commit -m "Add CI/CD deployment"
git push origin main
```

Le déploiement se lancera automatiquement ! 🚀

---

## Option 2 : GitLab CI/CD

### Prérequis

1. Repository GitLab (privé recommandé)
2. Accès SSH au VPS configuré

### Étape 1 : Générer une clé SSH

```bash
ssh-keygen -t ed25519 -C "gitlab-ci-deploy" -f ~/.ssh/gitlab_deploy_key
```

### Étape 2 : Ajouter la clé au VPS

```bash
cat ~/.ssh/gitlab_deploy_key.pub | ssh root@VOTRE_IP_VPS "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

### Étape 3 : Configurer les variables GitLab

1. Allez sur votre repository GitLab
2. **Settings** → **CI/CD** → **Variables**
3. Ajoutez les variables suivantes :

| Variable | Valeur | Type | Protégé |
|----------|--------|------|---------|
| `VPS_HOST` | IP du VPS | Variable | ✓ |
| `VPS_USERNAME` | `root` | Variable | ✓ |
| `VPS_SSH_KEY` | Clé privée | File | ✓ |
| `VPS_PORT` | `22` | Variable | ✓ |
| `ENV_FILE` | Contenu de `.env` | File | ✓ |

### Étape 4 : Créer le fichier .gitlab-ci.yml

Créez `.gitlab-ci.yml` à la racine du projet (voir ci-dessous).

### Étape 5 : Push et déploiement

```bash
git add .
git commit -m "Add GitLab CI/CD"
git push origin main
```

---

## Option 3 : Déploiement manuel sécurisé avec rsync

Si vous ne voulez pas de CI/CD complet mais un déploiement sécurisé :

```bash
# Script de déploiement local
#!/bin/bash

# Configuration
VPS_HOST="votre-ip-vps"
VPS_USER="gestionstock"
VPS_PATH="/home/gestionstock/app"

# Synchronisation des fichiers (exclut les fichiers sensibles)
rsync -avz --delete \
  --exclude='.git' \
  --exclude='.env' \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  --exclude='db.sqlite3' \
  --exclude='media' \
  --exclude='staticfiles' \
  --exclude='venv' \
  ./ $VPS_USER@$VPS_HOST:$VPS_PATH/

# Commandes sur le VPS
ssh $VPS_USER@$VPS_HOST << 'EOF'
cd /home/gestionstock/app
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
exit
EOF

# Redémarrer l'application
ssh root@$VPS_HOST "systemctl restart gestionstock"

echo "✓ Déploiement terminé !"
```

---

## 🔐 Sécurité CI/CD

### Bonnes pratiques :

1. ✅ **Repository privé** toujours
2. ✅ **Secrets GitHub/GitLab** pour les credentials
3. ✅ **Clés SSH dédiées** (une par service CI/CD)
4. ✅ **Environnement protégé** (production)
5. ✅ **Tests automatisés** avant déploiement
6. ✅ **Notifications** en cas d'échec

### Ce qui NE doit JAMAIS être dans le code :

```
❌ .env
❌ Mots de passe
❌ Clés API
❌ SECRET_KEY
❌ Credentials de base de données
❌ Clés SSH privées
```

---

## 📊 Monitoring des déploiements

### Voir l'historique des déploiements

**GitHub Actions** :
- Allez sur votre repository → **Actions**
- Vous verrez tous les workflows exécutés

**GitLab CI** :
- Allez sur votre repository → **CI/CD** → **Pipelines**

### Notifications

Configurez des notifications :
- Slack
- Discord
- Email
- Microsoft Teams

---

## 🐛 Dépannage

### Le déploiement échoue

1. **Vérifiez les logs** dans GitHub Actions / GitLab CI
2. **Testez la connexion SSH** :
   ```bash
   ssh -i ~/.ssh/github_deploy_key root@VOTRE_IP_VPS
   ```
3. **Vérifiez les secrets** sont correctement configurés
4. **Vérifiez les permissions** sur le VPS

### Tests de connexion

```bash
# Test de connexion SSH
ssh -vvv -i ~/.ssh/github_deploy_key root@VOTRE_IP_VPS

# Test de rsync
rsync -avzn --dry-run \
  -e "ssh -i ~/.ssh/github_deploy_key" \
  ./ root@VOTRE_IP_VPS:/home/gestionstock/app/
```

---

## 🎯 Workflow recommandé

```
main (production)
  ↑
  └── develop (staging)
       ↑
       └── feature/* (développement)
```

### Branches et déploiements :

- `feature/*` → Pas de déploiement
- `develop` → Déploiement sur serveur de staging
- `main` → Déploiement en production

---

## 📚 Ressources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitLab CI/CD Documentation](https://docs.gitlab.com/ee/ci/)
- [Best Practices for CI/CD](https://www.atlassian.com/continuous-delivery/principles/continuous-integration-vs-delivery-vs-deployment)

---

**Prochaine étape** : Créez les fichiers de workflow ci-dessous !
