import django
import os
import sys
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime


def make_plot_file(start_date, end_date):
    print(start_date, end_date)

    # Django setup
    sys.path.append(os.path.join(os.path.dirname(__file__), 'planora'))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "planora.settings")
    django.setup()

    from home.models import Attendance, Task
    from registration.models import CustomUser

    # Период анализа
    #start_date = datetime(2025, 6, 2).date()
    #end_date = datetime(2025, 6, 15).date()

    # Готовим данные
    students = CustomUser.objects.filter(role='student')
    print(f"students: {students}")
    names = []
    attendance_percents = []
    task_completion_percents = []

    for student in students:
        # Посещаемость
        total_attend = Attendance.objects.filter(student=student, lesson__date__range=(start_date, end_date)).count()
        present_attend = Attendance.objects.filter(student=student, present=True, lesson__date__range=(start_date, end_date)).count()
        attendance_percent = (present_attend / total_attend * 100) if total_attend else 0

        # Задачи
        total_tasks = Task.objects.filter(user=student, date__range=(start_date, end_date)).count()
        done_tasks = Task.objects.filter(user=student, done=True, date__range=(start_date, end_date)).count()
        task_percent = (done_tasks / total_tasks * 100) if total_tasks else 0

        names.append(student.full_name)
        attendance_percents.append(attendance_percent)
        task_completion_percents.append(task_percent)

    # === Графики ===
    sns.set(style="whitegrid")

    fig, axs = plt.subplots(2, 1, figsize=(14, 8))

    # 1. Посещаемость
    sns.barplot(x=names, y=attendance_percents, ax=axs[0], palette="Greens_d")
    axs[0].set_title("Посещаемость студентов (%)", fontsize=16)
    axs[0].set_ylabel("Процент")
    axs[0].set_ylim(0, 100)
    axs[0].tick_params(axis='x', rotation=45)
    for i, v in enumerate(attendance_percents):
        axs[0].text(i, v + 1, f"{v:.1f}%", ha='center', fontsize=9)

    # 2. Выполнение задач
    sns.barplot(x=names, y=task_completion_percents, ax=axs[1], palette="Blues_d")
    axs[1].set_title("Выполнение задач (%)", fontsize=16)
    axs[1].set_ylabel("Процент")
    axs[1].set_ylim(0, 100)
    axs[1].tick_params(axis='x', rotation=45)
    for i, v in enumerate(task_completion_percents):
        axs[1].text(i, v + 1, f"{v:.1f}%", ha='center', fontsize=9)

    plt.tight_layout()

    # === Сохранение графика ===
    print("AAAAAAAAAAAAAAAAAAAAAAAAAAAaaaaaaaa")
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    print(BASE_DIR)
    reports_dir = os.path.join(BASE_DIR, 'home', 'static','reports')
    os.makedirs(reports_dir, exist_ok=True)
    print(reports_dir)
    output_path = os.path.join(reports_dir, 'report.png')
    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close(fig)

    print(f"✅ График сохранён: {output_path}")
    plt.show()
