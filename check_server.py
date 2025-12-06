"""
Script pour vérifier si le serveur Django est accessible
"""
import socket

print("=" * 70)
print("VÉRIFICATION DE LA CONNECTIVITÉ DU SERVEUR DJANGO")
print("=" * 70)

# Adresse et port du serveur
host = "192.168.0.150"
port = 8000

# Test: Vérifier si le port est ouvert
print(f"\nTest de connexion au port {port} sur {host}...")
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(2)
result = sock.connect_ex((host, port))
sock.close()

print("\n" + "=" * 70)
print("RÉSULTAT")
print("=" * 70)

if result == 0:
    print(f"\n[OK] Port {port} est OUVERT et accessible sur {host}")
    print(f"\n   Le serveur Django semble etre en cours d'execution!")
    print(f"\nURLs a utiliser:")
    print(f"   - Interface web: http://{host}:{port}/")
    print(f"   - API tournees: http://{host}:{port}/API/distribution/tournees/")
else:
    print(f"\n[ERREUR] Port {port} est FERME ou inaccessible sur {host}")
    print(f"\n   Le serveur Django n'est PAS en cours d'execution")
    print(f"\nSolutions possibles:")
    print(f"\n   1. Demarrer le serveur Django:")
    print(f"      python manage.py runserver {host}:{port}")
    print(f"\n   2. Ou sur localhost:")
    print(f"      python manage.py runserver 0.0.0.0:{port}")
    print(f"\n   3. Verifier que le firewall n'est pas bloque")
    print(f"\n   4. Verifier votre adresse IP reseau avec: ipconfig")

print("\n" + "=" * 70)
