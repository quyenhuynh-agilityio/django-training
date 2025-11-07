"""
Shared utility functions for course-related views.
Optimized, documented with INPUT/OUTPUT for clarity.
"""

import uuid
from django.core.paginator import Paginator
from courses.models import Course, Category
from enrollments.models import Enrollment


def get_course_filter_params(request):
    """
    Extract filter inputs from request.

    INPUT:
        request (HttpRequest) - GET params:
            q = search text
            category = UUID of category
            page = page number

    OUTPUT:
        (str query, str category, int page_number)
    """
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    page_number = request.GET.get("page", 1)
    return query, category, page_number


def filter_courses_by_category(courses, category):
    """
    Filter courses by active category UUID.

    INPUT:
        courses (QuerySet[Course])
        category (str UUID or empty)

    OUTPUT:
        (
            QuerySet filtered_courses,
            str category_name,   # label for UI
            str category         # returned valid UUID or ""
        )
    """
    category_name = ""

    if category:
        try:
            uuid.UUID(category)  # validate UUID
            category_obj = Category.objects.only("id", "name").get(
                id=category, is_active=True
            )
            courses = courses.filter(categories=category_obj)
            category_name = category_obj.name
        except (Category.DoesNotExist, ValueError, TypeError):
            courses = courses.none()
            category, category_name = "", ""

    return courses, category_name, category


def get_categories_for_courses(course_ids=None):
    """
    Get categories linked to active courses.

    INPUT:
        course_ids (list[UUID] or None)

    OUTPUT:
        QuerySet[Category] ordered by name
    """
    qs = Course.objects.filter(is_active=True, categories__isnull=False)

    if course_ids is not None:
        if not course_ids:  # Empty list means no courses
            return Category.objects.none()
        qs = qs.filter(id__in=course_ids)

    category_ids = qs.values_list("categories__id", flat=True).distinct()

    return Category.objects.filter(id__in=category_ids, is_active=True).order_by("name")


def get_courses_for_user(user, enrolled_only=False):
    """
    Return course list based on user type and mode.

    INPUT:
        user (User or AnonymousUser)
        enrolled_only (bool)

    OUTPUT:
        QuerySet[Course]
    """
    if enrolled_only:
        if not user.is_authenticated:
            return Course.objects.none()

        enrolled_ids = Enrollment.objects.filter(user=user, is_active=True).values_list(
            "course_id", flat=True
        )

        return Course.objects.filter(
            id__in=enrolled_ids, is_active=True
        ).select_related()

    # Normal full list mode -------------------------

    if not user.is_authenticated:
        return Course.objects.filter(is_active=True).select_related()

    if user.is_staff or user.is_superuser:
        return Course.objects.all().select_related()

    return Course.objects.filter(is_active=True).select_related()


def build_course_list_context(request, courses, enrolled_ids=None, page_size=3):
    """
    Build final context for course list page.

    INPUT:
        request (HttpRequest)
        courses (QuerySet[Course])
        enrolled_ids (list[UUID] or None)
        page_size (int)

    OUTPUT (dict):
        {
            "courses": page_obj.object_list,
            "query": str,
            "category": str,
            "category_name": str,
            "categories": QuerySet[Category],
            "enrolled_ids": list[UUID],
            "page_obj": Paginator.page
        }
    """
    query, category, page_number = get_course_filter_params(request)

    if query:
        courses = courses.filter(title__icontains=query)

    courses, category_name, category = filter_courses_by_category(courses, category)

    categories = (
        get_categories_for_courses(enrolled_ids)
        if enrolled_ids
        else get_categories_for_courses()
    )

    paginator = Paginator(courses, page_size)
    page_obj = paginator.get_page(page_number)

    if enrolled_ids is None and request.user.is_authenticated:
        enrolled_ids = list(
            Enrollment.objects.filter(user=request.user, is_active=True).values_list(
                "course_id", flat=True
            )
        )

    return {
        "courses": page_obj.object_list,
        "query": query,
        "category": category,
        "category_name": category_name,
        "categories": categories,
        "enrolled_ids": enrolled_ids or [],
        "page_obj": page_obj,
    }
