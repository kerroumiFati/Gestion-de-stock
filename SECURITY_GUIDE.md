# Guide de Sécurité - Déploiement VPS

## 🔐 Comprendre les risques

### Qui peut accéder au code sur le VPS ?

| Type d'accès | Peut voir le code ? | Niveau de risque |
|--------------|-------------------|------------------|
| Utilisateurs avec accès SSH root | ✓ OUI | 🔴 CRITIQUE |
| Utilisateurs SSH non-root | ✓ OUI (si permissions mal configurées) | 🟡 MOYEN |
| Utilisateurs système (gestionstock) | ✓ OUI (leur propre dossier) | 🟢 NORMAL |
| Accès web (visiteurs du site) | ✗ NON (si bien configuré) | 🟢 FAIBLE |
| Hébergeur (Octenium) | ✓ OUI (accès physique au serveur) | 🟡 MOYEN |

### Ce qu'il faut protéger en priorité

1. **Fichier `.env`** - Contient tous vos secrets
2. **Base de données** - Données sensibles des utilisateurs
3. **Clés d'API** - Accès à des services tiers
4. **SECRET_KEY Django** - Sécurité des sessions
5. **Credentials PostgreSQL** - Accès à la base de données

---

## 🛡️ Stratégies de Protection

### 1. Repository Git Privé vs Public

#### ✓ Avec un Repository PRIVÉ (Recommandé)

```bash
# Sur le VPS
cd /home/gestionstock/app
git clone https://github.com/votre-username/votre-repo-PRIVE.git .

# Configurez l'authentification
git config credential.helper store
# Ou utilisez une clé SSH
```

**Avantages** :
- Code source protégé
- Facilite les mises à jour
- Historique des versions

**Inconvénients** :
- Le code reste accessible sur le VPS pour ceux ayant accès SSH

#### ✗ Avec un Repository PUBLIC (À éviter)

⚠️ **DANGER** : Tout le monde peut voir votre code source !

**À ne faire que si** :
- Le projet est open-source
- Aucune donnée sensible dans le code
- Le `.env` n'est JAMAIS commité

### 2. Protection du fichier .env

Le `.env` ne doit **JAMAIS** être dans Git :

```bash
# Vérifiez que .env est ignoré
cat .gitignore | grep .env

# Si absent, ajoutez-le
echo ".env" >> .gitignore

# Si déjà commité par erreur, supprimez-le
git rm --cached .env
git commit -m "Remove .env from version control"
git push

# Puis créez-le manuellement sur le VPS
```

#### Créer .env sur le VPS de manière sécurisée

```bash
# Connectez-vous au VPS
ssh gestionstock@VOTRE_IP_VPS

# Créez le fichier
nano /home/gestionstock/app/.env

# Collez la configuration
# Sauvegardez (Ctrl+X, Y, Enter)

# Sécurisez les permissions
chmod 600 /home/gestionstock/app/.env
chown gestionstock:gestionstock /home/gestionstock/app/.env

# Vérifiez
ls -l /home/gestionstock/app/.env
# Devrait afficher : -rw------- 1 gestionstock gestionstock
```

### 3. Sécurisation de l'accès SSH

#### A. Utiliser des clés SSH (OBLIGATOIRE)

```bash
# Sur votre machine locale
ssh-keygen -t ed25519 -C "votre-email@example.com"

# Copiez la clé sur le VPS
ssh-copy-id -i ~/.ssh/id_ed25519.pub votre-utilisateur@VOTRE_IP_VPS

# Testez la connexion
ssh -i ~/.ssh/id_ed25519 votre-utilisateur@VOTRE_IP_VPS
```

#### B. Désactiver l'authentification par mot de passe

```bash
# Sur le VPS
sudo nano /etc/ssh/sshd_config

# Modifiez ces lignes :
PermitRootLogin prohibit-password
PasswordAuthentication no
ChallengeResponseAuthentication no
PubkeyAuthentication yes

# Redémarrez SSH
sudo systemctl restart sshd
```

