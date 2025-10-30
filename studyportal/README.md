# Study Portal Practice
Student Course Management System built with Django for managing students, courses, and enrollments.

### Tech stack
- Python 3.13+
- Django
- Django REST Framework
- PostgreSQL
- uv (Python package/dependency manager)
- pre-commit (git hooks)

### Prerequisites
Install on your machine:
- [uv](https://docs.astral.sh/uv)
- [pre-commit](https://pre-commit.com/)
- A running PostgreSQL instance

### Environment setup
1. From the project root `studyportal`, create your environment file from the example:
   - Copy `.env.example` to `.env` and fill in your database settings: `DB_NAME`, `DB_USER`, `DB_PASS`, `DB_HOST`, `DB_PORT`.
2. Install dependencies (creates a virtual environment if missing):
   - `uv sync`
3. Install git hooks (optional but recommended):
   - `pre-commit install`

### Run the project
- Apply migrations:
  - `uv run python manage.py migrate`
- Create a superuser (to access the admin):
  - `uv run python manage.py createsuperuser`
- Start the development server:
  - `uv run python manage.py runserver`

Access:
- Admin site: `http://localhost:8000/admin/`

### Notes
- Apps included: `accounts`, `courses`, `enrollments`, `core`.
- Custom user model: `accounts.User`.
- Environment variables are loaded via `python-dotenv`.

### Useful commands
- Add a package: `uv add <package>`
- Add a dev-only package: `uv add --dev <package>`
- Sync all deps: `uv sync`
- Sync without dev deps: `uv sync --no-group dev`
- Run inside venv: `uv run <command>`
- Lint (ruff): `ruff check`

### pre-commit
- Install hooks: `pre-commit install`
- Run on all files: `pre-commit run --all-files`
