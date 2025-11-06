from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from core.utils import get_courses_for_user, build_course_list_context


@login_required(login_url="/accounts/login/")
def enrolled_courses(request):
    """
    Display enrolled courses for authenticated users.
    Shows courses based on user role and authentication status.
    """
    # Get enrolled courses for the user
    courses = get_courses_for_user(request.user, enrolled_only=True)

    # Get enrolled course IDs for category filtering
    from .models import Enrollment

    enrolled_ids = list(
        Enrollment.objects.filter(user=request.user, is_active=True).values_list(
            "course_id", flat=True
        )
    )

    # Build context with filtering, pagination, etc.
    context = build_course_list_context(request, courses, enrolled_ids=enrolled_ids)

    return render(request, "courses/course_list.html", context)
