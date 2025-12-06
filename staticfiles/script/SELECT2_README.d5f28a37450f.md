# Select2 - Documentation

## Fonctionnement Automatique

Select2 est **automatiquement appliqué à TOUS les selects** du logiciel.

Le script `select2-init.js` :
- S'exécute au chargement de chaque page
- Détecte tous les `<select>` présents
- Les transforme en champs de recherche intelligents
- Surveille les changements DOM pour initialiser les nouveaux selects

## Fonctionnalités

### Pour TOUS les selects :
- ✅ Barre de recherche intégrée
- ✅ Recherche en temps réel pendant la frappe
- ✅ Bouton "X" pour effacer la sélection
- ✅ Messages en français
- ✅ Design Bootstrap 4
- ✅ Placeholders intelligents selon le contexte

### Placeholders Automatiques

Le script détecte automatiquement le type de select et adapte le placeholder :

| Type de Select | Placeholder |
|----------------|-------------|
| Produit | "Rechercher un produit..." |
| Client | "Rechercher un client..." |
| Fournisseur | "Rechercher un fournisseur..." |
| Catégorie | "Rechercher une catégorie..." |
| Entrepôt | "Rechercher un entrepôt..." |
| Utilisateur | "Rechercher un utilisateur..." |
| Rôle/Groupe | "Rechercher un rôle..." |
| Devise/Currency | "Rechercher une devise..." |
| Paiement | "Choisir un mode de paiement..." |
| Statut | "Choisir un statut..." |
| Autres | Utilise le texte de la première option ou "Sélectionner..." |

## Désactiver Select2 sur un Select Spécifique

Si vous voulez **désactiver** Select2 sur un select particulier, ajoutez la classe `no-select2` :

```html
<select class="form-control no-select2" id="mon-select">
    <option>Option 1</option>
    <option>Option 2</option>
</select>
```

## Forcer la Réinitialisation

Si vous ajoutez des selects dynamiquement et qu'ils ne sont pas automatiquement transformés :

### JavaScript
```javascript
// Réinitialiser tous les selects
window.reinitSelect2();

// OU forcer la destruction et réinitialisation complète
window.forceReinitSelect2();
```

## Configuration Personnalisée

Pour personnaliser le placeholder d'un select spécifique :

### HTML
```html
<select data-placeholder="Mon placeholder personnalisé">
    <option></option>
    <option>Option 1</option>
</select>
```

## Styles Personnalisés

Le fichier `static/style/select2-custom.css` contient les styles personnalisés.

Vous pouvez le modifier pour ajuster :
- Les couleurs
- Les tailles
- Les effets de hover/focus
- Le responsive

## Compatibilité

- ✅ Bootstrap 4
- ✅ jQuery 3.6+
- ✅ Tous les navigateurs modernes
- ✅ Mobile et tablette

## Dépannage

### Select2 ne s'applique pas
1. Vérifiez que jQuery est chargé avant Select2
2. Vérifiez que le select n'a pas la classe `no-select2`
3. Essayez `window.forceReinitSelect2()` dans la console

### Le select est trop petit
Ajustez dans `select2-custom.css` :
```css
.select2-container--bootstrap4 .select2-selection {
    min-height: 38px; /* Modifier cette valeur */
}
```

### Conflit avec d'autres scripts
Select2 attend 500ms avant de s'initialiser pour laisser le temps aux autres scripts.
Si nécessaire, augmentez ce délai dans `select2-init.js` ligne 237.

## Support

Pour plus d'informations sur Select2 :
- Documentation officielle : https://select2.org/
- GitHub : https://github.com/select2/select2
