from django.core.paginator import Paginator

from categories.models import Category
from core.cache import build_cache_key, cache_get_or_set, get_timeout
from courses.models import Course
from enrollments.models import Enrollment

DEFAULT_PAGE_SIZE = 3  # Default number of courses per page (small, for better UX)
CATEGORY_CACHE_KEY = 'all_categories'  # Cache key to avoid repeated DB hits


def get_user_enrolled_ids(user):
    if not user.is_authenticated:
        # No enrollments for anonymous users
        return set()

    # Efficiently fetch only course IDs using values_list, convert to set for O(1) lookups
    return set(
        Enrollment.objects.filter(student=user, is_active=True).values_list('course_id', flat=True)
    )


def get_all_categories():
    cache_key = build_cache_key(CATEGORY_CACHE_KEY)
    timeout = get_timeout('CATEGORY_CACHE_TIMEOUT', 300)

    return cache_get_or_set(
        cache_key,
        lambda: Category.objects.order_by('name').all(),
        timeout=timeout,
    )


def filter_courses_by_user(courses, user):
    return courses if user.is_staff or user.is_superuser else courses.filter(is_active=True)


def filter_courses_by_view(courses, view, user):
    # Convert to match-case if there are more views later
    return (
        courses.filter(enrollments__student=user, enrollments__is_active=True).distinct()
        if view == 'enrolled'
        else courses
    )


def filter_courses_by_search_query(courses, query):
    # Case-insensitive search on title (uses SQL ILIKE on PostgreSQL)
    return courses.filter(title__icontains=query) if query else courses


def filter_courses_by_category(courses, category_id):
    return courses.filter(categories__id=category_id) if category_id else courses


def get_courses(user, view, query, category_id):
    # Optimized queryset for course list pages to avoid N+1 when rendering
    # instructor and category data.
    courses = Course.objects.select_related('instructor').prefetch_related('categories')

    # Filter by user type
    courses = filter_courses_by_user(courses, user)

    # Filter by view
    courses = filter_courses_by_view(courses, view, user)

    # Filter by search query
    courses = filter_courses_by_search_query(courses, query)

    # Filter by category
    courses = filter_courses_by_category(courses, category_id)

    return courses


def get_category(category_id):
    if not category_id:
        return '', ''
    return Category.objects.filter(id=category_id).values_list('name', 'id').first() or ('', '')


def build_course_list_context(request, view='all', page_size=DEFAULT_PAGE_SIZE):
    # view: "all" or "enrolled" -> can be extended later if there are more views

    search_query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '').strip()

    # Get courses - filtered by criteria
    courses = get_courses(request.user, view, search_query, category_id)

    # Get category
    category_name, selected_category = get_category(category_id)

    # -----------------------
    # Pagination
    # -----------------------
    page_number = request.GET.get('page', 1)
    # Paginator handles slicing efficiently (no need to manually slice queryset)
    paginator = Paginator(courses, page_size)
    # Get page object safely (handles invalid page numbers)
    page_obj = paginator.get_page(page_number)

    # -----------------------
    # Build context
    # -----------------------
    return {
        'courses': page_obj.object_list,  # List of courses for current page
        'page_obj': page_obj,  # Full pagination info for templates
        'query': search_query,  # The search query string
        'category': selected_category,  # Selected category ID
        'category_name': category_name,  # Selected category name
        'categories': get_all_categories(),  # All categories cached
        'enrolled_ids': get_user_enrolled_ids(request.user),  # IDs for quick template lookup
    }
