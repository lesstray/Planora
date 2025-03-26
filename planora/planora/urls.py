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


# Импорт представлений из приложений
from home.views import home_view
from login.views import login_view, verify_2fa
from registration.views import register_view
from about.views import about_view


urlpatterns = [
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('admin/', admin.site.urls),
    path('home/', home_view, name='home'),
    path('', home_view, name='home'),
    path('about/', about_view, name='about'),
    path('logout/', logout, {'next_page': settings.LOGOUT_REDIRECT_URL}, name='logout'),
    path('oauth/', include('social_django.urls', namespace='social')),
    path('verify-2fa/', verify_2fa, name='verify_2fa')
]
