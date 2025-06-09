from typing import Any, Union
from .models import TwoFactorCode
from registration.views import check_captcha
from registration.views import verify_recaptcha
from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.http import HttpRequest, HttpResponseRedirect
from django.contrib.auth import authenticate, login as auth_login


User = get_user_model()


def get_form_context(request: HttpRequest) -> dict:
    """
    Передача значений формы в шаблон
    :param request: HTTP-POST-запрос от пользователя
    :return: словарь значений
    """
    return {
        'username': request.POST.get('username', ''),
    }


def get_data_from_post(request: HttpRequest) -> tuple:
    """
    Получает данные из полей, отправленные пользователем при регистрации
    :param request: HTTP-POST-запрос от пользователя
    :return: кортеж из данных
    """
    return request.POST.get('username').strip(), request.POST.get('password')


def finish_login(request: HttpRequest, user: Any, email: str) -> None:
    """
    Завершает авторизацию (посылка 2FA и редирект на страницу подтверждения авторизации)
    :param request: HTTP-POST-запрос от пользователя
    :param user: пользователь в БД
    :param email: электронная почта пользователя
    :param role: роль пользователя (студент/преподаватель)
    :param group_number: номер учебной группы пользователя (если студент)
    :return: None
    """
    # Отправка 2FA кода
    send_mail(
        subject='Подтверждение входа',
        message=f'Ваш код подтверждения: {TwoFactorCode.generate_code(user).code}',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=True,
    )

    # Сохранение ID пользователя в сессии
    request.session['2fa_user_id'] = user.id

    messages.success(request, 'Код подтверждения отправлен на вашу почту')


def login_view(request: HttpRequest) -> Union[HttpResponseRedirect, Any]:
    """
    Обрабатывает вход пользователя с двухфакторной аутентификацией
    :param request: HTTP-запрос от пользователя
    :return: HttpResponseRedirect при успешной аутентификации, render с формой входа при ошибке или GET-запросе
    """
    # Если пользователь уже авторизован - перенаправление на dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')

    # Обработка POST-запроса
    if request.method == "POST":
        # # Проверка CAPTCHA
        # if not check_captcha(request):
        #     return render(request, 'login.html', get_form_context(request))

        # Получение входных данных
        username, password = get_data_from_post(request)

        # Валидация входных данных
        if not username or not password:
            messages.error(request, 'Заполните все поля')
            return render(request, 'login.html', {'username': username})

        # Аутентификация пользователя
        user = authenticate(request, username=username, password=password)
        if user is None:
            messages.error(request, 'Неверное имя пользователя или пароль')
            return render(request, 'login.html', {'username': username})

        # Завершение авторизации
        finish_login(request, user, user.email)
        return redirect('verify_2fa')

    # Обработка остальных запросов (например, GET)
    return render(request, 'login.html')


def verify_2fa(request: HttpRequest) -> Union[HttpResponseRedirect, Any]:
    """
    Обрабатывает подтверждение двухфакторной аутентификации
    :param request: HTTP-запрос от пользователя
    :return: HttpResponseRedirect при успешном подтверждении, render с формой подтверждения при ошибке или GET-запросе
    """
    # Проверка сессии
    user_id = request.session.get('2fa_user_id')
    if not user_id:
        messages.error(request, 'Сессия подтверждения истекла')
        return redirect('login')

    # Получение пользователя
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'Пользователь не найден')
        return redirect('login')

    # Обработка повторной отправки кода
    if request.method == "POST" and request.POST.get('resend') == 'true':
        # Очистка старых 2FA кодов
        TwoFactorCode.objects.filter(user=user).delete()

        # Завершение авторизации
        finish_login(request, user, user.email)
        return redirect('verify_2fa')

    # Обработка POST-запроса с кодом подтверждения
    if request.method == "POST":
        entered_code = request.POST.get('code', '').strip()
        try:
            code = TwoFactorCode.objects.get(user=user, code=entered_code)
            # Проверка валидности кода
            if code.is_valid():
                # Пометка кода как использованного и сохранение
                code.is_used = True
                code.save()

                # Авторизация пользователя
                auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')

                # Очистка сессии
                del request.session['2fa_user_id']
                return redirect('dashboard')
            else:
                messages.error(request, 'Код устарел или уже использован')

        # Обработка неверного кода
        except TwoFactorCode.DoesNotExist:
            code, created = TwoFactorCode.objects.get_or_create(
                user=user,
                defaults={'code': 'invalid', 'is_used': True}
            )
            if not created:
                if code.attempt_count >= 2:
                    messages.error(request, 'Превышено количество попыток')

                    # Очистка сессии
                    del request.session['2fa_user_id']

                    return redirect('login')
                code.attempt_count += 1
                code.save()

            remind = 'Осталось' if 3 - code.attempt_count == 2 else 'Осталась'
            attempts = 'попытки' if 3 - code.attempt_count == 2 else 'попытка'
            messages.error(request, f'Неверный код подтверждения. {remind} {3 - code.attempt_count} {attempts}!')
            return render(request, 'verify_2fa.html', {'email': user.email})

    # Обработка остальных запросов (например, GET)
    return render(request, 'verify_2fa.html', {'email': user.email})
