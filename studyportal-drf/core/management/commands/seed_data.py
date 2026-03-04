"""
Seed the database with 10 categories, 10 courses (full content), instructors,
10 students, and enrollments. Safe to run multiple times (uses get_or_create by
email / course_code where possible).
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from core.choices import CourseStatus, UserRole
from categories.models import Category
from courses.models import Course
from enrollments.models import Enrollment

# 10 categories for seed
SEED_CATEGORY_NAMES = [
    'Programming',
    'Mathematics',
    'Science',
    'Business',
    'Design',
    'Languages',
    'Health & Wellness',
    'Data & Analytics',
    'DevOps & Cloud',
    'Soft Skills',
]

# (email, username, first_name, last_name) for seed instructors
SEED_INSTRUCTORS = [
    ('instructor1@seed.example.com', 'instructor1_seed', 'Jane', 'Smith'),
    ('instructor2@seed.example.com', 'instructor2_seed', 'Michael', 'Chen'),
]

# Default course logo/thumbnail (real Unsplash image)
DEFAULT_COURSE_IMAGE = 'https://images.unsplash.com/photo-1523240795612-9a054b0db644?w=600'
# Per-course image (Unsplash) and YouTube video URL
SEED_COURSE_MEDIA = [
    ('https://images.unsplash.com/photo-1526379095098-d400fd0bf935?w=600', 'https://www.youtube.com/watch?v=_uQrJ0TkZlc'),   # Python
    ('https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=600', 'https://www.youtube.com/watch?v=hdI2bqOjy3c'),   # Web
    ('https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=600', 'https://www.youtube.com/watch?v=Jzz4CH0lSMA'),   # Data Science
    ('https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=600', 'https://www.youtube.com/watch?v=ZumgfOei0Ak'),   # Linear Algebra
    ('https://images.unsplash.com/photo-1509228627152-72ae9ae6848d?w=600', 'https://www.youtube.com/watch?v=xxpc-HPKN28'),   # Statistics
    ('https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=600', 'https://www.youtube.com/watch?v=8-SqQHti_4k'),   # Business
    ('https://images.unsplash.com/photo-1561070791-2526d30994b5?w=600', 'https://www.youtube.com/watch?v=c9Wg6Cb_YlU'),   # UX
    ('https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?w=600', 'https://www.youtube.com/watch?v=2nRJ_O1zb-c'),   # English
    ('https://images.unsplash.com/photo-1618477388954-7852f32655ec?w=600', 'https://www.youtube.com/watch?v=lJB3FvODb2Y'),   # DevOps
    ('https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=600', 'https://www.youtube.com/watch?v=KxGRhd_iWuE'),   # Soft Skills
]

# (email, username, first_name, last_name) for 10 seed students
SEED_STUDENTS = [
    ('student1@seed.example.com', 'student1_seed', 'Alice', 'Johnson'),
    ('student2@seed.example.com', 'student2_seed', 'Bob', 'Williams'),
    ('student3@seed.example.com', 'student3_seed', 'Carol', 'Brown'),
    ('student4@seed.example.com', 'student4_seed', 'David', 'Davis'),
    ('student5@seed.example.com', 'student5_seed', 'Eva', 'Martinez'),
    ('student6@seed.example.com', 'student6_seed', 'Frank', 'Garcia'),
    ('student7@seed.example.com', 'student7_seed', 'Grace', 'Lee'),
    ('student8@seed.example.com', 'student8_seed', 'Henry', 'Wilson'),
    ('student9@seed.example.com', 'student9_seed', 'Ivy', 'Anderson'),
    ('student10@seed.example.com', 'student10_seed', 'Jack', 'Thomas'),
]


class Command(BaseCommand):
    help = (
        'Create sample data: 10 categories, 2 instructors, 10 students, '
        '10 courses (full content), and enrollments. Safe to run multiple times.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete all seed-created data before seeding (optional).',
        )

    def handle(self, *args, **options):
        User = get_user_model()

        if options['clear']:
            self._clear_seed_data(User)
            return

        self.stdout.write('Seeding categories (10)...')
        categories = self._seed_categories()

        self.stdout.write('Seeding users (2 instructors + 10 students)...')
        instructors, students = self._seed_users(User)

        self.stdout.write('Seeding courses (10 with full content)...')
        courses = self._seed_courses(instructors, categories)

        self.stdout.write('Seeding enrollments...')
        self._seed_enrollments(students, courses)

        self.stdout.write(self.style.SUCCESS('Seed data applied successfully.'))

    def _clear_seed_data(self, User):
        """Remove sample data (optional)."""
        Enrollment.objects.filter(is_active=True).delete()
        Course.objects.all().delete()
        for email, *_ in SEED_INSTRUCTORS:
            User.objects.filter(email=email).delete()
        for email, *_ in SEED_STUDENTS:
            User.objects.filter(email=email).delete()
        Category.objects.filter(name__in=SEED_CATEGORY_NAMES).delete()
        self.stdout.write(self.style.WARNING('Seed data cleared.'))

    def _seed_categories(self):
        categories = []
        for name in SEED_CATEGORY_NAMES:
            cat, created = Category.objects.get_or_create(
                name=name,
                defaults={'is_active': True},
            )
            categories.append(cat)
            if created:
                self.stdout.write(f'  Created category: {name}')
        return categories

    def _seed_users(self, User):
        default_kw = {'is_active': True, 'email_verified_at': timezone.now()}
        instructors = []
        for email, username, first_name, last_name in SEED_INSTRUCTORS:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': username,
                    'first_name': first_name,
                    'last_name': last_name,
                    'role': UserRole.INSTRUCTOR,
                    'is_staff': False,
                    **default_kw,
                },
            )
            if created:
                user.set_password('SeedInstructor1!')
                user.save()
                self.stdout.write(f'  Created instructor: {email}')
            instructors.append(user)

        students = []
        for email, username, first_name, last_name in SEED_STUDENTS:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': username,
                    'first_name': first_name,
                    'last_name': last_name,
                    'role': UserRole.STUDENT,
                    **default_kw,
                },
            )
            if created:
                user.set_password('SeedStudent1!')
                user.save()
                self.stdout.write(f'  Created student: {email}')
            students.append(user)

        return instructors, students

    def _seed_courses(self, instructors, categories):
        # (title, code, description, is_intro, is_auto, max_students, cat_indices, instructor_index)
        courses_spec = [
            (
                'Introduction to Python',
                'SEED-PY101',
                'Learn Python from scratch: variables, control flow, functions, and basic data structures. '
                'This course includes hands-on exercises and small projects to build a solid foundation '
                'for further programming and data science courses.',
                True,
                True,
                60,
                [0, 1],
                0,
            ),
            (
                'Web Development: HTML, CSS & JavaScript',
                'SEED-WEB201',
                'Build modern, responsive websites. Cover HTML5 semantics, CSS Grid and Flexbox, and '
                'JavaScript fundamentals including DOM manipulation and async programming. '
                'By the end you will create a portfolio-ready project.',
                False,
                False,
                40,
                [0, 4],
                0,
            ),
            (
                'Data Science with Python',
                'SEED-DS301',
                'Explore data analysis and visualization using pandas, NumPy, and Matplotlib. '
                'Topics include data cleaning, exploratory analysis, and an introduction to machine learning. '
                'Real-world datasets and case studies are used throughout.',
                False,
                False,
                35,
                [0, 7],
                0,
            ),
            (
                'Linear Algebra for Machine Learning',
                'SEED-MATH201',
                'A practical introduction to linear algebra focused on concepts used in machine learning: '
                'vectors, matrices, eigenvalues, and linear transformations. Includes Python exercises '
                'with NumPy to reinforce theory.',
                False,
                False,
                45,
                [1, 7],
                0,
            ),
            (
                'Introduction to Statistics',
                'SEED-STAT101',
                'Descriptive and inferential statistics: mean, variance, distributions, hypothesis testing, '
                'and confidence intervals. No prior math beyond high school required. '
                'Uses real examples from business and science.',
                False,
                False,
                50,
                [1, 2, 7],
                0,
            ),
            (
                'Business Fundamentals',
                'SEED-BIZ101',
                'Core business concepts: strategy, marketing, operations, and finance. '
                'Learn how organizations work and how to read financial statements. '
                'Suitable for aspiring managers and entrepreneurs.',
                False,
                False,
                55,
                [3, 9],
                1,
            ),
            (
                'User Experience (UX) Design',
                'SEED-UX201',
                'Principles of user-centered design: research, wireframing, prototyping, and usability testing. '
                'Create a complete UX project from discovery to high-fidelity mockups. '
                'Tools include Figma and best practices for accessibility.',
                False,
                False,
                30,
                [4, 9],
                1,
            ),
            (
                'English for Academic Purposes',
                'SEED-LANG101',
                'Improve reading, writing, and presentation skills for academic and professional settings. '
                'Covers essay structure, critical analysis, and formal communication. '
                'Includes practice with feedback and peer review.',
                False,
                False,
                40,
                [5, 9],
                1,
            ),
            (
                'Introduction to DevOps & CI/CD',
                'SEED-DEVOPS201',
                'Automate build, test, and deployment with Git, Docker, and CI/CD pipelines. '
                'Topics include version control workflows, containerization, and cloud basics (AWS/GCP). '
                'Hands-on labs with real tooling.',
                False,
                False,
                35,
                [0, 8],
                1,
            ),
            (
                'Communication & Teamwork',
                'SEED-SOFT101',
                'Develop soft skills essential for the workplace: clear communication, giving feedback, '
                'managing conflict, and collaborating in diverse teams. Includes role-plays and '
                'self-assessment tools.',
                False,
                False,
                60,
                [9],
                1,
            ),
        ]
        created_courses = []
        for idx, spec in enumerate(courses_spec):
            (title, code, description, is_intro, is_auto, max_students, cat_indices, instr_idx) = spec
            instructor = instructors[instr_idx]
            image_url, video_url = SEED_COURSE_MEDIA[idx] if idx < len(SEED_COURSE_MEDIA) else (DEFAULT_COURSE_IMAGE, '')
            course, created = Course.objects.get_or_create(
                course_code=code,
                defaults={
                    'title': title,
                    'description': description,
                    'instructor': instructor,
                    'status': CourseStatus.ACTIVE,
                    'is_active': True,
                    'is_introduction': is_intro,
                    'is_auto_enrolled': is_auto,
                    'max_students': max_students,
                    'image_url': image_url,
                    'video_url': video_url,
                },
            )
            if created:
                course.categories.set([categories[i] for i in cat_indices])
                created_courses.append(course)
                self.stdout.write(f'  Created course: {code} - {title}')
            else:
                # Update existing course with media if missing
                if not course.image_url or not course.video_url:
                    course.image_url = course.image_url or image_url
                    course.video_url = course.video_url or video_url
                    course.save(update_fields=['image_url', 'video_url'])
                created_courses.append(course)

        return created_courses

    def _seed_enrollments(self, students, courses):
        # Spread enrollments: each student in several courses, each course with several students
        # (student_index, course_index)
        enrollments_spec = [
            (0, 0), (0, 1), (0, 2), (0, 4), (0, 9),
            (1, 0), (1, 1), (1, 3), (1, 5),
            (2, 0), (2, 2), (2, 4), (2, 7),
            (3, 0), (3, 1), (3, 5), (3, 8),
            (4, 0), (4, 2), (4, 6), (4, 9),
            (5, 0), (5, 3), (5, 5), (5, 8),
            (6, 0), (6, 1), (6, 4), (6, 7),
            (7, 0), (7, 2), (7, 5), (7, 9),
            (8, 0), (8, 1), (8, 6), (8, 8),
            (9, 0), (9, 3), (9, 4), (9, 7), (9, 9),
        ]
        for si, ci in enrollments_spec:
            student, course = students[si], courses[ci]
            if not course.is_active or course.status != CourseStatus.ACTIVE:
                continue
            if Enrollment.objects.filter(student=student, course=course, is_active=True).exists():
                continue
            Enrollment.objects.create(
                student=student,
                course=course,
                status=Enrollment.STATUS_ACTIVE,
                is_active=True,
            )
            self.stdout.write(f'  Enrolled {student.email} in {course.course_code}')
