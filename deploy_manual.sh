#!/bin/bash

# ========================================
# Script de déploiement manuel sécurisé
# GestionStock Django Application
# ========================================

set -e  # Arrêter en cas d'erreur

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ========================================
# CONFIGURATION - Modifiez ces valeurs
# ========================================

VPS_HOST="votre-ip-vps"           # Changez avec votre IP VPS
VPS_USER="gestionstock"            # Utilisateur sur le VPS
VPS_PORT="22"                      # Port SSH (22 par défaut)
VPS_PATH="/home/gestionstock/app"  # Chemin de l'application sur le VPS
SSH_KEY="$HOME/.ssh/id_rsa"        # Chemin vers votre clé SSH

# ========================================
# FONCTIONS
# ========================================

print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Vérifier la configuration
check_config() {
    print_header "Vérification de la configuration"

    if [ "$VPS_HOST" == "votre-ip-vps" ]; then
        print_error "Veuillez configurer VPS_HOST dans le script"
        exit 1
    fi

    if [ ! -f "$SSH_KEY" ]; then
        print_error "Clé SSH introuvable: $SSH_KEY"
        exit 1
    fi

    print_success "Configuration valide"
}

# Tester la connexion SSH
test_connection() {
    print_header "Test de connexion SSH"

    if ssh -i "$SSH_KEY" -p "$VPS_PORT" -o ConnectTimeout=5 "$VPS_USER@$VPS_HOST" "echo 'Connexion SSH réussie'" &>/dev/null; then
        print_success "Connexion SSH réussie"
    else
        print_error "Impossible de se connecter au VPS"
        print_info "Commande de test: ssh -i $SSH_KEY -p $VPS_PORT $VPS_USER@$VPS_HOST"
        exit 1
    fi
}

# Créer une sauvegarde sur le VPS
create_backup() {
    print_header "Création d'une sauvegarde"

    ssh -i "$SSH_KEY" -p "$VPS_PORT" "$VPS_USER@$VPS_HOST" bash << 'EOF'
        BACKUP_DIR="/home/gestionstock/backups"
        mkdir -p ${BACKUP_DIR}
        DATE=$(date +%Y%m%d_%H%M%S)

        echo "Sauvegarde de la base de données..."
        sudo -u postgres pg_dump gestion_stock_db > ${BACKUP_DIR}/db_${DATE}.sql 2>/dev/null || echo "Avertissement: impossible de sauvegarder la base de données"

        echo "Sauvegarde des fichiers media..."
        tar -czf ${BACKUP_DIR}/media_${DATE}.tar.gz -C /home/gestionstock/app media/ 2>/dev/null || echo "Avertissement: pas de fichiers media à sauvegarder"

        echo "✓ Sauvegarde créée: ${BACKUP_DIR}/db_${DATE}.sql"

        # Garder seulement les 5 dernières sauvegardes
        cd ${BACKUP_DIR}
        ls -t db_*.sql | tail -n +6 | xargs rm -f 2>/dev/null || true
        ls -t media_*.tar.gz | tail -n +6 | xargs rm -f 2>/dev/null || true
EOF

    print_success "Sauvegarde créée"
}

# Synchroniser les fichiers
sync_files() {
    print_header "Synchronisation des fichiers"

    print_info "Transfert des fichiers vers le VPS..."

    rsync -avz --delete \
        -e "ssh -i $SSH_KEY -p $VPS_PORT" \
        --exclude='.git' \
        --exclude='*.pyc' \
        --exclude='__pycache__' \
        --exclude='db.sqlite3' \
        --exclude='media' \
        --exclude='staticfiles' \
        --exclude='venv' \
        --exclude='.env' \
        --exclude='*.log' \
        --exclude='.github' \
        --exclude='.gitlab-ci.yml' \
        --exclude='deploy_*.sh' \
        --exclude='check_security.sh' \
        --exclude='*.md' \
        --progress \
        ./ "$VPS_USER@$VPS_HOST:$VPS_PATH/"

    print_success "Fichiers synchronisés"
}

# Installer les dépendances
install_dependencies() {
    print_header "Installation des dépendances"

    ssh -i "$SSH_KEY" -p "$VPS_PORT" "$VPS_USER@$VPS_HOST" bash << EOF
        cd $VPS_PATH
        source venv/bin/activate

        echo "Installation des packages Python..."
        pip install -r requirements.txt -q

        echo "✓ Dépendances installées"
EOF

    print_success "Dépendances installées"
}

# Exécuter les migrations
run_migrations() {
    print_header "Exécution des migrations"

    ssh -i "$SSH_KEY" -p "$VPS_PORT" "$VPS_USER@$VPS_HOST" bash << EOF
        cd $VPS_PATH
        source venv/bin/activate

        echo "Exécution des migrations..."
        python manage.py migrate --noinput

        echo "✓ Migrations exécutées"
EOF

    print_success "Migrations exécutées"
}

