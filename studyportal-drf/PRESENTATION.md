# Student Course Management System - REST API
## Project Presentation & Requirements Documentation

---

## 📋 Project Overview

### Objective
Extend the "Student Course Management System" by building, testing, and documenting REST APIs using Django Rest Framework (DRF). This phase focuses on RESTful API design and providing endpoints for the system's mobile application (e.g., a React Native app).

### Timeline
**8 days**

### Technology Stack
- **Backend**: Django 5.1.5 + Django REST Framework 3.15.2+
- **Authentication**: JWT (Simple JWT)
- **Database**: PostgreSQL (production), SQLite in-memory (tests)
- **API Documentation**: drf-spectacular (Swagger/OpenAPI)
- **Testing**: pytest, pytest-django (86% coverage)
- **Package Manager**: uv

---

## 🎯 Feature Requirements & Implementation Details

### 1. Admin Dashboard - Instructor Management

#### Requirements
- View, create, edit, delete, and filter instructors
- Set instructor to a course

#### Implementation Details

**Admin Interface Features:**
- ✅ **User Management** (`/admin/users/user/`)
  - List view with role badges (Student/Instructor/Admin)
  - Filter by role, active status, staff status
  - Search by email, username, name
  - Create/edit instructors with role assignment
  - Color-coded role badges for visual identification

- ✅ **Course-Instructor Assignment** (`/admin/courses/course/`)
  - Bulk action: "Assign instructor" to multiple courses
  - Autocomplete field for instructor selection
  - Instructor link in course list view
  - Validation: Only users with `role='instructor'` can be assigned

**Code Location:**
- `users/admin.py` - UserAdmin with role management
- `courses/admin.py` - CourseAdmin with instructor assignment actions

**API Endpoints:**
- Admin interface uses Django admin (not REST API)
- Instructors can be managed via `/admin/users/user/`
- Courses can be assigned instructors via `/admin/courses/course/`

---

### 2. Student Management APIs

#### 2.1 Student Registration

**Requirement**: Students can register, log in, and reset their password.

**Implementation:**
- ✅ **Registration Endpoint**: `POST /api/v1/users/auth/register/`
  - Creates student account with email/password
  - Validates email uniqueness
  - Validates password strength (Django validators)
  - Password confirmation matching
  - Email normalization (lowercase)
  - Username validation (alphanumeric + underscores)
  - Automatically sets `role='student'`

**Request Example:**
```json
POST /api/v1/users/auth/register/
{
  "email": "student@example.com",
  "username": "student123",
  "first_name": "John",
  "last_name": "Doe",
  "password": "StrongPass123",
  "password_confirm": "StrongPass123"
}
```

**Response:**
```json
{
  "message": "Registration successful. Please login.",
  "user": {
    "id": "uuid",
    "email": "student@example.com",
    "username": "student123",
    "first_name": "John",
    "last_name": "Doe",
    "role": "student"
  }
}
```

**Validation Rules:**
- Email must be unique
- Username must be unique and alphanumeric (with underscores)
- Password must meet Django strength requirements
- Passwords must match

**Code Location:**
- `users/api/serializers.py` - `UserRegistrationSerializer`
- `users/api/viewsets.py` - `AuthViewSet.register()`

---

#### 2.2 Student Login

**Requirement**: Students can log in to the system.

**Implementation:**
- ✅ **Login Endpoint**: `POST /api/v1/users/auth/login/`
  - Authenticates with email + password
  - Returns JWT access and refresh tokens
  - Validates user is active
  - Works for all roles (student, instructor, admin)

**Request Example:**
```json
POST /api/v1/users/auth/login/
{
  "email": "student@example.com",
  "password": "StrongPass123"
}
```

**Response:**
```json
{
  "message": "Login successful",
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": "uuid",
    "email": "student@example.com",
    "username": "student123",
    "full_name": "John Doe",
    "role": "student"
  }
}
```

**Security Features:**
- Generic error message (prevents email enumeration)
- Email normalization
- Token blacklisting on logout
- Token rotation on refresh

**Code Location:**
- `users/api/serializers.py` - `UserLoginSerializer`
- `users/api/viewsets.py` - `AuthViewSet.login()`

---

#### 2.3 Password Reset

**Requirement**: Students can reset their password.

