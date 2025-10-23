#!/usr/bin/env python
"""
Script de déploiement pour Windows - Version corrigée
"""
import os
import subprocess
import sys

def run_command(command, description, use_python_m=False):
    """Exécute une commande et affiche le résultat"""
    print(f"🔄 {description}...")
    
    # Pour Windows, utiliser python -m pip au lieu de pip directement
    if use_python_m and command.startswith('pip'):
        command = command.replace('pip', 'python -m pip')
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} - Succès")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - Erreur: {e.stderr}")
        return False

def check_requirements():
    """Vérifie que tous les fichiers nécessaires sont présents"""
    required_files = [
        'requirements.txt',
        'vercel.json',
        'build_files.sh',
        'manage.py',
        'Gestion_stock/settings.py',
        'Gestion_stock/wsgi.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Fichiers manquants: {', '.join(missing_files)}")
        return False
    
    print("✅ Tous les fichiers requis sont présents")
    return True

def check_python_setup():
    """Vérifie la configuration Python"""
    print("🔍 Vérification de la configuration Python...")
    
    # Vérifier Python
    try:
        result = subprocess.run([sys.executable, '--version'], capture_output=True, text=True)
        print(f"✅ Python: {result.stdout.strip()}")
    except:
        print("❌ Python non trouvé")
        return False
    
    # Vérifier pip
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', '--version'], capture_output=True, text=True)
        print(f"✅ Pip: {result.stdout.strip()}")
        return True
    except:
        print("❌ Pip non disponible")
        return False

def prepare_for_deployment():
    """Prépare l'application pour le déploiement"""
    commands = [
        ("python -m pip install -r requirements.txt", "Installation des dépendances", True),
        ("python manage.py check", "Vérification de la configuration Django", False),
        ("python manage.py collectstatic --noinput", "Collecte des fichiers statiques", False),
    ]
    
    for command, description, use_python_m in commands:
        if not run_command(command, description, use_python_m):
            return False
    
    return True

def main():
    print("🚀 Préparation du déploiement Django pour Vercel (Windows)")
    print("=" * 60)
    
    # Vérification de Python et pip
    if not check_python_setup():
        print("\n🔧 Solutions possibles:")
        print("1. Réinstaller Python depuis python.org avec 'Add to PATH' coché")
        print("2. Ou utiliser: python -m pip install -r requirements.txt")
        print("3. Ou utiliser un environnement virtuel:")
        print("   python -m venv venv")
        print("   venv\\Scripts\\activate")
        print("   python -m pip install -r requirements.txt")
        sys.exit(1)
    
    # Vérification des prérequis
    if not check_requirements():
        sys.exit(1)
    
    # Préparation du déploiement
    if not prepare_for_deployment():
        print("❌ Erreur lors de la préparation du déploiement")
        sys.exit(1)
    
    print("\n🎉 Application prête pour le déploiement!")
    print("\n📋 Étapes suivantes:")
    print("1. Commitez vos changements: git add . && git commit -m 'Ready for deployment'")
    print("2. Poussez vers GitHub: git push origin main")
    print("3. Connectez votre repo sur vercel.com")
    print("4. Configurez les variables d'environnement (voir .env.example)")
    print("5. Déployez!")
    
    print("\n⚠️  RAPPEL: Vercel a des limitations avec Django.")
    print("   Pour la production, considérez Railway, Render ou Heroku.")

if __name__ == "__main__":
    main()