# Gouvernance des droits d'accès

Ce document décrit les rôles, permissions et la façon dont ils sont appliqués dans l'application.

## Rôles (Groupes)
- Administrateur: contrôle total (toutes permissions sur les modèles du domaine).
- Magasinier: gestion opérationnelle des stocks (ajout/modification/consultation sur Produits, Entrepôts, Stocks, Mouvements, Inventaires, BL; lecture sur référentiels).
- Comptable: focus finance/ventes (création/modification/consultation sur Ventes, Factures, Lignes; lecture sur le reste; quelques changements autorisés sur Clients et Devises selon le besoin).

La commande `python manage.py setup_roles` crée/actualise ces groupes et leur assigne les permissions détaillées dans le fichier `API/management/commands/setup_roles.py`.

## Application des permissions
- Côté API, `DEFAULT_PERMISSION_CLASSES = DjangoModelPermissions` est activé. Chaque ViewSet DRF applique les permissions `view/add/change/delete` sur le modèle concerné.
- Les utilisateurs doivent être authentifiés et avoir les permissions nécessaires via leur(s) groupe(s).
- Les endpoints d'administration des utilisateurs/roles/permissions sont restreints aux utilisateurs staff (IsAdminUser).

## Mapping permissions -> modèles
Voir la structure `API_MODELS` dans `API/management/commands/setup_roles.py` pour le détail par modèle et par rôle.

## Gestion des utilisateurs
- UI Frontoffice simple: `/users-admin/` (liste, création, modification, suppression) et `/roles-admin/` (liste des rôles et permissions).
- Pour l'API: `/API/users/`, `/API/roles/`, `/API/permissions/`.

## Bonnes pratiques
- Créer un compte Admin (staff + superuser) pour la gouvernance.
- Assigner les utilisateurs aux Groupes plutôt que de gérer des permissions individuelles.
- Réviser périodiquement les permissions attribuées aux rôles au fil des évolutions du modèle.