**Implementation:**
- ✅ **Request Reset**: `POST /api/v1/users/auth/password-reset/`
  - Accepts email address
  - Generates reset token
  - Sends email with reset link (or returns token in DEBUG mode)
  - Always returns success (prevents email enumeration)

- ✅ **Confirm Reset**: `POST /api/v1/users/auth/password-reset-confirm/`
  - Validates UID and token
  - Sets new password
  - Validates password strength
  - Password confirmation matching

**Request Example:**
```json
POST /api/v1/users/auth/password-reset/
{
  "email": "student@example.com"
}

POST /api/v1/users/auth/password-reset-confirm/
{
  "uid": "base64_encoded_user_id",
  "token": "reset_token",
  "new_password": "NewStrongPass123",
  "new_password_confirm": "NewStrongPass123"
}
```

**Code Location:**
- `users/api/serializers.py` - `PasswordResetRequestSerializer`, `PasswordResetConfirmSerializer`
- `users/api/viewsets.py` - `AuthViewSet.password_reset()`, `password_reset_confirm()`

---

#### 2.4 Profile Management

**Requirement**: Students can view and update their profiles.

**Implementation:**
- ✅ **View Profile**: `GET /api/v1/users/auth/me/`
  - Returns full user profile
  - Includes: id, email, username, name, role, enrollment count
  - Read-only fields: email, username, role (security)

- ✅ **Update Profile**: `PUT/PATCH /api/v1/users/auth/me/`
  - Update first_name, last_name
  - Name validation (letters, spaces, hyphens, apostrophes)
  - Proper capitalization

**Request Example:**
```json
GET /api/v1/users/auth/me/
Authorization: Bearer <access_token>

Response:
{
  "id": "uuid",
  "email": "student@example.com",
  "username": "student123",
  "first_name": "John",
  "last_name": "Doe",
  "full_name": "John Doe",
  "role": "student",
  "is_active": true,
  "date_joined": "2024-01-01T00:00:00Z",
  "created_at": "2024-01-01T00:00:00Z"
}

PATCH /api/v1/users/auth/me/
{
  "first_name": "Jane",
  "last_name": "Smith"
}
```

**Code Location:**
- `users/api/serializers.py` - `UserProfileSerializer`
- `users/api/viewsets.py` - `AuthViewSet.me()`

---

#### 2.5 View Enrolled Courses

**Requirement**: Students can see their enrolled courses (with pagination).

**Implementation:**
- ✅ **List Enrollments**: `GET /api/v1/enrollments/students/enrollments/`
  - Returns paginated list of student's enrollments
  - Includes course details (title, code, instructor, categories)
  - Shows enrollment status and dates
  - Default pagination: 10 per page
  - Only shows active enrollments by default

**Request Example:**
```json
GET /api/v1/enrollments/students/enrollments/?page=1
Authorization: Bearer <access_token>

Response:
{
  "count": 5,
  "next": "http://localhost:8000/api/v1/enrollments/students/enrollments/?page=2",
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "course": {
        "id": "uuid",
        "title": "Python Programming",
        "course_code": "PY101",
        "instructor": {
          "id": "uuid",
          "full_name": "Dr. Smith"
        },
        "categories": ["Backend", "Programming"]
      },
      "status": "active",
      "is_active": true,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

**Query Parameters:**
- `?page={number}` - Pagination
- `?search={query}` - Search in course title/code
- `?status={status}` - Filter by status (active, completed, dropped)
- `?is_active={bool}` - Filter by active status
- `?ordering={field}` - Sort (created_at, updated_at)

**Code Location:**
- `enrollments/api/viewsets.py` - `StudentEnrolledCoursesViewSet.list()`
- `enrollments/api/serializers.py` - `EnrollmentSerializer`

---

#### 2.6 Enroll in Course

**Requirement**: Students can enroll in or leave an active course.

**Implementation:**
- ✅ **Enroll**: `POST /api/v1/enrollments/students/enrollments/enroll/`
  - Validates course exists and is active
  - Validates course status is 'active' (not draft/in_progress)
  - Validates course is not full
  - Prevents duplicate enrollments
  - Uses database locking to prevent race conditions
  - Creates enrollment with status='active'

**Request Example:**
```json
POST /api/v1/enrollments/students/enrollments/enroll/
{
  "course_id": "123e4567-e89b-12d3-a456-426614174000"
}

