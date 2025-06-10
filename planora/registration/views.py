import requests
from datetime import datetime
from typing import Any, Union
from login.models import TwoFactorCode
from home.models import Subject, StudyGroup
from home.ruz_teacher_parser import collect_teacher_month_schedule
from home.ruz_student_parser import collect_student_month_schedule
from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth import login as auth_login
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect

# Swagger
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.decorators import api_view
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from rest_framework import status


register_body = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['role', 'username', 'password1', 'password2', 'email', 'full_name'],
    properties={
        'role': openapi.Schema(type=openapi.TYPE_STRING, enum=['teacher', 'student'], description='Роль пользователя'),
        'username': openapi.Schema(type=openapi.TYPE_STRING, description='Логин пользователя'),
        'password1': openapi.Schema(type=openapi.TYPE_STRING, description='Пароль пользователя'),
        'password2': openapi.Schema(type=openapi.TYPE_STRING, description='Подтверждение пароля'),
        'email': openapi.Schema(type=openapi.TYPE_STRING, format='email', description='Email пользователя'),
        'full_name': openapi.Schema(type=openapi.TYPE_STRING, description='Полное имя пользователя'),
        'group_number': openapi.Schema(type=openapi.TYPE_STRING, description='Номер группы (если роль student)'),
    }
)

verify_body = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['code'],
    properties={
        'code': openapi.Schema(type=openapi.TYPE_STRING, description='Код подтверждения из email'),
        'resend': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Запрос повторной отправки кода', default=False),
    }
)
#

User = get_user_model()


