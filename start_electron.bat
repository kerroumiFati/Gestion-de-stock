@echo off
echo ============================================
echo   Application Desktop Gestion de Stock
echo ============================================
echo.

REM Vérifier que Python est installé
python --version >nul 2>&1
if errorlevel 1 (
    echo ERREUR: Python n'est pas installé ou n'est pas dans le PATH
    echo Veuillez installer Python depuis https://www.python.org/
    pause
    exit /b 1
)

REM Vérifier que Node.js est installé
node --version >nul 2>&1
if errorlevel 1 (
    echo ERREUR: Node.js n'est pas installé ou n'est pas dans le PATH
    echo Veuillez installer Node.js depuis https://nodejs.org/
    pause
    exit /b 1
)

echo [OK] Python est installé
echo [OK] Node.js est installé
echo.

REM Vérifier si les dépendances Python sont installées
echo Verification des dependances Python...
python -c "import django" >nul 2>&1
if errorlevel 1 (
    echo Installation des dependances Python...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERREUR: Impossible d'installer les dependances Python
        pause
        exit /b 1
    )
)

REM Vérifier si les dépendances Node.js sont installées
if not exist "node_modules\" (
    echo Installation des dependances Node.js...
    call npm install
    if errorlevel 1 (
        echo ERREUR: Impossible d'installer les dependances Node.js
        pause
        exit /b 1
    )
)

REM Appliquer les migrations Django
echo Application des migrations de la base de donnees...
python manage.py migrate --noinput

REM Collecter les fichiers statiques
echo Collecte des fichiers statiques...
python manage.py collectstatic --noinput

echo.
echo ============================================
echo   Demarrage de l'application...
echo ============================================
echo.

REM Lancer l'application Electron
npm start
