from .views import *
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'home'


urlpatterns = [
    # API endpoints
    # path('', include(router.urls)),
    path('schedule/', views.schedule, name='schedule'),
    path('export.ics', views.export_ics, name='export_ics'),
    # Дополнительные кастомные эндпоинты (если нужны)
    # path('some-custom-endpoint/', views.some_view, name='some-view'),
  
    # Для создания задачи (POST) и получения списка (GET)
    
    path('create-task/', views.create_task, name='create_task'),

    path('delete_task/', views.delete_task, name='delete_task'),

    path('toggle_task_done/<int:task_id>/', views.toggle_task_done, name='toggle_task_done'),

]
