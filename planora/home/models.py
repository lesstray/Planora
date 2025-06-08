from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Subject(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name="Предмет")

    def __str__(self):
        return self.name

class StudyGroup(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="Учебная группа")

    def __str__(self):
        return self.name

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