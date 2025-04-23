from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate, login, get_user_model
import requests
from django.core.mail import send_mail
from django.urls import reverse
from login.models import TwoFactorCode


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

        # Проверка существующих пользователей
        existing_user = User.objects.filter(username=username).first()
        if existing_user:
            if existing_user.is_active:
                errors['username'] = 'Пользователь с таким именем уже существует'
            else:
                # Удаляем старую неактивную регистрацию
                existing_user.delete()
                TwoFactorCode.objects.filter(user=existing_user).delete()

        existing_email = User.objects.filter(email=email).first()
        if existing_email:
            if existing_email.is_active:
                errors['email'] = 'Пользователь с таким email уже существует'
            else:
                # Удаляем старую неактивную регистрацию
                existing_email.delete()
                TwoFactorCode.objects.filter(user=existing_email).delete()

        if errors:
            for field, error in errors.items():
                messages.error(request, f'{field}: {error}')
            return render(request, 'register.html', {
                'username': username,
                'email': email,
                'full_name': full_name,
                'errors': errors
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
                'Подтверждение регистрации',
                f'Ваш код подтверждения: {code.code}',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )

            # Сохранение user_id в сессии для подтверждения
            request.session['registration_user_id'] = user.id
            messages.success(request, 'Код подтверждения отправлен на вашу почту')
            return redirect('verify_registration')

        except Exception as e:
            messages.error(request, f'Ошибка при создании пользователя: {str(e)}')
            return render(request, 'register.html', {
                'username': username,
                'email': email,
                'full_name': full_name
            })

    return render(request, 'register.html')


def verify_registration(request):
    if 'registration_user_id' not in request.session:
        messages.error(request, 'Сессия подтверждения истекла')
        return HttpResponseRedirect(reverse('register'))

    try:
        user = User.objects.get(id=request.session['registration_user_id'])
    except User.DoesNotExist:
        messages.error(request, 'Пользователь не найден')
        return HttpResponseRedirect(reverse('register'))

    if request.method == "POST":
        entered_code = request.POST.get('code', '').strip()

        try:
            code = TwoFactorCode.objects.get(user=user, code=entered_code)

            # Проверка количества попыток ДО увеличения счетчика
            if code.attempt_count >= 3:
                messages.error(request, 'Превышено количество попыток')
                return HttpResponseRedirect(reverse('register'))

            # Увеличение счетчика и сохранение
            code.attempt_count += 1
            code.save()

            if code.is_valid():
                code.is_used = True
                code.save()

                # Активация пользователя
                user.is_active = True
                user.save()

                del request.session['registration_user_id']
                messages.success(request, 'Регистрация успешно подтверждена! Теперь вы можете войти.')
                return HttpResponseRedirect(reverse('login'))
            else:
                messages.error(request, 'Код устарел или уже использован')
        except TwoFactorCode.DoesNotExist:
            # Получение или создание записи для неверного кода
            code, created = TwoFactorCode.objects.get_or_create(
                user=user,
                defaults={'code': 'invalid', 'is_used': True}
            )
            if not created:
                if code.attempt_count >= 3:
                    messages.error(request, 'Превышено количество попыток')
                    return HttpResponseRedirect(reverse('register'))
                code.attempt_count += 1
                code.save()

            messages.error(request, 'Неверный код подтверждения')

    return render(request, 'verify_registration.html', {'email': user.email})
