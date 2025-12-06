# Spécifications GPS pour Application Mobile
## Envoi des Coordonnées GPS des Clients

---

## 📋 Vue d'ensemble

L'application mobile doit envoyer les coordonnées GPS (Latitude et Longitude) des clients lors de la création ou mise à jour d'un client dans le système.

---

## 🔧 API Backend - Déjà Configurée ✅

### Endpoint API
```
URL: /API/clients/
Méthode: POST (création) ou PATCH (modification)
Auth: Bearer Token JWT requis
Content-Type: application/json
```

### Champs GPS Disponibles

Le modèle `Client` dispose déjà de ces champs :

| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| `lat` | Decimal(10,7) | ❌ Non | Latitude GPS (ex: 36.7372502) |
| `lng` | Decimal(10,7) | ❌ Non | Longitude GPS (ex: 3.0865015) |

---

## 📱 Ce qu'il faut ajouter dans l'App Mobile

### 1. **Permissions GPS** (Android)

Dans `AndroidManifest.xml` :
```xml
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
```

### 2. **Permissions GPS** (iOS)

Dans `Info.plist` :
```xml
<key>NSLocationWhenInUseUsageDescription</key>
<string>Nous avons besoin de votre position pour enregistrer l'emplacement des clients</string>
<key>NSLocationAlwaysUsageDescription</key>
<string>Nous avons besoin de votre position pour les livraisons</string>
```

---

## 🌍 Capture des Coordonnées GPS

### Option 1 : Géolocalisation Automatique (Recommandée)

Lors de la visite d'un client, capturer automatiquement la position du livreur :

```javascript
// Exemple JavaScript (React Native / Cordova)
navigator.geolocation.getCurrentPosition(
    (position) => {
        const latitude = position.coords.latitude;
        const longitude = position.coords.longitude;

        console.log('Position:', latitude, longitude);

        // Envoyer au backend
        updateClientLocation(clientId, latitude, longitude);
    },
    (error) => {
        console.error('Erreur GPS:', error);
        // Gérer l'erreur (permissions refusées, GPS désactivé, etc.)
    },
    {
        enableHighAccuracy: true,
        timeout: 5000,
        maximumAge: 0
    }
);
```

**Exemple Kotlin (Android natif) :**
```kotlin
import android.location.Location
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationServices

val fusedLocationClient: FusedLocationProviderClient =
    LocationServices.getFusedLocationProviderClient(this)

fusedLocationClient.lastLocation.addOnSuccessListener { location: Location? ->
    location?.let {
        val latitude = it.latitude
        val longitude = it.longitude

        // Envoyer au backend
        updateClientLocation(clientId, latitude, longitude)
    }
}
```

**Exemple Swift (iOS natif) :**
```swift
import CoreLocation

let locationManager = CLLocationManager()
locationManager.requestWhenInUseAuthorization()

if let location = locationManager.location {
    let latitude = location.coordinate.latitude
    let longitude = location.coordinate.longitude

    // Envoyer au backend
    updateClientLocation(clientId: clientId, lat: latitude, lng: longitude)
}
```

---

### Option 2 : Sélection Manuelle sur Carte

Permettre au livreur de placer un marqueur sur une carte :

```javascript
// Exemple avec Google Maps (React Native)
<MapView
    onPress={(event) => {
        const { latitude, longitude } = event.nativeEvent.coordinate;
        setClientLat(latitude);
        setClientLng(longitude);
    }}
>
    <Marker coordinate={{ latitude: clientLat, longitude: clientLng }} />
</MapView>
```

---

## 📤 Envoi des Données au Backend

### 1. **Création d'un Nouveau Client**

```http
POST /API/clients/
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json

{
    "nom": "Dupont",
    "prenom": "Jean",
    "email": "jean.dupont@example.com",
    "telephone": "0555123456",
    "adresse": "123 Rue de la Paix, Alger",
    "secteur": 1,
    "lat": 36.7372502,
    "lng": 3.0865015
}
```

**Réponse (201 Created) :**
```json
{
    "id": 42,
    "nom": "Dupont",
    "prenom": "Jean",
    "email": "jean.dupont@example.com",
    "telephone": "0555123456",
    "adresse": "123 Rue de la Paix, Alger",
    "secteur": 1,
    "secteur_nom": "Alger Centre",
    "secteur_code": "ALG-C",
    "secteur_couleur": "#3B82F6",
    "lat": "36.7372502",
    "lng": "3.0865015",
    "nif": null,
    "nis": null,
    "ai": null,
    "rc": null,
    "produits": []
}
```

---

### 2. **Mise à Jour des Coordonnées d'un Client Existant**

```http
PATCH /API/clients/42/
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json

{
    "lat": 36.7543210,
    "lng": 3.0998765
}
```

**Réponse (200 OK) :**
```json
{
    "id": 42,
    "nom": "Dupont",
    "prenom": "Jean",
    "lat": "36.7543210",
    "lng": "3.0998765",
    ...
}
```

---

## 🎯 Scénarios d'Utilisation

### Scénario 1 : Visite Client avec Géolocalisation Automatique

1. Le livreur arrive chez le client
2. Il ouvre la fiche client dans l'app mobile
3. Il clique sur un bouton **"Enregistrer ma position actuelle"**
4. L'app capture automatiquement les coordonnées GPS
5. L'app envoie une requête `PATCH /API/clients/{id}/` avec `lat` et `lng`
6. Message de confirmation : "✅ Position enregistrée"

