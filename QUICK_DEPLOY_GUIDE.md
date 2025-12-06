# 🚀 Guide Rapide - Déploiement Django

## ⚠️ IMPORTANT - Lisez d'abord !

**Vercel n'est PAS recommandé pour Django en production** car :
- Base de données SQLite non persistante
- Limitations de timeout (10s)
- Stockage éphémère

## 🎯 Options Recommandées (par ordre de préférence)

### 1. 🌟 **Railway (Le plus simple)**
```bash
# 1. Créer un compte sur railway.app
# 2. Connecter votre repo GitHub
# 3. Railway configure automatiquement Django + PostgreSQL
# 4. Déploiement en 1 clic !
```

### 2. 🔥 **Render (Gratuit)**
```bash
# 1. Créer un compte sur render.com
# 2. Nouveau "Web Service" depuis GitHub
# 3. Build Command: pip install -r requirements.txt && python manage.py collectstatic --noinput
# 4. Start Command: gunicorn Gestion_stock.wsgi:application
# 5. Ajouter PostgreSQL gratuit
```

### 3. 💙 **Heroku**
```bash
# Créer Procfile
echo "web: gunicorn Gestion_stock.wsgi --log-file -" > Procfile

# Déployer
heroku create votre-app-name
heroku addons:create heroku-postgresql:hobby-dev
git push heroku main
heroku run python manage.py migrate
```

## 🤷‍♂️ Si vous voulez quand même essayer Vercel

### Étapes rapides :

1. **Préparer le projet :**
```bash
python deploy.py  # Utilise notre script de préparation
```

2. **Git setup :**
```bash
git init
git add .
git commit -m "Ready for Vercel deployment"
git remote add origin https://github.com/votre-username/votre-repo.git
git push -u origin main
```

3. **Sur Vercel.com :**
   - Importer depuis GitHub
   - Configurer ces variables d'environnement :
     - `SECRET_KEY`: Une clé secrète unique
     - `DEBUG`: `False`
     - `ALLOWED_HOSTS`: `.vercel.app`

4. **Déployer !**

## 🎯 Ma recommandation

**Utilisez Railway** - C'est vraiment le plus simple pour Django :
1. Compte gratuit sur railway.app
2. "Deploy from GitHub"
3. Sélectionnez votre repo
4. Railway fait tout automatiquement !

## 🆘 Besoin d'aide ?

Dites-moi quelle option vous intéresse et je vous guide étape par étape !