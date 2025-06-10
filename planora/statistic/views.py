from django.shortcuts import render
from django.utils import timezone
from django.conf import settings
from home.models import Attendance, Lesson, Task
from registration.models import CustomUser
from datetime import datetime, timedelta
import os
import io
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

#
from plot_reports import make_plot_file


def statistics_view(request):
    # Попытка получить даты из GET-параметров
    start_str = request.GET.get('start_date')
    end_str = request.GET.get('end_date')

    # Значения по умолчанию — последние 14 дней
    today = timezone.localdate()  # локальная дата, Europe/Bucharest
    default_end = today
    default_start = today - timedelta(days=13)

    # Парсим GET-параметры, или берём по умолчанию
    try:
        start_date = datetime.strptime(start_str, '%Y-%m-%d').date() if start_str else default_start
    except ValueError:
        start_date = default_start

    try:
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date() if end_str else default_end
    except ValueError:
        end_date = default_end

    # Гарантируем, что start_date <= end_date
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    # Далее по вашей логике — получаем студентов, считаем статистику…
    students = CustomUser.objects.filter(role='student')
    teachers = CustomUser.objects.filter(role='teacher')

    student_data = []
    for student in students:
        # Общая посещаемость
        total_attend = Attendance.objects.filter(student=student).count()
        present_attend = Attendance.objects.filter(student=student, present=True).count()

        # Посещаемость за период
        total_period_attend = Attendance.objects.filter(
            student=student,
            lesson__date__range=(start_date, end_date)
        ).count()
        present_period_attend = Attendance.objects.filter(
            student=student,
            present=True,
            lesson__date__range=(start_date, end_date)
        ).count()
        attend_percent = (present_period_attend / total_period_attend * 100) if total_period_attend else 0

        # Задачи
        total_tasks = Task.objects.filter(user=student).count()
        done_tasks = Task.objects.filter(user=student, done=True).count()
        done_percent = (done_tasks / total_tasks * 100) if total_tasks else 0

        lessons_in_period = Lesson.objects.filter(
            study_groups=student.student_group,
            date__range=(start_date, end_date)
        ).distinct().count()
        tasks_in_period = Task.objects.filter(
            user=student,
            date__range=(start_date, end_date)
        ).count()

        student_data.append({
            'name': student.full_name,
            'present_total': present_attend,
            'attend_total': total_attend,
            'attend_percent': round(attend_percent, 1),
            'done_tasks': done_tasks,
            'total_tasks': total_tasks,
            'done_percent': round(done_percent, 1),
            'lessons_in_period': lessons_in_period,
            'tasks_in_period': tasks_in_period,
        })

    teacher_data = []
    for teacher in teachers:
        lessons = Lesson.objects.filter(
            teacher=teacher.full_name,
            date__range=(start_date, end_date)
        ).count()
        teacher_data.append({
            'name': teacher.full_name,
            'groups': [g.name for g in teacher.teaching_groups.all()],
            'lessons': lessons
        })

    make_plot_file(start_date, end_date)

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'student_data': student_data,
        'teacher_data': teacher_data,
        'chart_data': '../reports/report.png'
    }
    return render(request, 'statistic.html', context)
