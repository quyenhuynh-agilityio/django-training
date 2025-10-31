from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Course
from enrollments.models import Enrollment


def course_list(request):
    # Handle search query and category from POST
    query = ""
    category = ""
    if request.method == "POST":
        query = request.POST.get("q", "").strip()
        category = request.POST.get("category", "").strip()

    # Get all active courses
    courses = Course.objects.filter(is_active=True)

    # Filter by search query
    if query:
        courses = courses.filter(title__icontains=query)

    # Get unique, normalized categories
    all_categories = Course.objects.filter(is_active=True).values_list(
        "category", flat=True
    )
    categories = sorted(set([cat.strip() for cat in all_categories if cat]))

    # Default category to first if none selected
    if not category and categories:
        category = categories[0]

    # Filter courses by selected category
    if category:
        courses = courses.filter(category=category)

    # Get enrolled course IDs for the current user
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
            "categories": categories,
            "enrolled_ids": enrolled_ids,
        },
    )


@login_required(login_url="/accounts/login/")
def enroll_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    Enrollment.objects.get_or_create(
        user=request.user, course=course, defaults={"is_deleted": False}
    )
    return redirect("enrolled_courses")
