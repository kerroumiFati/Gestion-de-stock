#!/usr/bin/env python
"""
Script de déploiement pour l'application Django
"""
import os
import subprocess
import sys

def run_command(command, description):
    """Exécute une commande et affiche le résultat"""
    print(f"🔄 {description}...")
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

def prepare_for_deployment():
    """Prépare l'application pour le déploiement"""
    commands = [
        ("pip install -r requirements.txt", "Installation des dépendances"),
        ("python manage.py check", "Vérification de la configuration Django"),
        ("python manage.py collectstatic --noinput", "Collecte des fichiers statiques"),
    ]
    
    for command, description in commands:
        if not run_command(command, description):
            return False
    
    return True

def main():
    print("🚀 Préparation du déploiement Django pour Vercel")
    print("=" * 50)
    
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