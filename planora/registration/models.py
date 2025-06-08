from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    full_name = models.CharField(max_length=255, verbose_name='Полное имя')
    ROLE_CHOICES = [
        ('teacher', 'Преподаватель'),
        ('student', 'Студент'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, verbose_name='Роль')
    subjects = models.ManyToManyField(
        'home.Subject',  # строковая нотация, чтобы не было цикла
        blank=True,
        verbose_name='Преподаваемые предметы'
    )
    groups = models.ManyToManyField(
        'home.StudyGroup',
        blank=True,
        verbose_name='Учебные группы'
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
