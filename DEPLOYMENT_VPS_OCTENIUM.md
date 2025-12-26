# Guide de déploiement sur VPS Octenium

Ce guide vous explique comment déployer votre application Django de gestion de stock sur un VPS Octenium.

## Prérequis

- Un VPS Octenium (Ubuntu 20.04/22.04 recommandé)
- Accès SSH à votre VPS
- Un nom de domaine (optionnel mais recommandé)

## Étape 1 : Connexion au VPS

Connectez-vous à votre VPS via SSH :

```bash
ssh root@votre-ip-vps
# ou
ssh votre-utilisateur@votre-ip-vps
```

## Étape 2 : Mise à jour du système

```bash
sudo apt update
sudo apt upgrade -y
```

## Étape 3 : Installation des dépendances système

```bash
# Python et outils de développement
sudo apt install -y python3 python3-pip python3-venv python3-dev

# PostgreSQL
sudo apt install -y postgresql postgresql-contrib libpq-dev

# Nginx (serveur web)
sudo apt install -y nginx

# Git
sudo apt install -y git

# Autres dépendances
sudo apt install -y build-essential libssl-dev libffi-dev


```

## Étape 4 : Configuration de PostgreSQL

```bash
# Se connecter à PostgreSQL
sudo -u postgres psql

# Dans le shell PostgreSQL, créer la base de données et l'utilisateur
CREATE DATABASE gestion_stock_db;
CREATE USER gestion_stock_user WITH PASSWORD '2000';
ALTER ROLE gestion_stock_user SET client_encoding TO 'utf8';
ALTER ROLE gestion_stock_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE gestion_stock_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE gestion_stock_db TO gestion_stock_user;
\q
```

## Étape 5 : Création de l'utilisateur système

```bash
# Créer un utilisateur pour l'application
sudo adduser --system --group --home /home/gestionstock gestionstock
```

## Étape 6 : Cloner le projet

```bash
# Se connecter en tant qu'utilisateur gestionstock
sudo su - gestionstock

# Créer le répertoire de l'application
mkdir -p /home/gestionstock/app
cd /home/gestionstock/app

# Cloner votre projet (adaptez avec votre repository)
# Option 1: Si vous avez un repository Git
git clone https://github.com/votre-username/GestionStock-django.git .

# Option 2: Si vous transférez les fichiers depuis votre machine locale
# Depuis votre machine locale, exécutez :
# scp -r /chemin/vers/GestionStock-django-master/* utilisateur@votre-ip-vps:/home/gestionstock/app/
```

## Étape 7 : Configuration de l'environnement virtuel Python

```bash
# Créer l'environnement virtuel
python3 -m venv venv

# Activer l'environnement virtuel
source venv/bin/activate

# Mettre à jour pip
pip install --upgrade pip

# Installer les dépendances
pip install -r requirements.txt
```

## Étape 8 : Configuration des variables d'environnement

Créez le fichier `.env` :

```bash
nano .env
```

Ajoutez le contenu suivant (adaptez les valeurs) :

```env
SECRET_KEY=votre-cle-secrete-tres-longue-et-aleatoire
DEBUG=False
ALLOWED_HOSTS=votre-domaine.com,www.votre-domaine.com,votre-ip-vps

# Database
DATABASE_URL=postgresql://gestion_stock_user:VotreMotDePasseSecurise@localhost:5432/gestion_stock_db

# CORS
CORS_ALLOW_ALL_ORIGINS=False
```

Pour générer une SECRET_KEY sécurisée :

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Étape 9 : Préparation de Django

```bash
# Collecter les fichiers statiques
python manage.py collectstatic --noinput

# Appliquer les migrations
python manage.py migrate

# Créer un superutilisateur
python manage.py createsuperuser
```

## Étape 10 : Configuration de Gunicorn

Créez le fichier de configuration Gunicorn :

```bash
nano /home/gestionstock/app/gunicorn_config.py
```

Ajoutez :

```python
import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 2
errorlog = "/home/gestionstock/logs/gunicorn-error.log"
accesslog = "/home/gestionstock/logs/gunicorn-access.log"
loglevel = "info"
```

Créez le répertoire des logs :

```bash
mkdir -p /home/gestionstock/logs
```

## Étape 11 : Configuration du service Systemd pour Gunicorn

Sortez de l'utilisateur gestionstock :

```bash
exit
```

