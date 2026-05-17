"""
URL configuration for fakenews_backend project.

"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("api/", include("api.urls")),
]