from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_protect

from enrollments.models import Enrollment
from utils.course_queries import build_course_list_context

from .models import Course


@csrf_protect
def course_list(request):
    context = build_course_list_context(request)
    return render(request, 'courses/course_list.html', context)


@login_required(login_url='/users/login/')
def enroll_course(request, course_id):
    """Enroll the current user into a course.

    Only POST requests are allowed to actually create an enrollment.
    GET requests are safely redirected without attempting enrollment.
    """
    course = get_object_or_404(Course, id=course_id, is_active=True)

    # Only allow enrollment via POST to avoid accidental enrollments on GET
    if request.method != 'POST':
        return redirect('course_list')

    try:
        Enrollment.objects.get_or_create(
            student=request.user,
            course=course,
            defaults={'is_active': True},
        )
    except ValidationError as exc:  # e.g. course reached maximum capacity
        # Extract a human-readable error message, if available
        messages_list = getattr(exc, 'messages', None)
        if not messages_list and hasattr(exc, 'message_dict'):
            messages_list = exc.message_dict.get('__all__')

        if messages_list:
            messages.error(request, messages_list[0])
        else:
            messages.error(request, 'Unable to enroll in this course.')

        # Redirect back to course list so the user stays on the catalog page
        return redirect('course_list')

    return redirect('enrolled_courses')


@login_required(login_url='/users/login/')
def enrolled_courses(request):
    context = build_course_list_context(request, view='enrolled')
    return render(request, 'courses/course_list.html', context)
