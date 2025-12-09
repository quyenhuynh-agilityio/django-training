import pytest

from courses.api.filters import CourseFilter
from courses.models import Course

pytestmark = pytest.mark.django_db


def test_filter_by_title_icontains(create_course):
    python_course = create_course(title='Python Basics', course_code='PY101')
    create_course(title='Django Advanced', course_code='DJ201')

    filterset = CourseFilter(data={'title': 'python'}, queryset=Course.objects.all())

    assert list(filterset.qs) == [python_course]


def test_filter_by_category(create_course, create_category):
    category = create_category(name='Data Science')
    course_with_category = create_course(course_code='DS101')
    course_with_category.categories.add(category)
    other_course = create_course(course_code='WEB101')

    filterset = CourseFilter(data={'category': str(category.id)}, queryset=Course.objects.all())

    assert course_with_category in filterset.qs
    assert other_course not in filterset.qs


def test_filter_by_status(create_course):
    active_course = create_course(status=Course.STATUS_ACTIVE, course_code='ACT101')
    draft_course = create_course(status=Course.STATUS_DRAFT, course_code='DRF101')

    filterset = CourseFilter(data={'status': Course.STATUS_DRAFT}, queryset=Course.objects.all())

    assert list(filterset.qs) == [draft_course]
    assert active_course not in filterset.qs
