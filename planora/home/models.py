from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Task(models.Model): # у модели будет уникальный ID
    title = models.CharField(max_length=200) # Название задачи
    description = models.TextField(blank=True) # Описание задачи
    due_date = models.DateField() # Дата выполнения
    is_completed = models.BooleanField(default=False) # Статус задачи

    def __str__(self):
        return self.title

class Group(models.Model):
    title = models.CharField(max_length=50) # Номер группы

    def __str__(self):
        return self.title