Response:
{
  "message": "Successfully enrolled in course",
  "data": {
    "id": "uuid",
    "course": { ... },
    "status": "active",
    "is_active": true
  }
}
```

**Validation Rules:**
- Course must exist
- Course must be active (`is_active=True`)
- Course status must be 'active' (not draft/in_progress)
- Course must not be full (if max_students set)
- Student must not already be enrolled
- Only students can enroll (role='student')

**Error Responses:**
- `400`: Course not found, course inactive, course full, already enrolled
- `403`: Not a student role

**Code Location:**
- `enrollments/api/viewsets.py` - `StudentEnrolledCoursesViewSet.enroll()`
- `enrollments/api/serializers.py` - `EnrollmentCreateSerializer`
- `enrollments/models.py` - `Enrollment.clean()` validation

---

#### 2.7 Leave Course

**Requirement**: Students can leave a course.

**Implementation:**
- ✅ **Leave Course**: `DELETE /api/v1/enrollments/students/enrollments/{id}/leave/`
  - Marks enrollment as inactive
  - Sets status to 'dropped'
  - Preserves enrollment record for history
  - Only student can leave their own enrollment

**Request Example:**
```json
DELETE /api/v1/enrollments/students/enrollments/{enrollment_id}/leave/
Authorization: Bearer <access_token>

Response:
{
  "message": "Successfully left the course",
  "data": {
    "enrollment_id": "uuid",
    "status": "dropped"
  }
}
```

**Code Location:**
- `enrollments/api/viewsets.py` - `StudentEnrolledCoursesViewSet.leave()`
- `enrollments/models.py` - `Enrollment.unenroll()`

---

#### 2.8 Filter/Search Enrolled Courses

**Requirement**: Students can filter/search enrolled courses.

**Implementation:**
- ✅ **Search**: `?search={query}` - Searches in course title and course code
- ✅ **Filter by Status**: `?status={active|completed|dropped}`
- ✅ **Filter by Active**: `?is_active={true|false}`
- ✅ **Ordering**: `?ordering={-created_at|created_at|-updated_at|updated_at}`

**Request Example:**
```json
GET /api/v1/enrollments/students/enrollments/?search=python&status=active&ordering=-created_at
```

**Code Location:**
- `enrollments/api/viewsets.py` - `StudentEnrolledCoursesViewSet` with filter backends

---

#### 2.9 Cannot Enroll in Inactive/Unavailable Courses

**Requirement**: Students cannot enroll in inactive/not available courses.

**Implementation:**
- ✅ **Validation in Enrollment Model**:
  - Course must be `is_active=True`
  - Course status must be `STATUS_ACTIVE` (not draft/in_progress/completed)
  - Course must not be full (if max_students set)

**Validation Code:**
```python
# enrollments/models.py
def clean(self):
    if not self.course.is_active:
        raise ValidationError('This course is not active.')
    if self.course.status != Course.STATUS_ACTIVE:
        raise ValidationError('Course is not open for enrollment.')
    if self.course.is_full:
        raise ValidationError('Course has reached maximum capacity.')
```

**Code Location:**
- `enrollments/models.py` - `Enrollment.clean()`
- `enrollments/api/serializers.py` - `EnrollmentCreateSerializer.validate()`

---

### 3. Course Management APIs

#### 3.1 View Course List

**Requirement**: Anonymous/Student can view list courses (with pagination).

**Implementation:**
- ✅ **List Courses**: `GET /api/v1/courses/courses/`
  - Public access (no authentication required)
  - Paginated results (10 per page)
  - Role-based filtering:
    - Anonymous: Only active courses with status='active'
    - Authenticated: All active courses
    - Instructors: Can filter to own courses with `?my_courses=true`

**Request Example:**
```json
GET /api/v1/courses/courses/?page=1