Créez le fichier de service :

```bash
sudo nano /etc/systemd/system/gestionstock.service
```

Ajoutez :

```ini
[Unit]
Description=GestionStock Gunicorn daemon
After=network.target

[Service]
User=gestionstock
Group=gestionstock
WorkingDirectory=/home/gestionstock/app
Environment="PATH=/home/gestionstock/app/venv/bin"
ExecStart=/home/gestionstock/app/venv/bin/gunicorn \
    --config /home/gestionstock/app/gunicorn_config.py \
    Gestion_stock.wsgi:application

[Install]
WantedBy=multi-user.target
```

Activez et démarrez le service :

```bash
sudo systemctl daemon-reload
sudo systemctl start gestionstock
sudo systemctl enable gestionstock
sudo systemctl status gestionstock
```

## Étape 12 : Configuration de Nginx

Créez le fichier de configuration Nginx :

```bash
sudo nano /etc/nginx/sites-available/gestionstock
```

Ajoutez :

```nginx
server {
    listen 80;
    server_name votre-domaine.com www.votre-domaine.com votre-ip-vps;

    client_max_body_size 20M;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        alias /home/gestionstock/app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /home/gestionstock/app/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
```

Activez la configuration :

```bash
sudo ln -s /etc/nginx/sites-available/gestionstock /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Étape 13 : Configuration du pare-feu

```bash
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
sudo ufw enable
```

## Étape 14 : Installation de SSL avec Certbot (optionnel mais recommandé)

Si vous avez un nom de domaine :

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d votre-domaine.com -d www.votre-domaine.com
```

Suivez les instructions et choisissez l'option de redirection automatique HTTPS.

## Étape 15 : Vérification du déploiement

Visitez votre site :
- http://votre-ip-vps ou http://votre-domaine.com
- Testez l'interface d'administration : http://votre-domaine.com/admin

## Commandes utiles

### Redémarrer l'application

```bash
sudo systemctl restart gestionstock
```

### Voir les logs de l'application

```bash
# Logs Gunicorn
tail -f /home/gestionstock/logs/gunicorn-error.log
tail -f /home/gestionstock/logs/gunicorn-access.log

# Logs Nginx
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log

# Logs Systemd
sudo journalctl -u gestionstock -f
```

### Mettre à jour l'application

```bash
sudo su - gestionstock
cd /home/gestionstock/app
source venv/bin/activate

# Récupérer les dernières modifications
git pull

# Installer les nouvelles dépendances
pip install -r requirements.txt

# Appliquer les migrations
python manage.py migrate

# Collecter les fichiers statiques
python manage.py collectstatic --noinput

# Redémarrer
exit
sudo systemctl restart gestionstock
```

### Sauvegarder la base de données

```bash
sudo -u postgres pg_dump gestion_stock_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restaurer la base de données

```bash
sudo -u postgres psql gestion_stock_db < backup_fichier.sql
```

## Dépannage

### L'application ne démarre pas

1. Vérifiez les logs :
   ```bash
   sudo journalctl -u gestionstock -n 50
   ```

2. Vérifiez que le service est actif :
   ```bash
   sudo systemctl status gestionstock
   ```

3. Vérifiez les permissions :
   ```bash
   sudo chown -R gestionstock:gestionstock /home/gestionstock/app
   ```

### Erreur 502 Bad Gateway

1. Vérifiez que Gunicorn tourne :
   ```bash
   sudo systemctl status gestionstock
   ```

2. Vérifiez la configuration Nginx :
   ```bash
   sudo nginx -t
   ```

### Problème de fichiers statiques

```bash
sudo su - gestionstock
cd /home/gestionstock/app
source venv/bin/activate
python manage.py collectstatic --noinput
exit
sudo systemctl restart gestionstock
sudo systemctl restart nginx
```

## Sécurité

1. **Changez régulièrement les mots de passe**
2. **Activez SSL/HTTPS** avec Certbot
3. **Configurez un pare-feu** avec UFW
4. **Gardez le système à jour** :
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```
5. **Configurez des sauvegardes automatiques**
6. **Limitez l'accès SSH** aux IPs de confiance
7. **Utilisez des clés SSH** au lieu de mots de passe

## Support

Pour toute question ou problème, consultez la documentation Django ou contactez le support Octenium.

---

**Dernière mise à jour** : Décembre 2024
