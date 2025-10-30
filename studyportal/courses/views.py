from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Course
from enrollments.models import Enrollment


def course_list(request):
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()

    courses = Course.objects.filter(is_active=True)

    if query:
        courses = courses.filter(title__icontains=query)

    if category:
        courses = courses.filter(category__icontains=category)

    enrolled_ids = []
    if request.user.is_authenticated:
        enrolled_ids = Enrollment.objects.filter(
            user=request.user, is_deleted=False
        ).values_list("course_id", flat=True)

    return render(
        request,
        "courses/course_list.html",
        {
            "courses": courses,
            "query": query,
            "category": category,
            "enrolled_ids": enrolled_ids,
        },
    )


@login_required(login_url="/accounts/login/")
def enroll_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    # Prevent duplicate enrollment
    Enrollment.objects.get_or_create(
        user=request.user, course=course, defaults={"is_deleted": False}
    )

    return redirect("enrolled_courses")
