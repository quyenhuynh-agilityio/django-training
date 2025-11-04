from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render
from .models import Enrollment


@login_required(login_url="/accounts/login/")
def enrolled_courses(request):
    enrollments = Enrollment.objects.filter(user=request.user, is_deleted=False)
    courses = [en.course for en in enrollments]

    # Build categories list from enrolled courses
    categories = sorted(
        {c.category.strip() for c in courses if getattr(c, "category", None)}
    )

    # Pagination to match course_list template expectations
    paginator = Paginator(courses, 3)
    page_obj = paginator.get_page(1)

    # Enrolled course ids for template logic
    enrolled_ids = [c.id for c in courses]

    context = {
        "courses": page_obj.object_list,
        "query": "",
        "category": "",
        "categories": categories,
        "enrolled_ids": enrolled_ids,
        "page_obj": page_obj,
    }

    return render(request, "courses/course_list.html", context)
