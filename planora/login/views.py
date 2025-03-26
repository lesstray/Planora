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
    if request.method == "POST":
        recaptcha_token = request.POST.get('g-recaptcha-response')
        if not verify_recaptcha(recaptcha_token):
            messages.error(request, 'Пожалуйста, подтвердите, что вы не робот')
            return render(request, 'login.html', {'captcha_error': 'Проверка reCAPTCHA не пройдена'})

        user_name = request.POST.get('login')
        user_password = request.POST.get('password')
        # usr = authenticate(request, username=user_name, password=user_password)

        # if usr is not None:
        #     login(request, usr)
        #     return HttpResponseRedirect('/')
        # else:
        #     # messages.error(request, 'Неверные учетные данные')

        return HttpResponseRedirect('/')

    return render(request, 'login.html')
