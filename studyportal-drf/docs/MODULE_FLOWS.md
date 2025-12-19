# StudyPortal DRF — Module Flows (Models → Serializers → ViewSets)
This document explains how each module in this codebase works end-to-end: database models, serializers, viewsets, permissions, query optimizations, and the reason each design choice exists.

## 1) Architecture overview
### 1.1 The pattern used in this repo
For each Django app, the architecture is consistent:
- **Model (DB layer)**: defines schema, constraints, invariants, and helper methods.
- **Serializer (API contract layer)**: defines input/output shape, validation, and create/update logic.
- **ViewSet (HTTP layer)**: defines routes/actions, permissions, and optimized querysets.

Why this separation is useful:
- Models protect data integrity even if data is created via admin/scripts.
- Serializers provide client-friendly validation errors and keep views thin.
- ViewSets focus on routing + permissions + performance.

### 1.2 API routing entry points
Main router wiring lives in `config/urls.py`.

API v1 prefixes:
- Users: `api/v1/users/` → `users/api/urls.py`
- Categories: `api/v1/categories/` → `categories/api/urls.py`
- Courses: `api/v1/courses/` → `courses/api/urls.py`
- Enrollments: `api/v1/enrollments/` → `enrollments/api/urls.py`

### 1.3 Shared conventions
- UUID primary keys are used for core models (safe to expose in URLs).
- “Soft delete” is used in places where history matters (e.g. courses via `is_active`).
- Role-based access control is implemented using a `role` field on `users.User`.

## 2) Shared Core Module
The `core/` app contains shared utilities used across modules.

### 2.1 Centralized choices (enums)
File: `core/choices.py`

Defines reusable `TextChoices`:
- `UserRole`: `student`, `instructor`, `admin`
- `CourseStatus`: `draft`, `active`, `in_progress`, `completed`
- `EnrollmentStatus`: `active`, `completed`, `dropped`

Why centralized choices:
- Avoids duplicated magic strings across the codebase.
- Guarantees consistent values between model fields, serializer validation, filters, and permissions.
- Makes future changes safe: add a new role/status in one place.

How to use:
- Model field: `choices=UserRole.choices`
- Constant: `UserRole.INSTRUCTOR` (value is `'instructor'`)

### 2.2 Common response helpers
File: `core/api_views.py`

`CommonViewSet` provides helper methods for consistent responses:
- `ok()` → HTTP 200
- `created()` → HTTP 201
- `bad_request()` → HTTP 400 with structured error payload
- `server_error()` → HTTP 500

Why:
- Reduces repeated `Response(...)` code.
- Keeps error responses consistent across endpoints.

## 3) Users Module (Authentication + Profile)
### 3.1 Model
File: `users/models.py`

Key fields / behavior:
- Extends `AbstractUser`.
- UUID primary key (`id`).
- Email is unique and used for login: `USERNAME_FIELD = 'email'`.
- Role-based access via `role = models.CharField(... choices=UserRole.choices ...)`.
- Convenience properties:
  - `is_student` and `is_instructor` used by permissions.
- `clean()` normalizes email to lowercase.

Why this design:
- Email login is common for mobile/web apps.
- Role on the user model supports RBAC without extra tables.
- Model-level normalization prevents duplicated emails differing only by case.

### 3.2 Serializers
Files:
- `users/api/serializers.py`
- `users/api/bases.py`

#### 3.2.1 Base classes (`users/api/bases.py`)
Reusable validation helpers:
- `EmailNormalizationBase`: ensures emails are lowercase and trimmed.
- `NameValidationBase`: validates names and normalizes capitalization.
- `PasswordConfirmationBase`: checks password + confirmation match.
- `ResetTokenValidationBase`: validates `uid` + `token` for password reset.

Why base classes:
- Reduces duplication across multiple authentication serializers.
- Keeps serializer logic consistent.

#### 3.2.2 Registration flow
Serializer: `UserRegistrationSerializer`

Step-by-step:
1. Validate email + username uniqueness.
2. Validate name formatting.
3. Validate password strength (`validate_password`).
4. Validate password confirmation.
5. Create user via `User.objects.create_user(...)` (password hashing happens here).
6. Force role to student (`role='student'`) in this serializer.

Why role is forced:
- Prevents users from self-registering as instructor/admin.

#### 3.2.3 Login flow
Serializer: `UserLoginSerializer`

Step-by-step:
1. Normalize email.
2. Look up user by email.
3. Check password.
4. Fail with a generic error (prevents email enumeration).

