from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework import generics
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.views import APIView


from .models import Lesson, Task, StudyGroup
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect

# загрузка расписания
import locale
import dateparser
from datetime import datetime as dt, timedelta
from datetime import date
from django.views.decorators.http import require_POST, require_GET
from django.shortcuts import get_object_or_404
from .ruz_parser import get_schedule
from django.shortcuts import render
import dateparser
from .ruz_parser import get_schedule
from datetime import datetime, timedelta
from django.urls import reverse
from django.http import JsonResponse
from itertools import chain
from icalendar import Calendar, Event
import pytz
from django.http import HttpResponse
from django.db import transaction
from .models import Lesson, Subject, StudyGroup
from django.utils.dateparse import parse_time
#

User = get_user_model()

# views.py


def root_redirect(request):
	return HttpResponseRedirect('/about')

# Для расписания
def _make_time_slots(start="08:00", end="20:00", step_hours=2):
	fmt = "%H:%M"
	t0 = datetime.strptime(start, fmt)
	t_end = datetime.strptime(end, fmt)
	slots = []
	while t0 < t_end:
		slots.append(t0.strftime(fmt))
		t0 += timedelta(hours=step_hours)
	return slots


@login_required
def schedule(request):
	print("DEBUG: hello from 'schedule' func...")
	"""
	Отображение расписания: пары из RUZ и задачи из БД, на выбранную неделю и группу.
	"""
	context = {
		'time_slots': _make_time_slots("08:00", "20:00", 2),
		'selected_group': '',
		'selected_date': '',
	}

	# читаем параметры
	group_name = request.GET.get('groupNumber', '')
	date_str   = request.GET.get('scheduleDate', '')
	context['selected_group'] = group_name
	context['selected_date']  = date_str

	if not date_str:
		date_str = date.today().isoformat()
		context['selected_date']  = date_str
	# если пользователь аутентифицирован и в GET нет groupNumber,
	# подставляем student_group из его профиля
	if not group_name and request.user.is_authenticated:
		sg = getattr(request.user, 'student_group', None)
		if sg:
			group_name = sg.name
			context['selected_group'] = group_name


	if group_name and date_str:
		# парсим дату
		try:
			selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
		except ValueError:
			context['error_message'] = "Неверный формат даты"
			return render(request, 'schedule.html', context)

		# границы недели
		week_start = selected_date - timedelta(days=selected_date.weekday())
		week_end   = week_start + timedelta(days=6)

		# 1) Пары из внешнего парсера RUZ
		raw = get_schedule(group_name, week_start.isoformat())
		if 'error' in raw:
			context['error_message'] = raw['error']
			return render(request, 'schedule.html', context)

		# 2) Сохраняем уроки в БД, если на эту группу и неделю их ещё нет
		sg = StudyGroup.objects.get(name=group_name)
		already = Lesson.objects.filter(
			study_groups=sg,
			date__range=(week_start, week_end)
		).exists()

		if not already:
			with transaction.atomic():
				# пройдём по каждому дню недели
				for offset in range(7):
					day = week_start + timedelta(days=offset)
					key = day.strftime('%Y-%m-%d')
					for les in raw['schedule'].get(key, []):
						st = les.get('start_time') or ''
						en = les.get('end_time')   or ''
						# упрощённо: берем первые 5 символов HH:MM
						st = st[:5]  
						en = en[:5]

						# 2.1) получаем или создаём предмет
						subject_obj, _ = Subject.objects.get_or_create(name=les['subject'])

						# 2.2) создаём Lesson
						lesson = Lesson.objects.create(
							date=day,
							start_time=parse_time(st) if st else None,
							end_time=parse_time(en) if en else None,
							teacher=les.get('teacher', ''),
							location=les.get('place', ''),
							notes=les.get('notes', ''),
							subject=subject_obj,
						)
						# 2.3) связываем с группой
						lesson.study_groups.add(sg)

		# 3) Теперь мы можем спокойно читать из БД
		lessons_qs = Lesson.objects.filter(
			study_groups=sg,
			date__range=(week_start, week_end)
		)

		tasks_qs = Task.objects.filter(
			study_group=sg,
			user=request.user,
			date__range=(week_start, week_end)
		)

		# Формируем по дням
		dates = [week_start + timedelta(days=i) for i in range(7)]
		schedule_by_date = []

		# есть ли данные в БД?
		use_raw = not already

		for day in dates:
			date_key = day.strftime('%Y-%m-%d')
			events = []

			if use_raw:
				# A) уроки из парсера, если их нет в БД (флаг use_raw)
				for les in raw['schedule'].get(date_key, []):
					st = les.get('start_time')
					en = les.get('end_time') or ''
					# форматируем времена
					if st and ':' in st:
						st = st[:5]
					if en and ':' in en:
						en = en[:5]
					events.append({
						'type': 'lesson',
						'start_time': st,
						'end_time': en,
						'subject': les.get('subject', ''),
						'teacher': les.get('teacher', ''),
						'place':   les.get('place', ''),
						'notes':   les.get('notes', ''),
						'attachment': None,
						'done': False,
					})

			# B) уроки из БД модели Lesson добавляются всегда
			for les in lessons_qs.filter(date=day):
				events.append({
					'type': 'lesson',
					'id': les.id,
					'start_time': les.start_time.strftime('%H:%M') if les.start_time else '',
					'end_time':   les.end_time.strftime('%H:%M')   if les.end_time else '',
					'subject':    les.subject.name,
					'teacher':    les.teacher,
					'place':      les.location,
					'notes':      les.notes,
					'attachment': les.attachment,
					'done':       False,
				})

			# C) пользовательские задачи
			for task in tasks_qs.filter(date=day):
				events.append({
					'type':      'task',
					'id':         task.id,
					'start_time': task.start_time.strftime('%H:%M') if task.start_time else '',
					'end_time':   task.end_time.strftime('%H:%M')   if task.end_time else '',
					'description':task.description,
					'place':      task.location,
					'notes':      task.notes,
					'attachment': task.attachment,
					'done':       task.done,
				})

			# сортируем по времени начала
			events.sort(key=lambda ev: ev['start_time'] or '00:00')
			schedule_by_date.append((day, events))

		context.update({
			'week_start': week_start,
			'week_end':   week_end,
			'schedule_by_date': schedule_by_date,
		})
	#print(f"DEBUG: {context}")
	return render(request, 'schedule.html', context)


