import pytest

from django.core.cache import cache
from django.test import RequestFactory

from utils.course_queries import (
    build_course_list_context,
    filter_courses_by_category,
    filter_courses_by_search_query,
    filter_courses_by_user,
    filter_courses_by_view,
    get_all_categories,
    get_category,
    get_courses,
    get_user_enrolled_ids,
)

pytestmark = pytest.mark.django_db


def test_get_user_enrolled_ids_anonymous_user():
    """Test that anonymous users return empty set"""
    from django.contrib.auth.models import AnonymousUser

    user = AnonymousUser()
    enrolled_ids = get_user_enrolled_ids(user)

    assert enrolled_ids == set()
    assert len(enrolled_ids) == 0


def test_get_user_enrolled_ids_authenticated_user(create_user, create_course, create_enrollment):
    """Test that authenticated users get their enrolled course IDs"""
    user = create_user(email='student@example.com', username='student', role='student')
    course1 = create_course(course_code='CRS001')
    course2 = create_course(course_code='CRS002')
    create_enrollment(student=user, course=course1)
    create_enrollment(student=user, course=course2)

    enrolled_ids = get_user_enrolled_ids(user)

    assert len(enrolled_ids) == 2
    assert course1.id in enrolled_ids
    assert course2.id in enrolled_ids


def test_get_all_categories_cached(create_category):
    """Test that categories are cached"""
    # Clear cache first
    cache.clear()
    create_category(name='Backend')
    create_category(name='Frontend')

    # First call should hit database
    categories1 = get_all_categories()
    assert len(categories1) == 2

    # Second call should use cache
    categories2 = get_all_categories()
    assert len(categories2) == 2
    assert list(categories1) == list(categories2)


def test_get_all_categories_ordering(create_category):
    """Test that categories are ordered by name"""
    cache.clear()
    create_category(name='Zebra')
    create_category(name='Alpha')
    create_category(name='Beta')

    categories = get_all_categories()
    names = [cat.name for cat in categories]
    assert names == ['Alpha', 'Beta', 'Zebra']


def test_filter_courses_by_user_staff(create_user, create_course):
    """Test that staff users see all courses including inactive"""
    staff_user = create_user(email='staff@example.com', username='staff', role='admin')
    staff_user.is_staff = True
    staff_user.save()

    active_course = create_course(course_code='CRS003', is_active=True)
    inactive_course = create_course(course_code='CRS004', is_active=False)

    from courses.models import Course

    courses = Course.objects.all()
    filtered = filter_courses_by_user(courses, staff_user)

    assert active_course in filtered
    assert inactive_course in filtered


def test_filter_courses_by_user_regular(create_user, create_course):
    """Test that regular users only see active courses"""
    user = create_user(email='user@example.com', username='user', role='student')

    active_course = create_course(course_code='CRS005', is_active=True)
    inactive_course = create_course(course_code='CRS006', is_active=False)

    from courses.models import Course

    courses = Course.objects.all()
    filtered = filter_courses_by_user(courses, user)

    assert active_course in filtered
    assert inactive_course not in filtered


def test_filter_courses_by_view_enrolled(create_user, create_course, create_enrollment):
    """Test filtering courses by enrolled view"""
    user = create_user(email='student@example.com', username='student', role='student')
    enrolled_course = create_course(course_code='CRS007')
    not_enrolled_course = create_course(course_code='CRS008')
    create_enrollment(student=user, course=enrolled_course)

    from courses.models import Course

    courses = Course.objects.all()
    filtered = filter_courses_by_view(courses, 'enrolled', user)

    assert enrolled_course in filtered
    assert not_enrolled_course not in filtered


def test_filter_courses_by_view_all(create_user, create_course):
    """Test filtering courses by all view"""
    user = create_user(email='student@example.com', username='student', role='student')
    course1 = create_course(course_code='CRS009')
    course2 = create_course(course_code='CRS010')

    from courses.models import Course

    courses = Course.objects.all()
    filtered = filter_courses_by_view(courses, 'all', user)

    assert course1 in filtered
    assert course2 in filtered


def test_filter_courses_by_search_query(create_course):
    """Test filtering courses by search query"""
    python_course = create_course(course_code='CRS011', title='Python Programming')
    java_course = create_course(course_code='CRS012', title='Java Basics')

    from courses.models import Course

    courses = Course.objects.all()
    filtered = filter_courses_by_search_query(courses, 'Python')

    assert python_course in filtered
    assert java_course not in filtered


def test_filter_courses_by_search_query_empty(create_course):
    """Test that empty search query returns all courses"""
    course1 = create_course(course_code='CRS013')
    course2 = create_course(course_code='CRS014')

    from courses.models import Course

    courses = Course.objects.all()
    filtered = filter_courses_by_search_query(courses, '')

    assert course1 in filtered
    assert course2 in filtered


def test_filter_courses_by_category(create_category, create_course):
    """Test filtering courses by category"""
    category = create_category(name='Backend')
    course1 = create_course(course_code='CRS015')
    course2 = create_course(course_code='CRS016')
    course1.categories.set([category])
    course2.categories.set([])

    from courses.models import Course

    courses = Course.objects.all()
    filtered = filter_courses_by_category(courses, str(category.id))

    assert course1 in filtered
    assert course2 not in filtered


