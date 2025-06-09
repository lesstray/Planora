from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings

User = get_user_model()

class AbstractEvent(models.Model):
    """
    Базовый абстрактный класс для любого события (пара или задача).
    """
    date        = models.DateField(null=True, blank=True)            # дата события
    start_time  = models.TimeField(null=True, blank=True)            # время начала
    end_time    = models.TimeField(null=True, blank=True)            # время окончания
    description = models.TextField(blank=True)                       # общие заметки/описание
    location    = models.CharField(max_length=200, blank=True)       # "Аудитория" или "Место"
    notes       = models.TextField(blank=True)                       # дополнительные заметки
    attachment  = models.FileField(upload_to='event_files/', blank=True, null=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        ordering = ['date', 'start_time']

    def duration(self):
        if self.start_time and self.end_time:
            # возвращает timedelta
            return datetime.combine(self.date, self.end_time) - datetime.combine(self.date, self.start_time)
        return None

    def __str__(self):
        rng = f"{self.start_time or ''}-{self.end_time or ''}"
        return f"{self.date} {rng} {self.description[:30]}"


class Lesson(AbstractEvent):
    """
    Пара из расписания.
    """
    subject     = models.ForeignKey('Subject', on_delete=models.PROTECT)
    study_groups= models.ManyToManyField('StudyGroup', related_name='lessons')
    teacher     = models.CharField(max_length=100, blank=True)

    def save(self, *args, **kwargs):
        # скопируем дисциплину в description для унификации
        self.description = self.subject.name
        super().save(*args, **kwargs)


class Task(AbstractEvent):
    """
    Пользовательская задача.
    """
    user        = models.ForeignKey(User, on_delete=models.CASCADE)
    study_group = models.ForeignKey('StudyGroup', on_delete=models.SET_NULL, null=True, blank=True)
    done        = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # если description пуст, можно скопировать из notes
        if not self.description and self.notes:
            self.description = self.notes[:200]
        super().save(*args, **kwargs)


class Attendance(models.Model):
    lesson    = models.ForeignKey('Lesson', on_delete=models.CASCADE, related_name='attendances')
    student   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    present   = models.BooleanField(default=False)
    comment   = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('lesson', 'student')


class Group(models.Model):
    title = models.CharField(max_length=50, default='') # Номер группы

    def __str__(self):
        return self.title


class Subject(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name="Предмет")

    def __str__(self):
        return self.name


class StudyGroup(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="Учебная группа")

    def __str__(self):
        return self.name