@require_POST
def create_task(request):
	"""
	Создать новую задачу из формы.
	"""
	user       = request.user
	group_name = request.POST.get('group')
	date       = request.POST.get('date')
	start_time = request.POST.get('start_time') or None
	end_time   = request.POST.get('end_time')   or None
	description= request.POST.get('description')
	place      = request.POST.get('place', '')
	notes      = request.POST.get('notes', '')
	done       = request.POST.get('done') == 'on'
	attachment = request.FILES.get('attachment', None)

	sg = None
	if group_name:
		sg, _ = StudyGroup.objects.get_or_create(name=group_name)

	Task.objects.create(
		user=user,
		study_group=sg,
		date=date,
		start_time=start_time,
		end_time=end_time,
		description=description,
		location=place,
		notes=notes,
		done=done,
		attachment=attachment,
	)

	url = reverse('home:schedule') + f"?groupNumber={group_name}&scheduleDate={date}"
	return HttpResponseRedirect(url)


@require_POST
def toggle_task_done(request, task_id):
	task = get_object_or_404(Task, id=task_id, user=request.user)
	task.done = not task.done
	task.save()
	return JsonResponse({'success': True, 'done': task.done})


@require_POST
def delete_task(request):
	task_id = request.POST.get('task_id')
	task = get_object_or_404(Task, id=task_id, user=request.user)
	task.delete()
	return JsonResponse({'success': True})


