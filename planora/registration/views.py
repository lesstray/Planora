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


def register_view(request):
    """
    Отображает страницу регистрации и обрабатывает ввод пользователя.

    :param request: HTTP-запрос от пользователя.
    :return: HTTP-ответ с HTML-страницей регистрации или редирект на домашнюю страницу.
    """
    if request.method == "POST":
        recaptcha_token = request.POST.get('g-recaptcha-response')
        if not verify_recaptcha(recaptcha_token):
            messages.error(request, 'Пожалуйста, подтвердите, что вы не робот')
            return render(request, 'register.html', {'captcha_error': 'Проверка reCAPTCHA не пройдена'})

        user_name = request.POST.get('login')
        user_password1 = request.POST.get('password1')
        user_password2 = request.POST.get('password2')
        email = request.POST.get('email')
        full_name = request.POST.get('full_name')

        if user_password1 == user_password2:
            # Здесь должна быть логика создания пользователя в БД
            # CustomUser.objects.create_user(username=user_name, password=user_password1, email=email, full_name=full_name)
            return HttpResponseRedirect('/home')
        else:
            messages.error(request, 'Пароли не совпадают')
            return HttpResponseRedirect('/register')

    return render(request, 'register.html')
