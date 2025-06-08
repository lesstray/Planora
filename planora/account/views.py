from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.sessions.models import Session
from django.shortcuts import render, redirect
from django.utils import timezone
from django.http import HttpRequest, HttpResponse
from django.contrib import messages
from typing import List, Dict, Any
from planora import settings


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    """Главная страница личного кабинета"""
    active_sessions = get_active_sessions(request.user, request.session.session_key)
    return render(request, 'dashboard.html', {
        'active_sessions': active_sessions,
    })


@login_required
def change_password(request: HttpRequest) -> HttpResponse:
    """Обработка смены пароля"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Обновляем сессию, чтобы пользователь не разлогинился
            update_session_auth_hash(request, user)
            messages.success(request, 'Пароль успешно изменён!')
            return redirect('dashboard')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'change_password.html', {
        'form': form,
    })


@login_required
def terminate_sessions(request: HttpRequest) -> HttpResponse:
    """Завершение всех сессий, кроме текущей"""
    if request.method == 'POST':
        terminate_other_sessions(request)
        messages.success(request, 'Все другие сеансы были завершены!')
    return redirect('dashboard')


def get_active_sessions(user, current_session_key: str) -> List[Dict[str, Any]]:
    """Получает список активных сессий пользователя

    Args:
        user: Объект пользователя
        current_session_key: Ключ текущей сессии для сравнения

    Returns:
        Список словарей с информацией о сессиях
    """
    sessions = []
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        data = session.get_decoded()
        if data.get('_auth_user_id') == str(user.pk):
            sessions.append({
                'session_key': session.session_key,
                'ip': data.get('ip', 'Неизвестно'),
                'user_agent': data.get('user_agent', 'Неизвестно'),
                'last_activity': session.expire_date - timezone.timedelta(seconds=settings.SESSION_COOKIE_AGE),
                'is_current': session.session_key == current_session_key,
            })
    return sessions


def terminate_other_sessions(request: HttpRequest) -> None:
    """Завершает все сессии пользователя, кроме текущей"""
    current_session_key = request.session.session_key
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        data = session.get_decoded()
        if data.get('_auth_user_id') == str(request.user.pk) and session.session_key != current_session_key:
            session.delete()