from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Group(models.Model):
    name = models.CharField(max_length=10, unique=True)
    schedule_url = models.URLField(blank=True, null=True)  # Ссылка на расписание СПбПУ

    def __str__(self):
        return self.name

class Lesson(models.Model):
    name = models.CharField(max_length=100)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='lessons')
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lessons_taught')
    is_cancelled = models.BooleanField(default=False)
    cancellation_reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.date})"

class StudentPlan(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='plans')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, blank=True, null=True)
    custom_plan = models.TextField(blank=True, null=True)  # Если заменяет пару своими планами
    date = models.DateField()
    is_attending = models.BooleanField(default=True)
    absence_reason = models.TextField(blank=True, null=True)
    proof_image = models.ImageField(upload_to='absence_proofs/', blank=True, null=True)  # Справка

    def __str__(self):
        return f"{self.student.username} - {self.date}"

class AttendanceStats(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='stats')
    present_count = models.IntegerField(default=0)
    absent_count = models.IntegerField(default=0)
    reasons = models.JSONField(default=dict)  # {"болезнь": 3, "другое": 1}

    def __str__(self):
        return f"Stats for {self.lesson.name}"