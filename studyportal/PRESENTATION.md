# Study Portal - Practice Project Presentation

## 📋 Agenda

1. **Project Overview**
2. **Architecture & Tech Stack**
3. **Core Features Implemented**
4. **Database Models & Design**
5. **Django Apps Structure**
6. **Key Implementation Details**
7. **Admin Interface**
8. **Frontend Features**
9. **Development Practices**
10. **What I Learned**

---

## 1. Project Overview

**Study Portal** is a Student Course Management System built with Django that allows users to:
- Browse and search courses
- Filter courses by category
- Enroll in courses
- View enrolled courses
- Manage courses through Django Admin

---

## 2. Architecture & Tech Stack

### Backend
- **Python 3.13+**
- **Django 5.1.4** - Web framework
- **Django REST Framework 3.15.2** - API support (ready for future use)
- **PostgreSQL** - Database (via psycopg)

### Development Tools
- **uv** - Modern Python package manager
- **pre-commit** - Git hooks for code quality
- **ruff** - Fast Python linter
- **coverage** - Test coverage reporting

### Configuration
- **python-dotenv** - Environment variable management
- **django-environ** - Enhanced environment configuration

---

## 3. Core Features Implemented

### ✅ User Authentication
- Custom user model with UUID primary keys
- Login/logout functionality
- Session-based authentication
- Protected routes with `@login_required` decorator

### ✅ Course Management
- Course listing with pagination (3 courses per page)
- Search functionality (title-based)
- Category filtering
- Course details (title, description, category, video/image URLs)
- Active/inactive course status
- Soft delete functionality

### ✅ Enrollment System
- User-course enrollment (many-to-many relationship)
- Prevent duplicate enrollments (unique constraint)
- View enrolled courses
- Soft delete enrollments

### ✅ Admin Interface
- Django Admin integration for all models
- Custom admin classes with:
  - List display customization
  - Filtering and search
  - Bulk soft delete actions
  - Pagination

---

## 4. Database Models & Design

### User Model (`accounts.User`)
```python
- UUID primary key (instead of auto-increment integer)
- Extends AbstractUser
- Soft delete flag (is_deleted)
- Custom table name: "user"
```

**Why UUID?**
- Better for distributed systems
- More secure (no sequential IDs)
- Works well with microservices

### Course Model (`courses.Course`)
```python
- UUID primary key
- title, course_code, description
- category (for filtering)
- video_url, image_url (optional media)
- is_active, is_deleted (status flags)
- created_at, updated_at (timestamps)
- Ordered by title
```

### Enrollment Model (`enrollments.Enrollment`)
```python
- UUID primary key
- ForeignKey to User
- ForeignKey to Course
- enrolled_at timestamp
- is_deleted (soft delete)
- Unique constraint: (user, course)
- Ordered by enrollment date (newest first)
```

**Design Decisions:**
- Soft delete pattern for data preservation
- UUID for all primary keys (consistency)
- Unique constraint prevents duplicate enrollments

---

## 5. Django Apps Structure

### App Organization
```
studyportal/
├── accounts/          # User authentication & custom user model
├── courses/           # Course management
├── enrollments/       # Enrollment system
├── core/              # Shared utilities (if needed)
└── config/            # Project settings & configuration
```

### URL Routing
- `/` - Course list (homepage)
- `/accounts/login/` - User login
- `/accounts/logout/` - User logout
- `/enroll/<course_id>/` - Enroll in a course
- `/enrollments/my-courses/` - View enrolled courses
- `/admin/` - Django Admin interface

---

## 6. Key Implementation Details

### Search & Filtering (`courses/views.py`)
- **Search**: Case-insensitive title search using `title__icontains`
- **Category Filter**: Dropdown filtering by course category
- **Combined Logic**: Search and category work together
- **Default Category**: Auto-selects first category if none selected

### Pagination
- 3 courses per page
- Works with search and filtering
- Uses Django's `Paginator` class

### Enrollment Logic
```python
Enrollment.objects.get_or_create(
    user=request.user,
    course=course,
    defaults={"is_deleted": False}
)
```
- Prevents duplicate enrollments
- Uses `get_or_create` for atomic operation

### CSRF Protection
- `@csrf_protect` decorator on POST views
- Django's built-in CSRF middleware enabled
- Secure form submissions

### Authentication Flow
1. User visits protected route
2. Redirected to `/accounts/login/` if not authenticated
3. After login, redirected to homepage
4. Session maintained via Django's session framework

