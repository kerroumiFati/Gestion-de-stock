# Guide de démarrage rapide - Application Desktop

## Démarrage rapide (Windows)

### Méthode 1 : Script automatique

Double-cliquez sur `start_electron.bat` - Le script va :
1. Vérifier les prérequis (Python, Node.js)
2. Installer les dépendances si nécessaire
3. Appliquer les migrations de base de données
4. Lancer l'application

### Méthode 2 : Ligne de commande

```bash
# 1. Installer les dépendances Python
pip install -r requirements.txt

# 2. Installer les dépendances Node.js
npm install

# 3. Préparer la base de données
python manage.py migrate

# 4. Lancer l'application
npm start
```

## Créer un exécutable Windows

### Méthode 1 : Script automatique

Double-cliquez sur `build_electron.bat`

### Méthode 2 : Ligne de commande

```bash
npm run build:win
```

L'installateur sera créé dans le dossier `dist/`

## Première utilisation

1. **Lancer l'application** avec l'une des méthodes ci-dessus
2. **Créer un compte administrateur** :
   - Arrêtez l'application (si elle tourne)
   - Ouvrez un terminal et exécutez :
   ```bash
   python manage.py createsuperuser
   ```
   - Suivez les instructions
   - Relancez l'application
3. **Se connecter** avec le compte créé

## Résolution des problèmes

### L'application ne démarre pas

**Vérifiez Python** :
```bash
python --version
```
Si erreur : Installez Python depuis https://www.python.org/

**Vérifiez Node.js** :
```bash
node --version
```
Si erreur : Installez Node.js depuis https://nodejs.org/

### Erreur "Port 8000 already in use"

Une autre instance de l'application ou un autre serveur utilise le port 8000.

**Solution** :
1. Fermez toute instance de l'application
2. Ouvrez le Gestionnaire des tâches (Ctrl+Shift+Esc)
3. Recherchez et arrêtez tout processus Python en cours
4. Relancez l'application

### Erreur lors de l'installation des dépendances

**Solution** :
```bash
# Mettre à jour pip
python -m pip install --upgrade pip

# Réinstaller les dépendances
pip install -r requirements.txt --force-reinstall
```

### L'application s'ouvre mais affiche une page blanche

Django n'a probablement pas démarré correctement.

**Solution** :
1. Ouvrez un terminal
2. Lancez Django manuellement pour voir les erreurs :
```bash
python manage.py runserver
```
3. Corrigez les erreurs affichées
4. Relancez l'application Electron

### Erreur de base de données

**Solution** :
```bash
# Supprimer la base de données (ATTENTION : perte de données)
del db.sqlite3

# Recréer la base de données
python manage.py migrate

# Recréer un superutilisateur
python manage.py createsuperuser
```

## Structure des fichiers

```
GestionStock-django-master/
├── main.js                 # Point d'entrée Electron
├── preload.js              # Script de sécurité Electron
├── package.json            # Configuration Node.js
├── manage.py               # Point d'entrée Django
├── db.sqlite3              # Base de données
├── start_electron.bat      # Script de démarrage Windows
├── build_electron.bat      # Script de build Windows
├── Gestion_stock/          # Configuration Django
├── Stock/                  # Application principale
├── static/                 # Fichiers statiques
├── media/                  # Fichiers uploadés
└── templates/              # Templates HTML
```

## Commandes utiles

### Django

```bash
# Créer un superutilisateur
python manage.py createsuperuser

# Appliquer les migrations
python manage.py migrate

# Collecter les fichiers statiques
python manage.py collectstatic

# Lancer le serveur (mode dev)
python manage.py runserver
```

### Electron

```bash
# Lancer en mode développement
npm start

# Builder pour Windows
npm run build:win

# Builder pour macOS
npm run build:mac

# Builder pour Linux
npm run build:linux
```

## Configuration

### Changer le port

Éditez `main.js` et changez la ligne :
```javascript
const DJANGO_PORT = 8000;  // Changez 8000 par le port désiré
```

### Mode développement

Pour activer les outils de développement, décommentez cette ligne dans `main.js` :
```javascript
mainWindow.webContents.openDevTools();
```

## Sauvegarde des données

Votre base de données est dans le fichier `db.sqlite3`.

**Pour sauvegarder vos données** :
1. Fermez l'application
2. Copiez le fichier `db.sqlite3` dans un lieu sûr
3. Copiez aussi le dossier `media/` si vous avez des fichiers uploadés

**Pour restaurer** :
1. Fermez l'application
2. Remplacez `db.sqlite3` par votre sauvegarde
3. Remplacez le dossier `media/` si nécessaire
4. Relancez l'application

## Mise à jour de l'application

Pour mettre à jour vers une nouvelle version :

1. **Sauvegardez vos données** (voir ci-dessus)
2. Téléchargez la nouvelle version
3. Copiez `db.sqlite3` et `media/` de l'ancienne version vers la nouvelle
4. Appliquez les migrations :
```bash
python manage.py migrate
```
5. Relancez l'application

## Support et documentation

- **Documentation Electron** : [ELECTRON_README.md](ELECTRON_README.md)
- **Prochaines étapes** : [NEXT_STEPS_ELECTRON.md](NEXT_STEPS_ELECTRON.md)
- **Documentation Django** : https://docs.djangoproject.com/

## Notes importantes

- **Python requis** : L'application nécessite Python installé sur le système
- **Connexion Internet** : Requise uniquement pour l'installation des dépendances
- **Système mono-utilisateur** : L'application utilise SQLite (base de données locale)
- **Sécurité** : Changez les clés secrètes Django avant la mise en production

## Licence et crédits

Cette application combine :
- **Django** : Framework web Python
- **Electron** : Framework pour applications desktop
- Consultez les fichiers LICENSE respectifs pour plus d'informations
