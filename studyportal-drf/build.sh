#!/bin/bash

# Define a flag environment variable (e.g., CREATE_DJANGO_SUPERUSER)
# and ensure superuser details are set

if [ "$CREATE_DJANGO_SUPERUSER" = "true" ]; then
    echo "Conditional superuser creation enabled. Proceeding without input."

    # Run the createsuperuser command with --no-input
    # Django will automatically pick up the credentials from the environment variables
    uv run python manage.py createsuperuser --first_name="$CREATE_DJANGO_FIRST_NAME" --last_name="$CREATE_DJANGO_LAST_NAME" --no-input
else
    echo "Conditional superuser creation skipped."
fi
