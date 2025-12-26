#!/bin/bash

# Script de vérification de sécurité pour le déploiement

echo "=== Vérification de la sécurité du déploiement ==="
echo ""

# Vérifier les permissions du fichier .env
echo "1. Vérification des permissions du fichier .env :"
if [ -f "/home/gestionstock/app/.env" ]; then
    ls -l /home/gestionstock/app/.env
    PERMS=$(stat -c %a /home/gestionstock/app/.env)
    if [ "$PERMS" = "600" ]; then
        echo "✓ Permissions correctes (600)"
    else
        echo "✗ ATTENTION: Permissions incorrectes ($PERMS). Devrait être 600"
        echo "  Exécutez: chmod 600 /home/gestionstock/app/.env"
    fi
else
    echo "✗ Fichier .env introuvable"
fi
echo ""

# Vérifier que .env n'est pas dans Git
echo "2. Vérification que .env n'est pas versionné dans Git :"
if [ -d "/home/gestionstock/app/.git" ]; then
    cd /home/gestionstock/app
    if git ls-files --error-unmatch .env 2>/dev/null; then
        echo "✗ DANGER: .env est versionné dans Git !"
        echo "  Exécutez: git rm --cached .env && git commit -m 'Remove .env from git'"
    else
        echo "✓ .env n'est pas dans Git"
    fi
else
    echo "  Pas de repository Git trouvé"
fi
echo ""

# Vérifier .gitignore
echo "3. Vérification du .gitignore :"
if [ -f "/home/gestionstock/app/.gitignore" ]; then
    if grep -q "^\.env$" /home/gestionstock/app/.gitignore; then
        echo "✓ .env est dans .gitignore"
    else
        echo "✗ ATTENTION: .env n'est pas dans .gitignore"
        echo "  Ajoutez .env dans votre .gitignore"
    fi
else
    echo "✗ Aucun .gitignore trouvé"
fi
echo ""

# Vérifier DEBUG=False
echo "4. Vérification de DEBUG dans .env :"
if [ -f "/home/gestionstock/app/.env" ]; then
    if grep -q "^DEBUG=False" /home/gestionstock/app/.env; then
        echo "✓ DEBUG=False (production)"
    else
        echo "✗ ATTENTION: DEBUG n'est pas à False"
    fi
else
    echo "✗ Fichier .env introuvable"
fi
echo ""

# Vérifier la présence de SECRET_KEY
echo "5. Vérification de SECRET_KEY :"
if [ -f "/home/gestionstock/app/.env" ]; then
    if grep -q "^SECRET_KEY=" /home/gestionstock/app/.env; then
        KEY_LENGTH=$(grep "^SECRET_KEY=" /home/gestionstock/app/.env | cut -d'=' -f2 | wc -c)
        if [ $KEY_LENGTH -gt 50 ]; then
            echo "✓ SECRET_KEY présente et suffisamment longue"
        else
            echo "✗ ATTENTION: SECRET_KEY trop courte"
        fi
    else
        echo "✗ SECRET_KEY non trouvée"
    fi
fi
echo ""

# Vérifier les permissions du répertoire app
echo "6. Vérification des permissions du répertoire :"
ls -ld /home/gestionstock/app/
OWNER=$(stat -c %U /home/gestionstock/app/)
if [ "$OWNER" = "gestionstock" ]; then
    echo "✓ Propriétaire correct (gestionstock)"
else
    echo "✗ ATTENTION: Propriétaire incorrect ($OWNER)"
    echo "  Exécutez: chown -R gestionstock:gestionstock /home/gestionstock/app"
fi
echo ""

# Vérifier la configuration SSH
echo "7. Vérification de la configuration SSH :"
if grep -q "^PermitRootLogin prohibit-password" /etc/ssh/sshd_config; then
    echo "✓ Connexion root par mot de passe désactivée"
else
    echo "⚠ Considérez désactiver la connexion root par mot de passe"
fi
echo ""

# Vérifier le pare-feu
echo "8. Vérification du pare-feu UFW :"
if command -v ufw &> /dev/null; then
    UFW_STATUS=$(ufw status | grep "Status:" | awk '{print $2}')
    if [ "$UFW_STATUS" = "active" ]; then
        echo "✓ UFW est actif"
    else
        echo "⚠ UFW n'est pas actif"
        echo "  Exécutez: ufw enable"
    fi
else
    echo "⚠ UFW n'est pas installé"
fi
echo ""

# Vérifier fail2ban (optionnel)
echo "9. Vérification de fail2ban :"
if systemctl is-active --quiet fail2ban; then
    echo "✓ fail2ban est actif"
else
    echo "⚠ fail2ban n'est pas installé/actif (recommandé)"
    echo "  Installation: apt install -y fail2ban"
fi
echo ""

# Vérifier les fichiers sensibles dans le répertoire
echo "10. Recherche de fichiers potentiellement sensibles :"
SENSITIVE_FILES=("*.key" "*.pem" "credentials.json" "db.sqlite3")
FOUND=0
for pattern in "${SENSITIVE_FILES[@]}"; do
    FILES=$(find /home/gestionstock/app -name "$pattern" -type f 2>/dev/null)
    if [ -n "$FILES" ]; then
        echo "⚠ Trouvé: $FILES"
        FOUND=1
    fi
done
if [ $FOUND -eq 0 ]; then
    echo "✓ Aucun fichier sensible évident trouvé"
fi
echo ""

echo "=== Fin de la vérification ==="
echo ""
echo "Recommandations de sécurité supplémentaires :"
echo "1. Utilisez des clés SSH au lieu de mots de passe"
echo "2. Changez régulièrement les mots de passe"
echo "3. Maintenez le système à jour: apt update && apt upgrade"
echo "4. Configurez des sauvegardes régulières"
echo "5. Surveillez les logs régulièrement"
echo "6. Utilisez un repository Git privé"
echo "7. Ne partagez jamais le fichier .env"
