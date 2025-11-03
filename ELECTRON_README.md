# Application Desktop Gestion de Stock

Cette application Django a été convertie en application desktop avec Electron.

## Prérequis

1. **Python** (3.8 ou supérieur)
2. **Node.js** (v18 ou supérieur)
3. **npm** (inclus avec Node.js)

## Installation

### 1. Installer les dépendances Python

```bash
pip install -r requirements.txt
```

### 2. Installer les dépendances Node.js

```bash
npm install
```

### 3. Préparer la base de données Django

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

### 4. (Optionnel) Créer un superutilisateur

```bash
python manage.py createsuperuser
```

## Utilisation

### Mode développement

Pour lancer l'application en mode développement :

```bash
npm start
```

Cela va :
1. Démarrer le serveur Django en arrière-plan
2. Ouvrir une fenêtre Electron qui affiche l'interface Django

### Créer un exécutable

#### Pour Windows

```bash
npm run build:win
```

L'installateur sera créé dans le dossier `dist/`.

#### Pour macOS

```bash
npm run build:mac
```

#### Pour Linux

```bash
npm run build:linux
```

## Structure du projet

- `main.js` - Point d'entrée Electron, gère le serveur Django et la fenêtre
- `preload.js` - Script de préchargement pour la sécurité
- `package.json` - Configuration Node.js et Electron Builder
- `manage.py` - Point d'entrée Django
- `Gestion_stock/` - Configuration Django
- `Stock/` - Application Django principale

## Configuration

### Changer le port

Par défaut, Django tourne sur le port 8000. Pour changer cela, modifiez la constante `DJANGO_PORT` dans `main.js`.

### Icônes

Pour personnaliser l'icône de l'application :

1. **Windows** : Placez votre icône dans `icon.ico`
2. **macOS** : Placez votre icône dans `icon.icns`
3. **Linux** : Placez votre icône dans `icon.png`

## Dépannage

### L'application ne démarre pas

1. Vérifiez que Python est installé : `python --version`
2. Vérifiez que Django est installé : `pip list | grep Django`
3. Vérifiez que le port 8000 n'est pas déjà utilisé

### Erreur "Port already in use"

Un autre processus utilise le port 8000. Fermez-le ou changez le port dans `main.js`.

### L'application se ferme immédiatement

Consultez les logs dans la console pour identifier l'erreur. Lancez avec la console ouverte en décommentant cette ligne dans `main.js` :

```javascript
mainWindow.webContents.openDevTools();
```

## Distribution

### Avant de distribuer

1. Assurez-vous que toutes les dépendances Python sont dans `requirements.txt`
2. Testez l'application en mode développement
3. Créez les icônes pour chaque plateforme
4. Configurez les paramètres de build dans `package.json`

### Inclure Python dans l'exécutable

Pour une distribution autonome (sans que l'utilisateur ait besoin d'installer Python), vous devrez :

1. Utiliser PyInstaller pour créer un exécutable Python autonome
2. Modifier `main.js` pour utiliser cet exécutable au lieu de `python`

## Support

Pour toute question ou problème, consultez la documentation de :
- [Electron](https://www.electronjs.org/docs)
- [Django](https://docs.djangoproject.com/)
- [Electron Builder](https://www.electron.build/)
