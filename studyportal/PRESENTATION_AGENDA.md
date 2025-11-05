# Study Portal - Presentation Agenda

## Quick Reference for Presentation

### 1. Project Overview (2 min)
- Student Course Management System
- Django web application
- Core features: browse, search, enroll in courses

### 2. Tech Stack (1 min)
- Python 3.13+, Django 5.1.4
- PostgreSQL database
- Modern tools: uv, pre-commit, ruff
- Environment-based configuration

### 3. Architecture (2 min)
- **4 Django Apps**: accounts, courses, enrollments, core
- **3 Models**: User (UUID), Course (UUID), Enrollment (UUID)
- **Custom User Model**: UUID primary key, soft delete
- **URL Structure**: Clean routing with app-level URLs

### 4. Key Features (3 min)
- ✅ User authentication (login/logout)
- ✅ Course listing with pagination
- ✅ Search & category filtering
- ✅ Course enrollment system
- ✅ View enrolled courses
- ✅ Django Admin integration

### 5. Database Design (2 min)
- **UUID Primary Keys**: All models use UUID instead of integers
  - Better for distributed systems
  - More secure
- **Soft Delete Pattern**: `is_deleted` flag instead of hard delete
  - Preserves data
  - Allows recovery
- **Unique Constraints**: Prevents duplicate enrollments

### 6. Implementation Highlights (3 min)
- **Search**: Case-insensitive title search
- **Filtering**: Category-based with auto-selection
- **Pagination**: 3 courses per page
- **CSRF Protection**: Secure form submissions
- **Authentication**: Session-based with decorators

### 7. Admin Interface (2 min)
- Custom admin classes for all models
- List display, filtering, search
- Bulk soft delete actions
- Efficient data management

### 8. Development Practices (1 min)
- Pre-commit hooks for code quality
- Environment variables for configuration
- Coverage testing setup
- Modern Python tooling (uv)

### 9. What I Learned (1 min)
- Django fundamentals (models, views, URLs, templates)
- Database design patterns
- Security best practices
- Modern Python development workflow

### 10. Demo (2 min)
- Show course browsing
- Demonstrate search & filtering
- Enroll in a course
- View enrolled courses
- Quick admin interface tour

---

## Talking Points

### Architecture Decisions
- Why UUID? Better scalability, security, distributed systems
- Why soft delete? Data preservation, audit trail
- Why 4 apps? Separation of concerns, modularity

### Feature Implementation
- Search uses `title__icontains` for case-insensitive matching
- Category filtering with default selection
- Pagination works seamlessly with search/filter
- Enrollment prevents duplicates with unique constraint

### Security
- CSRF protection on all POST requests
- `@login_required` for protected views
- Session-based authentication
- Environment variables for secrets

### Code Quality
- Pre-commit hooks catch issues early
- Ruff linter ensures consistency
- Coverage reports track test quality
- Clean, readable code structure

---

## Demo Flow

1. **Homepage** → Show course listing
2. **Search** → Type "python" → Show filtered results
3. **Category Filter** → Select category → Show filtered results
4. **Login** → If not logged in, show login form
5. **Enroll** → Click enroll button → Redirect to enrolled courses
6. **My Courses** → Show enrolled courses page
7. **Admin** → Quick tour of admin interface

---

## Time Allocation: ~15 minutes total

- Introduction: 2 min
- Technical details: 8 min
- Demo: 2 min
- Q&A: 3 min

---

*Use this as a quick reference during your presentation!*