@require_GET
def export_ics(request):
	
	# читаем параметры
	group_name = request.GET.get('groupNumber', '')
	date_str   = request.GET.get('scheduleDate', '')

	if group_name and date_str:
		# парсим дату
		try:
			selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
		except ValueError:
			pass

		# границы недели
		week_start = selected_date - timedelta(days=selected_date.weekday())
		week_end   = week_start + timedelta(days=6)

		# 1) Пары из внешнего парсера RUZ
		raw = get_schedule(group_name, week_start.isoformat())
		if 'error' in raw:
			pass

		# 2) Локальные пары из БД
		try:
			sg = StudyGroup.objects.get(name=group_name)
			lessons_qs = Lesson.objects.filter(
				study_groups=sg,
				date__range=(week_start, week_end)
			)
		except StudyGroup.DoesNotExist:
			lessons_qs = Lesson.objects.none()

		# 3) Пользовательские задачи
		try:
			sg = StudyGroup.objects.get(name=group_name)
		except StudyGroup.DoesNotExist:
			sg = None

		tasks_qs = Task.objects.filter(
			study_group=sg,
			user=request.user,
			date__range=(week_start, week_end)
		)

		# Формируем по дням
		dates = [week_start + timedelta(days=i) for i in range(7)]
		schedule_by_date = []

		for day in dates:
			date_key = day.strftime('%Y-%m-%d')
			events = []

			# A) Пары из парсера
			for les in raw['schedule'].get(date_key, []):
				st = les.get('start_time')
				en = les.get('end_time') or ''
				# форматируем времена
				if st and ':' in st:
					st = st[:5]
				if en and ':' in en:
					en = en[:5]
				events.append({
					'type': 'lesson',
					'start_time': st,
					'end_time': en,
					'subject': les.get('subject', ''),
					'teacher': les.get('teacher', ''),
					'place':   les.get('place', ''),
					'notes':   les.get('notes', ''),
					'attachment': None,
					'done': False,
				})

			# B) Пары из БД модели Lesson
			for les in lessons_qs.filter(date=day):
				events.append({
					'type': 'lesson',
					'start_time': les.start_time.strftime('%H:%M') if les.start_time else '',
					'end_time':   les.end_time.strftime('%H:%M')   if les.end_time else '',
					'subject':    les.subject.name,
					'teacher':    les.teacher,
					'place':      les.location,
					'notes':      les.notes,
					'attachment': les.attachment,
					'done':       False,
				})

			# C) пользовательские задачи
			for task in tasks_qs.filter(date=day):
				events.append({
					'type':      'task',
					'id':         task.id,
					'start_time': task.start_time.strftime('%H:%M') if task.start_time else '',
					'end_time':   task.end_time.strftime('%H:%M')   if task.end_time else '',
					'description':task.description,
					'place':      task.location,
					'notes':      task.notes,
					'attachment': task.attachment,
					'done':       task.done,
				})

			# сортируем по времени начала
			events.sort(key=lambda ev: ev['start_time'] or '00:00')
			schedule_by_date.append((day, events))

	cal = Calendar()
	cal.add('prodid', '-//Planora Export//')
	cal.add('version', '2.0')
	tz = pytz.timezone('Europe/Moscow')

	for day, events in schedule_by_date:
		for ev in events:
			# только уроки и задачи, у которых есть время
			if not ev['start_time']:
				continue
			start = datetime.combine(day, datetime.strptime(ev['start_time'], '%H:%M').time())
			end = start
			if ev.get('end_time'):
				end = datetime.combine(day, datetime.strptime(ev['end_time'], '%H:%M').time())
			# локализуем
			start = tz.localize(start)
			end   = tz.localize(end)

			e = Event()
			e.add('dtstart', start)
			e.add('dtend',   end)
			if ev['type']=='lesson':
				e.add('summary', ev.get('subject','Пара'))
				e.add('location', ev.get('place',''))
				e.add('description', f"{ev.get('teacher','')} {ev.get('notes','')}")
			else:
				e.add('summary', f"Задача: {ev.get('description','')}")
				e.add('location', ev.get('place',''))
				e.add('description', ev.get('notes',''))
			cal.add_component(e)

	ics_content = cal.to_ical()
	resp = HttpResponse(ics_content, content_type='text/calendar; charset=utf-8')
	resp['Content-Disposition'] = 'attachment; filename="planora_week.ics"'
	return resp


@require_POST
def upload_task_attachment(request, task_id):
	task = get_object_or_404(Task, id=task_id, user=request.user)
	attachment = request.FILES.get('attachment')
	if not attachment:
		return JsonResponse({'success': False, 'error': 'Файл не пришёл'})
	task.attachment = attachment
	task.save()
	return JsonResponse({
		'success': True,
		'url': task.attachment.url,
		'filename': task.attachment.name.split('/')[-1]
	})


@require_POST
def upload_lesson_attachment(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    attachment = request.FILES.get('attachment')
    if not attachment:
        return JsonResponse({'success': False, 'error': 'Файл не пришёл'})
    lesson.attachment = attachment
    lesson.save()
    return JsonResponse({
        'success':  True,
        'url':      lesson.attachment.url,
        'filename': lesson.attachment.name.split('/')[-1]
    })