**Code Exemple :**
```javascript
async function saveCurrentLocationForClient(clientId) {
    try {
        // 1. Obtenir la position actuelle
        const position = await getCurrentPosition();

        // 2. Envoyer au backend
        const response = await fetch(`${API_BASE}/clients/${clientId}/`, {
            method: 'PATCH',
            headers: {
                'Authorization': `Bearer ${getToken()}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                lat: position.latitude,
                lng: position.longitude
            })
        });

        if (response.ok) {
            showMessage('✅ Position enregistrée avec succès');
        } else {
            showError('❌ Erreur lors de l\'enregistrement');
        }
    } catch (error) {
        console.error('Erreur GPS:', error);
        showError('Impossible d\'obtenir votre position');
    }
}
```

---

### Scénario 2 : Nouveau Client avec Position Manuelle

1. Le livreur crée un nouveau client
2. Il remplit le formulaire (nom, téléphone, etc.)
3. Il clique sur **"Définir la position sur la carte"**
4. Une carte s'ouvre avec un marqueur déplaçable
5. Il place le marqueur à l'adresse du client
6. Il valide → les coordonnées sont envoyées avec la création du client

---

## 🛡️ Gestion des Erreurs

### Erreurs Possibles

| Code | Erreur | Solution |
|------|--------|----------|
| 400 | Format GPS invalide | Vérifier que lat/lng sont des nombres décimaux |
| 401 | Non authentifié | Rafraîchir le token JWT |
| 403 | Permission refusée | Vérifier les droits de l'utilisateur |
| 404 | Client introuvable | Vérifier l'ID du client |

### Validation des Coordonnées

Avant d'envoyer, valider les coordonnées :

```javascript
function validateGPS(lat, lng) {
    // Latitude : -90 à +90
    if (lat < -90 || lat > 90) {
        throw new Error('Latitude invalide');
    }

    // Longitude : -180 à +180
    if (lng < -180 || lng > 180) {
        throw new Error('Longitude invalide');
    }

    return true;
}
```

---

## 📊 Format des Données

### Précision GPS

- **Format**: Décimal (pas de degrés/minutes/secondes)
- **Précision**: 7 décimales maximum
- **Exemple Algérie**:
  - Alger: `lat: 36.7372502, lng: 3.0865015`
  - Oran: `lat: 35.6969752, lng: -0.6331179`
  - Constantine: `lat: 36.3650032, lng: 6.6147052`

### Valeurs NULL

Les champs `lat` et `lng` sont **optionnels** :
- Vous pouvez envoyer `null` si pas de coordonnées
- Vous pouvez omettre complètement les champs
- Le backend accepte les deux

```json
// Ces 3 formats sont valides :
{"nom": "Test", "lat": 36.7372502, "lng": 3.0865015}
{"nom": "Test", "lat": null, "lng": null}
{"nom": "Test"}
```

---

## 🔍 Test de l'API

### Test avec cURL

**Créer un client avec GPS :**
```bash
curl -X POST http://localhost:8000/API/clients/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "nom": "Test",
    "prenom": "GPS",
    "email": "test@example.com",
    "telephone": "0555000000",
    "adresse": "Test Address",
    "lat": 36.7372502,
    "lng": 3.0865015
  }'
```

**Mettre à jour les coordonnées :**
```bash
curl -X PATCH http://localhost:8000/API/clients/1/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 36.7543210,
    "lng": 3.0998765
  }'
```

---

## 📱 Interface Utilisateur Recommandée

### Bouton "Enregistrer ma position"

```
┌─────────────────────────────────────┐
│  📱 Fiche Client                    │
├─────────────────────────────────────┤
│  Nom: Dupont Jean                   │
│  Tél: 0555123456                    │
│  Adresse: 123 Rue de la Paix        │
│                                     │
│  📍 Position GPS                    │
│  Lat: 36.7372502                    │
│  Lng: 3.0865015                     │
│                                     │
│  [📍 Enregistrer ma position]       │
│  [🗺️ Voir sur la carte]            │
└─────────────────────────────────────┘
```

---

## ✅ Checklist Développement Mobile

- [ ] Ajouter permissions GPS (Android/iOS)
- [ ] Implémenter fonction de géolocalisation
- [ ] Créer bouton "Enregistrer ma position actuelle"
- [ ] Valider les coordonnées avant envoi
- [ ] Gérer les erreurs de permissions GPS
- [ ] Gérer l'absence de signal GPS
- [ ] Tester l'envoi API avec coordonnées
- [ ] Afficher les coordonnées enregistrées
- [ ] (Optionnel) Ajouter sélection manuelle sur carte
- [ ] (Optionnel) Afficher client sur carte

---

## 🆘 Support

**Questions techniques :**
- Vérifier que l'API retourne bien `lat` et `lng` : `GET /API/clients/1/`
- Les coordonnées sont stockées dans la table `API_client`
- Format dans la base : `DECIMAL(10,7)`

**Problèmes courants :**
1. **401 Unauthorized** → Token JWT expiré ou invalide
2. **GPS ne fonctionne pas** → Vérifier permissions et service de localisation activé
3. **Coordonnées nulles** → Vérifier que `lat`/`lng` sont bien envoyés dans le JSON

---

## 📅 Date de mise à jour
**6 Décembre 2025**

Le backend est **prêt et opérationnel** ✅
Il ne reste plus qu'à implémenter côté mobile ! 🚀
