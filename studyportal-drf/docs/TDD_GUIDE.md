# Test-Driven Development Guide

This guide covers using pytest and factory_boy for test-driven development in the studyportal-drf project.

## Table of Contents
- [Quick Start](#quick-start)
- [Running Tests](#running-tests)
- [Writing Tests](#writing-tests)
- [Factory Boy Usage](#factory-boy-usage)
- [Best Practices](#best-practices)
- [Examples](#examples)

---

## Quick Start

### Installation
All dependencies are already installed in your project:
- `pytest` - Testing framework
- `pytest-django` - Django integration for pytest
- `pytest-cov` - Coverage reporting
- `pytest-xdist` - Parallel test execution
- `factory-boy` - Test data generation
- `faker` - Realistic fake data

### Verify Setup
```bash
pytest --version
pytest --collect-only  # See all available tests
```

---

## Running Tests

### Basic Commands
```bash
# Run all tests
pytest

# Run tests in a specific file
pytest tests/users/test_models.py

# Run tests matching a pattern
pytest -k "test_user"

# Run tests in parallel (faster)
pytest -n auto

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov

# Run specific test function
pytest tests/users/test_models.py::test_full_name_with_names

# Run and stop on first failure
pytest -x

# Run last failed tests only
pytest --lf
```

### Watch Mode (TDD)
For true TDD workflow, use `pytest-watch` (install with `uv add --dev pytest-watch`):
```bash
ptw  # Automatically re-run tests on file changes
```

---

## Writing Tests

### Test File Structure
```
tests/
├── __init__.py
├── conftest.py          # Shared fixtures
├── factories.py         # Factory Boy factories
├── users/
│   ├── test_models.py
│   ├── test_serializers.py
│   └── test_viewsets.py
└── courses/
    ├── test_models.py
    └── test_viewsets.py
```

### Basic Test Structure
```python
import pytest

# Mark all tests in file as requiring database
pytestmark = pytest.mark.django_db


def test_user_creation(user_factory):
    """Test that users can be created."""
    user = user_factory()

    assert user.email is not None
    assert user.is_active is True


@pytest.mark.django_db
class TestUserModel:
    """Group related tests in a class."""

    def test_full_name(self, user_factory):
        user = user_factory(first_name='John', last_name='Doe')
        assert user.full_name == 'John Doe'

    def test_student_role(self, student_factory):
        student = student_factory()
        assert student.is_student is True
```

---

## Factory Boy Usage

### Available Factories
All factories are defined in `tests/factories.py`:
- `UserFactory` - Base user
- `StudentFactory` - Student users
- `InstructorFactory` - Instructor users
- `AdminUserFactory` - Admin users
- `CategoryFactory` - Course categories
- `CourseFactory` - Courses
- `EnrollmentFactory` - Student enrollments
- `LessonFactory` - Course lessons

### Basic Usage

#### Create Single Instance
```python
from tests.factories import UserFactory, CourseFactory

def test_example(db):
    # Create with defaults
    user = UserFactory()

    # Override specific fields
    student = UserFactory(
        email='student@test.com',
        first_name='Jane',
        role='student'
    )

    # Use specialized factory
    from tests.factories import InstructorFactory
    instructor = InstructorFactory()
```

#### Create Multiple Instances
```python
def test_batch_creation(db):
    # Create 5 users at once
    users = UserFactory.create_batch(5)
    assert len(users) == 5

    # Create batch with same attribute
    students = UserFactory.create_batch(3, role='student')
```

#### Build Without Saving
```python
def test_build_without_save():
    # Build instance without saving to DB
    user = UserFactory.build()
    assert user.pk is None  # Not saved yet

    user.save()
    assert user.pk is not None  # Now saved
```

#### Handle Relationships
```python
def test_relationships(db):
    from tests.factories import CourseFactory, EnrollmentFactory

    # Create with specific related object
    instructor = InstructorFactory(email='prof@example.com')
    course = CourseFactory(instructor=instructor)

    # Factory handles relationships automatically
    enrollment = EnrollmentFactory()  # Creates student and course

    # Override related objects
    student = StudentFactory()
    course = CourseFactory()
    enrollment = EnrollmentFactory(student=student, course=course)
```

#### Many-to-Many Relationships
```python
def test_many_to_many(db):
    from tests.factories import CourseFactory, CategoryFactory

    # Create categories
    cat1 = CategoryFactory(name='Programming')
    cat2 = CategoryFactory(name='Web Development')

    # Pass to course
    course = CourseFactory(categories=[cat1, cat2])
    assert course.categories.count() == 2
```

### Using Fixtures (Recommended in Tests)

The factories are also available as pytest fixtures in `conftest.py`:

```python
def test_with_fixtures(user_factory, course_factory):
    """Using factory fixtures - recommended approach."""
    user = user_factory()
    course = course_factory(instructor=user)

    assert course.instructor == user
```

Available factory fixtures:
- `user_factory`
- `student_factory`
- `instructor_factory`
- `category_factory`
- `course_factory`
- `enrollment_factory`

---

## Best Practices

### 1. Database Markers
Always mark tests that touch the database:
```python
import pytest

# Mark single test
@pytest.mark.django_db
def test_something():
    pass

# Mark entire file
pytestmark = pytest.mark.django_db

# Mark test class
@pytest.mark.django_db
class TestSomething:
    pass
```

### 2. Arrange-Act-Assert Pattern
```python
def test_user_enrollment(student_factory, course_factory):
    # Arrange - Setup test data
    student = student_factory()
    course = course_factory()

    # Act - Perform the action
    enrollment = Enrollment.objects.create(
        student=student,
        course=course
    )

    # Assert - Verify results
    assert enrollment.status == 'enrolled'
    assert enrollment.student == student
```

### 3. Use Descriptive Test Names
```python
# Good
def test_student_cannot_enroll_in_full_course():
    pass

def test_instructor_can_update_own_course():
    pass

# Bad
def test_enrollment():
    pass

def test_course_1():
    pass
```

### 4. One Assertion Per Test (When Possible)
```python
# Good
def test_user_has_email(user_factory):
    user = user_factory()
    assert user.email is not None

def test_user_is_active_by_default(user_factory):
    user = user_factory()
    assert user.is_active is True

# Acceptable for related checks
def test_student_properties(student_factory):
    student = student_factory()
    assert student.role == 'student'
    assert student.is_student is True
    assert student.is_instructor is False
```

### 5. Use Parametrize for Similar Tests
```python
@pytest.mark.parametrize('role,expected', [
    ('student', True),
    ('instructor', False),
    ('admin', False),
])
def test_is_student_for_different_roles(user_factory, role, expected):
    user = user_factory(role=role)
    assert user.is_student == expected
```

### 6. Test Edge Cases
```python
def test_course_enrollment_at_capacity(course_factory, student_factory):
    course = course_factory(max_students=2)

    # Enroll up to capacity
    student_factory.create_batch(2)
    # ... enroll them

    # Try to enroll one more
    extra_student = student_factory()
    # Assert enrollment fails or waitlist
```

---

## Examples

### Testing Models
```python
import pytest
from django.core.exceptions import ValidationError

pytestmark = pytest.mark.django_db


class TestUserModel:
    def test_create_user(self, user_factory):
        user = user_factory(email='test@example.com')
        assert user.email == 'test@example.com'

    def test_email_is_lowercase(self, user_factory):
        user = user_factory.build(email='UPPER@EXAMPLE.COM')
        user.clean()
        assert user.email == 'upper@example.com'

    def test_user_str_representation(self, user_factory):
        user = user_factory(email='john@example.com')
        assert str(user) == 'john@example.com'


class TestCourseModel:
    def test_course_creation(self, course_factory):
        course = course_factory(title='Python 101')
        assert course.title == 'Python 101'
        assert course.instructor is not None

    def test_course_has_categories(self, course_factory, category_factory):
        categories = category_factory.create_batch(2)
        course = course_factory(categories=categories)
        assert course.categories.count() == 2
```

### Testing Serializers
```python
import pytest

pytestmark = pytest.mark.django_db


class TestUserSerializer:
    def test_serializer_with_valid_data(self):
        from users.serializers import UserSerializer

        data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'SecurePass123!',
        }
        serializer = UserSerializer(data=data)
        assert serializer.is_valid()

    def test_serializer_with_invalid_email(self):
        from users.serializers import UserSerializer

        data = {'email': 'invalid-email'}
        serializer = UserSerializer(data=data)
        assert not serializer.is_valid()
        assert 'email' in serializer.errors
```

### Testing API Views
```python
import pytest
from rest_framework import status

pytestmark = pytest.mark.django_db


class TestUserViewSet:
    def test_list_users(self, api_client, user_factory):
        # Create test data
        user_factory.create_batch(3)

        # Make request
        response = api_client.get('/api/users/')

        # Assert response
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 3

    def test_create_user_unauthorized(self, api_client):
        data = {'email': 'new@example.com'}
        response = api_client.post('/api/users/', data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_user_as_admin(self, api_client, user_factory):
        # Authenticate as admin
        admin = user_factory(is_staff=True)
        api_client.force_authenticate(user=admin)

        # Create user
        data = {
            'email': 'new@example.com',
            'username': 'newuser',
            'password': 'SecurePass123!',
        }
        response = api_client.post('/api/users/', data)
        assert response.status_code == status.HTTP_201_CREATED


class TestCourseEnrollment:
    def test_student_can_enroll(self, api_client, student_factory, course_factory):
        student = student_factory()
        course = course_factory()
        api_client.force_authenticate(user=student)

        response = api_client.post(f'/api/courses/{course.id}/enroll/')
        assert response.status_code == status.HTTP_201_CREATED

    def test_instructor_cannot_enroll(self, api_client, instructor_factory, course_factory):
        instructor = instructor_factory()
        course = course_factory()
        api_client.force_authenticate(user=instructor)

        response = api_client.post(f'/api/courses/{course.id}/enroll/')
        assert response.status_code == status.HTTP_403_FORBIDDEN
```

### Testing with Fixtures
```python
import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def enrolled_student(student_factory, course_factory, enrollment_factory):
    """Fixture that provides a student enrolled in a course."""
    student = student_factory()
    course = course_factory()
    enrollment = enrollment_factory(student=student, course=course)
    return {
        'student': student,
        'course': course,
        'enrollment': enrollment,
    }


def test_student_can_access_course(api_client, enrolled_student):
    student = enrolled_student['student']
    course = enrolled_student['course']

    api_client.force_authenticate(user=student)
    response = api_client.get(f'/api/courses/{course.id}/')

    assert response.status_code == 200
```

---

## Advanced Patterns

### Custom Factory Methods
```python
# In tests/factories.py
class CourseFactory(DjangoModelFactory):
    # ... existing code ...

    @classmethod
    def create_full_course(cls, **kwargs):
        """Create a course at max capacity."""
        course = cls(max_students=5, **kwargs)
        StudentFactory.create_batch(5)
        # ... enroll them
        return course

# Usage in tests
def test_waitlist(db):
    course = CourseFactory.create_full_course()
    assert course.is_full()
```

### Traits with SubFactory
```python
class CourseFactory(DjangoModelFactory):
    # ... existing code ...

    class Params:
        full = factory.Trait(
            max_students=5,
            # Could trigger post_generation to enroll students
        )

# Usage
course = CourseFactory(full=True)
```

---

## TDD Workflow

### Red-Green-Refactor Cycle

1. **RED** - Write a failing test
```python
def test_user_cannot_enroll_twice():
    # This will fail because feature doesn't exist yet
    student = StudentFactory()
    course = CourseFactory()

    Enrollment.objects.create(student=student, course=course)

    with pytest.raises(ValidationError):
        Enrollment.objects.create(student=student, course=course)
```

2. **GREEN** - Write minimal code to pass
```python
# In enrollments/models.py
class Enrollment(models.Model):
    # ... fields ...

    class Meta:
        unique_together = ['student', 'course']
```

3. **REFACTOR** - Improve the code
```python
# Add custom validation with better error messages
def clean(self):
    if Enrollment.objects.filter(
        student=self.student,
        course=self.course
    ).exists():
        raise ValidationError('Student already enrolled in this course')
```

---

## Coverage Reports

### Generate Coverage Report
```bash
# HTML report (opens in browser)
pytest --cov --cov-report=html
open htmlcov/index.html

# Terminal report
pytest --cov --cov-report=term-missing

# XML report (for CI/CD)
pytest --cov --cov-report=xml
```

### Coverage Configuration
Already configured in `pyproject.toml`:
- Covers: `users`, `courses`, `categories`, `enrollments`, `core`
- Omits: migrations, test files, admin, boilerplate

---

## Troubleshooting

### Common Issues

**Tests can't find factories:**
```python
# Make sure to import from tests
from tests.factories import UserFactory
```

**Database errors:**
```python
# Add database marker
@pytest.mark.django_db
def test_something():
    pass
```

**Factories not creating expected data:**
```python
# Check factory definition in tests/factories.py
# Use .build() to inspect without saving:
user = UserFactory.build()
print(user.__dict__)
```

**Slow tests:**
```bash
# Run in parallel
pytest -n auto

# Use --reuse-db
pytest --reuse-db

# Check for N+1 queries
pytest --durations=10
```

---

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-django documentation](https://pytest-django.readthedocs.io/)
- [factory_boy documentation](https://factoryboy.readthedocs.io/)
- [Django REST Framework testing](https://www.django-rest-framework.org/api-guide/testing/)

---

## Quick Reference Card

```bash
# Run tests
pytest                              # All tests
pytest tests/users/                 # Specific directory
pytest -k "user"                    # By keyword
pytest -x                          # Stop on first failure
pytest --lf                        # Last failed only
pytest -n auto                     # Parallel

# Coverage
pytest --cov                       # Basic coverage
pytest --cov --cov-report=html    # HTML report

# Debugging
pytest -v                          # Verbose
pytest -s                          # Show print statements
pytest --pdb                       # Drop into debugger on failure

# Factory usage in tests
user = user_factory()              # Create with defaults
user = user_factory(role='admin')  # Override fields
users = user_factory.create_batch(5)  # Create multiple
```
