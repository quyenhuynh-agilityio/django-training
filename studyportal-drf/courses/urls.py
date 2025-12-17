from django.urls import path

from .views import course_list, enroll_course, enrolled_courses

urlpatterns = [
    path('', course_list, name='course_list'),
    path('enroll/<uuid:course_id>/', enroll_course, name='enroll_course'),
    path('my-courses/', enrolled_courses, name='enrolled_courses'),
]
