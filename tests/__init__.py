# Test initialisation based on details provided at
# https://django-module-crash-course.readthedocs.io/en/latest/03-testing.html
import os
import django

test_runner = None
old_config = None

os.environ["DJANGO_SETTINGS_MODULE"] = "tests.settings"

if hasattr(django, "setup"):
    django.setup()


def setup():
    global test_runner
    global old_config

    from django.test.runner import DiscoverRunner
    test_runner = DiscoverRunner()
    test_runner.setup_test_environment()
    old_config = test_runner.setup_databases()


def teardown():
    test_runner.teardown_databases(old_config)
    test_runner.teardown_test_environment()
