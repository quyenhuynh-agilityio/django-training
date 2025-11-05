from django.urls import path
from .views import enrolled_courses

urlpatterns = [
    path("my-courses/", enrolled_courses, name="enrolled_courses"),
]
