#!/bin/bash
# Define a flag environment variable (e.g., CREATE_DJANGO_SUPERUSER)
# and ensure superuser details are set
if [ "$CREATE_DJANGO_SUPERUSER" = "true" ]; then
    echo "Conditional superuser creation enabled. Proceeding without input."

    # Run the createsuperuser command with --no-input
    # Django will automatically pick up the credentials from the environment variables
    uv run python manage.py createsuperuser \
        --first_name="$CREATE_DJANGO_FIRST_NAME" \
        --last_name="$CREATE_DJANGO_LAST_NAME" \
        --no-input

    # Update the created user to set is_active=True and role=admin
    uv run python manage.py shell -c "
from django.contrib.auth import get_user_model;
import os;
User = get_user_model();
username = os.environ.get('DJANGO_SUPERUSER_USERNAME');
if username:
    user = User.objects.get(username=username);
    user.is_active = True;
    user.role = 'admin';
    user.save();
    print(f'✓ User {user.username} updated: is_active=True, role=admin');
else:
    print('⚠ DJANGO_SUPERUSER_USERNAME not set');
"
else
    echo "Conditional superuser creation skipped."
fi

# Optional: seed database with sample data (e.g. for staging/dev; set RUN_SEED_DATA=true)
if [ "${RUN_SEED_DATA:-false}" = "true" ]; then
    echo "Running seed data..."
    uv run python manage.py seed_data
    echo "Seed data completed."
else
    echo "Seed data skipped (set RUN_SEED_DATA=true to run)."
fi