# Collecter les fichiers statiques
collect_static() {
    print_header "Collecte des fichiers statiques"

    ssh -i "$SSH_KEY" -p "$VPS_PORT" "$VPS_USER@$VPS_HOST" bash << EOF
        cd $VPS_PATH
        source venv/bin/activate

        echo "Collecte des fichiers statiques..."
        python manage.py collectstatic --noinput

        echo "✓ Fichiers statiques collectés"
EOF

    print_success "Fichiers statiques collectés"
}

# Redémarrer l'application
restart_app() {
    print_header "Redémarrage de l'application"

    ssh -i "$SSH_KEY" -p "$VPS_PORT" "$VPS_USER@$VPS_HOST" bash << 'EOF'
        echo "Redémarrage du service..."
        sudo systemctl restart gestionstock

        # Attendre un peu
        sleep 3

        # Vérifier le statut
        if sudo systemctl is-active --quiet gestionstock; then
            echo "✓ Application redémarrée avec succès"
        else
            echo "✗ Échec du redémarrage de l'application"
            sudo journalctl -u gestionstock -n 20 --no-pager
            exit 1
        fi
EOF

    print_success "Application redémarrée"
}

# Health check
health_check() {
    print_header "Vérification de santé"

    print_info "Attente du démarrage de l'application..."
    sleep 5

    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://$VPS_HOST" || echo "000")

    if [ "$HTTP_STATUS" == "200" ] || [ "$HTTP_STATUS" == "302" ] || [ "$HTTP_STATUS" == "301" ]; then
        print_success "Health check réussi (HTTP $HTTP_STATUS)"
    else
        print_error "Health check échoué (HTTP $HTTP_STATUS)"
        print_info "L'application peut mettre quelques secondes à démarrer"
    fi
}

# Afficher le résumé
show_summary() {
    print_header "Résumé du déploiement"

    echo -e "${GREEN}Application déployée avec succès!${NC}"
    echo ""
    echo "📍 URL: http://$VPS_HOST"
    echo "📅 Date: $(date)"
    echo "👤 Utilisateur: $VPS_USER"
    echo "🖥️  Serveur: $VPS_HOST"
    echo ""
    print_info "Pour voir les logs: ssh $VPS_USER@$VPS_HOST 'sudo journalctl -u gestionstock -f'"
}

# ========================================
# MENU INTERACTIF
# ========================================

show_menu() {
    clear
    print_header "Déploiement GestionStock - Menu"
    echo ""
    echo "1. Déploiement complet (recommandé)"
    echo "2. Synchroniser les fichiers uniquement"
    echo "3. Installer les dépendances uniquement"
    echo "4. Exécuter les migrations uniquement"
    echo "5. Redémarrer l'application uniquement"
    echo "6. Créer une sauvegarde uniquement"
    echo "7. Health check uniquement"
    echo "8. Tout faire avec tests de connexion"
    echo "0. Quitter"
    echo ""
    read -p "Choisissez une option: " choice

    case $choice in
        1)
            deploy_full
            ;;
        2)
            sync_files
            ;;
        3)
            install_dependencies
            ;;
        4)
            run_migrations
            ;;
        5)
            restart_app
            ;;
        6)
            create_backup
            ;;
        7)
            health_check
            ;;
        8)
            deploy_with_checks
            ;;
        0)
            exit 0
            ;;
        *)
            print_error "Option invalide"
            sleep 2
            show_menu
            ;;
    esac
}

# Déploiement complet
deploy_full() {
    create_backup
    sync_files
    install_dependencies
    run_migrations
    collect_static
    restart_app
    health_check
    show_summary
}

# Déploiement avec vérifications
deploy_with_checks() {
    check_config
    test_connection
    deploy_full
}

# ========================================
# POINT D'ENTRÉE
# ========================================

# Si des arguments sont passés
if [ $# -eq 0 ]; then
    # Mode interactif
    show_menu
else
    # Mode commande
    case "$1" in
        full)
            deploy_full
            ;;
        check)
            deploy_with_checks
            ;;
        sync)
            sync_files
            ;;
        backup)
            create_backup
            ;;
        restart)
            restart_app
            ;;
        health)
            health_check
            ;;
        *)
            echo "Usage: $0 {full|check|sync|backup|restart|health}"
            echo ""
            echo "Options:"
            echo "  full     - Déploiement complet"
            echo "  check    - Déploiement avec vérifications"
            echo "  sync     - Synchroniser les fichiers uniquement"
            echo "  backup   - Créer une sauvegarde"
            echo "  restart  - Redémarrer l'application"
            echo "  health   - Vérification de santé"
            echo ""
            echo "Ou lancez sans arguments pour le menu interactif"
            exit 1
            ;;
    esac
fi
