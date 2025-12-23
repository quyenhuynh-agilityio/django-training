import importlib

from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    verbose_name = 'User Accounts'

    def ready(self):
        importlib.import_module('users.signals')
