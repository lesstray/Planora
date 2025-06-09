from .views import *
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'home'


urlpatterns = [
    # API endpoints
    # path('', include(router.urls)),
    path('schedule/', views.schedule, name='schedule'),
    # экспорт в календарь
    path('export.ics', views.export_ics, name='export_ics'),
    # добавить файл к существующей задаче
    path('task/<int:task_id>/upload_task_attachment/', views.upload_task_attachment, name='upload_task_attachment'),
    # добавить файл к существующей паре
    path('lesson/<int:lesson_id>/upload_lesson_attachment/', views.upload_lesson_attachment, name='upload_lesson_attachment'),
    # Дополнительные кастомные эндпоинты (если нужны)
    # path('some-custom-endpoint/', views.some_view, name='some-view'),
  
    # Для создания задачи (POST) и получения списка (GET)
    # создать новую задачу
    path('create-task/', views.create_task, name='create_task'),
    # удалить существующую задачу
    path('delete_task/', views.delete_task, name='delete_task'),
    # отметить задачу выполненной
    path('toggle_task_done/<int:task_id>/', views.toggle_task_done, name='toggle_task_done'),

]