def verify_recaptcha(token: str) -> Union[bool, HttpResponse]:
    """
    Проверяет токен Google reCAPTCHA v2
    :param token: токен reCAPTCHA, полученный из формы
    :return: True, если проверка пройдена успешно, иначе False
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


def check_captcha(request: HttpRequest) -> bool:
    """
    Проверяет пройдена ли reCAPTCHA
    :param request: токен reCAPTCHA, полученный из формы
    :return: True, если проверка пройдена успешно, иначе False
    """
    recaptcha_token = request.POST.get('g-recaptcha-response')
    if not recaptcha_token:
        messages.error(request, 'Пожалуйста, подтвердите, что вы не робот')
        return False
    if not verify_recaptcha(recaptcha_token):
        messages.error(request, 'Ошибка проверки reCAPTCHA')
        return False
    return True


def get_form_context(request: HttpRequest) -> dict:
    """
    Передача значений формы в шаблон
    :param request: HTTP-POST-запрос от пользователя
    :return: словарь значений
    """
    return {
        'role': request.POST.get('role', ''),
        'full_name': request.POST.get('full_name', ''),
        'email': request.POST.get('email', ''),
        'username': request.POST.get('username', ''),
        'group_number': request.POST.get('group_number', ''),
    }


def get_data_from_post(request: HttpRequest) -> tuple:
    """
    Получает данные из полей, отправленные пользователем при регистрации
    :param request: HTTP-POST-запрос от пользователя
    :return: кортеж из данных
    """
    return (
        request.POST.get('role'), request.POST.get('username').strip(),
        request.POST.get('password1'), request.POST.get('password2'),
        request.POST.get('email').strip(), request.POST.get('full_name').strip(),
        request.POST.get('group_number', '').strip()
    )


def validate_email_domain(email: str, role: str) -> bool:
    """
    Проверяет домен email
    :param email: адрес электронной почты
    :param role: преподаватель или студент
    :return: True, если домен email валидный, иначе False.
    """
    domain = email.split('@')[-1].lower()
    if role == 'teacher':
        return domain == 'spbstu.ru'
    if role == 'student':
        return domain == 'edu.spbstu.ru'
    return False


def validate_data_from_post(role, username, pass1, pass2, email, full_name, group_number) -> dict:
    """
    Проверяет данные из формы
    :param role: роль пользователя (студент/преподаватель)
    :param username: логин пользователя
    :param pass1: пароль пользователя
    :param pass2: пароль пользователя, введенный второй раз
    :param email: электронная почта пользователя
    :param full_name: ФИО пользователя
    :param group_number: номер учебной группы пользователя (если студент)
    :return: словарь с ошибками
    """
    errors: dict = {}
    if role not in ('teacher', 'student'):
        errors['role_log'] = 'Выберите роль'
    if role == 'student':
        if not group_number:
            errors['group_number_log'] = 'Укажите номер учебной группы'
    if not full_name:
        errors['full_name_log'] = 'Введите ФИО'
    if not email:
        errors['email_log'] = 'Введите email'
    # elif not validate_email_domain(email, role):
    #     errors['email'] = f'Email должен оканчиваться на {"@spbstu.ru" if role == "teacher" else "@edu.spbstu.ru"}'
    if not username:
        errors['username_log'] = 'Введите логин'
    if not pass1 or not pass2:
        errors['password_log'] = 'Введите пароль'
    elif pass1 != pass2:
        errors['password_log'] = 'Пароли не совпадают'
    else:
        try:
            validate_password(pass1)
        except ValidationError as e:
            errors['password_log'] = ', '.join(e.messages)
    return errors


def finish_register(request: HttpRequest, user: Any, email: str, role: str, group_number: str) -> None:
    """
    Завершает регистрацию (посылка 2FA и редирект на страницу подтверждения регистрации)
    :param request: HTTP-POST-запрос от пользователя
    :param user: пользователь в БД
    :param email: электронная почта пользователя
    :param role: роль пользователя (студент/преподаватель)
    :param group_number: номер учебной группы пользователя (если студент)
    :return: None
    """
    # Отправка 2FA кода
    send_mail(
        subject='Подтверждение регистрации',
        message=f'Ваш код подтверждения: {TwoFactorCode.generate_code(user).code}',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=True,
    )

    # Сохранение ID пользователя в сессии
    request.session['registration_user_id'] = user.id

    # Сохранение группы студента в сессии
    if role == 'student':
        request.session['student_group_number'] = group_number

    messages.success(request, 'Код подтверждения отправлен на вашу почту')


def reregistration(request: HttpRequest, user: Any, email: str, role: str, group_number: str) -> None:
    """
    Проводит повторную регистрацию с 2FA
    :param request: HTTP-POST-запрос от пользователя
    :param user: пользователь в БД
    :param email: электронная почта пользователя
    :param role: роль пользователя (студент/преподаватель)
    :param group_number: номер учебной группы пользователя (если студент)
    :return: None
    """
    # Очистка старых 2FA кодов
    TwoFactorCode.objects.filter(user=user).delete()

    # Завершение регистрации
    finish_register(request, user, email, role, group_number)


def check_user_duplicate(
        request: HttpRequest, username: str, email: str,
        role: str, group_number: str, errors: dict
) -> bool:
    """
    Проверяет наличие пользователя в БД - дубликата
    :param request: HTTP-POST-запрос от пользователя
    :param username: логин пользователя
    :param email: электронная почта пользователя
    :param role: роль пользователя (студент/преподаватель)
    :param group_number: номер учебной группы пользователя (если студент)
    :param errors: словарь с ошибками
    :return: False если дубликата нет или он активен, иначе True
    """
    # Поиск дубликата по логину
    existing_user = User.objects.filter(username=username).first()
    if not existing_user:
        # Поиск дубликата по почте
        existing_email = User.objects.filter(email=email).first()
        if not existing_email:
            return False
        else:
            # Учетная запись дубликата активна
            if existing_email.is_active:
                errors['email'] = 'Email уже зарегистрирован'
                return False
            # Учетная запись дубликата неактивна
            else:
                reregistration(request, existing_user, email, role, group_number)
    else:
        # Учетная запись дубликата активна
        if existing_user.is_active:
            errors['username'] = 'Логин уже используется'
            return False
        # Учетная запись дубликата неактивна
        else:
            reregistration(request, existing_user, email, role, group_number)

    return True


def create_inactive_user(
        request: HttpRequest, username: str, password: str, email: str,
        full_name: str, role: str, group_number: str
) -> None:
    """
    :param request: HTTP-POST-запрос от пользователя
    :param username: логин пользователя
    :param password: пароль пользователя
    :param email: электронная почта пользователя
    :param full_name: ФИО пользователя
    :param role: роль пользователя
    :param group_number: номер учебной группы пользователя (если студент)
    :return: None
    """
    # Добавление пользователя в БД
    user = User.objects.create_user(
        username=username,
        password=password,
        email=email,
        full_name=full_name,
        is_active=False,
        role=role,
    )

    # Завершение регистрации
    finish_register(request, user, email, role, group_number)

@swagger_auto_schema(
    method='post',
    operation_description="Регистрация нового пользователя",
    request_body=register_body,
    responses={
        status.HTTP_302_FOUND: openapi.Response('Редирект на страницу подтверждения регистрации'),
        status.HTTP_400_BAD_REQUEST: openapi.Response('Ошибка валидации данных', schema=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'errors': openapi.Schema(type=openapi.TYPE_OBJECT, additional_properties=openapi.Schema(type=openapi.TYPE_STRING))
            }
        ))
    },
    tags=['Registration']
)
@api_view(['POST'])
def register_view(request: HttpRequest) -> Union[HttpResponseRedirect, Any]:
    """
    Обрабатывает регистрацию нового пользователя с подтверждением по email
    :param request: HTTP-запрос от пользователя
    :return: HttpResponseRedirect при успехе или render с формой при ошибке
    """
    # Если пользователь уже авторизован - перенаправление на dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')

    # Обработка POST-запроса
    if request.method == "POST":
        # # Проверка CAPTCHA
        # if not check_captcha(request):
        #     return render(request, 'register.html', get_form_context(request))

        # Получение входных данных
        role, username, pass1, pass2, email, full_name, group_number = get_data_from_post(request)

        # Валидация входных данных
        errors = validate_data_from_post(role, username, pass1, pass2, email, full_name, group_number)

        # Проверка на дубликат пользователя
        if check_user_duplicate(request, username, email, role, group_number, errors):
            # Редирект на страницу подтверждения регистрации
            return redirect('verify_registration')
        else:
            # Обработка ошибок
            if errors:
                for e in errors.values():
                    messages.error(request, e)
                return render(request, 'register.html', get_form_context(request))

            # Создание неактивного пользователя
            create_inactive_user(request, username, pass1, email, full_name, role, group_number)

            # Редирект на страницу подтверждения регистрации
            return redirect('verify_registration')

    # Обработка остальных запросов (например, GET)
    return render(request, 'register.html', get_form_context(request))


@swagger_auto_schema(
    method='post',
    operation_description="Подтверждение регистрации по коду 2FA",
    request_body=verify_body,
    responses={
        status.HTTP_302_FOUND: openapi.Response('Редирект на дашборд после успешной активации'),
        status.HTTP_400_BAD_REQUEST: openapi.Response('Ошибка проверки кода', schema=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'error': openapi.Schema(type=openapi.TYPE_STRING)
            }
        ))
    },
    tags=['Registration']
)
@api_view(['POST'])
def verify_registration(request: HttpRequest) -> Union[HttpResponseRedirect, Any]:
    """
    Подтверждает регистрацию по коду из email
    :param request: HTTP-запрос
    :return: HttpResponseRedirect при успехе или render с формой подтверждения
    """
    # Проверка сессии
    user_id = request.session.get('registration_user_id')
    if not user_id:
        messages.error(request, 'Сессия подтверждения истекла.')
        return redirect('register')

    # Получение пользователя
    user = User.objects.get(id=user_id)

    # Обработка повторной отправки кода
    if request.method == "POST" and request.POST.get('resend') == 'true':
        if user.role == 'teacher':
            reregistration(request, user, user.email, user.role, '')
        else:
            reregistration(request, user, user.email, user.role, request.session['student_group_number'])
        return redirect('verify_registration')

    # Обработка POST-запроса
    if request.method == "POST":
        entered_code = request.POST.get('code', '').strip()
        try:
            code = TwoFactorCode.objects.get(user=user, code=entered_code)
            # Проверка валидности кода
            if code.is_valid():
                # Пометка кода как использованного и сохранение
                code.is_used = True
                code.save()

                # Активация пользователя
                user.is_active = True

                # Если преподаватель - собираем и сохраняем предметы и группы
                if user.role == 'teacher':
                    # Взять расписание за ближайший месяц (сегодняшняя дата)
                    lessons, groups = collect_teacher_month_schedule(
                        teacher_fullname=user.full_name,
                        start_date=datetime.today().isoformat()[:10],  # 'YYYY-MM-DD'
                        weeks=4
                    )
                    # Создать/получить объекты Subject
                    subj_objs = []
                    for subj in set(lessons):
                        obj, _ = Subject.objects.get_or_create(name=subj)
                        subj_objs.append(obj)
                    # Создать/получить объекты StudyGroup
                    group_objs = []
                    for grp in set(groups):
                        obj, _ = StudyGroup.objects.get_or_create(name=grp)
                        group_objs.append(obj)
                    # Назначить M2M-поля
                    user.teaching_subjects.set(subj_objs)
                    user.teaching_groups.set(group_objs)

                # Если студент - собираем и сохраняем предметы и ФИО преподавателей
                if user.role == 'student':
                    # 1) привязать студента к группе
                    grp_name = request.session.get('student_group_number')
                    group_obj, _ = StudyGroup.objects.get_or_create(name=grp_name)
                    user.student_group = group_obj

                    # 2) спарсить расписание на месяц вперёд:
                    lessons = []  # список названий предметов
                    teachers = []  # список ФИО преподавателей
                    if grp_name:
                        lessons, teachers = collect_student_month_schedule(
                            group_number=grp_name,
                            start_date=datetime.today().isoformat()[:10],
                            weeks=4
                        )
                    # 3) сохранить предметы и связь студент-предметы
                    subj_objs = []
                    for subj in set(lessons):
                        obj, _ = Subject.objects.get_or_create(name=subj)
                        subj_objs.append(obj)
                    user.student_subjects.add(*subj_objs)

                    # 4) связь студент-преподаватели
                    # если ваши преподаватели есть в CustomUser, найдём их:
                    for full in set(teachers):
                        try:
                            t = User.objects.get(full_name=full, role='teacher')
                            user.student_teachers.add(t)
                        except User.DoesNotExist:
                            pass

                # Сохранение информации о пользователе (распарсенное расписание)
                user.save()

                # Очистка сессии
                del request.session['registration_user_id']
                request.session.pop('student_group_number', None)

                messages.success(request, 'Регистрация успешно подтверждена!')

                # Авторизация пользователя
                auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
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
                    del request.session['registration_user_id']
                    request.session.pop('student_group_number', None)

                    return redirect('register')
                code.attempt_count += 1
                code.save()

            remind = 'Осталось' if 3 - code.attempt_count == 2 else 'Осталась'
            attempts = 'попытки' if 3 - code.attempt_count == 2 else 'попытка'
            messages.error(request, f'Неверный код подтверждения. {remind} {3 - code.attempt_count} {attempts}!')
            return render(request, 'verify_registration.html', {'email': user.email})

    # Обработка остальных запросов (например, GET)
    return render(request, 'verify_registration.html', {'email': user.email})