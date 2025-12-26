# Démarrage Rapide - Déploiement VPS Octenium

## Option 1 : Déploiement Automatique (Recommandé)

### Étape 1 : Copier le script sur votre VPS

Depuis votre machine locale :

```bash
scp deploy_vps.sh root@VOTRE_IP_VPS:/root/
```

### Étape 2 : Exécuter le script

Connectez-vous à votre VPS et exécutez :

```bash
ssh root@VOTRE_IP_VPS
chmod +x /root/deploy_vps.sh
./deploy_vps.sh
```

Le script vous guidera à travers toutes les étapes !

### Étape 3 : Copier vos fichiers

Quand le script vous le demande, depuis votre machine locale :

```bash
scp -r C:\Users\KB\Documents\autre\GestionStock-django-master\GestionStock-django-master/* root@VOTRE_IP_VPS:/home/gestionstock/app/
```

---

## Option 2 : Déploiement Manuel

Consultez le fichier `DEPLOYMENT_VPS_OCTENIUM.md` pour les instructions détaillées.

---

## Après le déploiement

### Accéder à votre application

- **Frontend**: http://votre-ip-vps ou http://votre-domaine.com
- **Administration**: http://votre-ip-vps/admin

### Vérifier que tout fonctionne

```bash
# Vérifier le service
sudo systemctl status gestionstock

# Vérifier les logs
sudo journalctl -u gestionstock -n 50

# Vérifier Nginx
sudo systemctl status nginx
```

### Mettre à jour l'application

```bash
sudo su - gestionstock
cd /home/gestionstock/app
source venv/bin/activate
git pull  # ou copiez les nouveaux fichiers
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
exit
sudo systemctl restart gestionstock
```

---

## Résolution de problèmes rapides

### L'application ne démarre pas

```bash
sudo journalctl -u gestionstock -f
```

### Erreur 502

```bash
sudo systemctl status gestionstock
sudo systemctl restart gestionstock
```

### Problème de fichiers statiques

```bash
sudo su - gestionstock
cd /home/gestionstock/app
source venv/bin/activate
python manage.py collectstatic --noinput
exit
sudo systemctl restart nginx
```

---

## Configuration SSL/HTTPS (Recommandé)

Si vous avez un nom de domaine :

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d votre-domaine.com -d www.votre-domaine.com
```

---

## Contacts & Support

- Documentation complète : `DEPLOYMENT_VPS_OCTENIUM.md`
- Support Octenium : https://octenium.com/support
- Django Documentation : https://docs.djangoproject.com/

---

**Bon déploiement ! 🚀**
