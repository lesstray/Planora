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

    # === для преподавателя ===
    teaching_subjects = models.ManyToManyField(
        'home.Subject',
        blank=True,
        verbose_name='Преподаваемые предметы',
        related_name='teachers'
    )
    teaching_groups = models.ManyToManyField(
        'home.StudyGroup',
        blank=True,
        verbose_name='Группы преподавания',
        related_name='teachers'
    )

    # === для студента ===
    student_group = models.ForeignKey(
        'home.StudyGroup',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name='Учебная группа студента',
        related_name='students'
    )
    student_subjects = models.ManyToManyField(
        'home.Subject',
        blank=True,
        verbose_name='Предметы студента',
        related_name='students'
    )
    student_teachers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        limit_choices_to={'role': 'teacher'},
        related_name='student_of',
        verbose_name='Препеподаватели студента'
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
