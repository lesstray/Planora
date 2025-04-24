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
from django.shortcuts import render
from django.http import HttpResponseRedirect

# загрузка расписания
import locale
import dateparser
from datetime import datetime as dt, timedelta
from django.views.decorators.http import require_POST
from .ruz_parser import get_schedule
#

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

    @swagger_auto_schema(
        operation_description="Аналитика посещаемости (графики)",
        responses={200: "Analytics data"},
    )
    @action(detail=False, methods=['get'])
    def analytics(self, request):
        return Response({'data': 'Analytics here'})

def root_redirect(request):
    return HttpResponseRedirect('/register')

def home_view(request):
    return render(request, 'index.html')

# Для расписания
def _make_time_slots(start="08:00", end="20:00", step_hours=2):
    fmt = "%H:%M"
    t0 = dt.strptime(start, fmt)
    t_end = dt.strptime(end, fmt)
    slots = []
    while t0 < t_end:
        # Формируем слоты как "10:00" вместо "10:00–12:00"
        slots.append(t0.strftime(fmt))
        t0 += timedelta(hours=step_hours)
    return slots  # ["08:00", "10:00", "12:00", ...]


month_map = {
    "янв": "Jan", "фев": "Feb", "мар": "Mar", "апр": "Apr", "май": "May", "июн": "Jun",
    "июл": "Jul", "авг": "Aug", "сен": "Sep", "окт": "Oct", "ноя": "Nov", "дек": "Dec"
}

weekday_map = {
    "пн": "Monday", "вт": "Tuesday", "ср": "Wednesday", "чт": "Thursday",
    "пт": "Friday", "сб": "Saturday", "вс": "Sunday"
}


def schedule(request):
    times = ["10:00", "12:00", "14:00", "16:00", "18:00", "20:00", "22:00"]
    context = {
        'time_slots': _make_time_slots("08:00", "20:00", 2),
        'selected_group': request.POST.get('groupNumber', ''),
        'selected_date': request.POST.get('scheduleDate', ''),
    }
    print(_make_time_slots("08:00", "20:00", 2))
    if request.method == 'POST':
        raw = get_schedule(context['selected_group'], context['selected_date'])
        
        # Очистка данных от дня недели и точек
        week_start = raw.get('week_start').split(',')[0].replace('.', '').strip()  # "21 апр"
        week_end = raw.get('week_end').split(',')[0].replace('.', '').strip()      # "25 апр"
        schedule = raw.get('schedule')
        # Парсинг даты через dateparser (более гибкий)
        current_date = dateparser.parse(week_start, languages=['ru'])
        end_date = dateparser.parse(week_end, languages=['ru'])
        
        if not current_date or not end_date:
            print(f"Ошибка парсинга даты: {week_start} или {week_end}")
            return render(request, 'schedule.html', context)
        
        # Формируем day_order с датами
        day_order = []
        delta = timedelta(days=1)
        while current_date <= end_date:
            day_name = current_date.strftime("%A").capitalize()
            day_date = current_date.strftime("%d %b")
            day_key = f"{day_name}, {day_date}"
            day_order.append(day_key)
            current_date += delta
        
        
        # Добавляем недостающие дни (Суббота и Воскресенье)
        required_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        existing_days = [d.split(", ")[0] for d in day_order]
        for day in required_days:
            if day not in existing_days:
                #print(day)
                day_date = (end_date + timedelta(days=1)).strftime("%d %b")
                day_key = f"{day}, {day_date}"
                day_order.append(day_key)
                end_date += timedelta(days=1)
        
        converted = {}
        for key, value in schedule.items():
            day_part, weekday_ru = key.split(", ")
            day_str, month_ru = day_part.split()

            # Переводим в английские сокращения
            month_en = month_map[month_ru.strip(".")]
            weekday_en = weekday_map[weekday_ru]

            # Формируем новый ключ
            new_key = f"{weekday_en}, {day_str} {month_en}"
            converted[new_key] = value

        print("Day Order:", day_order)
        print("Schedule Keys:", converted.keys())
        #print(converted)
        structured = {}
        for day_key in day_order:
            # lessons = corrected_raw.get(day_key, [])
            lessons = converted.get(day_key, [])  # Используем converted вместо corrected_raw
            day_map = {}
            for les in lessons:
                st = les.get('start_time')
                if st:
                    day_map[st] = les  # Ключ должен совпадать с форматом времени в time_slots
            structured[day_key] = day_map
        print(structured)
        context.update({
            'week_start': week_start,
            'week_end': week_end,
            'schedule': structured,
            'day_order': day_order,
            'saturday_date': (end_date + timedelta(days=1)).strftime("%d %b"),
            'sunday_date': (end_date + timedelta(days=2)).strftime("%d %b"),
        })

    return render(request, 'schedule.html', context)
#
