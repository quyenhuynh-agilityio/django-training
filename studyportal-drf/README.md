# Study Portal Practice

A Student Course Management System built with Django for managing students, courses, and enrollments.

## Tech Stack

- **Python**: 3.13+
- **Framework**: Django with custom user model (`accounts.User`)
- **API**: Django REST Framework with Simple JWT authentication
- **Database**: PostgreSQL (production), SQLite (tests)
- **Package Manager**: uv
- **Code Quality**: pre-commit hooks

## Prerequisites

Before starting, ensure you have:

- [Python 3.13+](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv) - Install with: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- [PostgreSQL](https://www.postgresql.org/download/) - Running instance with a database created
- [pre-commit](https://pre-commit.com/) (optional but recommended)

## Getting Started

### 1. Clone and Navigate to Project

```bash
cd studyportal-drf
```

### 2. Environment Configuration

Create your environment file from the example:

```bash
cp .env.example .env
```

Edit `.env` and configure the following variables:

```env
# Database Configuration
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_HOST=localhost
DB_PORT=5432

# Django Configuration
SECRET_KEY=your-secret-key-here-generate-a-secure-one
DEBUG=True

# Optional: For production
ALLOWED_HOSTS=localhost,127.0.0.1
```

**Generate a secure SECRET_KEY:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 3. Install Dependencies

Create virtual environment and install all dependencies:

```bash
uv sync
```

This creates a `.venv` directory and installs all required packages.

### 4. Set Up Git Hooks (Recommended)

Install pre-commit hooks for code quality checks:

```bash
pre-commit install
```

### 5. Database Setup

Run migrations to create database tables:

```bash
uv run python manage.py migrate
```

### 6. Create Superuser

Create an admin account to access Django admin panel:

```bash
uv run python manage.py createsuperuser
```

Follow the prompts to set username, email, and password.

### 7. Start Development Server

```bash
uv run python manage.py runserver
```

The server will start at `http://localhost:8000/`

## Access Points

- **Django Admin**: http://localhost:8000/admin/
- **API Authentication**: http://localhost:8000/api/v1/auth/
- **API Root**: http://localhost:8000/api/v1/

## Running Tests

The project uses pytest with a separate test settings module (`config.settings.test`).

### Run All Tests

```bash
uv run pytest
```

### Run Tests with Verbose Output

```bash
uv run pytest -v
```

### Run Specific Test File

```bash
uv run pytest path/to/test_file.py
```

### Run Tests with Coverage

```bash
uv run pytest --cov=. --cov-report=term-missing
```

### Generate HTML Coverage Report

```bash
uv run pytest --cov=. --cov-report=html
```

Then open `htmlcov/index.html` in your browser.

### Alternative: Django Test Runner

```bash
uv run python manage.py test
```

## Project Structure

```
studyportal-drf/
├── users/       # Custom user model and authentication
├── courses/        # Course management
├── categories/     # Course categories
├── enrollments/    # Student enrollments
├── core/          # Shared utilities and base classes
├── config/        # Project settings
│   └── settings/
│       ├── base.py
│       ├── local.py
│       └── test.py
├── manage.py
├── .env
└── pyproject.toml
```

## Common Commands

### Package Management

```bash
# Add a production dependency
uv add <package-name>

# Add a development dependency
uv add --dev <package-name>

# Update dependencies
uv sync

# Sync without dev dependencies (production)
uv sync --no-group dev

# Remove a package
uv remove <package-name>
```

### Django Management

```bash
# Create a new app
uv run python manage.py startapp <app-name>

# Make migrations
uv run python manage.py makemigrations

# Apply migrations
uv run python manage.py migrate

# Create superuser
uv run python manage.py createsuperuser

# Collect static files
uv run python manage.py collectstatic

# Open Django shell
uv run python manage.py shell

# Show all URLs
uv run python manage.py show_urls  # if django-extensions installed
```

### Code Quality

```bash
# Run pre-commit on all files
pre-commit run --all-files

# Run ruff linter
uv run ruff check

# Run ruff formatter
uv run ruff format

# Run ruff with auto-fix
uv run ruff check --fix
```

## Development Workflow

1. **Create a new branch** for your feature/fix
2. **Make your changes**
3. **Run tests** to ensure nothing breaks: `uv run pytest`
4. **Check code quality**: `pre-commit run --all-files`
5. **Commit your changes** (pre-commit hooks will run automatically)
6. **Push and create a pull request**

## Troubleshooting

### Virtual Environment Issues

If you encounter issues with the virtual environment:

```bash
# Remove existing venv
rm -rf .venv

# Reinstall
uv sync
```

### Database Connection Issues

- Ensure PostgreSQL is running: `pg_isready`
- Verify database credentials in `.env`
- Check if database exists: `psql -l`

### Migration Issues

```bash
# Reset migrations (development only!)
uv run python manage.py migrate <app-name> zero
uv run python manage.py makemigrations
uv run python manage.py migrate
```

### Port Already in Use

```bash
# Run on different port
uv run python manage.py runserver 8001
```

## Authentication

The project uses JWT (JSON Web Tokens) for API authentication:

- **Obtain Token**: `POST /api/v1/auth/token/`
- **Refresh Token**: `POST /api/v1/auth/token/refresh/`
- **Verify Token**: `POST /api/v1/auth/token/verify/`

Include the token in API requests:
```
Authorization: Bearer <your-access-token>
```

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `DB_NAME` | PostgreSQL database name | `studyportal_db` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | `your_password` |
| `DB_HOST` | Database host | `localhost` |
| `DB_PORT` | Database port | `5432` |
| `SECRET_KEY` | Django secret key | Generate with Python |
| `DEBUG` | Debug mode | `True` or `False` |
| `ALLOWED_HOSTS` | Allowed hosts (production) | `localhost,127.0.0.1` |

## Additional Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [uv Documentation](https://docs.astral.sh/uv/)
- [pytest Documentation](https://docs.pytest.org/)