def test_filter_courses_by_category_none(create_course):
    """Test that None category_id returns all courses"""
    course1 = create_course(course_code='CRS017')
    course2 = create_course(course_code='CRS018')

    from courses.models import Course

    courses = Course.objects.all()
    filtered = filter_courses_by_category(courses, None)

    assert course1 in filtered
    assert course2 in filtered


def test_get_courses_complex_filter(create_user, create_category, create_course):
    """Test get_courses with multiple filters"""
    user = create_user(email='student@example.com', username='student', role='student')
    category = create_category(name='Backend')
    course1 = create_course(course_code='CRS019', title='Python Course', is_active=True)
    course2 = create_course(course_code='CRS020', title='Java Course', is_active=True)
    course1.categories.set([category])

    courses = get_courses(user, 'all', 'Python', str(category.id))

    assert course1 in courses
    assert course2 not in courses


def test_get_category_valid_id(create_category):
    """Test get_category with valid category ID"""
    category = create_category(name='Backend')
    name, cat_id = get_category(str(category.id))

    assert name == 'Backend'
    # cat_id is returned as UUID object, convert to string for comparison
    assert str(cat_id) == str(category.id)


def test_get_category_invalid_id():
    """Test get_category with invalid category ID"""
    name, cat_id = get_category('00000000-0000-0000-0000-000000000000')

    assert name == ''
    assert cat_id == ''


def test_get_category_empty():
    """Test get_category with empty string"""
    name, cat_id = get_category('')

    assert name == ''
    assert cat_id == ''


def test_get_category_none():
    """Test get_category with None"""
    name, cat_id = get_category(None)

    assert name == ''
    assert cat_id == ''


def test_build_course_list_context_all_view(create_user, create_course):
    """Test build_course_list_context with all view"""
    user = create_user(email='user@example.com', username='user', role='student')
    create_course(course_code='CRS021', title='Test Course')

    factory = RequestFactory()
    request = factory.get('/courses/')
    request.user = user

    context = build_course_list_context(request, view='all')

    assert 'courses' in context
    assert 'page_obj' in context
    assert 'query' in context
    assert 'category' in context
    assert 'category_name' in context
    assert 'categories' in context
    assert 'enrolled_ids' in context
    assert len(context['courses']) > 0


def test_build_course_list_context_enrolled_view(create_user, create_course, create_enrollment):
    """Test build_course_list_context with enrolled view"""
    user = create_user(email='student@example.com', username='student', role='student')
    enrolled_course = create_course(course_code='CRS022')
    not_enrolled_course = create_course(course_code='CRS023')
    create_enrollment(student=user, course=enrolled_course)

    factory = RequestFactory()
    request = factory.get('/courses/my-courses/')
    request.user = user

    context = build_course_list_context(request, view='enrolled')

    course_ids = [str(course.id) for course in context['courses']]
    assert str(enrolled_course.id) in course_ids
    assert str(not_enrolled_course.id) not in course_ids


def test_build_course_list_context_with_search(create_user, create_course):
    """Test build_course_list_context with search query"""
    user = create_user(email='user@example.com', username='user', role='student')
    create_course(course_code='CRS024', title='Python Programming')
    create_course(course_code='CRS025', title='Java Basics')

    factory = RequestFactory()
    request = factory.get('/courses/?q=Python')
    request.user = user

    context = build_course_list_context(request)

    course_titles = [course.title for course in context['courses']]
    assert 'Python Programming' in course_titles
    assert 'Java Basics' not in course_titles
    assert context['query'] == 'Python'


def test_build_course_list_context_with_category(create_user, create_category, create_course):
    """Test build_course_list_context with category filter"""
    user = create_user(email='user@example.com', username='user', role='student')
    category = create_category(name='Backend')
    course1 = create_course(course_code='CRS026')
    course2 = create_course(course_code='CRS027')
    course1.categories.set([category])

    factory = RequestFactory()
    request = factory.get(f'/courses/?category={category.id}')
    request.user = user

    context = build_course_list_context(request)

    course_ids = [str(course.id) for course in context['courses']]
    assert str(course1.id) in course_ids
    assert str(course2.id) not in course_ids
    # category can be UUID object or string, convert to string for comparison
    assert str(context['category']) == str(category.id)
    assert context['category_name'] == 'Backend'


def test_build_course_list_context_pagination(create_user, create_course):
    """Test build_course_list_context pagination"""
    user = create_user(email='user@example.com', username='user', role='student')
    # Create more courses than default page size (3)
    for i in range(5):
        create_course(course_code=f'CRS{28+i:03d}', title=f'Course {i}')

    factory = RequestFactory()
    request = factory.get('/courses/')
    request.user = user

    context = build_course_list_context(request, page_size=3)

    assert len(context['courses']) == 3
    assert context['page_obj'].has_other_pages() is True


def test_build_course_list_context_page_number(create_user, create_course):
    """Test build_course_list_context with specific page number"""
    user = create_user(email='user@example.com', username='user', role='student')
    for i in range(5):
        create_course(course_code=f'CRS{33+i:03d}', title=f'Course {i}')

    factory = RequestFactory()
    request = factory.get('/courses/?page=2')
    request.user = user

    context = build_course_list_context(request, page_size=3)

    assert len(context['courses']) == 2  # Remaining courses on page 2
    assert context['page_obj'].number == 2
