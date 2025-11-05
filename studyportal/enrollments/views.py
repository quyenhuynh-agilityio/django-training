from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render
from courses.models import Course
from .models import Enrollment


@login_required(login_url="/accounts/login/")
def enrolled_courses(request):
    query = ""
    category = ""

    # Handle POST search/category/pagination
    if request.method == "POST":
        query = request.POST.get("q", "").strip()
        category = request.POST.get("category", "").strip()
        page_number = request.POST.get("page", 1)
    else:
        page_number = 1

    # Get enrolled courses as a queryset (not a list) for better performance
    enrollments = Enrollment.objects.filter(
        user=request.user, is_deleted=False
    ).select_related("course")

    # Get courses from enrollments using queryset
    enrolled_course_ids = enrollments.values_list("course_id", flat=True)
    courses = Course.objects.filter(id__in=enrolled_course_ids, is_active=True)

    # Apply search filter if provided
    if query:
        courses = courses.filter(title__icontains=query)

    # Build categories list from enrolled courses (efficiently using values_list)
    all_categories = (
        Course.objects.filter(id__in=enrolled_course_ids, is_active=True)
        .values_list("category", flat=True)
        .distinct()
    )
    categories = sorted({cat.strip() for cat in all_categories if cat})

    # Only filter by category if one is explicitly selected
    if category:
        courses = courses.filter(category=category)

    # Pagination to match course_list template expectations
    paginator = Paginator(courses, 3)
    page_obj = paginator.get_page(page_number)

    # Enrolled course ids for template logic (all enrolled IDs, not just current page)
    enrolled_ids = list(enrolled_course_ids)

    context = {
        "courses": page_obj.object_list,
        "query": query,
        "category": category,
        "categories": categories,
        "enrolled_ids": enrolled_ids,
        "page_obj": page_obj,
    }

    return render(request, "courses/course_list.html", context)
