# CI/CD Quick Start - Déploiement Automatique

## 🎯 Objectif

Déployer automatiquement votre application à chaque `git push` sur la branche `main`.

---

## ⚡ Installation en 5 minutes

### Étape 1 : Générer la clé SSH (2 min)

```bash
# Sur votre machine locale
ssh-keygen -t ed25519 -C "cicd-deploy" -f ~/.ssh/cicd_deploy_key

# Afficher la clé PUBLIQUE
cat ~/.ssh/cicd_deploy_key.pub
# Copiez le résultat

# Afficher la clé PRIVÉE
cat ~/.ssh/cicd_deploy_key
# Copiez TOUT (y compris BEGIN et END)
```

### Étape 2 : Ajouter la clé au VPS (1 min)

```bash
# Copier automatiquement
ssh-copy-id -i ~/.ssh/cicd_deploy_key.pub root@VOTRE_IP_VPS

# OU manuellement
ssh root@VOTRE_IP_VPS
nano ~/.ssh/authorized_keys
# Collez la clé publique
# Ctrl+X, Y, Enter
```

### Étape 3 : Configurer les secrets GitHub (2 min)

1. Allez sur votre repo : `github.com/votre-username/votre-repo`
2. **Settings** → **Secrets and variables** → **Actions**
3. Ajoutez 5 secrets :

```
VPS_HOST       = votre-ip-vps
VPS_USERNAME   = gestionstock
VPS_PORT       = 22
VPS_SSH_KEY    = [collez la clé PRIVÉE]
ENV_FILE       = [collez le contenu de votre .env]
```

### Étape 4 : Ajouter le workflow GitHub (30 sec)

```bash
# Les fichiers sont déjà créés dans votre projet !
# Vérifiez :
ls -la .github/workflows/

# Vous devriez voir :
# - deploy.yml
# - deploy-with-tests.yml
```

### Étape 5 : Déployer ! (10 sec)

```bash
git add .
git commit -m "Setup CI/CD deployment"
git push origin main

# C'est tout ! 🚀
# Le déploiement se lance automatiquement
```

---

## 📊 Voir le déploiement

### Sur GitHub :

```
1. Allez sur votre repository
2. Cliquez sur l'onglet "Actions"
3. Vous verrez le workflow en cours d'exécution
4. Cliquez dessus pour voir les détails
```

**États possibles :**
- 🟡 Jaune (en cours) - Le déploiement est en cours
- 🟢 Vert (success) - Déploiement réussi !
- 🔴 Rouge (failed) - Erreur, vérifiez les logs

---

## 🔄 Flux de travail typique

```
1. Vous développez localement
   ↓
2. git add .
   git commit -m "Add new feature"
   git push origin main
   ↓
3. GitHub Actions détecte le push
   ↓
4. Tests automatiques (si configuré)
   ↓
5. Sauvegarde de la base de données
   ↓
6. Synchronisation des fichiers
   ↓
7. Installation des dépendances
   ↓
8. Migrations de la base de données
   ↓
9. Collecte des fichiers statiques
   ↓
10. Redémarrage de l'application
    ↓
11. Health check
    ↓
12. ✅ Déploiement terminé !
```

**Temps total** : ~2-3 minutes

---

## 🎮 Commandes utiles

### Déclencher un déploiement manuel

Sur GitHub :
```
Actions → Deploy to VPS → Run workflow → Run workflow
```

### Voir les logs en temps réel sur le VPS

```bash
ssh gestionstock@VOTRE_IP_VPS
sudo journalctl -u gestionstock -f
```

### Vérifier l'état de l'application

```bash
ssh gestionstock@VOTRE_IP_VPS
sudo systemctl status gestionstock
```

### Restaurer une sauvegarde

```bash
ssh gestionstock@VOTRE_IP_VPS
ls -lh /home/gestionstock/backups/

# Restaurer la base de données
sudo -u postgres psql gestion_stock_db < /home/gestionstock/backups/db_YYYYMMDD_HHMMSS.sql
```

---

## 🐛 Problèmes courants

### ❌ Le workflow ne se lance pas

**Cause :** Le fichier workflow n'est pas au bon endroit

**Solution :**
```bash
# Vérifiez l'emplacement
ls -la .github/workflows/deploy.yml

# Doit être exactement :
# .github/workflows/deploy.yml
```

### ❌ "Permission denied (publickey)"

**Cause :** La clé SSH n'est pas correctement configurée

**Solution :**
```bash
# Testez la connexion
ssh -i ~/.ssh/cicd_deploy_key root@VOTRE_IP_VPS

# Si ça ne marche pas, réajoutez la clé
ssh-copy-id -i ~/.ssh/cicd_deploy_key.pub root@VOTRE_IP_VPS
```

### ❌ L'application ne redémarre pas

