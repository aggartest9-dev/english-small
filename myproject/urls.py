# myproject/urls.py

"""
Main URL configuration for myproject
"""

from django.contrib import admin
from django.urls import path, include, re_path

from rest_framework import permissions

from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from myapp.views import home


# =====================================================
# SWAGGER / OPENAPI CONFIG
# =====================================================

schema_view = get_schema_view(
    openapi.Info(
        title="English Learning Platform API",
        default_version="v1",
        description="Production REST API documentation",
        terms_of_service="https://example.com/terms/",
        contact=openapi.Contact(
            email="support@example.com"
        ),
        license=openapi.License(
            name="Private License"
        ),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


# =====================================================
# URL PATTERNS
# =====================================================

urlpatterns = [

    # ---------------------------------------------
    # HOME / HEALTH CHECK
    # ---------------------------------------------
    path(
        "",
        home,
        name="home"
    ),

    # ---------------------------------------------
    # DJANGO ADMIN
    # ---------------------------------------------
    path(
        "admin/",
        admin.site.urls
    ),

    # ---------------------------------------------
    # APPLICATION API
    # ---------------------------------------------
    path(
        "api/",
        include(("myapp.urls", "myapp"), namespace="myapp")
    ),

    # ---------------------------------------------
    # SWAGGER UI
    # ---------------------------------------------
    path(
        "swagger/",
        schema_view.with_ui(
            "swagger",
            cache_timeout=0
        ),
        name="schema-swagger-ui"
    ),

    # ---------------------------------------------
    # REDOC UI
    # ---------------------------------------------
    path(
        "redoc/",
        schema_view.with_ui(
            "redoc",
            cache_timeout=0
        ),
        name="schema-redoc"
    ),
    path("accounts/", include("django.contrib.auth.urls")),

    # ---------------------------------------------
    # OPENAPI JSON / YAML
    # ---------------------------------------------
    re_path(
        r"^swagger(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(
            cache_timeout=0
        ),
        name="schema-json"
    ),
]