# Documentation API - Application Mobile Livreurs

## Base URL
```
http://votre-domaine.com/API
```

## ⚠️ Important: Authentification Requise

**TOUS les endpoints de l'API nécessitent une authentification JWT**, sauf l'endpoint de login. Vous devez d'abord vous connecter pour obtenir un token, puis inclure ce token dans toutes vos requêtes.

---

## 0. Authentification JWT (OBLIGATOIRE)

### 🔑 Login - Obtenir le token d'accès

#### Endpoint
```http
POST /API/token/
```

#### Headers
```http
Content-Type: application/json
```

#### Body
```json
{
  "username": "LIV001",
  "password": "LIV0011311"
}
```

#### Exemple de requête
```bash
curl -X POST "http://localhost:8000/API/token/" \
  -H "Content-Type: application/json" \
  -d '{"username": "LIV001", "password": "LIV0011311"}'
```

#### Exemple de réponse (200 OK)
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### Code d'intégration - React Native / JavaScript

```javascript
import AsyncStorage from '@react-native-async-storage/async-storage';

const API_BASE = 'http://votre-domaine.com/API';

// Fonction de connexion
async function login(username, password) {
  try {
    const response = await fetch(`${API_BASE}/token/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username: username,
        password: password
      })
    });

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('Identifiants incorrects');
      }
      throw new Error(`Erreur HTTP: ${response.status}`);
    }

    const data = await response.json();

    // Stocker les tokens
    await AsyncStorage.setItem('access_token', data.access);
    await AsyncStorage.setItem('refresh_token', data.refresh);

    console.log('✅ Connexion réussie');
    return data;

  } catch (error) {
    console.error('❌ Erreur de connexion:', error);
    throw error;
  }
}

// Fonction pour récupérer le token
async function getAccessToken() {
  try {
    const token = await AsyncStorage.getItem('access_token');
    if (!token) {
      throw new Error('Non authentifié - veuillez vous connecter');
    }
    return token;
  } catch (error) {
    console.error('Erreur récupération token:', error);
    throw error;
  }
}

