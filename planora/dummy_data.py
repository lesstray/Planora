import os
import sys
import django
import random
from datetime import datetime, timedelta

# === Django setup ===
sys.path.append(os.path.join(os.path.dirname(__file__), 'planora'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "planora.settings")
django.setup()

from home.models import Lesson, Task, Attendance, Subject, StudyGroup
from registration.models import CustomUser

# Очистка (опционально)
# Lesson.objects.all().delete()
# Task.objects.all().delete()
# Attendance.objects.all().delete()

# === Настройки ===
start_date = datetime(2024, 6, 1)
end_date = datetime(2024, 6, 15)
days_range = (end_date - start_date).days

# === Подготовка данных ===
subjects = Subject.objects.all()
if not subjects:
    subjects = [Subject.objects.create(name=f"Предмет {i}") for i in range(1, 4)]

groups = StudyGroup.objects.all()
if not groups:
    groups = [StudyGroup.objects.create(name=f"Группа {i}") for i in range(1, 4)]

students = CustomUser.objects.filter(role='student')
if not students:
    for i in range(10):
        s = CustomUser.objects.create_user(
            username=f"student{i}",
            full_name=f"Студент {i}",
            role='student'
        )
        s.student_group = random.choice(groups)
        s.save()
    students = CustomUser.objects.filter(role='student')

teachers = CustomUser.objects.filter(role='teacher')
if not teachers:
    for i in range(3):
        t = CustomUser.objects.create_user(
            username=f"teacher{i}",
            full_name=f"Преподаватель {i}",
            role='teacher'
        )
    teachers = CustomUser.objects.filter(role='teacher')

# === Генерация Lessons и Attendance ===
for _ in range(30):
    date = start_date + timedelta(days=random.randint(0, days_range))
    subject = random.choice(subjects)
    group = random.choice(groups)
    teacher = random.choice(teachers)

    lesson = Lesson.objects.create(
        subject=subject,
        date=date,
        start_time=datetime.strptime("10:00", "%H:%M").time(),
        end_time=datetime.strptime("11:30", "%H:%M").time(),
        location="Ауд. 101",
        teacher=teacher.full_name
    )
    lesson.study_groups.add(group)

    # Заполняем посещаемость
    group_students = CustomUser.objects.filter(role='student', student_group=group)
    for student in group_students:
        Attendance.objects.create(
            lesson=lesson,
            student=student,
            present=random.choice([True, False])
        )

# === Генерация задач (Tasks) ===
for student in students:
    for _ in range(random.randint(3, 7)):
        Task.objects.create(
            user=student,
            date=start_date + timedelta(days=random.randint(0, days_range)),
            done=random.choice([True, False]),
            notes="Пример задачи"
        )

print("✅ Данные успешно сгенерированы.")
