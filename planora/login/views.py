from django.contrib.auth import authenticate, login as auth_login
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.urls import reverse
from typing import Any, Union
from registration.views import verify_recaptcha
from .models import TwoFactorCode


User = get_user_model()


def login_view(request: HttpRequest) -> Union[HttpResponseRedirect, Any]:
    """
    Обрабатывает вход пользователя с двухфакторной аутентификацией

    :param request: HTTP-запрос от пользователя
    :return: HttpResponseRedirect при успешной аутентификации, render с формой входа при ошибке или GET-запросе
    """
    # Если пользователь уже авторизован - перенаправление
    # if request.user.is_authenticated:
    #     return redirect(settings.LOGIN_REDIRECT_URL)

    if request.method == "POST":
        recaptcha_token = request.POST.get('g-recaptcha-response')
        if not recaptcha_token:
            messages.error(request, 'Пожалуйста, подтвердите, что вы не робот')
            return render(request, 'login.html', {
                'captcha_error': 'Необходимо пройти проверку reCAPTCHA',
                'username': request.POST.get('username', '')
            })
        if not verify_recaptcha(recaptcha_token):
            messages.error(request, 'Ошибка проверки reCAPTCHA')
            return render(request, 'login.html', {
                'captcha_error': 'Проверка reCAPTCHA не пройдена',
                'username': request.POST.get('username', '')
            })

        # Получение данных
        username = request.POST.get('username').strip()
        password = request.POST.get('password')

        # Валидация входных данных
        if not username or not password:
            messages.error(request, 'Заполните все поля')
            return render(request, 'login.html', {'username': username})

        # Аутентификация пользователя
        user = authenticate(request, username=username, password=password)
        if user is None:
            messages.error(request, 'Неверное имя пользователя или пароль')
            return render(request, 'login.html', {'username': username})

        # Генерация и отправка кода подтверждения
        try:
            code = TwoFactorCode.generate_code(user)
            send_mail(
                subject='Ваш код подтверждения',
                message=f'Ваш код для входа: {code.code}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False
            )

            # Сохранение ID пользователя в сессии для 2FA
            request.session['2fa_user_id'] = user.id
            return redirect('verify_2fa')

        except Exception as e:
            messages.error(request, 'Ошибка при отправке кода подтверждения')
            return render(request, 'login.html', {'username': username})

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

    # Обработка POST-запроса с кодом подтверждения
    if request.method == "POST":
        entered_code = request.POST.get('code', '').strip()

        try:
            code = TwoFactorCode.objects.get(user=user, code=entered_code)

            # Проверка количества попыток ДО увеличения счетчика
            if code.attempt_count >= 3:
                messages.error(request, 'Превышено количество попыток')
                return HttpResponseRedirect(reverse('login'))

            # Увеличение счетчика и сохранение
            code.attempt_count += 1
            code.save()

            if code.is_valid():
                code.is_used = True
                code.save()

                auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')

                # Очистка сессии
                del request.session['2fa_user_id']
                return HttpResponseRedirect(reverse('dashboard'))
            else:
                messages.error(request, 'Код устарел или уже использован')

        except TwoFactorCode.DoesNotExist:
            # Обработка неверного кода
            code, created = TwoFactorCode.objects.get_or_create(
                user=user,
                defaults={'code': 'invalid', 'is_used': True}
            )
            if not created:
                if code.attempt_count >= 3:
                    messages.error(request, 'Превышено количество попыток')
                    return redirect('login')
                code.attempt_count += 1
                code.save()

            messages.error(request, 'Неверный код подтверждения')

    return render(request, 'verify_2fa.html', {'email': user.email})
