from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from enrollments.models import Enrollment
from .models import Course
from core.utils import get_courses_for_user, build_course_list_context


# This ensures Django regenerates a valid CSRF(Cross-Site Request Forgery) token properly.
@csrf_protect
def course_list(request):
    """
    Display course list for all users (authenticated and unauthenticated).
    Shows courses based on user role and authentication status.
    """
    # Get courses based on user authentication and role
    courses = get_courses_for_user(request.user, enrolled_only=False)

    # Build context with filtering, pagination, etc.
    context = build_course_list_context(request, courses)

    return render(request, "courses/course_list.html", context)


@login_required(login_url="/accounts/login/")
def enroll_course(request, course_id):
    """
    Enroll the authenticated user in a course if not already enrolled.
    """
    course = get_object_or_404(Course, id=course_id)

    Enrollment.objects.get_or_create(
        user=request.user, course=course, defaults={"is_deleted": False}
    )

    return redirect("enrolled_courses")
