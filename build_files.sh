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

# Run migrations
echo "Running Django migrations..."
$PYTHON_CMD manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
$PYTHON_CMD manage.py collectstatic --noinput --clear

# Copy static files to Vercel expected location
echo "Organizing static files for Vercel..."
if [ -d "staticfiles_build/static" ]; then
    # Create the static directory that Vercel expects
    mkdir -p static
    # Copy all static files to the expected location
    cp -r staticfiles_build/static/* static/
    file_count=$(find static -type f | wc -l)
    echo "✅ Static files organized: $file_count files in 'static' directory"
    ls -la static/ | head -10
else
    echo "❌ Static files directory not found"
    exit 1
fi

echo "✅ Build completed successfully!"