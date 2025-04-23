import requests
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from login.models import TwoFactorCode
from typing import Dict, Any, Union


User = get_user_model()


def verify_recaptcha(token: str) -> bool:
    """
    Проверяет токен Google reCAPTCHA v2.

    :param token: токен reCAPTCHA, полученный из формы.
    :return: True, если проверка пройдена успешно, иначе False.
    """
    data = {
        'secret': settings.RECAPTCHA_PRIVATE_KEY,
        'response': token
    }
    try:
        response = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data=data,
            timeout=5
        )
        result = response.json()
        return result.get('success', False)
    except requests.RequestException:
        return False


def register_view(request: HttpRequest) -> Union[HttpResponseRedirect, Any]:
    """
    Обрабатывает регистрацию нового пользователя с подтверждением по email

    :param request: HTTP-запрос от пользователя.
    :return: HttpResponseRedirect при успехе или render с формой при ошибке
    """
    if request.method != "POST":
        return render(request, 'register.html')

    # Проверка CAPTCHA
    recaptcha_token = request.POST.get('g-recaptcha-response')
    if not recaptcha_token:
        messages.error(request, 'Пожалуйста, подтвердите, что вы не робот')
        return render(request, 'register.html', {
            'captcha_error': 'Необходимо пройти проверку reCAPTCHA',
            'username': request.POST.get('username', ''),
            'email': request.POST.get('email', ''),
            'full_name': request.POST.get('full_name', '')
        })
    if not verify_recaptcha(recaptcha_token):
        messages.error(request, 'Ошибка проверки reCAPTCHA')
        return render(request, 'register.html', {
            'captcha_error': 'Проверка reCAPTCHA не пройдена',
            'username': request.POST.get('username', ''),
            'email': request.POST.get('email', ''),
            'full_name': request.POST.get('full_name', '')
        })

    # Получение и очистка данных формы
    username = request.POST.get('username').strip()
    password1 = request.POST.get('password1')
    password2 = request.POST.get('password2')
    email = request.POST.get('email').strip()
    full_name = request.POST.get('full_name').strip()

    # Валидация данных
    errors: Dict[str, str] = {}

    # Проверка обязательных полей
    if not username:
        errors['username'] = 'Введите логин'
    if not email:
        errors['email'] = 'Введите email'
    if not full_name:
        errors['full_name'] = 'Введите ФИО'

    # Проверка паролей
    if not password1 or not password2:
        errors['password'] = 'Введите пароль'
    elif password1 != password2:
        errors['password'] = 'Пароли не совпадают'
    else:
        try:
            validate_password(password1)
        except ValidationError as e:
            errors['password'] = ', '.join(e.messages)

    # Проверка существующих пользователей
    existing_user = User.objects.filter(username=username).first()
    if existing_user:
        if existing_user.is_active:
            errors['username'] = 'Пользователь с таким именем уже существует'
        else:
            # Удаление старой неактивной регистрации
            existing_user.delete()
            TwoFactorCode.objects.filter(user=existing_user).delete()

    existing_email = User.objects.filter(email=email).first()
    if existing_email:
        if existing_email.is_active:
            errors['email'] = 'Пользователь с таким email уже существует'
        else:
            # Удаление старой неактивной регистрации
            existing_email.delete()
            TwoFactorCode.objects.filter(user=existing_email).delete()

    # Обработка ошибок
    if errors:
        for error in errors.values():
            messages.error(request, error)
        return render(request, 'register.html', {
            'username': username,
            'email': email,
            'full_name': full_name
        })

    # Создание неактивного пользователя
    try:
        user = User.objects.create_user(
            username=username,
            password=password1,
            email=email,
            full_name=full_name,
            is_active=False     # Пользователь неактивен до подтверждения почты
        )

        # Генерация и отправка кода подтверждения
        code = TwoFactorCode.generate_code(user)
        send_mail(
            subject='Подтверждение регистрации',
            message=f'Ваш код подтверждения: {code.code}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

        # Сохранение ID пользователя в сессии
        request.session['registration_user_id'] = user.id
        messages.success(request, 'Код подтверждения отправлен на вашу почту')
        return redirect('verify_registration')

    except Exception as e:
        messages.error(request, f'Ошибка при регистрации: {str(e)}')
        return render(request, 'register.html', {
            'username': username,
            'email': email,
            'full_name': full_name
        })


def verify_registration(request: HttpRequest) -> Union[HttpResponseRedirect, Any]:
    """
    Подтверждение регистрации по коду из email

    :param request: HTTP-запрос
    :return: HttpResponseRedirect при успехе или render с формой подтверждения
    """

    # Проверка сессии
    user_id = request.session.get('registration_user_id')
    if not user_id:
        messages.error(request, 'Сессия подтверждения истекла')
        return redirect('register')

    # Получение пользователя
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'Пользователь не найден')
        return redirect('register')

    # Обработка POST-запроса с кодом подтверждения
    if request.method == "POST":
        entered_code = request.POST.get('code', '').strip()

        try:
            code = TwoFactorCode.objects.get(user=user, code=entered_code)

            # Проверка количества попыток ДО увеличения счетчика
            if code.attempt_count >= 3:
                messages.error(request, 'Превышено количество попыток')
                return redirect('register')

            # Увеличение счетчика и сохранение
            code.attempt_count += 1
            code.save()

            # Проверка валидности кода
            if code.is_valid():
                code.is_used = True
                code.save()

                # Активация пользователя
                user.is_active = True
                user.save()

                # Очистка сессии
                del request.session['registration_user_id']
                messages.success(request, 'Регистрация успешно подтверждена! Теперь вы можете войти.')
                return redirect('login')
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
                    return redirect('register')
                code.attempt_count += 1
                code.save()

            messages.error(request, 'Неверный код подтверждения')

    return render(request, 'verify_registration.html', {'email': user.email})
