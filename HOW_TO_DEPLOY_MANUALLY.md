# Comment Déployer Manuellement

Guide visuel simple pour déployer quand VOUS le décidez.

---

## 🎯 Principe

```
Push du code → GitHub (stockage uniquement)
               ↓
               Rien ne se passe automatiquement
               ↓
Vous cliquez "Deploy" → Déploiement sur VPS
```

**Résultat** : Vous pushez autant que vous voulez, le déploiement ne se fait QUE quand vous cliquez.

---

## ⚡ Setup rapide (une seule fois)

### 1. Supprimer les workflows automatiques

```bash
# Supprimer les anciens workflows automatiques
rm .github/workflows/deploy.yml 2>/dev/null || true
rm .github/workflows/deploy-with-tests.yml 2>/dev/null || true

# Garder uniquement
ls .github/workflows/deploy-manual-only.yml

# Commit
git add .
git commit -m "Switch to manual deployment only"
git push
```

### 2. Vérifier les secrets GitHub

Allez sur : `github.com/votre-username/votre-repo/settings/secrets/actions`

Vérifiez que vous avez :
- ✅ VPS_HOST
- ✅ VPS_USERNAME
- ✅ VPS_PORT
- ✅ VPS_SSH_KEY
- ✅ ENV_FILE

**C'est tout ! Configuration terminée.** 🎉

---

## 🚀 Comment déployer (à chaque fois)

### Étape 1 : Développez normalement

```bash
# Travaillez sur votre code
git add .
git commit -m "Add new feature"
git push origin main
```

**Résultat** : Le code est sur GitHub, mais **RIEN ne se déploie**.

### Étape 2 : Quand vous voulez déployer

#### Sur ordinateur :

1. **Allez sur GitHub**
   ```
   https://github.com/votre-username/votre-repo
   ```

2. **Cliquez sur l'onglet "Actions"**
   ```
   [Code] [Issues] [Pull requests] [Actions] ← Cliquez ici
   ```

3. **Sélectionnez le workflow**
   ```
   Dans la barre de gauche :
   → Deploy to VPS (Manual Only)
   ```

4. **Cliquez sur "Run workflow"**
   ```
   Un bouton bleu "Run workflow" apparaît en haut à droite
   ```

5. **Choisissez les options**
   ```
   Branch: main (ou autre branche)
   Environnement: production
   Créer sauvegarde: ✓ (recommandé)
   Exécuter migrations: ✓ (si modifs DB)
   ```

6. **Cliquez "Run workflow"**
   ```
   Le déploiement démarre !
   ```

### Étape 3 : Suivre le déploiement

1. Le workflow apparaît dans la liste
2. Cliquez dessus pour voir les détails
3. Vous verrez chaque étape en temps réel :
   ```
   ✓ Checkout code
   ✓ Setup SSH
   ✓ Create backup
   ✓ Deploy to VPS
   ✓ Install dependencies
   ✓ Run migrations
   ✓ Collect static files
   ✓ Restart application
   ✓ Health check
   ```

4. Quand tout est vert ✅ : **Déploiement réussi !**

---

## 📱 Déployer depuis votre téléphone

### Via l'app GitHub Mobile :

1. **Ouvrez l'app GitHub**
2. **Allez sur votre repository**
3. **Menu → Actions**
4. **Deploy to VPS (Manual Only)**
5. **Run workflow**
6. **Choisissez les options**
7. **Run workflow**

### Via navigateur mobile :

1. **Allez sur github.com**
2. **Votre repository → Actions**
3. **Deploy to VPS (Manual Only)**
4. **Run workflow**

---

## 🔄 Workflow typique

### Scénario : Travail sur plusieurs projets

```
Lundi - Client A :
├─ git checkout client-a
├─ [développement]
├─ git push
└─ Pas de déploiement

Mardi - Client B :
├─ git checkout client-b
├─ [développement]
├─ git push
└─ Pas de déploiement

Mercredi - Client A terminé :
├─ git checkout client-a
├─ GitHub → Actions → Run workflow
└─ Déploiement Client A ✅

Jeudi - Client B terminé :
├─ git checkout client-b
├─ GitHub → Actions → Run workflow
└─ Déploiement Client B ✅
```

---

## 📊 Timeline d'un déploiement manuel

```
00:00 - Vous cliquez "Run workflow"
00:05 - GitHub démarre le workflow
00:10 - Connexion SSH au VPS
00:20 - Création de sauvegarde
00:40 - Synchronisation des fichiers
01:00 - Installation des dépendances
01:30 - Exécution des migrations
01:50 - Collecte des fichiers statiques
02:00 - Redémarrage de l'application
02:10 - Health check
02:15 - ✅ Terminé !

Durée totale : ~2-3 minutes
```

---

## ✅ Checklist avant déploiement

Avant de cliquer "Run workflow" :

- [ ] Code testé en local
- [ ] Migrations créées (si modif DB)
- [ ] Code poussé sur GitHub
- [ ] Bonne branche sélectionnée
- [ ] Sauvegarde activée
- [ ] Heure appropriée (éviter heures de pointe)

---

## 🎛️ Options de déploiement expliquées

### Branch (Branche)

