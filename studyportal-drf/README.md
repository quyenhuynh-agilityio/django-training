# Student Course Management System - REST API

A comprehensive Django REST Framework (DRF) based API system for managing students, courses, instructors, and enrollments. This system provides RESTful APIs to support mobile applications (e.g., React Native) with full authentication, authorization, and business logic validation.

## 📋 Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Features](#features)
- [API Endpoints](#api-endpoints)
- [Getting Started](#getting-started)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Authentication](#authentication)
- [Documentation](#documentation)

## 🎯 Overview

This project extends the "Student Course Management System" by building, testing, and documenting REST APIs using Django Rest Framework. The system supports:

- **Student Management**: Registration, authentication, profile management, course enrollment
- **Course Management**: CRUD operations with filtering, search, and pagination
- **Instructor Management**: Course creation, student roster management
- **Enrollment Management**: Enroll/leave courses with business rule validation
- **Category Management**: Course categorization and filtering

## 🛠 Tech Stack

## 📚 Developer Documentation

- Module flows (models → serializers → viewsets): `docs/MODULE_FLOWS.md`

- **Python**: 3.13+
- **Framework**: Django 5.1.5
- **API Framework**: Django REST Framework 3.15.2+
- **Authentication**: JWT (Simple JWT 5.3.1+)
- **Database**: PostgreSQL (production), SQLite in-memory (tests)
- **Package Manager**: uv
- **API Documentation**: drf-spectacular (Swagger/OpenAPI)
- **Testing**: pytest, pytest-django, pytest-cov
- **Code Quality**: ruff, pre-commit hooks

## ✨ Features

### Student Management
- ✅ Student registration with email/password
- ✅ JWT-based authentication (login/logout)
- ✅ Password reset via email
- ✅ Profile viewing and updating
- ✅ View enrolled courses with pagination
- ✅ Enroll in or leave active courses
- ✅ Filter/search enrolled courses
- ✅ Cannot enroll in inactive/unavailable courses

### Course Management
- ✅ Anonymous/Student can view course list (with pagination)
- ✅ Anonymous/Student can view course details
- ✅ Filter courses by category, name, status
- ✅ Search courses by title, course code, description
- ✅ Instructors can create/update courses
- ✅ Instructors can view enrolled students in their courses
- ✅ Cannot disable courses in progress with enrolled students
- ✅ Soft delete (mark inactive) instead of hard delete

### Instructor Management
- ✅ Instructors can login to the system
- ✅ Instructors can view and update their profile
- ✅ Instructors can create or update courses
- ✅ Instructors can view all enrolled students in their courses
- ✅ Admin dashboard for instructor management (view, create, edit, delete, filter)
- ✅ Set instructor to a course via admin

### Category Management
- ✅ Public read-only access to active categories
- ✅ Search and ordering support
- ✅ Used for course filtering

### Security & Permissions
- ✅ Role-based access control (Student, Instructor, Admin)
- ✅ JWT token authentication
- ✅ Token blacklisting on logout
- ✅ Password strength validation
- ✅ Email normalization and uniqueness validation

### Testing
- ✅ 134 unit tests with 86% code coverage
- ✅ Tests use SQLite in-memory database (isolated from PostgreSQL)
- ✅ Comprehensive test coverage for models, serializers, viewsets, permissions
- ✅ Test fixtures and factories for easy test data creation

## 🔌 API Endpoints

### Authentication (`/api/v1/users/auth/`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/register/` | Register new student account | No |
| POST | `/login/` | Login and get JWT tokens | No |
| POST | `/logout/` | Logout and blacklist refresh token | Yes |
| GET | `/me/` | Get current user profile | Yes |
| PUT/PATCH | `/me/` | Update current user profile | Yes |
| POST | `/password-change/` | Change password (authenticated) | Yes |
| POST | `/password-reset/` | Request password reset email | No |
| POST | `/password-reset-confirm/` | Confirm password reset with token | No |

### Courses (`/api/v1/courses/courses/`)

| Method | Endpoint | Description | Auth Required | Role |
|--------|----------|-------------|---------------|------|
| GET | `/` | List courses (paginated) | No | Any |
| POST | `/` | Create new course | Yes | Instructor |
| GET | `/{id}/` | Get course details | No | Any |
| PUT/PATCH | `/{id}/` | Update course | Yes | Instructor (owner) |
| DELETE | `/{id}/` | Soft delete course | Yes | Instructor (owner) |
| GET | `/{id}/enrolled-students/` | List enrolled students | Yes | Instructor (owner) |

**Query Parameters:**
- `?category={uuid}` - Filter by category
- `?status={status}` - Filter by status (draft, active, in_progress, completed)
- `?search={query}` - Search in title, course_code, description
- `?my_courses=true` - Show only instructor's courses (instructors only)
- `?ordering={field}` - Order by field (title, created_at, enrolled_count)
- `?page={number}` - Pagination

### Categories (`/api/v1/categories/categories/`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/` | List active categories | No |
| GET | `/{id}/` | Get category details | No |

**Query Parameters:**
- `?search={query}` - Search category names
- `?ordering={field}` - Order by field (name, created_at)

### Enrollments (`/api/v1/enrollments/students/enrollments/`)

| Method | Endpoint | Description | Auth Required | Role |
|--------|----------|-------------|---------------|------|
| GET | `/` | List my enrollments (paginated) | Yes | Student |
| GET | `/{id}/` | Get enrollment details | Yes | Student |
| POST | `/enroll/` | Enroll in a course | Yes | Student |
| DELETE | `/{id}/leave/` | Leave a course | Yes | Student |

**Query Parameters:**
- `?search={query}` - Search in course title/code
- `?status={status}` - Filter by status (active, completed, dropped)
- `?is_active={bool}` - Filter by active status
- `?ordering={field}` - Order by field (created_at, updated_at)

### API Documentation

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/schema/` | OpenAPI schema (JSON) |
| GET | `/api/docs/` | Swagger UI interactive documentation |

## 🚀 Getting Started

### Prerequisites

- Python 3.13+
- PostgreSQL (for production/development)
- [uv](https://docs.astral.sh/uv) package manager

### Installation

1. **Clone the repository**
```bash
cd studyportal-drf
```

2. **Create environment file**
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```env
# Database Configuration
DB_NAME=studyportal_db
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# Redis / Celery (defaults match settings.base)
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Django Configuration
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

**Generate a secure SECRET_KEY:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

3. **Install dependencies**
```bash
uv sync
```

4. **Run migrations**
```bash
uv run python manage.py migrate
```

5. **Create superuser**
```bash
uv run python manage.py createsuperuser
```

6. **Start development server**
```bash
uv run python manage.py runserver
```

Run with a specific settings module (and it will auto-load the matching `.env.<env>` if present):
```bash
# Local (config.settings.local)
DJANGO_SETTINGS_MODULE=config.settings.local uv run python manage.py runserver

# Production settings (config.settings.production)
DJANGO_SETTINGS_MODULE=config.settings.production uv run python manage.py runserver
```

The server will start at `http://localhost:8000/`

### Background workers: Redis, Celery, Celery Beat

This project uses **Redis** as cache and Celery broker/result backend, plus **Celery** and
**Celery Beat** for background jobs (emails, notifications, reports).

1. **Start Redis** (choose one):

   - Using Homebrew (macOS):

     ```bash
     brew install redis
     brew services start redis
     ```

   - Or using Docker:

     ```bash
     docker run --name studyportal-redis -p 6379:6379 -d redis:7
     ```

2. **Start Celery worker** (in a new terminal):

   ```bash
   cd studyportal-drf
   DJANGO_SETTINGS_MODULE=config.settings.local \
     uv run celery -A config worker -l info
   ```

3. **Start Celery Beat scheduler** (in another terminal):

   ```bash
   cd studyportal-drf
   DJANGO_SETTINGS_MODULE=config.settings.local \
     uv run celery -A config beat -l info
   ```

   Celery Beat uses the schedules defined in `CELERY_BEAT_SCHEDULE` inside
   `config/settings/base.py` (e.g. weekly cleanup, monthly reports).

4. **Optional: Monitor tasks with Flower** (dev only):

   ```bash
   cd studyportal-drf
   DJANGO_SETTINGS_MODULE=config.settings.local \
     uv run celery -A config flower --port=5555
   ```

   Then open `http://localhost:5555` to see task status and history.

## 🧪 Testing

### Test Configuration

Tests use **SQLite in-memory database** (`:memory:`) to ensure complete isolation from PostgreSQL. The test database is automatically created and destroyed for each test run.

**Important**: Tests will NEVER touch your PostgreSQL database.

### Run Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/users/test_views.py

# Run with coverage report
uv run pytest --cov=users --cov=courses --cov=categories --cov=enrollments --cov=core --cov-report=term-missing

# Generate HTML coverage report
uv run pytest --cov=users --cov=courses --cov=categories --cov=enrollments --cov=core --cov-report=html
```

Then open `htmlcov/index.html` in your browser.

### Test Coverage

Current test coverage: **86%**

- **134 tests passing**
- **0 tests failing**
- Comprehensive coverage of models, serializers, viewsets, permissions, and business logic

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures (create_user, create_course, etc.)
├── users/
│   ├── test_models.py       # User model tests
│   ├── test_serializers.py  # Authentication serializer tests
│   ├── test_views.py        # View tests (login, logout)
│   └── test_bases.py        # Base class tests
├── courses/
│   ├── test_models.py       # Course model tests
│   ├── test_serializers.py  # Course serializer tests
│   ├── test_viewsets.py     # Course API tests
│   ├── test_permissions.py  # Permission tests
│   └── test_filters.py      # Filter tests
├── categories/
│   ├── test_models.py       # Category model tests
│   ├── test_serializers.py  # Category serializer tests
│   └── test_viewsets.py     # Category API tests
├── enrollments/
│   ├── test_models.py       # Enrollment model tests
│   ├── test_serializers.py  # Enrollment serializer tests
│   └── test_viewsets.py     # Enrollment API tests
└── core/
    ├── test_api_views.py    # Common viewset tests
    └── test_course_queries.py # Query function tests
```

## 📁 Project Structure

```
studyportal-drf/
├── users/                    # User authentication & management
│   ├── api/
│   │   ├── serializers.py   # Auth serializers (register, login, password reset)
│   │   ├── viewsets.py      # AuthViewSet (all auth endpoints)
│   │   ├── bases.py         # Base classes (email normalization, password confirmation)
│   │   └── urls.py          # API routes
│   ├── models.py            # Custom User model (email login, roles)
│   ├── admin.py             # Admin interface for user management
│   └── signals.py           # User signals (deactivate enrollments)
│
├── courses/                  # Course management
│   ├── api/
│   │   ├── serializers.py   # Course serializers (list, detail, write)
│   │   ├── viewsets.py       # CourseViewSet (CRUD + enrolled_students)
│   │   ├── permissions.py   # IsInstructorOrReadOnly, IsStudent
│   │   ├── filters.py       # CourseFilter (category, status, search)
│   │   └── urls.py          # API routes
│   ├── models.py            # Course model (status, categories, instructor)
│   ├── admin.py             # Admin interface with bulk actions
│   └── signals.py           # Course signals (deactivate enrollments)
│
├── categories/               # Course categories
│   ├── api/
│   │   ├── serializers.py   # CategorySerializer
│   │   ├── viewsets.py      # CategoryViewSet (read-only)
│   │   └── urls.py          # API routes
│   └── models.py            # Category model
│
├── enrollments/             # Student enrollments
│   ├── api/
│   │   ├── serializers.py   # Enrollment serializers
│   │   ├── viewsets.py      # StudentEnrolledCoursesViewSet
│   │   └── urls.py          # API routes
│   └── models.py            # Enrollment model (validation, unenroll)
│
├── core/                     # Shared utilities
│   ├── api_views.py         # CommonViewSet (standardized responses)
│   └── course_queries.py    # Query functions for course listing
│
├── config/                   # Django configuration
│   ├── settings/
│   │   ├── base.py          # Base settings (PostgreSQL)
│   │   ├── local.py         # Local development settings
│   │   ├── test.py          # Test settings (SQLite in-memory)
│   │   └── production.py    # Production settings
│   └── urls.py              # Root URL configuration
│
├── tests/                    # Test suite
│   ├── conftest.py          # Pytest fixtures
│   └── [app]/               # App-specific tests
│
├── utils/                    # Utility modules
│   ├── serializers.py       # Shared serializer base classes
│   └── admin/               # Admin utilities
│
├── manage.py
├── pytest.ini                # Pytest configuration
├── pyproject.toml            # Project dependencies
└── README.md
```

## 🔐 Authentication

### JWT Token Authentication

The system uses JWT (JSON Web Tokens) for API authentication:

1. **Register/Login** to obtain tokens:
```bash
POST /api/v1/users/auth/login/
{
  "email": "student@example.com",
  "password": "password123"
}

Response:
{
  "message": "Login successful",
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": { ... }
}
```

2. **Include token in requests**:
```bash
Authorization: Bearer <access_token>
```

3. **Refresh token** when access token expires:
```bash
POST /api/v1/users/auth/token/refresh/
{
  "refresh": "<refresh_token>"
}
```

### Role-Based Access Control

- **Student**: Can enroll in courses, view own enrollments
- **Instructor**: Can create/update own courses, view enrolled students
- **Admin**: Full access via Django admin

## 📚 Documentation

### Interactive API Documentation

Access Swagger UI at: `http://localhost:8000/api/docs/`

Features:
- Interactive API testing
- Request/response examples
- Authentication testing
- Schema validation

### OpenAPI Schema

Download OpenAPI schema at: `http://localhost:8000/api/schema/`

## 🎯 Access Points

- **Django Admin**: http://localhost:8000/admin/
- **API Documentation (Swagger)**: http://localhost:8000/api/docs/
- **API Schema (OpenAPI)**: http://localhost:8000/api/schema/
- **API Root**: http://localhost:8000/api/v1/

## 🔧 Common Commands

### Package Management
```bash
# Add dependency
uv add <package-name>

# Add dev dependency
uv add --dev <package-name>

# Update dependencies
uv sync
```

### Django Management
```bash
# Create migrations
uv run python manage.py makemigrations

# Apply migrations
uv run python manage.py migrate

# Create superuser
uv run python manage.py createsuperuser

# Django shell
uv run python manage.py shell
```

### Code Quality
```bash
# Run linter
uv run ruff check

# Format code
uv run ruff format

# Run pre-commit hooks
pre-commit run --all-files
```

## 🐛 Troubleshooting

### Database Issues

**Tests affecting production database?**
- Tests use SQLite in-memory (`:memory:`) - completely isolated
- Verify with: `python verify_test_isolation.py` (if script exists)
- Check `config/settings/test.py` uses SQLite, not PostgreSQL

**Database connection errors:**
- Ensure PostgreSQL is running: `pg_isready`
- Verify credentials in `.env`
- Check database exists: `psql -l`

### Test Issues

**Import errors:**
- Ensure virtual environment is activated: `source venv/bin/activate`
- Install dependencies: `uv sync`
- Check `DJANGO_SETTINGS_MODULE` is set to `config.settings.test`

## 📊 Project Statistics

- **Total Tests**: 134
- **Test Coverage**: 86%
- **API Endpoints**: 20+
- **Models**: 4 (User, Course, Category, Enrollment)
- **ViewSets**: 4 (Auth, Course, Category, Enrollment)
- **Serializers**: 15+
- **Permissions**: Role-based (Student, Instructor, Admin)

## 📝 License

MIT License

## 👥 Author

Quyen Huynh - quyen.huynh@asnet.com.vn

## 🔗 Additional Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Simple JWT](https://django-rest-framework-simplejwt.readthedocs.io/)
- [drf-spectacular](https://drf-spectacular.readthedocs.io/)
- [pytest-django](https://pytest-django.readthedocs.io/)
- [uv Documentation](https://docs.astral.sh/uv/)