**Cause :** Problème avec les migrations ou les dépendances

**Solution :**
```bash
# Connectez-vous au VPS
ssh gestionstock@VOTRE_IP_VPS

# Vérifiez les logs
sudo journalctl -u gestionstock -n 50

# Redémarrez manuellement
sudo systemctl restart gestionstock
```

### ❌ "rsync: command not found"

**Cause :** rsync n'est pas installé sur le VPS

**Solution :**
```bash
ssh root@VOTRE_IP_VPS
apt install -y rsync
```

---

## 📁 Structure des fichiers

```
votre-projet/
├── .github/
│   └── workflows/
│       ├── deploy.yml              # Workflow simple
│       └── deploy-with-tests.yml   # Workflow avec tests
├── .gitlab-ci.yml                  # Pour GitLab (optionnel)
├── deploy_manual.sh                # Déploiement manuel
├── CICD_DEPLOYMENT_GUIDE.md        # Guide complet
├── SETUP_CICD_SECRETS.md           # Configuration des secrets
└── CICD_QUICK_START.md             # Ce fichier
```

---

## 🔐 Sécurité - Checklist

Avant de déployer, vérifiez :

- [ ] Repository GitHub est **privé**
- [ ] Fichier `.env` est dans `.gitignore`
- [ ] `.env` n'est **jamais** commité dans Git
- [ ] Secrets GitHub sont configurés
- [ ] Clé SSH dédiée au CI/CD
- [ ] `DEBUG=False` dans le fichier ENV_FILE
- [ ] `SECRET_KEY` est forte et unique
- [ ] Sauvegarde automatique activée dans le workflow

---

## 📈 Workflow recommandé pour une équipe

### Branches :

```
main           → Production (déploie automatiquement)
develop        → Staging (déploie sur serveur de test)
feature/*      → Développement (pas de déploiement)
```

### Processus :

```
1. Créer une branche feature
   git checkout -b feature/nouvelle-fonctionnalite

2. Développer et tester localement
   [code code code]

3. Commit et push
   git add .
   git commit -m "Add: nouvelle fonctionnalité"
   git push origin feature/nouvelle-fonctionnalite

4. Créer une Pull Request vers develop
   GitHub → Pull Requests → New

5. Review et merge vers develop
   → Déploie sur serveur de staging

6. Tester sur staging
   → Si OK, créer PR de develop vers main

7. Merge vers main
   → Déploie automatiquement en production
```

---

## 📚 Fichiers de configuration

### Workflow simple (deploy.yml)

✅ Recommandé pour débuter
- Déploiement direct
- Pas de tests
- Rapide (~2 min)

### Workflow avec tests (deploy-with-tests.yml)

✅ Recommandé pour production
- Exécute les tests avant déploiement
- Sauvegarde automatique
- Health check
- Plus sûr (~4-5 min)

### Déploiement manuel (deploy_manual.sh)

✅ Alternative sans CI/CD
- Script interactif
- Déploiement depuis votre machine
- Pas besoin de configurer GitHub

**Utilisation :**
```bash
chmod +x deploy_manual.sh

# Éditez les variables en haut du fichier
nano deploy_manual.sh

# Lancez
./deploy_manual.sh
```

---

## 🎓 Pour aller plus loin

### Ajouter des notifications

Modifiez le workflow pour envoyer des notifications :

```yaml
# Dans .github/workflows/deploy.yml
- name: Send notification
  if: success()
  run: |
    curl -X POST https://hooks.slack.com/services/YOUR/WEBHOOK/URL \
      -H 'Content-Type: application/json' \
      -d '{"text":"✅ Deployment successful!"}'
```

### Déployer sur plusieurs environnements

```yaml
# Staging pour develop
on:
  push:
    branches:
      - develop
env:
  VPS_HOST: ${{ secrets.STAGING_VPS_HOST }}

# Production pour main
on:
  push:
    branches:
      - main
env:
  VPS_HOST: ${{ secrets.PRODUCTION_VPS_HOST }}
```

### Rollback automatique

Ajoutez un step qui vérifie le health check et rollback si échec :

```yaml
- name: Rollback on failure
  if: failure()
  run: |
    ssh ... << 'EOF'
      cd /home/gestionstock/app
      git checkout HEAD~1
      sudo systemctl restart gestionstock
    EOF
```

---

## ✅ C'est tout !

Votre workflow CI/CD est maintenant configuré. À chaque `git push` sur `main`, votre application se déploiera automatiquement ! 🎉

**Questions ?** Consultez :
- `CI_CD_DEPLOYMENT_GUIDE.md` - Guide détaillé
- `SETUP_CICD_SECRETS.md` - Configuration des secrets
- [GitHub Actions Docs](https://docs.github.com/en/actions)

---

**Happy deploying! 🚀**
