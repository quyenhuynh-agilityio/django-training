#!/usr/bin/env bash
# build.sh - Render build script for UV projects

set -o errexit  # Exit on error

echo "🚀 Starting build process..."

# Install UV if not present
echo "📦 Installing UV..."
pip install uv

# Install dependencies using UV
echo "📦 Installing dependencies with UV..."
uv sync --frozen

# Collect static files
echo "📁 Collecting static files..."
uv run python manage.py collectstatic --no-input

# Run database migrations
echo "🗄️  Running database migrations..."
uv run python manage.py migrate --no-input

echo "✅ Build complete!"
