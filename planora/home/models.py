from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Task(models.Model):
    user        = models.ForeignKey(User, on_delete=models.CASCADE)
    group       = models.CharField(max_length=50, default='', blank=True)    # номер группы
    date        = models.DateField(null=True, blank=True) # дата
    start_time  = models.TimeField(null=True, blank=True) # время начала
    end_time    = models.TimeField(null=True, blank=True) # время окончания
    description = models.TextField() # описание задачи
    place       = models.CharField(max_length=100, blank=True) # место
    notes       = models.TextField(blank=True) # заметки
    done        = models.BooleanField(default=False) # флаг о выполнении
    attachment  = models.FileField(upload_to='task_files/', blank=True, null=True) # прикрепленные файлы
    created_at  = models.DateTimeField(auto_now_add=True, null=True, editable=False) # когда создана

    def __str__(self):
        return f"{self.group} {self.date} {self.start_time}-{self.end_time} {self.description[:20]}"

class Group(models.Model):
    title = models.CharField(max_length=50, default='') # Номер группы

    def __str__(self):
        return self.title