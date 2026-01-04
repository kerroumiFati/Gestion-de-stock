# Configuration des Secrets CI/CD

Ce guide vous explique comment configurer les secrets pour GitHub Actions et GitLab CI/CD.

---

## 📋 Secrets nécessaires

Vous aurez besoin de ces 5 secrets :

| Secret | Description | Exemple |
|--------|-------------|---------|
| `VPS_HOST` | Adresse IP de votre VPS | `123.45.67.89` |
| `VPS_USERNAME` | Utilisateur SSH | `gestionstock` ou `root` |
| `VPS_PORT` | Port SSH | `22` (défaut) |
| `VPS_SSH_KEY` | Clé SSH privée | Voir ci-dessous |
| `ENV_FILE` | Contenu du fichier .env | Voir ci-dessous |

---

## 🔑 Étape 1 : Générer une clé SSH pour le déploiement

### Sur votre machine locale :

```bash
# Créer une clé SSH dédiée au CI/CD
ssh-keygen -t ed25519 -C "cicd-deploy" -f ~/.ssh/cicd_deploy_key

# Cela créera deux fichiers :
# ~/.ssh/cicd_deploy_key     (PRIVÉE - pour GitHub/GitLab)
# ~/.ssh/cicd_deploy_key.pub (PUBLIQUE - pour le VPS)
```

### Afficher la clé PRIVÉE :

```bash
cat ~/.ssh/cicd_deploy_key
```

**Résultat** (exemple) :
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACC0muNzQAhZSi5rVnmvT0kssHxDlUnGxY+NMKWsEpuW1QAAAJBMu6ZZTLum
WQAAAAtzc2gtZWQyNTUxOQAAACC0muNzQAhZSi5rVnmvT0kssHxDlUnGxY+NMKWsEpuW1Q
AAAEB2uXytVsZVpNSLb/+u/MWN3hEkiZPzgZOTaaj3AKtzarSa43NACFlKLmtWea9PSSyw
fEOVScbFj40wpawSm5bVAAAAC2NpY2QtZGVwbG95AQI=
-----END OPENSSH PRIVATE KEY-----
```

⚠️ **Copiez TOUT** (y compris BEGIN et END) - C'est ce qui ira dans `VPS_SSH_KEY`

### Afficher la clé PUBLIQUE :

```bash
cat ~/.ssh/cicd_deploy_key.pub
```

**Résultat** (exemple) :
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILSa43NACFlKLmtWea9PSSywfEOVScbFj40wpawSm5bV cicd-deploy
```

---

## 🖥️ Étape 2 : Ajouter la clé publique au VPS

### Méthode 1 : Automatique (recommandée)

```bash
ssh-copy-id -i ~/.ssh/cicd_deploy_key.pub root@VOTRE_IP_VPS
```

### Méthode 2 : Manuelle

```bash
# 1. Connectez-vous au VPS
ssh root@VOTRE_IP_VPS

# 2. Éditez le fichier authorized_keys
nano ~/.ssh/authorized_keys

# 3. Collez la clé publique sur une nouvelle ligne
# (Ctrl+V pour coller)

# 4. Sauvegardez (Ctrl+X, puis Y, puis Enter)

# 5. Vérifiez les permissions
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

### Tester la connexion :

```bash
# Depuis votre machine locale
ssh -i ~/.ssh/cicd_deploy_key root@VOTRE_IP_VPS

# Si ça fonctionne, vous êtes connecté !
# Tapez 'exit' pour quitter
```

---

## 📄 Étape 3 : Préparer le fichier ENV_FILE

### Sur votre VPS, affichez le contenu de .env :

```bash
ssh root@VOTRE_IP_VPS
cat /home/gestionstock/app/.env
```

**Exemple de contenu** :
```env
SECRET_KEY=votre-cle-secrete-django-tres-longue
DEBUG=False
ALLOWED_HOSTS=votre-domaine.com,www.votre-domaine.com,123.45.67.89

# Database
DATABASE_URL=postgresql://gestion_stock_user:MotDePasseDB@localhost:5432/gestion_stock_db

# CORS
CORS_ALLOW_ALL_ORIGINS=False
```

⚠️ **Copiez TOUT le contenu** - C'est ce qui ira dans `ENV_FILE`

---

## 🔧 Étape 4A : Configuration GitHub Actions

### 1. Aller sur votre repository GitHub

Naviguez vers : `https://github.com/votre-username/votre-repo`

