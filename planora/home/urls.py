from .views import *
from django.urls import path, include

urlpatterns = [
    # Для создания задачи (POST) и получения списка (GET)
    path('tasks/', TaskListCreate.as_view(), name='task-list-create'),
    
    # Для работы с конкретной задачей (GET/DELETE)
    path('tasks/<int:pk>/', TaskDetail.as_view(), name='task-detail'),

    path('groups/<int:pk>/',GroupStatistic.as_view(),name='group-detail')
]
