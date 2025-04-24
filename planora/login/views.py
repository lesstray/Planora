from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.contrib import messages
from django.conf import settings
from django.contrib.auth import get_user_model
import requests
from .models import TwoFactorCode
from django.core.mail import send_mail
from django.urls import reverse


User = get_user_model()


def verify_recaptcha(token):
    """
    Проверяет токен Google reCAPTCHA.

    :param token: Токен reCAPTCHA, полученный из формы.
    :return: True, если проверка пройдена успешно, иначе False.
    """
    data = {
        'secret': settings.RECAPTCHA_PRIVATE_KEY,
        'response': token
    }
    response = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data)
    return response.json().get('success', False)


def login_view(request):
    """
    Отображает страницу входа и обрабатывает форму аутентификации.

    :param request: HTTP-запрос от пользователя.
    :return: HTTP-ответ с HTML-страницей входа или редирект на главную страницу.
    """
    # Если пользователь уже авторизован - перенаправляем
    # if request.user.is_authenticated:
    #     return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)

    if request.method == "POST":
        # # Проверка CAPTCHA
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

        if not username or not password:
            messages.error(request, 'Заполните все поля')
            return render(request, 'login.html', {
                'username': username
            })

        # Попытка аутентификации
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # Генерируем и отправляем код
            code = TwoFactorCode.generate_code(user)

            send_mail(
                'Ваш код подтверждения',
                f'Ваш код для входа: {code.code}',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )

            # Сохраняем user_id в сессии
            request.session['2fa_user_id'] = user.id
            return HttpResponseRedirect(reverse('verify_2fa'))
        else:
            messages.error(request, 'Неверное имя пользователя или пароль')
            return render(request, 'login.html', {'username': username})

    return render(request, 'login.html')


def verify_2fa(request):
    if '2fa_user_id' not in request.session:
        return HttpResponseRedirect(reverse('login'))

    user_id = request.session['2fa_user_id']
    user = User.objects.get(id=user_id)

    if request.method == "POST":
        entered_code = request.POST.get('code', '').strip()

        try:
            code = TwoFactorCode.objects.get(user=user, code=entered_code)

            # Проверяем количество попыток ДО увеличения счетчика
            if code.attempt_count >= 3:  # Используем >= вместо >
                messages.error(request, 'Превышено количество попыток')
                return HttpResponseRedirect(reverse('login'))

            # Увеличиваем счетчик и сохраняем
            code.attempt_count += 1
            code.save()

            if code.is_valid():
                code.is_used = True
                code.save()

                auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                del request.session['2fa_user_id']
                next_url = request.POST.get('next') or request.GET.get('next') or settings.LOGIN_REDIRECT_URL
                return HttpResponseRedirect(next_url)
            else:
                messages.error(request, 'Код устарел или уже использован')
        except TwoFactorCode.DoesNotExist:
            # Получаем или создаем запись для неверного кода
            code, created = TwoFactorCode.objects.get_or_create(
                user=user,
                defaults={'code': 'invalid', 'is_used': True}
            )
            if not created:
                if code.attempt_count >= 3:
                    messages.error(request, 'Превышено количество попыток')
                    return HttpResponseRedirect(reverse('login'))
                code.attempt_count += 1
                code.save()

            messages.error(request, 'Неверный код подтверждения')

    return render(request, 'verify_2fa.html')
