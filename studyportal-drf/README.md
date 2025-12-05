# Study Portal Practice

Student Course Management System built with Django for managing students, courses, and enrollments.

### Tech stack

- Python 3.13+
- Django (custom user model `accounts.User`)
- Django REST Framework + Simple JWT
- PostgreSQL (default), SQLite in tests
- uv (dependency manager)
- pre-commit (git hooks)

### Prerequisites

- [uv](https://docs.astral.sh/uv)
- [pre-commit](https://pre-commit.com/)
- Running PostgreSQL instance

### Environment setup

From the project root `studyportal-drf`:

1) Copy `.env.example` to `.env` and set at least: `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `SECRET_KEY`, `DEBUG`.
2) Install dependencies (creates `.venv` if missing):
   - `uv sync`
3) Install git hooks (recommended):
   - `pre-commit install`

### Run the project

The default settings module is `config.settings.local` (see `manage.py`).

- Apply migrations: `uv run python manage.py migrate`
- Create a superuser: `uv run python manage.py createsuperuser`
- Start dev server: `uv run python manage.py runserver`

Access:
- Admin: `http://localhost:8000/admin/`
- API auth routes are included under `http://localhost:8000/api/v1/auth/`

### Run tests and coverage

- Pytest (fast, uses `config.settings.test`): `uv run pytest`
- Django test runner (uses default settings): `uv run python manage.py test`
- Coverage (optional):
  - ensure dev dep: `uv add --dev coverage` (one time)
  - run with coverage: `uv run pytest --cov=. --cov-report=term-missing`
  - terminal summary: `uv run coverage report -m`
  - HTML report: `uv run coverage html` then open `htmlcov/index.html`

### Notes

- Apps: `accounts`, `courses`, `categories`, `enrollments`, `core`.
- Authentication uses JWT via `rest_framework_simplejwt`.
- Environment variables are loaded with `django-environ`.

### Useful commands

- Add a package: `uv add <package>`
- Add a dev-only package: `uv add --dev <package>`
- Sync all deps: `uv sync`
- Sync without dev deps: `uv sync --no-group dev`
- Run inside venv: `uv run <command>`
- Lint (ruff): `uv run ruff check`

### pre-commit

- Install hooks: `pre-commit install`
- Run on all files: `pre-commit run --all-files`