### 2. Accéder aux secrets

```
Settings → Secrets and variables → Actions → New repository secret
```

### 3. Ajouter chaque secret

Cliquez sur **"New repository secret"** et ajoutez **un par un** :

#### Secret 1 : VPS_HOST
- **Name:** `VPS_HOST`
- **Secret:** `123.45.67.89` (votre IP VPS)
- Cliquez sur **Add secret**

#### Secret 2 : VPS_USERNAME
- **Name:** `VPS_USERNAME`
- **Secret:** `gestionstock` (ou `root`)
- Cliquez sur **Add secret**

#### Secret 3 : VPS_PORT
- **Name:** `VPS_PORT`
- **Secret:** `22`
- Cliquez sur **Add secret**

#### Secret 4 : VPS_SSH_KEY
- **Name:** `VPS_SSH_KEY`
- **Secret:** Collez le contenu de `cat ~/.ssh/cicd_deploy_key`
- ⚠️ **Incluez BEGIN et END**
- Cliquez sur **Add secret**

#### Secret 5 : ENV_FILE
- **Name:** `ENV_FILE`
- **Secret:** Collez le contenu de votre fichier .env
- Cliquez sur **Add secret**

### 4. Vérifier

Vous devriez voir 5 secrets :

```
✓ VPS_HOST
✓ VPS_USERNAME
✓ VPS_PORT
✓ VPS_SSH_KEY
✓ ENV_FILE
```

---

## 🔧 Étape 4B : Configuration GitLab CI/CD

### 1. Aller sur votre repository GitLab

Naviguez vers : `https://gitlab.com/votre-username/votre-repo`

### 2. Accéder aux variables

```
Settings → CI/CD → Variables → Expand → Add variable
```

### 3. Ajouter chaque variable

#### Variable 1 : VPS_HOST
- **Key:** `VPS_HOST`
- **Value:** `123.45.67.89`
- **Type:** Variable
- **Protect variable:** ✓ (coché)
- **Mask variable:** ☐ (non coché)
- Cliquez sur **Add variable**

#### Variable 2 : VPS_USERNAME
- **Key:** `VPS_USERNAME`
- **Value:** `gestionstock`
- **Type:** Variable
- **Protect variable:** ✓
- **Mask variable:** ☐
- Cliquez sur **Add variable**

#### Variable 3 : VPS_PORT
- **Key:** `VPS_PORT`
- **Value:** `22`
- **Type:** Variable
- **Protect variable:** ✓
- **Mask variable:** ☐
- Cliquez sur **Add variable**

#### Variable 4 : VPS_SSH_KEY
- **Key:** `VPS_SSH_KEY`
- **Value:** Collez le contenu de `cat ~/.ssh/cicd_deploy_key`
- **Type:** File
- **Protect variable:** ✓
- **Mask variable:** ☐
- Cliquez sur **Add variable**

#### Variable 5 : ENV_FILE
- **Key:** `ENV_FILE`
- **Value:** Collez le contenu de votre .env
- **Type:** File
- **Protect variable:** ✓
- **Mask variable:** ☐
- Cliquez sur **Add variable**

### 4. Vérifier

Vous devriez voir 5 variables dans la liste.

---

## ✅ Étape 5 : Tester le déploiement

### Pour GitHub Actions :

```bash
# 1. Committez et pushez le workflow
git add .github/workflows/deploy.yml
git commit -m "Add CI/CD deployment"
git push origin main

# 2. Vérifiez l'exécution
# Allez sur : https://github.com/votre-username/votre-repo/actions
```

### Pour GitLab CI :

```bash
# 1. Committez et pushez le fichier CI
git add .gitlab-ci.yml
git commit -m "Add GitLab CI/CD"
git push origin main

# 2. Vérifiez l'exécution
# Allez sur : https://gitlab.com/votre-username/votre-repo/-/pipelines
```

---

## 🐛 Dépannage

### Erreur : "Permission denied (publickey)"

**Problème :** La clé SSH n'est pas correctement configurée

**Solution :**
```bash
# Vérifiez que la clé publique est sur le VPS
ssh root@VOTRE_IP_VPS "cat ~/.ssh/authorized_keys"

# Testez la connexion manuellement
ssh -i ~/.ssh/cicd_deploy_key root@VOTRE_IP_VPS
```

