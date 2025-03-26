from django.contrib.auth import authenticate, login
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.contrib import messages
from django.conf import settings
import requests


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
    if request.user.is_authenticated:
        return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)

    if request.method == "POST":
        # # Проверка CAPTCHA
        # recaptcha_token = request.POST.get('g-recaptcha-response')
        # if not recaptcha_token:
        #     messages.error(request, 'Пожалуйста, подтвердите, что вы не робот')
        #     return render(request, 'login.html', {
        #         'captcha_error': 'Необходимо пройти проверку reCAPTCHA',
        #         'username': request.POST.get('username', '')
        #     })
        # if not verify_recaptcha(recaptcha_token):
        #     messages.error(request, 'Ошибка проверки reCAPTCHA')
        #     return render(request, 'login.html', {
        #         'captcha_error': 'Проверка reCAPTCHA не пройдена',
        #         'username': request.POST.get('username', '')
        #     })

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
            login(request, user)
            return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
        else:
            messages.error(request, 'Неверное имя пользователя или пароль')
            return render(request, 'login.html', {'username': username})

    return render(request, 'login.html')
