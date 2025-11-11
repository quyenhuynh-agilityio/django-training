import uuid
from django.core.paginator import Paginator
from django.core.cache import cache

from courses.models import Course, Category
from enrollments.models import Enrollment

DEFAULT_PAGE_SIZE = 3  # Default number of courses per page (small, for better UX)
CATEGORY_CACHE_KEY = "all_categories"  # Cache key to avoid repeated DB hits


def get_courses_for_user(user):
    # Prefetch related categories in one query to reduce N+1 query problem
    qs = Course.objects.prefetch_related("categories")

    if not user.is_authenticated:
        # Only show active courses for anonymous users
        return qs.filter(is_active=True)

    if user.is_staff or user.is_superuser:
        # Staff can see all courses, including inactive
        return qs

    # Regular authenticated users: only active courses
    return qs.filter(is_active=True)


def get_user_enrolled_ids(user):
    if not user.is_authenticated:
        # No enrollments for anonymous users
        return set()

    # Efficiently fetch only course IDs using values_list, convert to set for O(1) lookups
    return set(
        Enrollment.objects.filter(user=user, is_active=True).values_list(
            "course_id", flat=True
        )
    )


def filter_by_category(qs, category_id):
    if not category_id:
        # Return unfiltered queryset and empty category info
        return qs, "", ""

    try:
        # Validate that the category ID is a valid UUID
        uuid.UUID(category_id)
        # Only fetch 'id' and 'name' fields to reduce DB load (optimization)
        category = Category.objects.only("id", "name").get(id=category_id)
        # Filter queryset by category (many-to-many relation)
        return qs.filter(categories=category), category.name, category_id
    except (ValueError, Category.DoesNotExist, TypeError):
        # Return empty queryset on invalid input to prevent errors
        return qs.none(), "", ""


def get_all_categories():
    # Try cache first to reduce DB queries (performance)
    categories = cache.get(CATEGORY_CACHE_KEY)
    if categories is None:
        # Fetch all categories ordered alphabetically
        categories = Category.objects.order_by("name").all()
        # Cache for 5 minutes (short-lived to reflect changes in categories)
        cache.set(CATEGORY_CACHE_KEY, categories, 300)
    return categories


def build_course_list_context(request, qs, page_size=DEFAULT_PAGE_SIZE):
    # -----------------------
    # Search filter
    # -----------------------
    # Get the search query from request and strip whitespace
    search = request.GET.get("q", "").strip()
    if search:
        # Case-insensitive search on title (uses SQL ILIKE on PostgreSQL)
        qs = qs.filter(title__icontains=search)

    # -----------------------
    # Category filter
    # -----------------------
    category_id = request.GET.get("category", "").strip()
    # Reuse filtering helper for category (single responsibility)
    qs, category_name, selected_category = filter_by_category(qs, category_id)

    # -----------------------
    # Pagination
    # -----------------------
    page_number = request.GET.get("page", 1)
    # Paginator handles slicing efficiently (no need to manually slice queryset)
    paginator = Paginator(qs, page_size)
    # Get page object safely (handles invalid page numbers)
    page_obj = paginator.get_page(page_number)

    # -----------------------
    # Build context
    # -----------------------
    return {
        "courses": page_obj.object_list,  # List of courses for current page
        "page_obj": page_obj,  # Full pagination info for templates
        "query": search,  # The search query string
        "category": selected_category,  # Selected category ID
        "category_name": category_name,  # Selected category name
        "categories": get_all_categories(),  # All categories cached
        "enrolled_ids": get_user_enrolled_ids(
            request.user
        ),  # IDs for quick template lookup
    }
