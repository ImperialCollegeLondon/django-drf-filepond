import re
import os
from setuptools import setup

with open("README.md", "r") as readme:
    long_description = readme.read()

setup(
    name="django-drf-filepond",
    version="0.0.2",
    description="Filepond server app for Django REST Framework",
    long_description=long_description,
    long_description_content_type='text/markdown',
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
        "shortuuid>=0.5.0",
        "requests>=2.20.1"
    ],
    tests_require=[
        "nose",
        "coverage",
        "httpretty",
        "mock;python_version<'3.3'"
    ],
    zip_safe=False,
    test_suite="tests.runner.start",
    classifiers=[
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ]
)
