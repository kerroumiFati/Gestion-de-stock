"""
Test script to verify import URLs are working
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User

# Create a test client
client = Client()

# Test 1: Check template download without auth (should work with AllowAny)
print("Test 1: Template download (no auth)")
response = client.get('/API/import/template/', {'type': 'products', 'format': 'excel'})
print(f"  Status: {response.status_code}")
print(f"  Content-Type: {response.get('Content-Type', 'N/A')}")
if response.status_code == 200:
    print("  ✅ SUCCESS - Template download works!")
else:
    print(f"  ❌ FAILED - Response: {response.content[:200]}")

print("\nTest 2: Template download (CSV)")
response = client.get('/API/import/template/', {'type': 'categories', 'format': 'csv'})
print(f"  Status: {response.status_code}")
print(f"  Content-Type: {response.get('Content-Type', 'N/A')}")
if response.status_code == 200:
    print("  ✅ SUCCESS - CSV Template download works!")
else:
    print(f"  ❌ FAILED - Response: {response.content[:200]}")

print("\nTest 3: Try with trailing slash variations")
for url in ['/API/import/template/', '/API/import/template']:
    response = client.get(url, {'type': 'products', 'format': 'excel'})
    print(f"  URL: {url} -> Status: {response.status_code}")

print("\nDone!")
