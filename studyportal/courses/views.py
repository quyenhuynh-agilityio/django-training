from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Course
from enrollments.models import Enrollment
import re


# Utility to extract YouTube video ID from any YouTube link
def extract_youtube_id(value):
    if not value:
        return ""

    patterns = [
        r"v=([^&]+)",  # ?v=VIDEOID
        r"youtu\.be/([^?&]+)",  # youtu.be/VIDEOID
        r"embed/([^?&]+)",  # embed/VIDEOID
    ]
    for pattern in patterns:
        match = re.search(pattern, value)
        if match:
            return match.group(1)

    # If no match, assume it's already an ID
    return value.strip()


def course_list(request):
    query = ""
    category = ""

    # Handle POST search/category (to avoid showing query in URL)
    if request.method == "POST":
        query = request.POST.get("q", "").strip()
        category = request.POST.get("category", "").strip()

    # Fetch active courses
    courses = Course.objects.filter(is_active=True)

    # Apply search filter
    if query:
        courses = courses.filter(title__icontains=query)

    # Get distinct categories
    all_categories = Course.objects.filter(is_active=True).values_list(
        "category", flat=True
    )
    categories = sorted({cat.strip() for cat in all_categories if cat})

    # Default category to first one if none selected
    if not category and categories:
        category = categories[0]

    # Apply category filter
    if category:
        courses = courses.filter(category=category)

    # Normalize video IDs on the fly for safe embedding
    for course in courses:
        if hasattr(course, "video_id") and course.video_id:
            course.video_id = extract_youtube_id(course.video_id)

    # Get enrolled course IDs for authenticated user
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