Response:
{
  "count": 25,
  "next": "http://localhost:8000/api/v1/courses/courses/?page=2",
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "title": "Python Programming",
      "course_code": "PY101",
      "description": "Learn Python...",
      "instructor": {
        "id": "uuid",
        "full_name": "Dr. Smith"
      },
      "categories": ["Backend", "Programming"],
      "status": "active",
      "is_active": true,
      "enrolled_count": 15,
      "max_students": 30,
      "is_full": false,
      "can_enroll": true,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

**Computed Fields:**
- `enrolled_count` - Number of active enrollments
- `is_full` - Whether course reached max capacity
- `can_enroll` - Whether enrollment is currently allowed

**Code Location:**
- `courses/api/viewsets.py` - `CourseViewSet.list()`
- `courses/api/serializers.py` - `CourseListSerializer`

---

#### 3.2 View Course Detail

**Requirement**: Anonymous/Student can view course detail.

**Implementation:**
- ✅ **Course Detail**: `GET /api/v1/courses/courses/{id}/`
  - Public access
  - Full course information
  - Includes category names as comma-separated string
  - Includes all computed fields

**Request Example:**
```json
GET /api/v1/courses/courses/{course_id}/

Response:
{
  "id": "uuid",
  "title": "Python Programming",
  "course_code": "PY101",
  "description": "Full course description...",
  "image_url": "https://example.com/image.jpg",
  "video_url": "https://youtube.com/watch?v=...",
  "instructor": {
    "id": "uuid",
    "email": "instructor@example.com",
    "full_name": "Dr. Smith"
  },
  "categories": [
    {"id": "uuid", "name": "Backend"},
    {"id": "uuid", "name": "Programming"}
  ],
  "category_names": "Backend, Programming",
  "status": "active",
  "is_active": true,
  "max_students": 30,
  "enrolled_count": 15,
  "is_full": false,
  "can_enroll": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

**Code Location:**
- `courses/api/viewsets.py` - `CourseViewSet.retrieve()`
- `courses/api/serializers.py` - `CourseDetailSerializer`

---

#### 3.3 Filter Courses

**Requirement**: Anonymous/Student can filter list courses by category, name, status.

**Implementation:**
- ✅ **Filter by Category**: `?category={category_uuid}`
- ✅ **Filter by Status**: `?status={draft|active|in_progress|completed}`
- ✅ **Search by Name**: `?search={query}` - Searches in title, course_code, description
- ✅ **Ordering**: `?ordering={title|created_at|enrolled_count}`

**Request Examples:**
```json
# Filter by category
GET /api/v1/courses/courses/?category=123e4567-e89b-12d3-a456-426614174000

# Filter by status
GET /api/v1/courses/courses/?status=active

# Search
GET /api/v1/courses/courses/?search=python

# Combined filters
GET /api/v1/courses/courses/?category={uuid}&status=active&search=python&ordering=-created_at
```

**Code Location:**
- `courses/api/filters.py` - `CourseFilter`
- `courses/api/viewsets.py` - `CourseViewSet` with filter backends

---

### 4. Instructor Management APIs

#### 4.1 Instructor Login

**Requirement**: Instructors can login to the system.

**Implementation:**
- ✅ **Same Login Endpoint**: `POST /api/v1/users/auth/login/`
  - Works for all roles (student, instructor, admin)
  - Returns role in user object
  - Same JWT token authentication

**Response Example:**
```json
{
  "message": "Login successful",
  "access_token": "...",
  "refresh_token": "...",
  "user": {
    "id": "uuid",
    "email": "instructor@example.com",
    "role": "instructor",
    ...
  }
}
```

---

#### 4.2 View/Update Profile

**Requirement**: Instructors can view and update their profile.

**Implementation:**
- ✅ **Same Profile Endpoints**: `GET/PUT/PATCH /api/v1/users/auth/me/`
  - Works for all authenticated users
  - Role-specific fields are read-only

---

#### 4.3 Create/Update Course

**Requirement**: Instructors can create or update a course.

**Implementation:**
- ✅ **Create Course**: `POST /api/v1/courses/courses/`
  - Requires authentication
  - Requires `role='instructor'`
  - Automatically sets instructor to current user
  - Validates course code uniqueness
  - Uppercases course code
  - Validates category IDs
  - Validates max_students (positive number or null)

**Request Example:**
```json
POST /api/v1/courses/courses/
Authorization: Bearer <instructor_token>
{
  "title": "Advanced Python",
  "course_code": "PY201",
  "description": "Advanced Python concepts...",
  "category_ids": ["uuid1", "uuid2"],
  "max_students": 25,
  "status": "active",
  "image_url": "https://example.com/image.jpg",
  "video_url": "https://youtube.com/watch?v=..."
}

Response:
{
  "id": "uuid",
  "title": "Advanced Python",
  "course_code": "PY201",
  "instructor": {
    "id": "uuid",
    "full_name": "Dr. Smith"
  },
  ...
}
```

- ✅ **Update Course**: `PUT/PATCH /api/v1/courses/courses/{id}/`
  - Requires course ownership (instructor must be course owner)
  - Validates business rules:
    - Cannot disable in-progress courses with enrolled students
    - Cannot reduce max_students below current enrollment
    - Valid status transitions

**Validation Rules:**
- Course code must be unique (case-insensitive)
- Course code format: letters, numbers, hyphens, underscores
- Category IDs must exist and be active
- Max students must be positive or null
- Video/image URLs must be valid HTTP(S) URLs
- Status must be valid choice

**Code Location:**
- `courses/api/viewsets.py` - `CourseViewSet.create()`, `update()`, `partial_update()`
- `courses/api/serializers.py` - `CourseWriteSerializer`
- `courses/api/permissions.py` - `IsInstructorOrReadOnly`

---

#### 4.4 View Enrolled Students

**Requirement**: Instructors can view all enrolled students in their course.

**Implementation:**
- ✅ **Enrolled Students**: `GET /api/v1/courses/courses/{id}/enrolled-students/`
  - Requires authentication
  - Requires instructor role
  - Requires course ownership
  - Returns paginated list of enrolled students
  - Includes student details and enrollment information

**Request Example:**
```json
GET /api/v1/courses/courses/{course_id}/enrolled-students/
Authorization: Bearer <instructor_token>

Response:
{
  "count": 15,
  "results": [
    {
      "student": {
        "id": "uuid",
        "email": "student@example.com",
        "full_name": "John Doe"
      },
      "status": "active",
      "is_active": true,
      "enrolled_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

**Code Location:**
- `courses/api/viewsets.py` - `CourseViewSet.enrolled_students()`
- `enrollments/api/serializers.py` - `EnrolledStudentSerializer`

---

#### 4.5 Cannot Disable In-Progress Courses

**Requirement**: Instructors cannot disable a course if it is in progress and has students enrolled in it.

**Implementation:**
- ✅ **Validation in Serializer**: `CourseWriteSerializer.validate()`
  - Checks if course status is `STATUS_IN_PROGRESS`
  - Checks if course has active enrollments
  - Prevents setting `is_active=False` if both conditions true

**Validation Code:**
```python
def _validate_is_active_change(self, attrs):
    if 'is_active' in attrs and attrs['is_active'] is False:
        if (self.instance.status == Course.STATUS_IN_PROGRESS and
            self.instance.enrollments.filter(is_active=True).exists()):
            raise ValidationError(
                'Cannot disable a course that is in progress with enrolled students.'
            )
```

**Code Location:**
- `courses/api/serializers.py` - `CourseWriteSerializer._validate_is_active_change()`
- `courses/models.py` - `Course.clean()` also validates this

---

## 🧪 Testing Implementation

### Test Coverage: 86%

**Total Tests**: 134 passing tests

### Test Categories

1. **Model Tests** (40+ tests)
   - User model validation
   - Course model business rules
   - Enrollment model validation
   - Category model

2. **Serializer Tests** (35+ tests)
   - Registration validation
   - Login validation
   - Password reset validation
   - Course serialization
   - Enrollment serialization

3. **ViewSet Tests** (25+ tests)
   - API endpoint functionality
   - Permission checks
   - Filtering and search
   - Pagination

4. **Permission Tests** (10+ tests)
   - Role-based access control
   - Object-level permissions

5. **Integration Tests** (20+ tests)
   - End-to-end API flows
   - Business rule validation

### Test Isolation

- ✅ **SQLite in-memory database** - Tests never touch PostgreSQL
- ✅ **Automatic cleanup** - Database reset between tests
- ✅ **Fixtures** - Reusable test data factories
- ✅ **Fast execution** - In-memory database is very fast

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=users --cov=courses --cov=categories --cov=enrollments --cov=core --cov-report=html

# Specific test file
pytest tests/users/test_viewsets.py
```

---

## 📊 API Documentation

### Interactive Documentation

**Swagger UI**: `http://localhost:8000/api/docs/`

Features:
- ✅ Interactive API testing
- ✅ Authentication testing (JWT tokens)
- ✅ Request/response examples
- ✅ Schema validation
- ✅ Try it out functionality

**OpenAPI Schema**: `http://localhost:8000/api/schema/`

- ✅ Machine-readable API specification
- ✅ Can be imported into Postman
- ✅ Can be used for code generation

### Postman Collection

**Recommended Setup:**
1. Import OpenAPI schema into Postman
2. Create environment variables:
   - `base_url`: `http://localhost:8000`
   - `access_token`: (set after login)
   - `refresh_token`: (set after login)
3. Use collection variables for dynamic testing

**Example Postman Flow:**
1. Register student → Save user_id
2. Login → Save access_token, refresh_token
3. Get profile → Verify user data
4. List courses → Browse available courses
5. Enroll in course → Create enrollment
6. List enrollments → Verify enrollment
7. Leave course → Remove enrollment

---

## 🔒 Security Features

### Authentication & Authorization

1. **JWT Token Authentication**
   - Access tokens (short-lived)
   - Refresh tokens (long-lived)
   - Token blacklisting on logout
   - Token rotation on refresh

2. **Role-Based Access Control**
   - Student role: Enrollment operations
   - Instructor role: Course management
   - Admin role: Full access via admin

3. **Password Security**
   - Django password validators (strength requirements)
   - Password hashing (bcrypt in production, MD5 in tests)
   - Password reset tokens (time-limited)

4. **Input Validation**
   - Email normalization and uniqueness
   - Username format validation
   - Course code format validation
   - URL validation for media fields

5. **Business Rule Validation**
   - Cannot enroll in inactive courses
   - Cannot enroll in full courses
   - Cannot disable in-progress courses with students
   - Prevents duplicate enrollments

---

## 🎓 Learning Outcomes

### Upon Completion, Trainee Should Demonstrate:

1. ✅ **RESTful API Design**
   - Proper HTTP methods (GET, POST, PUT, PATCH, DELETE)
   - Resource-based URLs
   - Status codes (200, 201, 400, 401, 403, 404, 500)
   - Consistent response formats

2. ✅ **Serialization & Validation**
   - Model serializers
   - Custom validation methods
   - Field-level and object-level validation
   - Nested serializers
   - Read-only and write-only fields

3. ✅ **Security Implementation**
   - JWT authentication
   - Role-based permissions
   - Object-level permissions
   - Password security
   - Input sanitization

4. ✅ **Testing Skills**
   - Unit tests for models
   - Serializer tests
   - ViewSet/API tests
   - Permission tests
   - High code coverage (86%)

5. ✅ **API Documentation**
   - OpenAPI/Swagger documentation
   - Interactive API explorer
   - Request/response examples
   - Postman collection ready

6. ✅ **AI-Assisted Development**
   - Using AI for code suggestions
   - AI-powered test generation
   - AI-assisted debugging
   - Documentation generation

---

## 📈 Project Statistics

- **Total API Endpoints**: 20+
- **Models**: 4 (User, Course, Category, Enrollment)
- **ViewSets**: 4 (Auth, Course, Category, Enrollment)
- **Serializers**: 15+
- **Permissions**: 3 custom permission classes
- **Tests**: 134
- **Test Coverage**: 86%
- **Lines of Code**: ~3,500+

---

## 🚀 Deployment Considerations

### Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Use strong `SECRET_KEY`
- [ ] Configure PostgreSQL database
- [ ] Set up email backend (SMTP)
- [ ] Configure CORS for mobile app
- [ ] Set up static file serving
- [ ] Configure JWT token lifetimes
- [ ] Enable token blacklisting
- [ ] Set up monitoring/logging

### Environment Variables

```env
# Production
DEBUG=False
SECRET_KEY=<strong-secret-key>
DB_NAME=studyportal_prod
DB_USER=postgres
DB_PASSWORD=<secure-password>
DB_HOST=db.example.com
ALLOWED_HOSTS=api.example.com
CORS_ALLOWED_ORIGINS=https://app.example.com
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
```

---

## 📝 Conclusion

This project successfully implements a comprehensive REST API for a Student Course Management System with:

- ✅ Complete student management (registration, login, profile, enrollment)
- ✅ Full course management (CRUD, filtering, search)
- ✅ Instructor management (course creation, student roster)
- ✅ Robust security (JWT, RBAC, validation)
- ✅ Comprehensive testing (86% coverage)
- ✅ Complete API documentation (Swagger/OpenAPI)
- ✅ Production-ready code quality

The system is ready for mobile app integration and can be extended with additional features as needed.

---

**Project Author**: Quyen Huynh
**Email**: quyen.huynh@asnet.com.vn
**Date**: 2024
