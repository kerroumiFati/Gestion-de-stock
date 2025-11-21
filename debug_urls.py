import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from django.urls import get_resolver

def show_urls(urllist, depth=0):
    for entry in urllist:
        pattern = str(entry.pattern)
        if hasattr(entry, 'url_patterns'):
            print("  " * depth + pattern)
            show_urls(entry.url_patterns, depth + 1)
        else:
            name = entry.name if hasattr(entry, 'name') else ''
            print("  " * depth + f"{pattern} [{name}]")

resolver = get_resolver()
print("=== ALL URLs ===\n")
show_urls(resolver.url_patterns)