### Erreur : "Host key verification failed"

**Problème :** Le VPS n'est pas dans known_hosts

**Solution :** Le workflow devrait gérer ça automatiquement avec `ssh-keyscan`, mais vous pouvez tester :
```bash
ssh-keyscan -p 22 VOTRE_IP_VPS >> ~/.ssh/known_hosts
```

### Erreur : "Bad owner or permissions on .ssh/config"

**Problème :** Permissions incorrectes sur les fichiers SSH

**Solution :**
```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/cicd_deploy_key
chmod 644 ~/.ssh/cicd_deploy_key.pub
```

### Le déploiement se lance mais échoue

1. **Vérifiez les logs** dans l'interface GitHub Actions / GitLab CI
2. **Vérifiez les secrets** sont correctement configurés
3. **Testez manuellement** :
   ```bash
   ssh -i ~/.ssh/cicd_deploy_key root@VOTRE_IP_VPS "cd /home/gestionstock/app && ls -la"
   ```

### Erreur : "Worker failed to boot" ou problèmes de variables d'environnement

**Problème :** Le fichier .env est mal formaté (variables sur la même ligne)

**Symptômes :**
- Gunicorn affiche "Worker failed to boot"
- Les variables d'environnement ne sont pas reconnues
- DEBUG et ALLOWED_HOSTS semblent fusionnés

**Cause :** Le secret `ENV_FILE` dans GitHub a un formatage incorrect

**Solution :**

1. **Vérifiez le format de votre .env** - Chaque variable DOIT être sur une ligne séparée :

   ✅ **CORRECT :**
   ```env
   SECRET_KEY=abc123
   DEBUG=False
   ALLOWED_HOSTS=example.com
   ```

   ❌ **INCORRECT :**
   ```env
   SECRET_KEY=abc123DEBUG=False
   ALLOWED_HOSTS=example.com
   ```

2. **Mettez à jour le secret ENV_FILE dans GitHub :**
   - Allez sur : `Settings → Secrets and variables → Actions`
   - Cliquez sur `ENV_FILE` → `Update`
   - Collez le contenu correctement formaté (une variable par ligne)
   - Cliquez sur `Update secret`

3. **Redéployez :**
   - Allez sur : `Actions → Deploy to VPS (Manual Only)`
   - Cliquez sur `Run workflow`

4. **Vérifiez sur le VPS** (après déploiement) :
   ```bash
   ssh root@VOTRE_IP_VPS "cat /home/gestionstock/app/.env"
   ```
   Assurez-vous que chaque variable est bien sur une ligne séparée

---

## 📱 Déploiement manuel (déclencher manuellement)

### GitHub Actions :

```
1. Allez sur : Actions → Deploy to VPS
2. Cliquez sur "Run workflow"
3. Sélectionnez la branche (main)
4. Cliquez sur "Run workflow"
```

### GitLab CI :

```
1. Allez sur : CI/CD → Pipelines
2. Cliquez sur "Run pipeline"
3. Sélectionnez la branche (main)
4. Dans la liste des jobs, cliquez sur le bouton "play" à côté de "deploy"
```

---

## 🔒 Sécurité

### ✅ Bonnes pratiques :

- ✓ Repository **privé**
- ✓ Secrets **protégés**
- ✓ Clé SSH **dédiée** au CI/CD
- ✓ Ne **jamais** commiter .env dans Git
- ✓ Utiliser **Protect variable** sur GitLab
- ✓ Limiter l'accès au repository

### ❌ À éviter :

- ✗ Repository public avec secrets
- ✗ Partager les secrets
- ✗ Utiliser votre clé SSH personnelle
- ✗ Commiter des credentials
- ✗ Laisser DEBUG=True en production

---

## 📞 Support

Si vous rencontrez des problèmes :

1. Vérifiez les logs du workflow
2. Testez la connexion SSH manuellement
3. Vérifiez que tous les secrets sont configurés
4. Consultez la documentation :
   - [GitHub Actions](https://docs.github.com/en/actions)
   - [GitLab CI/CD](https://docs.gitlab.com/ee/ci/)

---

**Prochaine étape** : Poussez votre code et regardez le déploiement automatique ! 🚀
