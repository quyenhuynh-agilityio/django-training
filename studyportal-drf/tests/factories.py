"""
Factory Boy Factories for Test Data Generation

This module provides factory_boy factories for all models in the application.
Factories generate realistic test data and handle model relationships automatically.
"""

import factory
from factory.django import DjangoModelFactory
from faker import Faker

from django.contrib.auth import get_user_model

from core.choices import UserRole

fake = Faker()
User = get_user_model()

# ─── USER FACTORIES ───────────────────────────────────────────


class UserFactory(DjangoModelFactory):
    """Factory for creating base User instances."""

    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f'user{n}@example.com')
    username = factory.Sequence(lambda n: f'user{n}')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    role = UserRole.STUDENT
    is_active = True
    is_staff = False
    is_superuser = False

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        """Set a default password for the user. Renamed 'obj' to 'self' for N805."""
        if not create:
            return
        password = extracted or 'TestPassword123!'
        self.set_password(password)
        self.save()


class StudentFactory(UserFactory):
    """Factory for creating Student users."""

    role = UserRole.STUDENT


class InstructorFactory(UserFactory):
    """Factory for creating Instructor users."""

    role = UserRole.INSTRUCTOR


class AdminUserFactory(UserFactory):
    """Factory for creating Admin users."""

    role = UserRole.ADMIN
    is_staff = True
    is_superuser = True


# ─── CATEGORY FACTORY ─────────────────────────────────────────


class CategoryFactory(DjangoModelFactory):
    """Factory for creating Category instances."""

    class Meta:
        model = 'categories.Category'
        skip_postgeneration_save = True

    name = factory.Sequence(lambda n: f'Category {n}')
    slug = factory.LazyAttribute(lambda self: self.name.lower().replace(' ', '-'))
    description = factory.Faker('text', max_nb_chars=200)
    is_active = True


# ─── COURSE FACTORY ───────────────────────────────────────────


class CourseFactory(DjangoModelFactory):
    """Factory for creating Course instances including new auto-enroll logic."""

    class Meta:
        model = 'courses.Course'
        skip_postgeneration_save = True

    title = factory.Sequence(lambda n: f'Course {n}')
    course_code = factory.Sequence(lambda n: f'CRS{n:03d}')
    description = factory.Faker('text', max_nb_chars=500)
    instructor = factory.SubFactory(InstructorFactory)

    # New Logic Fields
    is_auto_enrolled = False
    is_introduction = factory.Faker('boolean', chance_of_getting_true=20)
    max_students = 30

    status = 'active'
    is_active = True

    @factory.post_generation
    def categories(self, create, extracted, **kwargs):
        """Handle M2M relationships. Renamed 'obj' to 'self' for N805."""
        if not create:
            return
        if extracted:
            self.categories.set(extracted)
        else:
            category = CategoryFactory()
            self.categories.add(category)


# ─── ENROLLMENT FACTORY ───────────────────────────────────────


class EnrollmentFactory(DjangoModelFactory):
    """Factory for creating Enrollment instances."""

    class Meta:
        model = 'enrollments.Enrollment'
        skip_postgeneration_save = True

    student = factory.SubFactory(StudentFactory)
    course = factory.SubFactory(CourseFactory)
    status = 'enrolled'
    enrollment_date = factory.Faker('past_date', start_date='-30d')
