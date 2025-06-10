import os
import sys
import django
from datetime import datetime, timedelta

# === Django setup ===
sys.path.append(os.path.join(os.path.dirname(__file__), 'planora'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "planora.settings")
django.setup()

from home.models import Lesson, Task, StudyGroup, Attendance
from registration.models import CustomUser
from django.db.models import Count, Q

# Задаем интервал (по умолчанию — последняя неделя)
start_date = datetime.strptime("2024-06-02", "%Y-%m-%d").date()
end_date = datetime.strptime("2024-06-15", "%Y-%m-%d").date()

print(f"\nАнализ за период: {start_date} — {end_date}\n")

# 1. Посещение пар студентами
print("1. Посещение пар студентами:")
for student in CustomUser.objects.filter(role='student'):
    total = Attendance.objects.filter(student=student).count()
    present = Attendance.objects.filter(student=student, present=True).count()
    print(f"  {student.full_name}: присутствовал на {present} из {total} пар")

# 2. Процент посещенных пар за определенный промежуток времени
print("\n2. Процент посещенных пар за период:")
for student in CustomUser.objects.filter(role='student'):
    total = Attendance.objects.filter(
        student=student,
        lesson__date__range=(start_date, end_date)
    ).count()
    present = Attendance.objects.filter(
        student=student,
        present=True,
        lesson__date__range=(start_date, end_date)
    ).count()
    percent = (present / total * 100) if total else 0
    print(f"  {student.full_name}: {percent:.1f}% ({present}/{total})")

# 3. Кол-во выполненных задач к созданным
print("\n3. Выполненные задачи:")
for student in CustomUser.objects.filter(role='student'):
    total_tasks = Task.objects.filter(user=student).count()
    done_tasks = Task.objects.filter(user=student, done=True).count()
    percent = (done_tasks / total_tasks * 100) if total_tasks else 0
    print(f"  {student.full_name}: {done_tasks}/{total_tasks} ({percent:.1f}%)")

# 4. Кол-во пар у студента за период
print("\n4. Количество пар у студента за период:")
for student in CustomUser.objects.filter(role='student'):
    group = student.student_group
    if not group:
        continue
    lessons = Lesson.objects.filter(
        study_groups=group,
        date__range=(start_date, end_date)
    ).distinct()
    print(f"  {student.full_name}: {lessons.count()} пар")

# 5. Кол-во задач у студента за период
print("\n5. Количество задач у студента за период:")
for student in CustomUser.objects.filter(role='student'):
    tasks = Task.objects.filter(user=student, date__range=(start_date, end_date))
    print(f"  {student.full_name}: {tasks.count()} задач")

# 6. Все группы преподавателя
print("\n6. Группы преподавателя:")
for teacher in CustomUser.objects.filter(role='teacher'):
    groups = teacher.teaching_groups.all()
    group_list = ", ".join([g.name for g in groups]) or "—"
    print(f"  {teacher.full_name}: {group_list}")

# 7. Кол-во пар преподавателя за период
print("\n7. Количество пар преподавателя за период:")
for teacher in CustomUser.objects.filter(role='teacher'):
    lessons = Lesson.objects.filter(
        teacher=teacher.full_name,
        date__range=(start_date, end_date)
    )
    print(f"  {teacher.full_name}: {lessons.count()} пар")
