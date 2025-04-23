from django.http import HttpResponseRedirect
from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Group, Lesson, StudentPlan, AttendanceStats
from .serializers import (
    GroupSerializer,
    LessonSerializer,
    StudentPlanSerializer,
    AttendanceStatsSerializer,
)
from django.contrib.auth import get_user_model

User = get_user_model()


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAdminUser]

    @swagger_auto_schema(
        operation_description="Получить список всех групп",
        responses={200: GroupSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Создать новую группу (только для админов)",
        request_body=GroupSerializer,
        responses={201: GroupSerializer()},
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Получить список всех пар",
        manual_parameters=[
            openapi.Parameter(
                name='group',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description='Фильтр по группе (например, `?group=1234`)',
            ),
        ],
        responses={200: LessonSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Отменить пару (для преподавателей)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'reason': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Причина отмены',
                ),
            },
        ),
        responses={200: "Lesson cancelled"},
    )
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        lesson = self.get_object()
        lesson.is_cancelled = True
        lesson.cancellation_reason = request.data.get('reason', '')
        lesson.save()
        return Response({'status': 'Lesson cancelled'})


class StudentPlanViewSet(viewsets.ModelViewSet):
    queryset = StudentPlan.objects.all()
    serializer_class = StudentPlanSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Создать план для студента",
        request_body=StudentPlanSerializer,
        responses={201: StudentPlanSerializer()},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(student=request.user)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    @swagger_auto_schema(
        operation_description="Обновить план студента",
        request_body=StudentPlanSerializer,
        responses={200: StudentPlanSerializer()},
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)


class AttendanceStatsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AttendanceStats.objects.all()
    serializer_class = AttendanceStatsSerializer

    @swagger_auto_schema(
        operation_description="Получить статистику посещаемости",
        responses={200: AttendanceStatsSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Аналитика посещаемости (графики)",
        responses={200: "Analytics data"},
    )
    @action(detail=False, methods=['get'])
    def analytics(self, request):
        # Здесь может быть логика для графиков (например, pandas + matplotlib)
        return Response({'data': 'Analytics here'})

def root_redirect(request):
    """
    Перенаправляет корневой URL на страницу регистрации.

    :param request: HTTP-запрос от пользователя.
    :return: HTTP-редирект на '/register'.
    """
    return HttpResponseRedirect('/register')


def home_view(request):
    return render(request, 'index.html')
