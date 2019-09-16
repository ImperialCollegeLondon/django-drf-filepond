from setuptools import setup

with open("README.md", "r") as readme:
    long_description = readme.read()

setup(
    name="django-drf-filepond",
    version="0.2.0rc1",
    description="Filepond server app for Django REST Framework",
    long_description=long_description,
    long_description_content_type='text/markdown',
    author="Jeremy Cohen",
    author_email="jeremy.cohen@imperial.ac.uk",
    url="https://github.com/ImperialCollegeLondon/django-drf-filepond",
    download_url=(
        "https://github.com/ImperialCollegeLondon/django-drf-filepond.git"),
    license="BSD 3-Clause",
    packages=[
        "django_drf_filepond",
        "django_drf_filepond.migrations",
    ],
    include_package_data=True,
    install_requires=[
        "Django<2.0.0;python_version=='2.7'",
        "Django>=2.0.0;python_version>='3.5'",
        "djangorestframework==3.9.3;python_version=='2.7'",
        "djangorestframework>=3.9.3;python_version>='3.5'",
        "shortuuid>=0.5.0",
        "requests>=2.20.1",
        "django-storages>=1.7.1"
    ],
    tests_require=[
        "nose",
        "coverage",
        "httpretty",
        "mock>=3.0.0;python_version<'3.3'",
        "paramiko"
    ],
    zip_safe=False,
    test_suite="tests.runner.start",
    classifiers=[
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ]
)