#### 3.2.4 Password reset flows
- `PasswordResetRequestSerializer`: accepts email. Always returns success style response.
- `PasswordResetConfirmSerializer`: validates uid/token and new password.

Why always “success” for reset request:
- Prevents leaking whether an email exists in the system.

#### 3.2.5 Profile
Serializer: `UserProfileSerializer`

- Exposes profile fields.
- Makes sensitive fields read-only (email/role/etc.) to prevent unintended changes.

### 3.3 ViewSet
File: `users/api/viewsets.py`
Route registration: `users/api/urls.py` registers `auth/`.

`AuthViewSet` is a `GenericViewSet` with custom actions (not CRUD).

Endpoints and steps:
- `POST /api/v1/users/auth/register/`
  1. Validate with `UserRegistrationSerializer`.
  2. Create user.
  3. Return 201 + user data.

- `POST /api/v1/users/auth/login/`
  1. Validate credentials.
  2. Create JWT tokens using SimpleJWT (`RefreshToken.for_user`).
  3. Return 200 + tokens.

- `POST /api/v1/users/auth/logout/`
  1. Requires authentication.
  2. Blacklists refresh token (if token blacklist app is enabled).

- `POST /api/v1/users/auth/password-reset/`
  1. Accept email.
  2. If user exists, create token + uid.
  3. Optionally send email.
  4. Return generic success response.

- `POST /api/v1/users/auth/password-reset-confirm/`
  1. Validate uid + token.
  2. Set new password.

- `POST /api/v1/users/auth/password-change/`
  1. Requires authentication.
  2. Validate old password.
  3. Set new password.

- `GET/PUT/PATCH /api/v1/users/auth/me/`
  1. Requires authentication.
  2. GET returns profile.
  3. PUT/PATCH updates allowed fields.

Why ViewSet actions:
- Authentication is not a CRUD resource; actions map better to auth use cases.

## 4) Categories Module (Public catalog)
### 4.1 Model
File: `categories/models.py`

- UUID primary key.
- `name` is unique + indexed.
- `is_active` flag enables soft disabling.

Why `is_active`:
- Allows hiding categories without deleting them (safer for history).

### 4.2 Serializer
File: `categories/api/serializers.py`

`CategorySerializer`:
- Validates `name` is non-empty after trimming.
- Enforces case-insensitive uniqueness.

Why validate in serializer even if DB has `unique=True`:
- Gives client-friendly validation errors instead of DB IntegrityErrors.

### 4.3 ViewSet
File: `categories/api/viewsets.py`
Routes: `categories/api/urls.py`

`CategoryViewSet(ReadOnlyModelViewSet)`:
- Public read access (`AllowAny`).
- Only returns active categories.
- Supports search and ordering.

Why read-only:
- Category creation/update is typically an admin responsibility.
- Keeps public API surface smaller and safer.

## 5) Courses Module (CRUD + access rules)
### 5.1 Model
File: `courses/models.py`

Key fields:
- `status`: workflow using `CourseStatus.choices`.
- `is_active`: soft delete.
- `instructor`: FK to user, restricted to instructor role.
- categories: ManyToMany.
- optional media URLs.
- `max_students`: capacity.

Key helpers:
- `_enrolled_count`: counts active enrollments.
- `is_full`: checks capacity.
- `can_enroll()`: enrollment eligibility rule.

Validation:
- `clean()` ensures instructor is truly an instructor.
- `save()` calls `full_clean()` so rules apply everywhere (API/admin/scripts).

### 5.2 Serializers
Files:
- `courses/api/serializers.py`
- `courses/api/bases.py`

Read serializers:
- `CourseListSerializer`: optimized for lists.
- `CourseDetailSerializer`: includes instructor + category names.

Write serializer:
- `CourseWriteSerializer`: creates/updates and enforces business rules:
  - category ids must exist and be active
  - course_code normalization + uniqueness
  - status transitions
  - prevent disabling in-progress courses with students
  - prevent reducing max_students below enrollment

Serializer base classes:
- `CourseEnrollmentFieldsBase`: computed fields (`enrolled_count`, `is_full`, `can_enroll`) use annotations when available.
- `CategoryNamesFieldBase`: computed `category_names`.

Why computed-fields base:
- Lets ViewSet annotate values for performance, while still working if annotation is missing.

### 5.3 Permissions
File: `courses/api/permissions.py`

