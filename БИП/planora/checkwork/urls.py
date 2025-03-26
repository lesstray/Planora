from django.contrib import admin
from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.root_redirect),
    path('about', views.about, name='about'),
    path('login', views.login_view, name='login'),
    path('register', views.reg_view, name='register'),
    path('home', views.home_view, name='home'),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)