// Fonction pour rafraîchir le token
async function refreshAccessToken() {
  try {
    const refreshToken = await AsyncStorage.getItem('refresh_token');

    if (!refreshToken) {
      throw new Error('Aucun refresh token disponible');
    }

    const response = await fetch(`${API_BASE}/token/refresh/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        refresh: refreshToken
      })
    });

    if (!response.ok) {
      throw new Error('Impossible de rafraîchir le token');
    }

    const data = await response.json();
    await AsyncStorage.setItem('access_token', data.access);

    return data.access;
  } catch (error) {
    console.error('Erreur rafraîchissement token:', error);
    // Si le refresh échoue, déconnecter l'utilisateur
    await AsyncStorage.removeItem('access_token');
    await AsyncStorage.removeItem('refresh_token');
    throw error;
  }
}

// Fonction helper pour faire des requêtes authentifiées
async function authenticatedFetch(url, options = {}) {
  try {
    let token = await getAccessToken();

    const response = await fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });

    // Si le token a expiré (401), essayer de le rafraîchir
    if (response.status === 401) {
      console.log('Token expiré, rafraîchissement...');
      token = await refreshAccessToken();

      // Réessayer la requête avec le nouveau token
      return await fetch(url, {
        ...options,
        headers: {
          ...options.headers,
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });
    }

    return response;
  } catch (error) {
    console.error('Erreur requête authentifiée:', error);
    throw error;
  }
}

// Exemple d'utilisation
async function loginAndGetProfile() {
  try {
    // 1. Se connecter
    await login('LIV001', 'LIV0011311');

    // 2. Faire une requête authentifiée
    const response = await authenticatedFetch(
      `${API_BASE}/distribution/livreurs/`
    );

    const data = await response.json();
    console.log('Profil récupéré:', data);

  } catch (error) {
    console.error('Erreur:', error);
  }
}
```

### Code d'intégration - Flutter / Dart

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class AuthService {
  static const String baseUrl = 'http://votre-domaine.com/API';

  // Login
  Future<Map<String, dynamic>> login(String username, String password) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/token/'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'username': username,
          'password': password,
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);

        // Stocker les tokens
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('access_token', data['access']);
        await prefs.setString('refresh_token', data['refresh']);

        print('✅ Connexion réussie');
        return data;
      } else if (response.statusCode == 401) {
        throw Exception('Identifiants incorrects');
      } else {
        throw Exception('Erreur de connexion: ${response.statusCode}');
      }
    } catch (e) {
      print('❌ Erreur: $e');
      throw e;
    }
  }

  // Récupérer le token
  Future<String?> getAccessToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('access_token');
  }

  // Rafraîchir le token
  Future<String> refreshToken() async {
    final prefs = await SharedPreferences.getInstance();
    final refreshToken = prefs.getString('refresh_token');

    if (refreshToken == null) {
      throw Exception('Aucun refresh token disponible');
    }

    final response = await http.post(
      Uri.parse('$baseUrl/token/refresh/'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'refresh': refreshToken}),
    );

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      await prefs.setString('access_token', data['access']);
      return data['access'];
    } else {
      throw Exception('Impossible de rafraîchir le token');
    }
  }

  // Requête authentifiée
  Future<http.Response> authenticatedGet(String endpoint) async {
    String? token = await getAccessToken();

    if (token == null) {
      throw Exception('Non authentifié');
    }

    var response = await http.get(
      Uri.parse('$baseUrl$endpoint'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
    );

    // Si le token a expiré, le rafraîchir
    if (response.statusCode == 401) {
      print('Token expiré, rafraîchissement...');
      token = await refreshToken();

      response = await http.get(
        Uri.parse('$baseUrl$endpoint'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
      );
    }

    return response;
  }
}
```

---

## 1. Récupérer les clients assignés à un livreur

### Endpoint
```http
GET /API/distribution/livreurs/{livreur_id}/clients_assignes/
```

### Description
Récupère la liste de tous les clients assignés à un livreur spécifique.

### 🔐 Authentification
**Requise** - Token JWT dans le header `Authorization: Bearer {token}`

### Paramètres
- `livreur_id` (path parameter) : ID du livreur

### Headers
```http
Content-Type: application/json
Authorization: Bearer {votre_token_jwt}
```

### Exemple de requête
```bash
curl -X GET "http://localhost:8000/API/distribution/livreurs/1/clients_assignes/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."
```

### Exemple de réponse (200 OK)
```json
{
  "livreur_id": 1,
  "livreur_nom": "Mohamed Alami",
  "clients": [
    {
      "id": 5,
      "nom": "Dupont",
      "prenom": "Jean",
      "email": "jean.dupont@email.com",
      "telephone": "0612345678",
      "adresse": "123 Rue de la Paix, Casablanca"
    },
    {
      "id": 12,
      "nom": "Martin",
      "prenom": "Sophie",
      "email": "sophie.martin@email.com",
      "telephone": "0698765432",
      "adresse": "456 Avenue Hassan II, Rabat"
    }
  ]
}
```

### Code d'intégration - React Native / JavaScript

```javascript
// Fonction pour récupérer les clients assignés (AVEC AUTHENTIFICATION)
async function getClientsAssignes(livreurId) {
  try {
    // Utiliser la fonction authenticatedFetch définie précédemment
    const response = await authenticatedFetch(
      `${API_BASE}/distribution/livreurs/${livreurId}/clients_assignes/`
    );

    if (!response.ok) {
      throw new Error(`Erreur HTTP: ${response.status}`);
    }

    const data = await response.json();
    console.log(`✅ ${data.clients.length} clients récupérés`);
    return data.clients;

  } catch (error) {
    console.error('❌ Erreur lors de la récupération des clients:', error);
    throw error;
  }
}

// Utilisation complète avec login
async function loadClientsForDriver(username, password) {
  try {
    // 1. Se connecter
    await login(username, password);

    // 2. Récupérer l'ID du livreur
    const response = await authenticatedFetch(`${API_BASE}/distribution/livreurs/`);
    const livreursData = await response.json();
    const livreurs = livreursData.results || livreursData;
    const monLivreur = livreurs[0]; // Premier livreur trouvé

    if (!monLivreur) {
      throw new Error('Aucun profil livreur trouvé');
    }

    // Stocker l'ID du livreur
    await AsyncStorage.setItem('livreur_id', String(monLivreur.id));

    // 3. Récupérer les clients assignés
    const clients = await getClientsAssignes(monLivreur.id);

    console.log('✅ Connexion complète réussie');
    return {
      livreur: monLivreur,
      clients: clients
    };

  } catch (error) {
    console.error('❌ Erreur:', error);
    throw error;
  }
}
```

### Code d'intégration - Flutter / Dart

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

class Client {
  final int id;
  final String nom;
  final String prenom;
  final String email;
  final String telephone;
  final String adresse;

  Client({
    required this.id,
    required this.nom,
    required this.prenom,
    required this.email,
    required this.telephone,
    required this.adresse,
  });

  factory Client.fromJson(Map<String, dynamic> json) {
    return Client(
      id: json['id'],
      nom: json['nom'] ?? '',
      prenom: json['prenom'] ?? '',
      email: json['email'] ?? '',
      telephone: json['telephone'] ?? '',
      adresse: json['adresse'] ?? '',
    );
  }
}

class ApiService {
  final AuthService authService = AuthService();

  // Récupérer les clients assignés (AVEC AUTHENTIFICATION)
  Future<List<Client>> getClientsAssignes(int livreurId) async {
    try {
      final response = await authService.authenticatedGet(
        '/distribution/livreurs/$livreurId/clients_assignes/'
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final List<dynamic> clientsJson = data['clients'];

        print('✅ ${clientsJson.length} clients récupérés');
        return clientsJson.map((json) => Client.fromJson(json)).toList();
      } else {
        throw Exception('Erreur: ${response.statusCode}');
      }
    } catch (e) {
      print('❌ Erreur: $e');
      throw e;
    }
  }
}

// Exemple d'utilisation
void main() async {
  final authService = AuthService();
  final apiService = ApiService();

  try {
    // 1. Se connecter
    await authService.login('LIV001', 'LIV0011311');

    // 2. Récupérer les clients
    final clients = await apiService.getClientsAssignes(1);

    print('Nombre de clients: ${clients.length}');
    for (var client in clients) {
      print('${client.nom} ${client.prenom} - ${client.telephone}');
    }
  } catch (e) {
    print('Erreur: $e');
  }
}
```

---

## 2. Flux de travail complet - Connexion et récupération des données

### React Native - Exemple Complet

```javascript
import React, { useState, useEffect } from 'react';
import { View, Text, FlatList, ActivityIndicator, Button, TextInput, Alert } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

const API_BASE = 'http://votre-domaine.com/API';

const App = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(false);
  const [livreurId, setLivreurId] = useState(null);

  // Vérifier si déjà connecté au démarrage
  useEffect(() => {
    checkAuthentication();
  }, []);

  const checkAuthentication = async () => {
    try {
      const token = await AsyncStorage.getItem('access_token');
      const savedLivreurId = await AsyncStorage.getItem('livreur_id');

      if (token && savedLivreurId) {
        setIsAuthenticated(true);
        setLivreurId(parseInt(savedLivreurId));
        loadClients(parseInt(savedLivreurId));
      }
    } catch (error) {
      console.error('Erreur vérification auth:', error);
    }
  };

  const handleLogin = async () => {
    try {
      setLoading(true);

      // 1. Connexion
      const loginResponse = await fetch(`${API_BASE}/token/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });

      if (!loginResponse.ok) {
        Alert.alert('Erreur', 'Identifiants incorrects');
        return;
      }

      const tokens = await loginResponse.json();
      await AsyncStorage.setItem('access_token', tokens.access);
      await AsyncStorage.setItem('refresh_token', tokens.refresh);

      // 2. Récupérer l'ID du livreur
      const livreurResponse = await fetch(`${API_BASE}/distribution/livreurs/`, {
        headers: { 'Authorization': `Bearer ${tokens.access}` }
      });

      const livreursData = await livreurResponse.json();
      const livreurs = livreursData.results || livreursData;
      const monLivreur = livreurs[0];

      if (!monLivreur) {
        Alert.alert('Erreur', 'Aucun profil livreur trouvé');
        return;
      }

      await AsyncStorage.setItem('livreur_id', String(monLivreur.id));
      setLivreurId(monLivreur.id);
      setIsAuthenticated(true);

      // 3. Charger les clients
      await loadClients(monLivreur.id);

    } catch (error) {
      Alert.alert('Erreur', error.message);
    } finally {
      setLoading(false);
    }
  };

  const loadClients = async (id) => {
    try {
      const token = await AsyncStorage.getItem('access_token');

      const response = await fetch(
        `${API_BASE}/distribution/livreurs/${id}/clients_assignes/`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (!response.ok) {
        throw new Error('Erreur de chargement');
      }

      const data = await response.json();
      setClients(data.clients);

      // Sauvegarder en cache
      await AsyncStorage.setItem('clients_cache', JSON.stringify(data.clients));

    } catch (error) {
      console.error('Erreur:', error);

      // Charger depuis le cache si disponible
      const cached = await AsyncStorage.getItem('clients_cache');
      if (cached) {
        setClients(JSON.parse(cached));
        Alert.alert('Mode hors ligne', 'Données chargées depuis le cache');
      }
    }
  };

  const handleLogout = async () => {
    await AsyncStorage.clear();
    setIsAuthenticated(false);
    setClients([]);
    setLivreurId(null);
  };

  if (!isAuthenticated) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', padding: 20 }}>
        <Text style={{ fontSize: 24, marginBottom: 20 }}>Connexion</Text>
        <TextInput
          placeholder="Nom d'utilisateur"
          value={username}
          onChangeText={setUsername}
          style={{ borderWidth: 1, padding: 10, marginBottom: 10 }}
        />
        <TextInput
          placeholder="Mot de passe"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          style={{ borderWidth: 1, padding: 10, marginBottom: 20 }}
        />
        <Button title="Se connecter" onPress={handleLogin} disabled={loading} />
      </View>
    );
  }

  return (
    <View style={{ flex: 1, padding: 20 }}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 20 }}>
        <Text style={{ fontSize: 20 }}>Mes Clients ({clients.length})</Text>
        <Button title="Déconnexion" onPress={handleLogout} />
      </View>

      <FlatList
        data={clients}
        keyExtractor={item => item.id.toString()}
        renderItem={({ item }) => (
          <View style={{ padding: 15, backgroundColor: '#f9f9f9', marginBottom: 10, borderRadius: 8 }}>
            <Text style={{ fontWeight: 'bold' }}>{item.nom} {item.prenom}</Text>
            <Text>📞 {item.telephone}</Text>
            <Text>📍 {item.adresse}</Text>
          </View>
        )}
      />
    </View>
  );
};

