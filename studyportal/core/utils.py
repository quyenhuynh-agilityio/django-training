"""
Shared utility functions for course-related views.
"""

import uuid
from django.core.paginator import Paginator
from courses.models import Course, Category


def get_course_filter_params(request):
    """
    Extract filter parameters from POST request.
    Returns: tuple of (query, category, page_number)
    """
    if request.method == "POST":
        query = request.POST.get("q", "").strip()
        category = request.POST.get("category", "").strip()
        page_number = request.POST.get("page", 1)
    else:
        query = ""
        category = ""
        page_number = 1

    return query, category, page_number


def filter_courses_by_category(courses, category):
    """
    Filter courses by category if provided.
    Returns: tuple of (filtered_courses, category_name)
    """
    category_name = ""

    if category:
        try:
            # Validate that category is a valid UUID string before querying
            uuid.UUID(category)  # This will raise ValueError if not a valid UUID
            category_obj = Category.objects.get(id=category, is_active=True)
            courses = courses.filter(categories=category_obj)
            category_name = category_obj.name  # Store name for template display
        except (Category.DoesNotExist, ValueError, TypeError):
            # Invalid category UUID or not a valid UUID format - return empty queryset
            courses = courses.none()
            category = ""
            category_name = ""

    return courses, category_name, category


def get_categories_for_courses(course_ids=None):
    """
    Get distinct categories from active courses.
    If course_ids is provided, only get categories for those courses.
    """
    if course_ids is not None:
        category_ids = (
            Course.objects.filter(
                id__in=course_ids, is_active=True, categories__isnull=False
            )
            .values_list("categories__id", flat=True)
            .distinct()
        )
    else:
        category_ids = (
            Course.objects.filter(is_active=True, categories__isnull=False)
            .values_list("categories__id", flat=True)
            .distinct()
        )

    return Category.objects.filter(id__in=category_ids, is_active=True).order_by("name")


def get_courses_for_user(user, enrolled_only=False):
    """
    Get courses based on user authentication and role.

    Args:
        user: The user object (can be AnonymousUser)
        enrolled_only: If True, only return enrolled courses

    Returns:
        QuerySet of courses
    """
    if enrolled_only:
        # Only return enrolled courses for authenticated users
        if not user.is_authenticated:
            return Course.objects.none()

        from enrollments.models import Enrollment

        enrolled_course_ids = Enrollment.objects.filter(
            user=user, is_deleted=False
        ).values_list("course_id", flat=True)

        return Course.objects.filter(
            id__in=enrolled_course_ids, is_active=True
        ).prefetch_related("categories")

    # For course list page
    if not user.is_authenticated:
        # Unauthenticated users see all active courses
        return Course.objects.filter(is_active=True).prefetch_related("categories")

    # Authenticated users
    if user.is_staff or user.is_superuser:
        # Staff and superusers see all courses (active and inactive) for management
        return Course.objects.all().prefetch_related("categories")

    # Regular authenticated users see all active courses
    return Course.objects.filter(is_active=True).prefetch_related("categories")


def build_course_list_context(request, courses, enrolled_ids=None, page_size=3):
    """
    Build context dictionary for course list views.

    Args:
        request: HTTP request object
        courses: QuerySet of courses
        enrolled_ids: List of enrolled course IDs (for authenticated users)
        page_size: Number of courses per page

    Returns:
        Dictionary with context for template
    """
    # Get filter parameters
    query, category, page_number = get_course_filter_params(request)

    # Apply search filter
    if query:
        courses = courses.filter(title__icontains=query)

    # Filter by category
    courses, category_name, category = filter_courses_by_category(courses, category)

    # Get categories for filter dropdown
    if enrolled_ids:
        # For enrolled courses, only show categories from enrolled courses
        categories = get_categories_for_courses(enrolled_ids)
    else:
        # For all courses, show all categories
        categories = get_categories_for_courses()

    # Pagination
    paginator = Paginator(courses, page_size)
    page_obj = paginator.get_page(page_number)

    # Get enrolled course IDs for authenticated users if not provided
    if enrolled_ids is None and request.user.is_authenticated:
        from enrollments.models import Enrollment

        enrolled_ids = list(
            Enrollment.objects.filter(user=request.user, is_deleted=False).values_list(
                "course_id", flat=True
            )
        )
    elif enrolled_ids is None:
        enrolled_ids = []

    return {
        "courses": page_obj.object_list,
        "query": query,
        "category": category,  # UUID for form submissions
        "category_name": category_name,  # Name for display
        "categories": categories,
        "enrolled_ids": enrolled_ids,
        "page_obj": page_obj,
    }