#### C. Changer le port SSH par défaut

```bash
sudo nano /etc/ssh/sshd_config

# Changez le port (choisissez entre 1024 et 65535)
Port 2222

# Redémarrez
sudo systemctl restart sshd

# Autorisez le nouveau port dans le pare-feu
sudo ufw allow 2222/tcp

# Nouvelle connexion
ssh -p 2222 utilisateur@VOTRE_IP_VPS
```

#### D. Limiter l'accès SSH par IP

```bash
sudo nano /etc/ssh/sshd_config

# Ajoutez (remplacez par votre IP)
AllowUsers votre-utilisateur@VOTRE_IP_FIXE

# Ou utilisez le pare-feu
sudo ufw allow from VOTRE_IP_FIXE to any port 22
sudo ufw deny 22
```

### 4. Configuration du pare-feu UFW

```bash
# Réinitialiser UFW
sudo ufw --force reset

# Politique par défaut : bloquer tout
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Autoriser SSH (IMPORTANT : avant d'activer UFW !)
sudo ufw allow 22/tcp
# Ou si vous avez changé le port :
# sudo ufw allow 2222/tcp

# Autoriser HTTP et HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Activer UFW
sudo ufw enable

# Vérifier le statut
sudo ufw status verbose
```

### 5. Installation de Fail2Ban

Fail2Ban bloque les tentatives de connexion répétées :

```bash
# Installer
sudo apt install -y fail2ban

# Créer la configuration locale
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local

# Éditer
sudo nano /etc/fail2ban/jail.local

# Configurez :
[DEFAULT]
bantime = 3600        # 1 heure
findtime = 600        # 10 minutes
maxretry = 5          # 5 tentatives

[sshd]
enabled = true
port = 22             # Ou votre port personnalisé

# Démarrer
sudo systemctl start fail2ban
sudo systemctl enable fail2ban

# Vérifier
sudo fail2ban-client status sshd
```

### 6. Permissions des fichiers

```bash
# Permissions recommandées

# Répertoire principal
chmod 750 /home/gestionstock/app
chown -R gestionstock:gestionstock /home/gestionstock/app

# Fichier .env (TRÈS IMPORTANT)
chmod 600 /home/gestionstock/app/.env

# Fichiers Python
find /home/gestionstock/app -type f -name "*.py" -exec chmod 644 {} \;

# Scripts exécutables
chmod 755 /home/gestionstock/app/manage.py

# Fichiers de configuration
chmod 640 /home/gestionstock/app/Gestion_stock/settings.py

# Logs
chmod 640 /home/gestionstock/logs/*.log
chown gestionstock:gestionstock /home/gestionstock/logs/*.log

# Base de données SQLite (si utilisée)
chmod 640 /home/gestionstock/app/db.sqlite3 2>/dev/null || true
```

### 7. Sécurité Django

#### settings.py

```python
# JAMAIS en production
DEBUG = False

# Limitez les hôtes autorisés
ALLOWED_HOSTS = ['votre-domaine.com', 'www.votre-domaine.com']

# Secret key forte
SECRET_KEY = 'une-très-longue-clé-aléatoire-de-50-caractères-minimum'

# Sécurité des cookies
SESSION_COOKIE_SECURE = True  # Nécessite HTTPS
CSRF_COOKIE_SECURE = True     # Nécessite HTTPS
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# Sécurité HTTPS
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Headers de sécurité
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
```

### 8. Gestion des secrets

#### Ne JAMAIS commiter dans Git :

```gitignore
# .gitignore
.env
.env.*
!.env.example
*.pyc
__pycache__/
db.sqlite3
*.log
*.pot
*.pyc
local_settings.py
media/
staticfiles/
*.key
*.pem
credentials.json
secrets.json
```

#### Générer une SECRET_KEY sécurisée

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

#### Stocker les secrets de manière sécurisée

