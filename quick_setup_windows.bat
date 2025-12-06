@echo off
echo 🚀 Configuration rapide pour Windows
echo =====================================

echo.
echo 🔍 Vérification de Python...
python --version
if %errorlevel% neq 0 (
    echo ❌ Python non trouvé. Installez Python depuis python.org
    pause
    exit /b 1
)

echo.
echo 🔍 Vérification de pip...
python -m pip --version
if %errorlevel% neq 0 (
    echo ❌ Pip non disponible
    pause
    exit /b 1
)

echo.
echo 📦 Installation des dépendances...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ❌ Erreur lors de l'installation des dépendances
    pause
    exit /b 1
)

echo.
echo ✅ Vérification de Django...
python manage.py check
if %errorlevel% neq 0 (
    echo ❌ Erreur de configuration Django
    pause
    exit /b 1
)

echo.
echo 📁 Collection des fichiers statiques...
python manage.py collectstatic --noinput
if %errorlevel% neq 0 (
    echo ⚠️ Attention: Erreur lors de la collecte des fichiers statiques
)

echo.
echo 🎉 Configuration terminée avec succès!
echo.
echo 📋 Étapes suivantes pour le déploiement:
echo 1. git init
echo 2. git add .
echo 3. git commit -m "Ready for deployment"
echo 4. git remote add origin https://github.com/username/repo.git
echo 5. git push -u origin main
echo 6. Déployer sur Railway/Render/Vercel
echo.
pause