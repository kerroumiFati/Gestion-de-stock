# 🚀 Déploiement sur Vercel - Guide Complet

## ⚠️ **IMPORTANT : Limitations de Vercel avec Django**

Vercel est principalement optimisé pour les applications JavaScript/Node.js. Déployer Django sur Vercel présente certaines limitations :

### 🔴 **Limitations importantes :**
- **Base de données SQLite** : Ne persiste pas entre les déploiements
- **Fichiers uploadés** : Ne persistent pas (stockage éphémère)
- **Timeout** : 10 secondes maximum par requête
- **Taille limitée** : 50MB maximum pour le déploiement

### ✅ **Solutions recommandées :**

#### **Option 1 : Déploiement sur Vercel (Basique)**
Pour un prototype ou une démonstration :

1. **Préparer le repository Git :**
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/votre-username/votre-repo.git
git push -u origin main
```

2. **Configurer les variables d'environnement sur Vercel :**
   - Aller sur [vercel.com](https://vercel.com)
   - Connecter votre repository GitHub
   - Dans les settings du projet, ajouter ces variables :
     - `SECRET_KEY` : Une clé secrète Django sécurisée
     - `DEBUG` : `False`
     - `ALLOWED_HOSTS` : `.vercel.app,votre-domaine.vercel.app`

3. **Déployer :**
   - Vercel détectera automatiquement le `vercel.json`
   - Le déploiement se fera automatiquement

#### **Option 2 : Solutions recommandées pour la production**

### 🌟 **Alternatives recommandées :**

#### **A. Railway (Recommandé)**
```bash
# Installation
npm install -g @railway/cli

# Login et déploiement
railway login
railway init
railway up
```

#### **B. Heroku**
```bash
# Créer Procfile
echo "web: gunicorn Gestion_stock.wsgi --log-file -" > Procfile

# Déployer
heroku create votre-app-name
git push heroku main
```

#### **C. DigitalOcean App Platform**
- Interface simple
- Base de données PostgreSQL incluse
- Scaling automatique

#### **D. Render**
- Alternative gratuite à Heroku
- Base de données PostgreSQL gratuite
- SSL automatique

## 📝 **Configuration pour Vercel (si vous voulez quand même essayer)**

### 1. Modifier la base de données pour PostgreSQL
Dans `settings.py`, ajoutez :

```python
import dj_database_url

# Database pour production
if not DEBUG:
    DATABASES = {
        'default': dj_database_url.parse(
            config('DATABASE_URL', default='sqlite:///' + os.path.join(BASE_DIR, 'db.sqlite3'))
        )
    }
```

### 2. Ajouter au requirements.txt :
```
dj-database-url>=1.0.0
```

### 3. Variables d'environnement Vercel :
- `SECRET_KEY` : Clé secrète Django
- `DEBUG` : `False`
- `ALLOWED_HOSTS` : `.vercel.app`
- `DATABASE_URL` : URL de votre base PostgreSQL

## 🎯 **Recommandation finale**

Pour votre application de gestion de stock, je recommande **Railway** ou **Render** :

### **Railway (Le plus simple) :**
1. Connectez votre repo GitHub
2. Railway détecte automatiquement Django
3. Ajoute automatiquement PostgreSQL
4. Déploiement en un clic

### **Render (Alternative gratuite) :**
1. Connectez votre repo GitHub
2. Configurez le build command : `pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput`
3. Start command : `gunicorn Gestion_stock.wsgi:application`
4. Ajoutez une base PostgreSQL gratuite

Voulez-vous que je vous aide avec l'une de ces alternatives ?