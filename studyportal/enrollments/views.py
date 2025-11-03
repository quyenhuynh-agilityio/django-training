from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Enrollment


@login_required(login_url="/accounts/login/")
def enrolled_courses(request):
    enrollments = Enrollment.objects.filter(user=request.user, is_deleted=False)
    courses = [en.course for en in enrollments]
    return render(request, "courses/course_list.html", {"courses": courses})
