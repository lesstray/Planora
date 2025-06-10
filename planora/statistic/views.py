from django.shortcuts import render
from home.models import Attendance, Lesson, Task
from registration.models import CustomUser
from datetime import datetime
import os
import matplotlib.pyplot as plt
import seaborn as sns


def statistics_view(request):
    start_date = datetime.strptime("2025-06-02", "%Y-%m-%d").date()
    end_date = datetime.strptime("2025-06-15", "%Y-%m-%d").date()

    students = CustomUser.objects.filter(role='student')
    teachers = CustomUser.objects.filter(role='teacher')

    student_data = []
    for student in students:
        total_attend = Attendance.objects.filter(student=student).count()
        present_attend = Attendance.objects.filter(student=student, present=True).count()

        total_period_attend = Attendance.objects.filter(student=student, lesson__date__range=(start_date, end_date)).count()
        present_period_attend = Attendance.objects.filter(student=student, present=True, lesson__date__range=(start_date, end_date)).count()
        attend_percent = (present_period_attend / total_period_attend * 100) if total_period_attend else 0

        total_tasks = Task.objects.filter(user=student).count()
        done_tasks = Task.objects.filter(user=student, done=True).count()
        done_percent = (done_tasks / total_tasks * 100) if total_tasks else 0

        lessons_in_period = Lesson.objects.filter(study_groups=student.student_group, date__range=(start_date, end_date)).distinct().count()
        tasks_in_period = Task.objects.filter(user=student, date__range=(start_date, end_date)).count()

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
        lessons = Lesson.objects.filter(teacher=teacher.full_name, date__range=(start_date, end_date)).count()
        teacher_data.append({
            'name': teacher.full_name,
            'groups': [g.name for g in teacher.teaching_groups.all()],
            'lessons': lessons
        })

    chart_url = generate_report_chart(start_date, end_date)

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'student_data': student_data,
        'teacher_data': teacher_data,
        'chart_url': chart_url,
    }

    return render(request, 'statistic.html', context)


def generate_report_chart(start_date, end_date):
    students = CustomUser.objects.filter(role='student')
    names = []
    attendance_percents = []
    task_completion_percents = []

    for student in students:
        total_attend = Attendance.objects.filter(student=student, lesson__date__range=(start_date, end_date)).count()
        present_attend = Attendance.objects.filter(student=student, present=True, lesson__date__range=(start_date, end_date)).count()
        attendance_percent = (present_attend / total_attend * 100) if total_attend else 0

        total_tasks = Task.objects.filter(user=student, date__range=(start_date, end_date)).count()
        done_tasks = Task.objects.filter(user=student, done=True, date__range=(start_date, end_date)).count()
        task_percent = (done_tasks / total_tasks * 100) if total_tasks else 0

        names.append(student.full_name)
        attendance_percents.append(attendance_percent)
        task_completion_percents.append(task_percent)

    sns.set(style="whitegrid")

    fig, axs = plt.subplots(2, 1, figsize=(14, 8))

    sns.barplot(x=names, y=attendance_percents, ax=axs[0], palette="Greens_d")
    axs[0].set_title("Посещаемость студентов (%)", fontsize=16)
    axs[0].set_ylabel("Процент")
    axs[0].set_ylim(0, 100)
    axs[0].tick_params(axis='x', rotation=45)
    for i, v in enumerate(attendance_percents):
        axs[0].text(i, v + 1, f"{v:.1f}%", ha='center', fontsize=9)

    sns.barplot(x=names, y=task_completion_percents, ax=axs[1], palette="Blues_d")
    axs[1].set_title("Выполнение задач (%)", fontsize=16)
    axs[1].set_ylabel("Процент")
    axs[1].set_ylim(0, 100)
    axs[1].tick_params(axis='x', rotation=45)
    for i, v in enumerate(task_completion_percents):
        axs[1].text(i, v + 1, f"{v:.1f}%", ha='center', fontsize=9)

    plt.tight_layout()

    # Папка для статичных файлов отчётов
    reports_dir = os.path.join('home', 'static', 'reports')
    os.makedirs(reports_dir, exist_ok=True)

    output_path = os.path.join(reports_dir, 'report.png')
    plt.savefig(output_path, dpi=300)
    plt.close(fig)

    return 'reports/report.png'  # путь относительно STATIC_URL
