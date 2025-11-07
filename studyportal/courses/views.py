from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required

from core.utils import get_courses_for_user, build_course_list_context
from .models import Course
from enrollments.models import Enrollment


@csrf_protect
def course_list(request):
    """
    Show all courses list page.

    INPUT:
        request (HttpRequest)

    OUTPUT:
        Render template: courses/course_list.html
        Context from build_course_list_context()
    """
    courses = get_courses_for_user(request.user)
    context = build_course_list_context(request, courses)
    return render(request, "courses/course_list.html", context)


@login_required(login_url="/accounts/login/")
def enroll_course(request, course_id):
    """
    Enroll user into course.

    INPUT:
        course_id (UUID)

    OUTPUT:
        Redirect to /my-courses/
    """
    course = get_object_or_404(Course, id=course_id, is_active=True)

    Enrollment.objects.get_or_create(
        user=request.user,
        course=course,
        defaults={"is_active": True},
    )
    return redirect("enrolled_courses")


@login_required(login_url="/accounts/login/")
def enrolled_courses(request):
    """
    Show only user's enrolled courses.

    INPUT:
        request (HttpRequest)

    OUTPUT:
        Render same course_list template, filtered
    """
    courses = get_courses_for_user(request.user, enrolled_only=True)

    enrolled_ids = list(
        Enrollment.objects.filter(user=request.user, is_active=True).values_list(
            "course_id", flat=True
        )
    )

    context = build_course_list_context(request, courses, enrolled_ids=enrolled_ids)
    return render(request, "courses/course_list.html", context)