- `IsInstructorOrReadOnly`:
  - Anyone can read.
  - Only instructors can write.
  - Only the course instructor can update/delete the object.

Why custom permission:
- Most course endpoints depend on role and ownership.

### 5.4 ViewSet
File: `courses/api/viewsets.py`
Routes: `courses/api/urls.py` registers `courses/`.

#### 5.4.1 List/retrieve flow
Route: `GET /api/v1/courses/courses/`

The ViewSet builds an optimized queryset:
1. `select_related('instructor')` to avoid N+1 queries.
2. `prefetch_related('categories')` to avoid N+1 queries.
3. Annotates computed fields for list/retrieve:
   - enrolled_count
   - is_full
   - can_enroll
4. Applies role-based filtering:
   - anonymous: only active + status=active
   - authenticated: only active
   - instructors with `?my_courses=true`: only own courses

Why annotate:
- Computing enrollment counts and capacity checks in SQL is faster than Python for large datasets.

#### 5.4.2 Create flow
Route: `POST /api/v1/courses/courses/`

1. Permission checks instructor role.
2. Serializer validates input.
3. `perform_create()` sets `instructor=request.user` (clients cannot spoof instructor).

#### 5.4.3 Soft delete flow
Route: `DELETE /api/v1/courses/courses/{id}/`

1. Checks if in-progress with enrolled students → reject.
2. Calls `course.soft_delete()` (marks inactive).

Why soft delete:
- Avoids losing history.
- Avoids breaking enrollments that reference the course.

#### 5.4.4 Enrolled students action
Route: `GET /api/v1/courses/courses/{id}/enrolled-students/`

1. Verifies requester is the course instructor.
2. Fetches active enrollments with `select_related('student')`.
3. Returns paginated list via `EnrolledStudentSerializer`.

## 6) Enrollments Module (Enroll/leave + history)
### 6.1 Model
File: `enrollments/models.py`

Key fields:
- `student` FK limited to student role.
- `course` FK.
- `status` via `EnrollmentStatus.choices`.
- `is_active` for current enrollment state.

Constraint:
- Only one active enrollment per student/course (conditional unique constraint).

Validation:
- `clean()` enforces:
  - only students can enroll
  - course is active and open and not full (new enrollments only)

Business action:
- `unenroll()` sets `is_active=False` + status dropped.

Why keep record instead of delete:
- Preserves enrollment history for auditing and potential “completed courses” screens.

### 6.2 Serializers
File: `enrollments/api/serializers.py`

Read:
- `EnrollmentSerializer`: includes course info for student views.
- `EnrolledStudentSerializer`: includes student info for instructor roster views.

Write:
- `EnrollmentCreateSerializer`:
  - Accepts `course_id`.
  - Validates course existence and enrollment rules.
  - Uses `transaction.atomic()` + `select_for_update()` to prevent race conditions.

Why row locking:
- Prevents two users from taking the last seat simultaneously.
- Prevents edge-case duplicates under concurrency.

### 6.3 ViewSet
File: `enrollments/api/viewsets.py`
Routes: `enrollments/api/urls.py` registers `students/enrollments/`.

Endpoints:
- `GET /api/v1/enrollments/students/enrollments/` list my enrollments
- `GET /api/v1/enrollments/students/enrollments/{id}/` detail
- `POST /api/v1/enrollments/students/enrollments/enroll/` enroll in course
- `DELETE /api/v1/enrollments/students/enrollments/{id}/leave/` leave course

Permission:
- `IsStudent` only.

Queryset is optimized:
- `select_related('course', 'course__instructor')`
- `prefetch_related('course__categories')`

Enroll action flow:
1. Validate request with `EnrollmentCreateSerializer`.
2. Create enrollment (locked transaction).
3. Return 201 with enrollment data.

Leave action flow:
1. Load enrollment.
2. Call `unenroll()`.
3. Return 200.

## 7) Extension guide (common changes)
### 7.1 Add a new role/status
1. Update `core/choices.py`.
2. Update any permission logic that checks the role/status.
3. Update any serializer validation that lists allowed statuses.
4. Update docs and tests.

### 7.2 Add a new course workflow rule
- Prefer putting invariants in `Course.clean()` (model-level) if it must always hold.
- Put API-only business rules (request-specific) in `CourseWriteSerializer.validate()`.

### 7.3 Performance checklist when adding new serializers
- If the serializer adds nested relationships, update the viewset queryset with:
  - `select_related(...)` for FK/OneToOne
  - `prefetch_related(...)` for M2M/reverse FK
