from .views import *
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'home'

# Создаем router и регистрируем ViewSets
router = DefaultRouter()
router.register(r'groups', views.GroupViewSet, basename='group')
router.register(r'lessons', views.LessonViewSet, basename='lesson')
router.register(r'plans', views.StudentPlanViewSet, basename='studentplan')
router.register(r'stats', views.AttendanceStatsViewSet, basename='attendancestats')

urlpatterns = [
    # API endpoints
    # path('', include(router.urls)),
    path('schedule/', views.schedule, name='schedule'),
    # Дополнительные кастомные эндпоинты (если нужны)
    # path('some-custom-endpoint/', views.some_view, name='some-view'),
  
    # Для создания задачи (POST) и получения списка (GET)
    path('tasks/', TaskListCreate.as_view(), name='task-list-create'),
    
    # Для работы с конкретной задачей (GET/DELETE)
    path('tasks/<int:pk>/', TaskDetail.as_view(), name='task-detail'),

    path('groups/<int:pk>/',GroupStatistic.as_view(),name='group-detail')
]
