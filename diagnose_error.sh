#!/bin/bash

# Script de diagnostic pour trouver l'erreur de démarrage
# GestionStock Django Application

set +e  # Ne pas arrêter en cas d'erreur

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration (modifiez selon vos besoins)
VPS_HOST="votre-ip-vps"  # Changez avec votre IP VPS
VPS_USER="gestionstock"
VPS_PORT="22"
SSH_KEY="$HOME/.ssh/id_rsa"

print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_error() {
    echo -e "${RED}$1${NC}"
}

print_info() {
    echo -e "${YELLOW}$1${NC}"
}

print_header "Diagnostic des erreurs GestionStock"

# Récupérer les logs complets
print_header "1. Logs systemd (100 dernières lignes)"
ssh -i "$SSH_KEY" -p "$VPS_PORT" "$VPS_USER@$VPS_HOST" \
    "sudo journalctl -u gestionstock -n 100 --no-pager"

echo ""
print_header "2. Logs Gunicorn (erreurs)"
ssh -i "$SSH_KEY" -p "$VPS_PORT" "$VPS_USER@$VPS_HOST" \
    "tail -100 /home/gestionstock/logs/gunicorn-error.log 2>/dev/null || echo 'Fichier de log introuvable'"

echo ""
print_header "3. Test manuel de l'application Django"
ssh -i "$SSH_KEY" -p "$VPS_PORT" "$VPS_USER@$VPS_HOST" bash << 'EOF'
    cd /home/gestionstock/app
    source venv/bin/activate

    echo "Test d'importation du WSGI..."
    python -c "
import sys
import os
sys.path.insert(0, '/home/gestionstock/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
try:
    from Gestion_stock.wsgi import application
    print('✓ WSGI importé avec succès')
except Exception as e:
    print(f'✗ Erreur d\'importation WSGI: {e}')
    import traceback
    traceback.print_exc()
"
EOF

echo ""
print_header "4. Vérification des dépendances"
ssh -i "$SSH_KEY" -p "$VPS_PORT" "$VPS_USER@$VPS_HOST" bash << 'EOF'
    cd /home/gestionstock/app
    source venv/bin/activate

    echo "Vérification des packages installés..."
    pip list

    echo ""
    echo "Vérification de requirements.txt..."
    if [ -f requirements.txt ]; then
        pip check
    else
        echo "✗ requirements.txt introuvable"
    fi
EOF

echo ""
print_header "5. Vérification des fichiers et permissions"
ssh -i "$SSH_KEY" -p "$VPS_PORT" "$VPS_USER@$VPS_HOST" bash << 'EOF'
    echo "Fichiers dans /home/gestionstock/app:"
    ls -la /home/gestionstock/app/

    echo ""
    echo "Fichier .env:"
    if [ -f /home/gestionstock/app/.env ]; then
        echo "✓ .env existe"
        echo "Variables définies (masquées):"
        grep -v "PASSWORD\|SECRET" /home/gestionstock/app/.env 2>/dev/null || echo "Impossible de lire .env"
    else
        echo "✗ .env introuvable"
    fi

    echo ""
    echo "Fichier manage.py:"
    if [ -f /home/gestionstock/app/manage.py ]; then
        echo "✓ manage.py existe"
    else
        echo "✗ manage.py introuvable"
    fi

    echo ""
    echo "Dossier Gestion_stock:"
    if [ -d /home/gestionstock/app/Gestion_stock ]; then
        echo "✓ Gestion_stock existe"
        ls -la /home/gestionstock/app/Gestion_stock/
    else
        echo "✗ Gestion_stock introuvable"
    fi
EOF

echo ""
print_header "6. Test de connexion à la base de données"
ssh -i "$SSH_KEY" -p "$VPS_PORT" "$VPS_USER@$VPS_HOST" bash << 'EOF'
    cd /home/gestionstock/app
    source venv/bin/activate

    python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
try:
    django.setup()
    from django.db import connection
    connection.ensure_connection()
    print('✓ Connexion à la base de données réussie')
except Exception as e:
    print(f'✗ Erreur de connexion à la base de données: {e}')
    import traceback
    traceback.print_exc()
"
EOF

echo ""
print_header "7. Statut du service"
ssh -i "$SSH_KEY" -p "$VPS_PORT" "$VPS_USER@$VPS_HOST" \
    "sudo systemctl status gestionstock --no-pager -l"

echo ""
print_info "=== Diagnostic terminé ==="
print_info "Analysez les erreurs ci-dessus pour identifier le problème."
