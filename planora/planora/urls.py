"""
URL configuration for planora project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.contrib.auth import logout
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from django.contrib.auth import views as auth_views


# Импорт представлений из приложений
from home.views import home_view, root_redirect
from login.views import login_view, verify_2fa
from registration.views import register_view, verify_registration
from about.views import about_view
from account.views import account_dashboard, change_password, terminate_sessions


schema_view = get_schema_view(
    openapi.Info(
        title="Student Planner API",
        default_version='v1',
        description="API для управления расписанием студентов и преподавателей СПбПУ",
        contact=openapi.Contact(email="support@example.com"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('admin/', admin.site.urls),
    # path('home/', home_view, name='home'),
    path('home/', include('home.urls', namespace='home')),
    path('', root_redirect, name='home'),
    path('about/', about_view, name='about'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('oauth/', include('social_django.urls', namespace='social')),
    path('verify-2fa/', verify_2fa, name='verify_2fa'),
    path('api/', include('home.urls')),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('verify-registration/', verify_registration, name='verify_registration'),
    path('dashboard', account_dashboard, name='account_dashboard'),
    path('change-password/', change_password, name='change_password'),
    path('terminate-sessions/', terminate_sessions, name='terminate_sessions'),
]
