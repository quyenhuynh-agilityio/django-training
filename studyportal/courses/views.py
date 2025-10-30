from django.shortcuts import render
from .models import Course


def course_list(request):
    query = ""
    category = ""

    if request.method == "POST":
        query = request.POST.get("q", "").strip()
        category = request.POST.get("category", "").strip()

    courses = Course.objects.filter(is_active=True)

    if query:
        courses = courses.filter(title__icontains=query)

    if category:
        courses = courses.filter(category__icontains=category)

    return render(
        request,
        "courses/course_list.html",
        {
            "courses": courses,
            "query": query,
            "category": category,
        },
    )
