import random
import string
from typing import Any, Type
from datetime import timedelta
from django.db import models
from django.conf import settings
from django.utils import timezone


class TwoFactorCode(models.Model):
    """
    Класс реализации подтверждения по почте (2FA)
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    attempt_count = models.PositiveIntegerField(default=0)

    @classmethod
    def generate_code(cls, user: Any) -> Type:
        """
        Генерация кода для конкретного пользователя
        :param user: пользователь
        :return: новый код 2FA
        """
        # Удаление старых кодов пользователя
        cls.objects.filter(user=user).delete()

        # Генерация 6-значного кода
        code = ''.join(random.choices(string.digits, k=6))

        # Создание и возврат нового кода
        return cls.objects.create(user=user, code=code)

    def is_valid(self) -> bool:
        """
        Проверка срок действия кода
        :return: True если не прошло 15 минут, иначе False
        """
        # Код действителен 15 минут
        return not self.is_used and (timezone.now() - self.created_at) < timedelta(minutes=15)
