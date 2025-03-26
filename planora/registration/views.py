from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate, login, get_user_model
import requests


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


def register_view(request):
    """
    Отображает страницу регистрации и обрабатывает ввод пользователя.

    :param request: HTTP-запрос от пользователя.
    :return: HTTP-ответ с HTML-страницей регистрации или редирект на домашнюю страницу.
    """
    if request.method == "POST":
        # # Проверка CAPTCHA
        # recaptcha_token = request.POST.get('g-recaptcha-response')
        # if not recaptcha_token:
        #     messages.error(request, 'Пожалуйста, подтвердите, что вы не робот')
        #     return render(request, 'register.html', {
        #         'captcha_error': 'Необходимо пройти проверку reCAPTCHA',
        #         'username': request.POST.get('username', ''),
        #         'email': request.POST.get('email', ''),
        #         'full_name': request.POST.get('full_name', '')
        #     })
        # if not verify_recaptcha(recaptcha_token):
        #     messages.error(request, 'Ошибка проверки reCAPTCHA')
        #     return render(request, 'register.html', {
        #         'captcha_error': 'Проверка reCAPTCHA не пройдена',
        #         'username': request.POST.get('username', ''),
        #         'email': request.POST.get('email', ''),
        #         'full_name': request.POST.get('full_name', '')
        #     })

        # Получение данных
        username = request.POST.get('username').strip()
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        email = request.POST.get('email').strip()
        full_name = request.POST.get('full_name').strip()

        # Валидация данных
        errors = {}

        if not username:
            errors['username'] = 'Введите логин'
        if not email:
            errors['email'] = 'Введите email'
        if not full_name:
            errors['full_name'] = 'Введите ФИО'
        if not password1 or not password2:
            errors['password1'] = 'Введите пароль'
        elif password1 != password2:
            errors['password2'] = 'Пароли не совпадают'
        else:
            try:
                validate_password(password1)
            except ValidationError as e:
                errors['password1'] = ', '.join(e.messages)

        if errors:
            for field, error in errors.items():
                messages.error(request, f'{field}: {error}')
            return render(request, 'register.html', {
                'username': username,
                'email': email,
                'full_name': full_name,
                'errors': errors
            })

        # Проверка существования пользователя
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Пользователь с таким именем уже существует')
            return render(request, 'register.html', {'email': email, 'full_name': full_name})
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Пользователь с таким email уже существует')
            return render(request, 'register.html', {'username': username, 'full_name': full_name})

        # Создание пользователя
        try:
            user = User.objects.create_user(
                username=username,
                password=password1,
                email=email,
                full_name=full_name
            )
            messages.success(request, 'Регистрация прошла успешно! Теперь вы можете войти.')
            return HttpResponseRedirect('/login')
        except Exception as e:
            messages.error(request, f'Ошибка при создании пользователя: {str(e)}')
            return render(request, 'register.html', {'username': username, 'email': email, 'full_name': full_name})

    return render(request, 'register.html')
