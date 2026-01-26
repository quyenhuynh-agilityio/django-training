#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "--- 📥 Pulling latest changes from GitHub ---"
git pull origin main

echo "--- 📦 Syncing dependencies with uv ---"
# uv sync ensures your .venv matches your uv.lock exactly
uv sync

echo "--- 🗄️ Running migrations ---"
uv run python manage.py migrate

echo "--- 🎨 Collecting static files for DRF ---"
# This ensures the browsable API and Admin CSS work
uv run python manage.py collectstatic --noinput

echo "--- ♻️ Reloading Web App ---"
# Touching the WSGI file forces PythonAnywhere to reload the app
touch /var/www/quyenhuynh_pythonanywhere_com_wsgi.py

echo "🚀 Deployment successful!"
