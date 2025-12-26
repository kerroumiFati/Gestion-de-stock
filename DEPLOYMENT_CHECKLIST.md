# Checklist de Déploiement VPS Octenium

## Avant le déploiement

### Préparation locale

- [ ] Tester l'application en local avec `DEBUG=False`
- [ ] Vérifier que `requirements.txt` est à jour
- [ ] S'assurer que toutes les migrations sont créées et testées
- [ ] Tester la collecte des fichiers statiques : `python manage.py collectstatic`
- [ ] Sauvegarder votre base de données locale
- [ ] Créer une sauvegarde de votre code

### Configuration VPS

- [ ] Créer un compte VPS Octenium
- [ ] Choisir une distribution Linux (Ubuntu 20.04/22.04 recommandé)
- [ ] Noter l'adresse IP du VPS
- [ ] Configurer l'accès SSH
- [ ] (Optionnel) Configurer un nom de domaine pointant vers l'IP du VPS

### Sécurité

- [ ] Préparer un mot de passe fort pour PostgreSQL
- [ ] Générer une nouvelle SECRET_KEY pour Django
- [ ] Désactiver l'authentification root par mot de passe (utiliser des clés SSH)
- [ ] Configurer un pare-feu

## Pendant le déploiement

### Installation système

- [ ] Mettre à jour le système : `apt update && apt upgrade`
- [ ] Installer Python 3
- [ ] Installer PostgreSQL
- [ ] Installer Nginx
- [ ] Installer Git

### Configuration de la base de données

- [ ] Créer la base de données PostgreSQL
- [ ] Créer l'utilisateur PostgreSQL
- [ ] Configurer les permissions
- [ ] Tester la connexion à la base de données

### Configuration de l'application

- [ ] Créer l'utilisateur système `gestionstock`
- [ ] Copier les fichiers du projet
- [ ] Créer et activer l'environnement virtuel Python
- [ ] Installer les dépendances Python
- [ ] Créer et configurer le fichier `.env`
- [ ] Exécuter `collectstatic`
- [ ] Exécuter les migrations : `python manage.py migrate`
- [ ] Créer un superutilisateur Django

### Configuration des services

- [ ] Configurer Gunicorn
- [ ] Créer le service Systemd pour Gunicorn
- [ ] Démarrer et activer le service Gunicorn
- [ ] Vérifier que Gunicorn fonctionne
- [ ] Configurer Nginx
- [ ] Tester la configuration Nginx
- [ ] Redémarrer Nginx

### Sécurité

- [ ] Configurer le pare-feu UFW
- [ ] Autoriser les ports nécessaires (80, 443, SSH)
- [ ] (Recommandé) Installer et configurer SSL/HTTPS avec Certbot
- [ ] Vérifier les permissions des fichiers

## Après le déploiement

### Tests fonctionnels

- [ ] Vérifier que le site est accessible via HTTP
- [ ] Tester la page d'accueil
- [ ] Tester la page d'administration (/admin)
- [ ] Se connecter avec le superutilisateur
- [ ] Vérifier que les fichiers statiques se chargent correctement
- [ ] Tester les fonctionnalités principales de l'application
- [ ] Vérifier que les formulaires fonctionnent
- [ ] Tester la création, modification et suppression de données
- [ ] Vérifier les rapports et exports si applicable

### Vérification des services

- [ ] Vérifier le statut de Gunicorn : `systemctl status gestionstock`
- [ ] Vérifier le statut de Nginx : `systemctl status nginx`
- [ ] Vérifier le statut de PostgreSQL : `systemctl status postgresql`
- [ ] Consulter les logs pour détecter des erreurs

### Monitoring

- [ ] Configurer les logs de rotation (logrotate)
- [ ] Vérifier que les logs Gunicorn sont écrits
- [ ] Vérifier que les logs Nginx sont écrits
- [ ] (Optionnel) Configurer un outil de monitoring (Sentry, Datadog, etc.)
- [ ] (Optionnel) Configurer des alertes par email en cas d'erreur

### Sauvegardes

- [ ] Configurer les sauvegardes automatiques de la base de données
- [ ] Configurer les sauvegardes des fichiers uploadés (media)
- [ ] Tester la restauration d'une sauvegarde
- [ ] Documenter la procédure de sauvegarde/restauration

### Performance

- [ ] Activer la compression gzip dans Nginx
- [ ] Configurer le cache des fichiers statiques
- [ ] Optimiser la configuration de Gunicorn (nombre de workers)
- [ ] (Optionnel) Configurer un CDN pour les fichiers statiques
- [ ] (Optionnel) Configurer Redis pour le cache Django

### Sécurité supplémentaire

- [ ] Vérifier que DEBUG=False en production
- [ ] Vérifier que ALLOWED_HOSTS est correctement configuré
- [ ] Vérifier que les fichiers sensibles (.env) ne sont pas publics
- [ ] Configurer CSRF_TRUSTED_ORIGINS
- [ ] Limiter les tentatives de connexion (fail2ban)
- [ ] Configurer les en-têtes de sécurité HTTP
- [ ] Mettre en place un système de détection d'intrusion (optionnel)

### Documentation

- [ ] Documenter les credentials (dans un gestionnaire de mots de passe sécurisé)
- [ ] Documenter l'architecture du déploiement
- [ ] Créer un runbook pour les tâches courantes
- [ ] Documenter la procédure de mise à jour
- [ ] Documenter la procédure de rollback

## Maintenance régulière

### Hebdomadaire

- [ ] Consulter les logs pour détecter des anomalies
- [ ] Vérifier l'espace disque disponible
- [ ] Vérifier les performances de l'application

### Mensuel

- [ ] Mettre à jour les paquets système : `apt update && apt upgrade`
- [ ] Vérifier et nettoyer les logs anciens
- [ ] Tester les sauvegardes
- [ ] Vérifier les certificats SSL (expiration)
- [ ] Analyser les statistiques d'utilisation

### Trimestriel

- [ ] Mettre à jour Django et les dépendances Python
- [ ] Effectuer un audit de sécurité
- [ ] Réviser et optimiser la base de données
- [ ] Vérifier les performances et optimiser si nécessaire

## Contacts d'urgence

- **Hébergeur VPS** : Support Octenium
- **Base de données** : Administrateur système
- **Développeur** : [Votre nom/contact]
- **Support Django** : https://docs.djangoproject.com/

## Commandes utiles pour le diagnostic

```bash
# Vérifier les services
systemctl status gestionstock nginx postgresql

# Voir les logs en temps réel
journalctl -u gestionstock -f
tail -f /home/gestionstock/logs/gunicorn-error.log
tail -f /var/log/nginx/error.log

# Vérifier l'espace disque
df -h

# Vérifier la mémoire
free -m

# Vérifier les processus
ps aux | grep gunicorn

# Vérifier les ports ouverts
netstat -tlnp

# Tester la connexion à PostgreSQL
sudo -u postgres psql -c "\l"
```

---

**Date de déploiement** : _______________

**Déployé par** : _______________

**Version de l'application** : _______________

**Notes supplémentaires** :

```
_______________________________________________
_______________________________________________
_______________________________________________
```
