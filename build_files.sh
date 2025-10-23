#!/bin/bash

echo "Starting Django build for Vercel..."

# Try different Python commands to ensure compatibility
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ No Python interpreter found"
    exit 1
fi

echo "✅ Using Python interpreter: $PYTHON_CMD"

# Install dependencies
echo "Installing Python dependencies..."
$PYTHON_CMD -m pip install --upgrade pip
$PYTHON_CMD -m pip install -r requirements.txt

# Skip migrations for Vercel (no database)
echo "Skipping migrations for Vercel static deployment..."

# Collect static files with Vercel settings
echo "Collecting static files for Vercel..."
DJANGO_SETTINGS_MODULE=Gestion_stock.vercel_settings $PYTHON_CMD manage.py collectstatic --noinput --clear

# Copy static files to Vercel expected location
echo "Organizing static files for Vercel..."

# Check if staticfiles_build directory exists
if [ -d "staticfiles_build" ]; then
    echo "✅ staticfiles_build directory found"
    ls -la staticfiles_build/
    
    # Check if static subdirectory exists
    if [ -d "staticfiles_build/static" ]; then
        # Create the static directory that Vercel expects
        mkdir -p static
        # Copy all static files to the expected location
        cp -r staticfiles_build/static/* static/
        file_count=$(find static -type f | wc -l)
        echo "✅ Static files organized: $file_count files in 'static' directory"
        ls -la static/ | head -10
    else
        echo "⚠️  staticfiles_build/static not found, using staticfiles_build directly"
        # Use staticfiles_build as static directory
        mv staticfiles_build static
        file_count=$(find static -type f | wc -l)
        echo "✅ Static files organized: $file_count files moved to 'static' directory"
    fi
else
    echo "❌ staticfiles_build directory not found after collectstatic"
    echo "Directory contents:"
    ls -la
    exit 1
fi

echo "✅ Build completed successfully!"