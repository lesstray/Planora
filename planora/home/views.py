from django.http import HttpResponseRedirect
from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework import generics
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.views import APIView


from .models import Task, Group
from .serializers import (
    TaskSerializer,
    GroupSerializer,
)
from django.contrib.auth import get_user_model

User = get_user_model()

# views.py
class TaskListCreate(APIView):
    # Отдельный класс для создания
    @swagger_auto_schema(
        request_body=TaskSerializer,
        responses={
            201: TaskSerializer,
            400: "Не получилось создать задачу"
        },
        operation_description="Создать новую задачу",
        tags=['Tasks']
    )
    def post(self, request):
        serializer = TaskSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GroupStatistic(APIView):
    @swagger_auto_schema(
        operation_id='group_detail',
        responses={
            200: GroupSerializer,  # Используем класс сериализатора
            404: "Группа не найдена"
        },
        operation_description="Получить статистику по группе",
        tags=['Groups']
    )
    def get(self, request, pk):
        try:
            group = Group.objects.get(pk=pk)
            serializer = GroupSerializer(group)  # Создаём экземпляр
            return Response(serializer.data)
        except Group.DoesNotExist:
            return Response(
                {"error": "Группа не найдена"},
                status=status.HTTP_404_NOT_FOUND
            )

   
class TaskDetail(APIView):
    @swagger_auto_schema(
        operation_id='task_detail',
        operation_description="Получить задачу по ID",
        responses={
            200: TaskSerializer,
            404: "Задача не найдена"
        },
        tags=['Tasks']
    )
    def get(self, request, pk):
        try:
            task = Task.objects.get(pk=pk)
            serializer = TaskSerializer(task)
            return Response(serializer.data)
        except Task.DoesNotExist:
            return Response(
                {"error": "Задача не найдена"},
                status=status.HTTP_404_NOT_FOUND
            )

    @swagger_auto_schema(
        operation_id='task_remove',
        operation_description="Удалить задачу по ID",
        responses={
            204: "Удалена",  # 204 - стандартный код для успешного удаления
            404: "Задача не найдена"
        },
        tags=['Tasks']
    )
    def delete(self, request, pk):
        try:
            task = Task.objects.delete(pk=pk)
            task.delete()  # Вот здесь фактическое удаление
            return Response(
                {"status": "OK"},  # Добавлена запятая
                status=status.HTTP_204_NO_CONTENT  # 204 вместо 200
            )
        except Task.DoesNotExist:
            return Response(
                {"error": "Задача не найдена"},
                status=status.HTTP_404_NOT_FOUND
            )


def root_redirect(request):
    """
    Перенаправляет корневой URL на страницу регистрации.

    :param request: HTTP-запрос от пользователя.
    :return: HTTP-редирект на '/register'.
    """
    return HttpResponseRedirect('/register')


def home_view(request):
    return render(request, 'index.html')
