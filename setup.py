import re
import os

try:
    from setuptools import setup
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup

setup(
    name="django-drf-filepond",
    version="0.0.1",
    description="Filepond server app for Django REST Framework",
    long_description="This module provides a server-side interface for the filepond file upload plugin.",
    author="Jeremy Cohen",
    author_email="jeremy.cohen@imperial.ac.uk",
    url="https://github.com/ImperialCollegeLondon/django-drf-filepond",
    download_url="https://github.com/ImperialCollegeLondon/django-drf-filepond.git",
    license="BSD 3-Clause",
    packages=[
        "django_drf_filepond",
        "django_drf_filepond.migrations",
    ],
    include_package_data=True,
    install_requires=[
        "Django>=1.11.0",
        "djangorestframework>=3.8.2",
        "shortuuid>=0.5.0"
    ],
    tests_require=[
        "nose",
        "coverage",
        "httpretty",
    ],
    zip_safe=False,
    test_suite="tests.runner.start",
    classifiers=[
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: Developers",
        #"License :: OSI Approved :: BSD 3-CLause License",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ]
)