**Option 1 : Gestionnaire de mots de passe**
- 1Password
- LastPass
- Bitwarden
- KeePass

**Option 2 : Services de gestion de secrets**
- AWS Secrets Manager
- HashiCorp Vault
- Google Secret Manager

### 9. Sauvegardes sécurisées

```bash
# Script de sauvegarde
cat > /home/gestionstock/backup.sh <<'EOF'
#!/bin/bash
BACKUP_DIR="/home/gestionstock/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Créer le répertoire
mkdir -p $BACKUP_DIR

# Sauvegarder la base de données
sudo -u postgres pg_dump gestion_stock_db | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Sauvegarder les fichiers uploadés
tar -czf $BACKUP_DIR/media_$DATE.tar.gz -C /home/gestionstock/app media/

# Garder seulement les 7 derniers jours
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete

# Permissions
chmod 600 $BACKUP_DIR/*
EOF

chmod +x /home/gestionstock/backup.sh

# Automatiser avec cron
crontab -e
# Ajoutez :
0 2 * * * /home/gestionstock/backup.sh
```

### 10. Monitoring et alertes

#### A. Surveiller les logs

```bash
# Créer un script de surveillance
cat > /usr/local/bin/check-errors.sh <<'EOF'
#!/bin/bash
ERRORS=$(grep -i error /home/gestionstock/logs/gunicorn-error.log | tail -10)
if [ -n "$ERRORS" ]; then
    echo "Erreurs détectées dans l'application :"
    echo "$ERRORS"
    # Envoyez un email ou une notification
fi
EOF

chmod +x /usr/local/bin/check-errors.sh

# Exécuter quotidiennement
crontab -e
# Ajoutez :
0 8 * * * /usr/local/bin/check-errors.sh
```

#### B. Installer un système de monitoring (optionnel)

- **Sentry** : Monitoring des erreurs Django
- **Datadog** : Monitoring complet
- **New Relic** : Performance monitoring
- **Prometheus + Grafana** : Open source

---

## 🔍 Script de vérification de sécurité

Utilisez le script `check_security.sh` créé précédemment :

```bash
# Sur le VPS
chmod +x check_security.sh
sudo ./check_security.sh
```

---

## ⚠️ Que faire en cas de compromission ?

### Si vous pensez que le VPS a été compromis :

1. **Isolez immédiatement le serveur**
   ```bash
   sudo ufw enable
   sudo ufw default deny incoming
   ```

2. **Changez tous les mots de passe**
   - PostgreSQL
   - Utilisateurs système
   - Django admin

3. **Régénérez la SECRET_KEY**
   - ⚠️ Cela déconnectera tous les utilisateurs

4. **Examinez les logs**
   ```bash
   sudo last          # Connexions récentes
   sudo journalctl -xe
   tail -100 /var/log/auth.log
   ```

5. **Restaurez depuis une sauvegarde saine**

6. **Renforcez la sécurité**

---

## 📋 Checklist de sécurité

- [ ] Repository Git privé
- [ ] `.env` non versionné dans Git
- [ ] Permissions `.env` à 600
- [ ] `DEBUG=False` en production
- [ ] SECRET_KEY forte et unique
- [ ] Authentification SSH par clé uniquement
- [ ] Port SSH changé (optionnel)
- [ ] Pare-feu UFW activé
- [ ] Fail2Ban installé et configuré
- [ ] SSL/HTTPS activé avec Certbot
- [ ] Sauvegardes automatiques configurées
- [ ] Monitoring des erreurs actif
- [ ] Mise à jour système régulière
- [ ] Logs vérifiés régulièrement

---

## 📞 En cas de problème

- **Support Octenium** : https://octenium.com/support
- **Documentation Django Security** : https://docs.djangoproject.com/en/stable/topics/security/
- **OWASP Top 10** : https://owasp.org/www-project-top-ten/

---

**Rappelez-vous** : La sécurité est un processus continu, pas une configuration unique !
