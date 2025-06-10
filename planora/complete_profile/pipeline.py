from social_core.exceptions import AuthForbidden
from django.shortcuts import redirect
from django.urls import reverse
from social_core.pipeline.partial import partial


def block_teachers_by_domain(backend, details, **kwargs):
    """
    Если email заканчивается на @spbstu.ru — считаем преподавателем
    и запрещаем OAuth-вход.
    """
    email = details.get('email') or ''
    if email.lower().endswith('@spbstu.ru'):
        # прервём пайплайн и вернём 403
        raise AuthForbidden(backend)


def require_additional_info(backend, details, user=None, is_new=False, *args, **kwargs):
    """
    Когда создан новый пользователь (студент) — запомним его PK в сессии
    и перенаправим на форму заполнения ФИО и группы.
    """
    if user and is_new:
        # Запоминаем PK в сессии
        backend.strategy.session_set('profile_user_pk', user.pk)
        return redirect(reverse('complete_profile'))