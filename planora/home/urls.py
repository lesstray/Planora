from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'home'


urlpatterns = [
    # API endpoints
    # path('', include(router.urls)),
    path('schedule/', views.schedule, name='schedule'),
    # Дополнительные кастомные эндпоинты (если нужны)
    # path('some-custom-endpoint/', views.some_view, name='some-view'),
]