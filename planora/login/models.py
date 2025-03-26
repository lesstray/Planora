from django.db import models
from django.conf import settings
import random
import string
from django.utils import timezone
from datetime import timedelta


class TwoFactorCode(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    attempt_count = models.PositiveIntegerField(default=0)

    @classmethod
    def generate_code(cls, user):
        # Удаляем старые коды пользователя
        cls.objects.filter(user=user).delete()

        # Генерируем 6-значный код
        code = ''.join(random.choices(string.digits, k=6))

        # Создаем и возвращаем новый код
        return cls.objects.create(user=user, code=code)

    def is_valid(self):
        # Код действителен 15 минут
        return not self.is_used and (timezone.now() - self.created_at) < timedelta(minutes=15)
