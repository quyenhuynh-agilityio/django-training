from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from .models import Course
from enrollments.models import Enrollment


def course_list(request):
    # POST request: save search/category in session
    if request.method == "POST":
        request.session["query"] = request.POST.get("q", "").strip()
        request.session["category"] = request.POST.get("category", "").strip()
        return redirect("course_list")  # redirect to GET to avoid resubmitting form

    # GET request: retrieve filters from session
    query = request.session.get("query", "")
    category = request.session.get("category", "")

    courses = Course.objects.filter(is_active=True)

    if query:
        courses = courses.filter(title__icontains=query)

    all_categories = Course.objects.filter(is_active=True).values_list(
        "category", flat=True
    )
    categories = sorted({cat.strip() for cat in all_categories if cat})

    if not category and categories:
        category = categories[0]

    if category:
        courses = courses.filter(category=category)

    # Pagination: 6 per page
    paginator = Paginator(courses, 3)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    enrolled_ids = []
    if request.user.is_authenticated:
        enrolled_ids = Enrollment.objects.filter(
            user=request.user, is_deleted=False
        ).values_list("course_id", flat=True)

    context = {
        "courses": page_obj.object_list,
        "query": query,
        "category": category,
        "categories": categories,
        "enrolled_ids": enrolled_ids,
        "page_obj": page_obj,
    }

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