export default App;
```

---

## 3. Récupérer les tournées d'un livreur

### Endpoint
```http
GET /API/distribution/livreurs/{livreur_id}/tournees/
```

### 🔐 Authentification
**Requise** - Token JWT dans le header

### Paramètres optionnels (query string)
- `date_debut` : Date de début (format: YYYY-MM-DD)
- `date_fin` : Date de fin (format: YYYY-MM-DD)

### Headers
```http
Content-Type: application/json
Authorization: Bearer {votre_token_jwt}
```

### Exemple de requête
```bash
curl -X GET "http://localhost:8000/API/distribution/livreurs/1/tournees/?date_debut=2025-01-01&date_fin=2025-01-31" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."
```

### Exemple de réponse (200 OK)
```json
[
  {
    "id": 10,
    "livreur": 1,
    "livreur_nom": "Mohamed Alami",
    "livreur_matricule": "LIV-001",
    "date_tournee": "2025-01-13",
    "numero_tournee": "T-2025-001",
    "statut": "planifiee",
    "argent_depart": 5000.00,
    "heure_debut": null,
    "heure_fin": null,
    "distance_km": null,
    "arrets": [
      {
        "id": 25,
        "ordre_passage": 1,
        "client_nom": "Dupont Jean",
        "client_adresse": "123 Rue de la Paix, Casablanca",
        "client_telephone": "0612345678",
        "statut": "en_attente",
        "heure_prevue": "09:00:00"
      }
    ],
    "statistiques": {
      "total_arrets": 5,
      "arrets_livres": 0,
      "arrets_echec": 0,
      "arrets_en_attente": 5,
      "taux_reussite": 0.0,
      "ca_total": 0.0
    }
  }
]
```

---

## 4. Gestion du cache local (Recommandé)

Pour une meilleure expérience utilisateur, stockez les données en local :

```javascript
import AsyncStorage from '@react-native-async-storage/async-storage';