```
main        → Version production
develop     → Version développement
feature-x   → Branche spécifique
```

Choisissez la branche que vous voulez déployer.

### Environment (Environnement)

```
production  → VPS principal
staging     → VPS de test (si configuré)
```

### Create backup (Créer sauvegarde)

```
true  (✓) → Sauvegarde DB et media AVANT déploiement (RECOMMANDÉ)
false (✗) → Pas de sauvegarde (déploiement plus rapide)
```

⚠️ **Toujours activer en production !**

### Run migrations (Exécuter migrations)

```
true  (✓) → Applique les migrations Django
false (✗) → Ignore les migrations
```

**Quand cocher ✓** :
- Vous avez modifié les models Django
- Vous avez créé de nouvelles migrations
- Premier déploiement

**Quand décocher ✗** :
- Aucun changement de DB
- Déploiement uniquement de code/templates/CSS

---

## 🔍 Voir l'historique des déploiements

### Sur GitHub :

```
Repository → Actions
```

Vous verrez :
```
✅ Deploy to VPS (Manual Only)  #12  main  2 hours ago  Déployé par: vous
✅ Deploy to VPS (Manual Only)  #11  main  1 day ago    Déployé par: vous
✅ Deploy to VPS (Manual Only)  #10  main  3 days ago   Déployé par: vous
```

Cliquez sur un déploiement pour voir :
- Date et heure
- Qui l'a déclenché
- Branche déployée
- Logs complets
- Durée

---

## 🐛 Que faire si un déploiement échoue ?

### Pendant le déploiement :

1. **Annuler** : Cliquez sur "Cancel workflow"

### Après un échec :

1. **Consultez les logs** :
   ```
   Actions → Déploiement échoué → Cliquez dessus
   → Trouvez l'étape en rouge ✗
   → Lisez le message d'erreur
   ```

2. **Erreurs courantes** :

   #### "Permission denied (publickey)"
   ```
   → Problème de clé SSH
   → Vérifiez VPS_SSH_KEY dans les secrets
   ```

   #### "Migration failed"
   ```
   → Problème de migration Django
   → Connectez-vous au VPS et vérifiez
   ```

   #### "rsync error"
   ```
   → Problème de synchronisation
   → Vérifiez l'espace disque du VPS
   ```

3. **Restaurer** :
   ```bash
   # Si backup créé, restaurez-le
   ssh gestionstock@VOTRE_IP_VPS
   ls /home/gestionstock/backups/

   # Restaurer la DB
   sudo -u postgres psql gestion_stock_db < /home/gestionstock/backups/db_XXXXXX.sql
   ```

---

## 💡 Astuces

### Astuce 1 : Déployer rapidement

Créez un bookmark :
```
https://github.com/VOTRE-USERNAME/VOTRE-REPO/actions/workflows/deploy-manual-only.yml
```

### Astuce 2 : Notifications

Ajoutez votre email dans Settings → Notifications pour être alerté.

### Astuce 3 : Déploiement programmé

Vous pouvez ajouter un déclencheur cron dans le workflow :
```yaml
on:
  workflow_dispatch:  # Manuel
  schedule:
    - cron: '0 2 * * 0'  # Tous les dimanches à 2h du matin
```

### Astuce 4 : Déployer plusieurs projets

Créez plusieurs workflows :
```
.github/workflows/
├── deploy-client-a.yml
├── deploy-client-b.yml
└── deploy-client-c.yml
```

Chacun avec ses propres secrets :
```
VPS_HOST_CLIENT_A
VPS_SSH_KEY_CLIENT_A
etc.
```

---

## 📋 Récapitulatif

### Ce qui a changé :

**AVANT** (déploiement automatique) :
```
git push → Déploiement automatique → Stressant !
```

**MAINTENANT** (déploiement manuel) :
```
git push → Rien
Quand prêt → Clic "Run workflow" → Déploiement → Contrôle total !
```

### Avantages pour vous :

✅ Pushez sans stress
✅ Travaillez sur plusieurs projets
✅ Déployez aux heures creuses
✅ Testez avant de déployer
✅ Contrôle total

---

## 🎓 Exemple complet

```bash
# 1. Lundi matin - Développement
git checkout main
git pull

# 2. Travail sur nouvelle feature
# ... code code code ...

# 3. Commit et push (plusieurs fois dans la journée)
git add .
git commit -m "Work in progress"
git push origin main
# → Rien ne se déploie, pas de stress

git commit -m "Continue feature"
git push origin main
# → Toujours rien

git commit -m "Complete feature"
git push origin main
# → Toujours rien

# 4. Vendredi après-midi - Feature terminée
# Tests locaux OK
python manage.py test  # ✓ OK

# 5. Déploiement
# GitHub → Actions → Run workflow
# [Choisir les options]
# Run workflow

# 6. Café ☕ (2-3 minutes)

# 7. Vérification
# → Logs verts ✅
# → Site en ligne ✅
# → Weekend tranquille ! 🎉
```

---

**Vous contrôlez maintenant vos déploiements ! 🚀**

Questions ? Consultez [DEPLOYMENT_STRATEGIES.md](DEPLOYMENT_STRATEGIES.md)
