import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from django.urls import get_resolver, reverse
from django.test import Client

print("=== Testing URL Resolution ===\n")

# Test 1: Check if URLs are registered
resolver = get_resolver()
print(f"Total URL patterns in root: {len(resolver.url_patterns)}")

# Test 2: Try to find API patterns
for i, pattern in enumerate(resolver.url_patterns):
    pattern_str = str(pattern.pattern)
    if 'API' in pattern_str or pattern_str == '':
        print(f"  Pattern {i}: {pattern}")
        if hasattr(pattern, 'url_patterns'):
            print(f"    - Has {len(pattern.url_patterns)} sub-patterns")
            # Show first few sub-patterns
            for j, sub in enumerate(pattern.url_patterns[:3]):
                print(f"      {j}: {sub}")

# Test 3: Try to reverse the import URL
print("\n=== Trying to reverse URLs ===")
try:
    url = reverse('import-template')
    print(f"OK import-template URL: {url}")
except Exception as e:
    print(f"ERROR import-template: {e}")

# Test 4: Try direct HTTP request
print("\n=== Testing HTTP Request ===")
client = Client()
response = client.get('/API/import/template/', {'type': 'products', 'format': 'excel'})
print(f"Status: {response.status_code}")
print(f"Content-Type: {response.get('Content-Type', 'N/A')}")
if response.status_code != 200:
    print(f"Content: {response.content[:200]}")
else:
    print("SUCCESS!")

# Test 5: Test the test URL
response = client.get('/API/import/test/')
print(f"\nTest URL Status: {response.status_code}")
if response.status_code == 200:
    print(f"Response: {response.json()}")