// Sauvegarder les clients en cache
const saveClientsToCache = async (livreurId, clients) => {
  try {
    await AsyncStorage.setItem(
      `clients_${livreurId}`,
      JSON.stringify(clients)
    );
    await AsyncStorage.setItem(
      `clients_${livreurId}_timestamp`,
      Date.now().toString()
    );
  } catch (error) {
    console.error('Erreur sauvegarde cache:', error);
  }
};

// Charger les clients depuis le cache
const loadClientsFromCache = async (livreurId) => {
  try {
    const cached = await AsyncStorage.getItem(`clients_${livreurId}`);
    return cached ? JSON.parse(cached) : null;
  } catch (error) {
    console.error('Erreur lecture cache:', error);
    return null;
  }
};

// Stratégie: Cache-first, puis mise à jour
const getClients = async (livreurId) => {
  // 1. Charger depuis le cache d'abord (affichage rapide)
  const cachedClients = await loadClientsFromCache(livreurId);

  if (cachedClients) {
    setClients(cachedClients); // Affichage immédiat
  }

  // 2. Mettre à jour depuis le serveur en arrière-plan
  try {
    const token = await AsyncStorage.getItem('access_token');
    const response = await fetch(
      `${API_BASE}/distribution/livreurs/${livreurId}/clients_assignes/`,
      {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    );

    const data = await response.json();

    // Sauvegarder dans le cache
    await saveClientsToCache(livreurId, data.clients);

    // Mettre à jour l'interface
    setClients(data.clients);
  } catch (error) {
    // Si erreur réseau, on garde le cache
    console.error('Erreur réseau:', error);
    if (!cachedClients) {
      setError('Impossible de charger les clients');
    }
  }
};
```

---

## 5. Codes d'erreur et résolution

| Code | Description | Action recommandée |
|------|-------------|-------------------|
| 200 | Succès | Traiter les données |
| 401 | Non authentifié / Token expiré | Rafraîchir le token ou redemander connexion |
| 403 | Accès refusé | Vérifier les permissions |
| 404 | Ressource non trouvée | Vérifier l'ID du livreur |
| 500 | Erreur serveur | Réessayer plus tard |
| Network Error | Pas de connexion | Utiliser le cache local |

### Gestion des erreurs 401 (Token expiré)

```javascript
async function handleAuthenticatedRequest(url, options = {}) {
  try {
    let token = await AsyncStorage.getItem('access_token');

    let response = await fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        'Authorization': `Bearer ${token}`
      }
    });

    // Si 401, rafraîchir le token
    if (response.status === 401) {
      console.log('Token expiré, rafraîchissement...');

      const refreshToken = await AsyncStorage.getItem('refresh_token');
      const refreshResponse = await fetch(`${API_BASE}/token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: refreshToken })
      });

      if (refreshResponse.ok) {
        const data = await refreshResponse.json();
        await AsyncStorage.setItem('access_token', data.access);

        // Réessayer avec le nouveau token
        response = await fetch(url, {
          ...options,
          headers: {
            ...options.headers,
            'Authorization': `Bearer ${data.access}`
          }
        });
      } else {
        // Impossible de rafraîchir, déconnecter
        await AsyncStorage.clear();
        throw new Error('Session expirée, veuillez vous reconnecter');
      }
    }

    return response;
  } catch (error) {
    throw error;
  }
}
```

---

## 6. Montant de départ prédéfini (argent_depart)

### Description
Chaque tournée contient un champ `argent_depart` qui représente le montant prédéfini donné au chauffeur en début de tournée. Ce montant est défini par le système et **ne peut pas être modifié** par le chauffeur dans l'application mobile.

### Caractéristiques
- ✅ Montant défini lors de la création de la tournée
- ✅ Lecture seule pour le chauffeur
- ✅ Inclus dans toutes les réponses d'API de tournée
- ✅ Montant en devise locale (MAD, EUR, etc.)

### Interface utilisateur recommandée

```
┌─────────────────────────────────┐
│ 🎯 Tournée T-2025-001          │
│                                 │
│ Montant de départ (prédéfini)  │
│ ┌───────────────────────────┐  │
│ │ 💰  5 000,00  MAD        │  │ (lecture seule)
│ └───────────────────────────┘  │
│ Ce montant a été défini         │
│ par le système                  │
│                                 │
│ [Démarrer la tournée]           │
└─────────────────────────────────┘
```

### Notes importantes

1. **Lecture seule** : Le chauffeur ne peut **JAMAIS** modifier ce montant
2. **Prédéfini** : Le montant est défini lors de la création de la tournée par l'administrateur
3. **Synchronisation** : Le montant est automatiquement synchronisé lors du pull
4. **Valeur par défaut** : Si aucun montant n'est défini, la valeur par défaut est 0

---

## 6 bis. Synchronisation incrémentale (deltas)

### Endpoint
```
GET /API/sync/deltas/?since=2026-11-28T07:00:00.000Z
```
Alias : `GET /API/distribution/sync/deltas/`.

### Paramètres (query string, tous optionnels)
| Paramètre | Description |
|-----------|-------------|
| `since` | Date ISO 8601 de la dernière synchronisation. Absent : tournées du jour et futures, non clôturées. |
| `livreur_id` | Livreur à synchroniser. Absent : le livreur du compte connecté. Un utilisateur du bureau doit le préciser. |

### Règles
- Même sélection de tournées, mêmes permissions et même filtrage par entreprise que `POST /API/distribution/sync/pull/` :
  un livreur ne reçoit que ses propres tournées ; un administrateur d'entreprise, seulement les livreurs de son entreprise.
- Statuts convertis au format du téléphone : tournée `planifiee` → `pending`, `en_cours` → `in_progress`,
  `terminee` / `cloturee` / `annulee` → `completed` ; arrêt `livre` → `success`, `echec` → `failure`, sinon `pending`.

### Réponse (200 OK)
```json
{
  "timestamp": "2026-11-28T08:15:02.120Z",
  "tournees": [{"id": "14", "date": "2026-11-28", "assigned_to": "29", "status": "in_progress",
                "argent_depart": 5000.0, "updated_at": "2026-11-28T07:58:11+00:00"}],
  "arrets": [{"id": "301", "tournee_id": "14", "client_id": "12", "client_nom": "MINI market",
              "client_tel": "0550...", "adresse": "...", "lat": 36.7, "lng": 3.05, "heure_prevue": "09:30",
              "statut": "pending", "notes": null, "updated_at": "2026-11-28T07:58:11+00:00"}],
  "clients": [],
  "suppressions": [],
  "nb_tournees": 1,
  "nb_arrets": 1,
  "message": "Synchronisation réussie: 1 tournée(s)"
}
```
Erreurs : `400` si `since` ou `livreur_id` est invalide, ou si le compte n'est pas un livreur et que `livreur_id` est absent ;
`403` pour le livreur d'un autre (ou d'une autre entreprise) ; `404` si le livreur n'existe pas.

## 6 ter. Stock du van — livreur sans van

`GET /API/distribution/livreurs/{id}/stock_van/` répond **200** (et non plus 404) quand aucun van n'est assigné :
```json
{"a_van": false, "sans_van": true, "message": "Ce livreur n'a pas de van assigné",
 "livreur_id": 29, "livreur_nom": "...", "livreur": {"id": 29, "nom": "...", "matricule": "..."},
 "van": null, "statistiques": {"nb_produits": 0, "nb_references": 0, "total_quantite": 0,
 "valeur_stock": 0, "currency_symbol": "DA"}, "stocks": []}
```
Avec un van, la réponse habituelle contient `"a_van": true`.

## 6 quater. Comptes clients

`GET /API/distribution/comptes-clients/?tournees=14,15` ou `?clients=12,13`.
Sans paramètre, pour un compte livreur : clients des arrêts de ses tournées planifiées ou en cours.
Aucun client trouvé (ex. tournée sans arrêt) : **200 `[]`** (avant : 400 « tournees ou clients est requis »).

---

## 7. Checklist de déploiement

Avant de déployer votre application mobile:

### Configuration serveur
- [ ] Le serveur Django est accessible depuis Internet (pas seulement localhost)
- [ ] HTTPS est activé en production (obligatoire pour JWT)
- [ ] CORS est configuré correctement
- [ ] Les endpoints `/API/token/` et `/API/token/refresh/` fonctionnent

### Configuration application
- [ ] L'URL de base (`API_BASE`) pointe vers le bon serveur
- [ ] La gestion des tokens JWT est implémentée
- [ ] Le rafraîchissement automatique des tokens fonctionne
- [ ] Le cache local est implémenté pour le mode hors ligne
- [ ] La gestion des erreurs réseau est en place

### Tests
- [ ] Connexion avec identifiants valides
- [ ] Connexion avec identifiants invalides
- [ ] Récupération des clients assignés
- [ ] Expiration et rafraîchissement du token
- [ ] Mode hors ligne avec cache

---

## 8. Résumé des URLs

| Action | Méthode | URL | Auth | Description |
|--------|---------|-----|------|-------------|
| **Login** | POST | `/API/token/` | ❌ Non | Obtenir les tokens JWT |
| **Refresh Token** | POST | `/API/token/refresh/` | ❌ Non | Rafraîchir le token d'accès |
| Liste livreurs | GET | `/API/distribution/livreurs/` | ✅ Oui | Liste de tous les livreurs |
| Détail livreur | GET | `/API/distribution/livreurs/{id}/` | ✅ Oui | Détails d'un livreur |
| **Clients assignés** | GET | `/API/distribution/livreurs/{id}/clients_assignes/` | ✅ Oui | Clients d'un livreur |
| Tournées livreur | GET | `/API/distribution/livreurs/{id}/tournees/` | ✅ Oui | Tournées d'un livreur |
| Synchro incrémentale | GET | `/API/sync/deltas/?since=...` | ✅ Oui | Tournées et arrêts modifiés depuis `since` |
| Stock du van | GET | `/API/distribution/livreurs/{id}/stock_van/` | ✅ Oui | Stock du van (200 + `a_van: false` sans van) |
| Comptes clients | GET | `/API/distribution/comptes-clients/` | ✅ Oui | Dettes, avances et historique des clients |

---

## 9. Support et Débogage

### Activer les logs détaillés

```javascript
// Activer les logs pour le débogage
const DEBUG = true;

function debugLog(message, data = null) {
  if (DEBUG) {
    console.log(`[DEBUG] ${message}`, data || '');
  }
}

// Utilisation
debugLog('Token récupéré:', token);
debugLog('Requête envoyée à:', url);
```

### Tester la connectivité

```javascript
async function testConnectivity() {
  try {
    const response = await fetch(`${API_BASE}/token/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: 'test',
        password: 'test'
      })
    });

    console.log('✅ Serveur accessible');
    return true;
  } catch (error) {
    console.error('❌ Serveur inaccessible:', error);
    return false;
  }
}
```

---

**📝 Note**: Cette documentation est mise à jour régulièrement. Pour toute question, contactez l'équipe de développement.
