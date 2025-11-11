from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required

from core.utils import build_course_list_context
from .models import Course
from enrollments.models import Enrollment


@csrf_protect
def course_list(request):
    context = build_course_list_context(request)
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
    context = build_course_list_context(request, view="enrolled")
    return render(request, "courses/course_list.html", context)
