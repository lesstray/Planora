from .views import *
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'home'


urlpatterns = [
    # API endpoints
    # path('', include(router.urls)),
    #path('schedule/', views.schedule, name='schedule'),
    # Дополнительные кастомные эндпоинты (если нужны)
    # path('some-custom-endpoint/', views.some_view, name='some-view'),
  
    # Для создания задачи (POST) и получения списка (GET)
    path('tasks/', TaskListCreate.as_view(), name='task-list-create'),
    
    # Для работы с конкретной задачей (GET/DELETE)
    path('tasks/<int:pk>/', TaskDetail.as_view(), name='task-detail'),

    path('groups/<int:pk>/',GroupStatistic.as_view(),name='group-detail'),

    path('create-task/', views.create_task, name='create_task'),

    path('delete_task/', views.delete_task, name='delete_task'),

    path('toggle_task_done/<int:task_id>/', views.toggle_task_done, name='toggle_task_done'),

]
