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
from home.models import Subject, StudyGroup
from home.ruz_teacher_parser import collect_teacher_month_schedule
from home.ruz_student_parser import collect_student_month_schedule
from datetime import datetime


User = get_user_model()


# функция для передачи в шаблон значений формы
def get_form_context(request) -> Dict:
    """
    Передача значений формы в шаблон

    :param request: запрос
    :param role: роль (преподаватель/студент)
    """
    return {
        'role': request.POST.get('role', ''),
        'full_name': request.POST.get('full_name', ''),
        'email': request.POST.get('email', ''),
        'username': request.POST.get('username', ''),
        'group_number': request.POST.get('group_number', ''),
    }


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


def verify_recaptcha(token: str) -> bool:
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


def register_view(request: HttpRequest) -> Union[HttpResponseRedirect, Any]:
    """
    Обрабатывает регистрацию нового пользователя с подтверждением по email

    :param request: HTTP-запрос от пользователя.
    :return: HttpResponseRedirect при успехе или render с формой при ошибке
    """
    if request.method == "POST":
        # Проверка CAPTCHA
        #recaptcha_token = request.POST.get('g-recaptcha-response')
        #if not recaptcha_token:
        #    messages.error(request, 'Пожалуйста, подтвердите, что вы не робот')
        #    return render(request, 'register.html', get_form_context(request))
        #if not verify_recaptcha(recaptcha_token):
        #    messages.error(request, 'Ошибка проверки reCAPTCHA')
        #    return render(request, 'register.html', get_form_context(request))

        # Получение данных
        role = request.POST.get('role')
        username = request.POST.get('username').strip()
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        email = request.POST.get('email').strip()
        full_name = request.POST.get('full_name').strip()
        group_number = request.POST.get('group_number', '').strip()

        # Валидация данных
        errors: Dict[str, str] = {}
        if not role or role not in ('teacher', 'student'):
            errors['role'] = 'Выберите роль'
        if role == 'student':
            if not group_number:
                errors['group_number'] = 'Укажите номер учебной группы'
        if not full_name:
            errors['full_name'] = 'Введите ФИО'
        if not email:
            errors['email'] = 'Введите email'
        if not username:
            errors['username'] = 'Введите логин'
        if not password1 or not password2:
            errors['password'] = 'Введите пароль'
        elif password1 != password2:
            errors['password'] = 'Пароли не совпадают'
        else:
            try:
                validate_password(password1)
            except ValidationError as e:
                errors['password'] = ', '.join(e.messages)

        # Проверка домена email в зависимости от роли
        if 'email' not in errors and not validate_email_domain(email, role):
            expected = '@spbstu.ru' if role == 'teacher' else '@edu.spbstu.ru'
            errors['email'] = f'Email должен оканчиваться на {expected}'

        # Проверка существующих пользователей
        existing_user = User.objects.filter(username=username).first()
        if existing_user:
            if existing_user.is_active:
                errors['username'] = 'Логин уже используется'
            else:
                # не удаляем сама запись, а очищаем всё, что нужно
                existing_user.set_password(password1)
                existing_user.email = email
                existing_user.full_name = full_name
                existing_user.role = role
                existing_user.is_active = False
                # очищаем старые коды
                TwoFactorCode.objects.filter(user=existing_user).delete()
                # очищаем новые M2M-поля (если есть)
                existing_user.teaching_subjects.clear()
                existing_user.teaching_groups.clear()
                existing_user.student_subjects.clear()
                existing_user.student_teachers.clear()
                existing_user.student_group = None
                existing_user.save()
                user = existing_user
                # сразу переходим к генерации кода и отправке письма
                code = TwoFactorCode.generate_code(user)
                send_mail(
                    subject='Подтверждение регистрации',
                    message=f'Ваш код подтверждения: {code.code}',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
                request.session['registration_user_id'] = user.id
                if role == 'student':
                    request.session['student_group_number'] = group_number
                messages.success(request, 'Код подтверждения отправлен на вашу почту')
                return redirect('verify_registration')

        existing_email = User.objects.filter(email=email).first()
        if existing_email:
            if existing_email.is_active:
                errors['email'] = 'Email уже зарегистрирован'
            else:
                # не удаляем сама запись, а очищаем всё, что нужно
                existing_email.set_password(password1)
                existing_email.email = email
                existing_email.full_name = full_name
                existing_email.role = role
                existing_email.is_active = False
                # очищаем старые коды
                TwoFactorCode.objects.filter(user=existing_email).delete()
                # очищаем новые M2M-поля (если есть)
                existing_email.teaching_subjects.clear()
                existing_email.teaching_groups.clear()
                existing_email.student_subjects.clear()
                existing_email.student_teachers.clear()
                existing_email.student_group = None
                existing_email.save()
                user = existing_email
                # сразу переходим к генерации кода и отправке письма
                code = TwoFactorCode.generate_code(user)
                send_mail(
                    subject='Подтверждение регистрации',
                    message=f'Ваш код подтверждения: {code.code}',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
                request.session['registration_user_id'] = user.id
                if role == 'student':
                    request.session['student_group_number'] = group_number
                messages.success(request, 'Код подтверждения отправлен на вашу почту')
                return redirect('verify_registration')

        # Обработка ошибок
        if errors:
            for e in errors.values():
                messages.error(request, e)
            return render(request, 'register.html', get_form_context(request))

        # Создание неактивного пользователя
        try:
            user = User.objects.create_user(
                username=username,
                password=password1,
                email=email,
                full_name=full_name,
                is_active=False,     # Пользователь неактивен до подтверждения почты
                role=role
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
            if role == 'student':
                # сохраняем порядковый номер группы в сессии
                request.session['student_group_number'] = group_number
            messages.success(request, 'Код подтверждения отправлен на вашу почту')
            return redirect('verify_registration')

        except Exception as e:
            messages.error(request, f'Ошибка при регистрации: {e}')
            return render(request, 'register.html', get_form_context(request))

    # GET
    return render(request, 'register.html', get_form_context(request))


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

                user.save()

                # Очистка сессии
                del request.session['registration_user_id']
                request.session.pop('student_group_number', None)
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
