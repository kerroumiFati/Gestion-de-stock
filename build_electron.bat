@echo off
echo ============================================
echo   Build Application Desktop - Windows
echo ============================================
echo.

REM Vérifier que Node.js est installé
node --version >nul 2>&1
if errorlevel 1 (
    echo ERREUR: Node.js n'est pas installé ou n'est pas dans le PATH
    echo Veuillez installer Node.js depuis https://nodejs.org/
    pause
    exit /b 1
)

echo [OK] Node.js est installé
echo.

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

echo.
echo ============================================
echo   Build en cours...
echo   Cela peut prendre plusieurs minutes
echo ============================================
echo.

REM Builder l'application pour Windows
call npm run build:win

if errorlevel 1 (
    echo.
    echo ERREUR: Le build a échoué
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Build terminé avec succès!
echo ============================================
echo.
echo L'installateur se trouve dans le dossier 'dist\'
echo.
pause
