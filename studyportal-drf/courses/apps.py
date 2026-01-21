import importlib

from django.apps import AppConfig


class CoursesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'courses'  # Match the 'users' pattern
    verbose_name = 'Course Management'

    def ready(self):
        importlib.import_module('courses.signals')
