from django.urls import path
from .views import course_list, enroll_course

urlpatterns = [
    path("", course_list, name="course_list"),
    path("enroll/<uuid:course_id>/", enroll_course, name="enroll_course"),
]
