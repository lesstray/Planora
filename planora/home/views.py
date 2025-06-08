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
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect

# загрузка расписания
import locale
import dateparser
from datetime import datetime as dt, timedelta
from django.views.decorators.http import require_POST
from .ruz_parser import get_schedule
from django.shortcuts import render
import dateparser
from .ruz_parser import get_schedule
from datetime import datetime, timedelta
from django.urls import reverse
from django.http import JsonResponse
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
			serializer = GroupSerializer(group)
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
	return HttpResponseRedirect('/about')

def home_view(request):
	context = {
		'time_slots': _make_time_slots("08:00", "20:00", 2),
		'selected_group': '',
		'selected_date': '',
	}
	group = request.GET.get('groupNumber', '')
	date_str = request.GET.get('scheduleDate', '')
	context['selected_group'] = group
	context['selected_date'] = date_str
	if group and date_str:
		try:
			selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
		except ValueError:
			context['error_message'] = "Неверный формат даты"
			return render(request, 'index.html', context)

		week_start = selected_date - timedelta(days=selected_date.weekday())
		week_end = week_start + timedelta(days=6)

		raw = get_schedule(group, week_start.isoformat())

		if 'error' in raw:
			context['error_message'] = raw['error']
			return render(request, 'index.html', context)

		dates = [week_start + timedelta(days=i) for i in range(7)]
		schedule_by_date = []
		for d in dates:
			date_key = d.strftime('%Y-%m-%d')
			lessons = raw['schedule'].get(date_key, [])
			day_map = {}
			for les in lessons:
				if les.get('start_time'):
					if ':' in les['start_time']:
						time_parts = les['start_time'].split(':')
						formatted_time = f"{time_parts[0]}:{time_parts[1]}"
						day_map[formatted_time] = les
			schedule_by_date.append((d, day_map))

		context.update({
			'week_start': week_start,
			'week_end': week_end,
			'schedule_by_date': schedule_by_date,
		})

	return render(request, 'index.html', context)

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


def schedule(request):
    context = {
        'time_slots': _make_time_slots("08:00", "20:00", 2),
        'selected_group': '',
        'selected_date': '',
    }

    if request.method == 'GET':
        group = request.GET.get('groupNumber', '')
        date_str = request.GET.get('scheduleDate', '')
    else:
        group = request.POST.get('groupNumber', '')
        date_str = request.POST.get('scheduleDate', '')

    context['selected_group'] = group
    context['selected_date'] = date_str

    if group and date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            context['error_message'] = "Неверный формат даты"
            return render(request, 'schedule.html', context)

        week_start = selected_date - timedelta(days=selected_date.weekday())
        week_end = week_start + timedelta(days=6)

        #print(f"Getting schedule for group={group}, date={week_start.isoformat()}")
        raw = get_schedule(group, week_start.isoformat())
        #print(f"Result: {raw}")

        tasks = Task.objects.filter(
            group=group,
            date__gte=week_start,
            date__lte=week_end
        ).values('date', 'start_time', 'description', 'done')

        if 'error' in raw:
            context['error_message'] = raw['error']
            return render(request, 'schedule.html', context)

        # Создаем список дат с понедельника по воскресенье
        dates = [week_start + timedelta(days=i) for i in range(7)]
        
        # Формируем расписание по дням
        schedule_by_date = []
        for d in dates:
            date_key = d.strftime('%Y-%m-%d')
            lessons = raw['schedule'].get(date_key, [])
            
            # Создаем словарь для быстрого доступа по времени начала
            day_map = {}
            for les in lessons:
                st = les.get('start_time')
                if st:
                    day_map[st] = {
                        'type':    'lesson',
                        'subject': les['subject'],
                        'teacher': les['teacher'],
                        'place':   les['place'],
                        'done':    False,
                    }

            # Задачи из БД
            for t in filter(lambda t: t['date'] == d, tasks):
                key = t['start_time'].strftime("%H:%M")
                day_map[key] = {
                    'type':        'task',
                    'description': t['description'],
                    'done':        t['done'],
                }

            # Сортируем события по времени
            sorted_events = [
                (time, info)
                for time, info in sorted(
                    day_map.items(),
                    key=lambda x: datetime.strptime(x[0], "%H:%M")
                )
            ]

            schedule_by_date.append((d, sorted_events))

        context.update({
            'week_start': week_start,
            'week_end': week_end,
            'schedule_by_date': schedule_by_date,
        })

    return render(request, 'schedule.html', context)


@require_POST
def create_task(request):
    user = request.user
    group = request.POST.get('group')
    date = request.POST.get('date')
    start_time = request.POST.get('start_time')
    end_time = request.POST.get('end_time')
    description = request.POST.get('description')
    place = request.POST.get('place')
    notes = request.POST.get('notes')
    done = request.POST.get('done') == 'on'
    attachment = request.FILES.get('attachment')

    Task.objects.create(
        user=user,
        group=group,
        date=date,
        start_time=start_time,
        end_time=end_time,
        description=description,
        place=place,
        notes=notes,
        done=done,
        attachment=attachment
    )
    url = reverse('home:schedule') + f"?groupNumber={request.POST['group']}&scheduleDate={request.POST['date']}"
    return HttpResponseRedirect(url)


@require_POST
def toggle_task_done(request, task_id):
    task = Task.objects.get(id=task_id)
    if task.user != request.user:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    task.done = not task.done
    task.save()
    return JsonResponse({'success': True, 'done': task.done})

@require_POST
def delete_task(request):
    task_id = request.POST.get('task_id')
    if not task_id:
        return JsonResponse({'success': False, 'error': 'task_id не передан'}, status=400)

    task = get_object_or_404(Task, id=task_id, user=request.user)  # если есть связь с пользователем

    task.delete()
    return JsonResponse({'success': True})