---

## 7. Admin Interface

### Course Admin (`courses/admin.py`)
- **List Display**: title, category, is_active, is_deleted, created_at
- **Filters**: category, is_active, is_deleted
- **Search**: title, category
- **Actions**: Soft delete selected courses
- **Pagination**: 20 items per page

### Enrollment Admin (`enrollments/admin.py`)
- **List Display**: user, course, enrolled_at, is_deleted
- **Filters**: course, is_deleted
- **Search**: username, course title
- **Actions**: Soft delete selected enrollments

### Benefits
- Quick data management
- Bulk operations
- No need for custom CRUD views
- Built-in authentication and permissions

---

## 8. Frontend Features

### Templates Structure
```
templates/
├── base.html              # Base template with navbar & footer
├── accounts/
│   └── login.html         # Login form
├── courses/
│   └── course_list.html    # Course listing with cards
└── partials/
    ├── navbar.html        # Navigation bar
    └── footer.html        # Footer
```

### UI Features
- Responsive design
- Course cards with images
- Search bar
- Category filter dropdown
- Pagination controls
- Enrollment status indicators
- Login/logout links in navbar

### Template Reusability
- Base template for consistent layout
- Partial templates (navbar, footer)
- Shared course list template for both:
  - All courses page
  - Enrolled courses page

---

## 9. Development Practices

### Code Quality
- **Pre-commit hooks**: Automated linting before commits
- **Ruff linter**: Fast Python linting (E, F codes)
- **Code formatting**: Consistent style

### Environment Management
- `.env` file for sensitive data
- Environment-based configuration
- No hardcoded secrets
- Database credentials externalized

### Testing Setup
- Coverage tool configured
- HTML coverage reports
- Test structure in place

### Dependency Management
- **uv**: Modern, fast package manager
- `pyproject.toml` for dependencies
- Separate dev dependencies
- Lock file for reproducible builds

### Project Structure
- Clean separation of concerns
- Modular app design
- Reusable components
- Follows Django best practices

---

## 10. What I Learned

### Technical Skills
1. **Django Fundamentals**
   - Models, Views, URLs, Templates
   - Custom user model
   - Admin customization

2. **Database Design**
   - UUID primary keys
   - Foreign key relationships
   - Unique constraints
   - Soft delete pattern

3. **Security**
   - CSRF protection
   - Authentication decorators
   - Session management

4. **Modern Python Tooling**
   - uv package manager
   - pre-commit hooks
   - Environment configuration

### Best Practices
- Modular app structure
- Environment-based configuration
- Code quality tools
- Soft delete for data preservation
- UUID for primary keys

### Future Enhancements
- REST API endpoints (DRF already included)
- User registration
- Course reviews/ratings
- Progress tracking
- Email notifications
- Payment integration

---

## 📊 Project Statistics

- **Apps**: 4 (accounts, courses, enrollments, core)
- **Models**: 3 (User, Course, Enrollment)
- **Views**: 5 (login, logout, course_list, enroll_course, enrolled_courses)
- **URL Patterns**: 8+
- **Templates**: 4+
- **Migrations**: 6+ (including initial migrations)

---

## 🎯 Key Takeaways

1. **Clean Architecture**: Well-organized Django apps with clear responsibilities
2. **Modern Tooling**: Using uv, pre-commit, and ruff for better development experience
3. **Security First**: CSRF protection, authentication, and proper access control
4. **Data Integrity**: Soft delete pattern preserves data while allowing "deletion"
5. **Scalability**: UUID primary keys and proper database design for future growth
6. **User Experience**: Search, filtering, pagination, and clear navigation

---

## 🚀 How to Run

1. **Setup Environment**
   ```bash
   uv sync
   cp .env.example .env  # Configure database
   ```

2. **Database Setup**
   ```bash
   uv run python manage.py migrate
   uv run python manage.py createsuperuser
   ```

3. **Run Server**
   ```bash
   uv run python manage.py runserver
   ```

4. **Access**
   - Homepage: `http://localhost:8000/`
   - Admin: `http://localhost:8000/admin/`

---

## 📝 Notes for Presentation

- **Duration**: 10-15 minutes recommended
- **Focus Areas**:
  - Architecture decisions (UUID, soft delete)
  - Feature implementation (search, filtering, enrollment)
  - Admin customization
  - Development practices
- **Demo**: Show live application with course browsing, enrollment, and admin interface

---

*This presentation document provides a comprehensive overview of the Study Portal practice project.*
