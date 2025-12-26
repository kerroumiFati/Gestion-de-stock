#!/bin/bash

# Script de déploiement automatique pour VPS Octenium
# GestionStock Django Application

set -e  # Arrêter en cas d'erreur

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}======================================"
echo "  Déploiement GestionStock Django"
echo "======================================${NC}"

# Vérifier si on est root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Veuillez exécuter ce script en tant que root ou avec sudo${NC}"
    exit 1
fi

echo -e "${YELLOW}Étape 1/13: Mise à jour du système${NC}"
apt update
apt upgrade -y

echo -e "${YELLOW}Étape 2/13: Installation des dépendances système${NC}"
apt install -y python3 python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib libpq-dev \
    nginx git build-essential libssl-dev libffi-dev

echo -e "${YELLOW}Étape 3/13: Configuration de PostgreSQL${NC}"
read -p "Nom de la base de données [gestion_stock_db]: " DB_NAME
DB_NAME=${DB_NAME:-gestion_stock_db}

read -p "Utilisateur PostgreSQL [gestion_stock_user]: " DB_USER
DB_USER=${DB_USER:-gestion_stock_user}

read -sp "Mot de passe PostgreSQL: " DB_PASSWORD
echo

# Créer la base de données
sudo -u postgres psql <<EOF
CREATE DATABASE $DB_NAME;
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
ALTER ROLE $DB_USER SET client_encoding TO 'utf8';
ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';
ALTER ROLE $DB_USER SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF

echo -e "${GREEN}Base de données créée avec succès${NC}"

echo -e "${YELLOW}Étape 4/13: Création de l'utilisateur système${NC}"
if ! id "gestionstock" &>/dev/null; then
    adduser --system --group --home /home/gestionstock gestionstock
    echo -e "${GREEN}Utilisateur gestionstock créé${NC}"
else
    echo -e "${YELLOW}L'utilisateur gestionstock existe déjà${NC}"
fi

echo -e "${YELLOW}Étape 5/13: Configuration du répertoire de l'application${NC}"
mkdir -p /home/gestionstock/app
mkdir -p /home/gestionstock/logs

# Demander le chemin du projet
read -p "Chemin vers le dossier du projet sur votre machine locale (sera copié via scp): " PROJECT_PATH
if [ -z "$PROJECT_PATH" ]; then
    echo -e "${RED}Chemin du projet requis. Veuillez copier manuellement vos fichiers vers /home/gestionstock/app/${NC}"
else
    echo -e "${YELLOW}Vous devrez exécuter depuis votre machine locale:${NC}"
    echo "scp -r $PROJECT_PATH/* root@$(hostname -I | awk '{print $1}'):/home/gestionstock/app/"
    read -p "Appuyez sur Entrée une fois les fichiers copiés..."
fi

echo -e "${YELLOW}Étape 6/13: Configuration de l'environnement virtuel Python${NC}"
cd /home/gestionstock/app
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${YELLOW}Étape 7/13: Configuration des variables d'environnement${NC}"
SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")

read -p "Nom de domaine (ou adresse IP): " DOMAIN
ALLOWED_HOSTS="$DOMAIN,www.$DOMAIN,$(hostname -I | awk '{print $1}')"

cat > /home/gestionstock/app/.env <<EOF
SECRET_KEY=$SECRET_KEY
DEBUG=False
ALLOWED_HOSTS=$ALLOWED_HOSTS

# Database
DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME

# CORS
CORS_ALLOW_ALL_ORIGINS=False
EOF

echo -e "${GREEN}Fichier .env créé${NC}"

echo -e "${YELLOW}Étape 8/13: Migration de la base de données${NC}"
python manage.py collectstatic --noinput
python manage.py migrate

echo -e "${YELLOW}Création du superutilisateur Django${NC}"
python manage.py createsuperuser

echo -e "${YELLOW}Étape 9/13: Configuration de Gunicorn${NC}"
cat > /home/gestionstock/app/gunicorn_config.py <<'EOF'
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
EOF

echo -e "${YELLOW}Étape 10/13: Configuration du service Systemd${NC}"
cat > /etc/systemd/system/gestionstock.service <<EOF
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
EOF

# Ajuster les permissions
chown -R gestionstock:gestionstock /home/gestionstock

# Démarrer le service
systemctl daemon-reload
systemctl start gestionstock
systemctl enable gestionstock

echo -e "${GREEN}Service Gunicorn démarré${NC}"

echo -e "${YELLOW}Étape 11/13: Configuration de Nginx${NC}"
cat > /etc/nginx/sites-available/gestionstock <<EOF
server {
    listen 80;
    server_name $ALLOWED_HOSTS;

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
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
    }
}
EOF

ln -sf /etc/nginx/sites-available/gestionstock /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

echo -e "${GREEN}Nginx configuré${NC}"

echo -e "${YELLOW}Étape 12/13: Configuration du pare-feu${NC}"
ufw allow 'Nginx Full'
ufw allow OpenSSH
echo "y" | ufw enable

echo -e "${YELLOW}Étape 13/13: Installation de SSL (optionnel)${NC}"
read -p "Voulez-vous installer un certificat SSL avec Let's Encrypt? (o/n): " INSTALL_SSL

if [ "$INSTALL_SSL" = "o" ] || [ "$INSTALL_SSL" = "O" ]; then
    apt install -y certbot python3-certbot-nginx
    certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN || echo -e "${YELLOW}Certificat SSL non installé. Vous pouvez le faire manuellement plus tard.${NC}"
fi

echo -e "${GREEN}======================================"
echo "  Déploiement terminé avec succès!"
echo "======================================${NC}"
echo ""
echo -e "${GREEN}Votre application est maintenant accessible à:${NC}"
echo "  http://$DOMAIN"
echo "  http://$(hostname -I | awk '{print $1}')"
echo ""
echo -e "${YELLOW}Informations importantes:${NC}"
echo "  - Répertoire de l'app: /home/gestionstock/app"
echo "  - Logs Gunicorn: /home/gestionstock/logs/"
echo "  - Base de données: $DB_NAME"
echo "  - Utilisateur DB: $DB_USER"
echo ""
echo -e "${YELLOW}Commandes utiles:${NC}"
echo "  - Redémarrer l'app: sudo systemctl restart gestionstock"
echo "  - Voir les logs: sudo journalctl -u gestionstock -f"
echo "  - Voir les logs Nginx: sudo tail -f /var/log/nginx/error.log"
echo ""
echo -e "${GREEN}Profitez de votre application!${NC}"
