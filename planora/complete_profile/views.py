from django.shortcuts import render, redirect
from .models import CompleteProfileForm
from .models import CustomUser
from home.models import Subject, StudyGroup
from django.contrib import messages
from django.contrib.auth import login as auth_login
from home.ruz_student_parser import collect_student_month_schedule
from datetime import datetime
from django.contrib.auth import get_user_model


User = get_user_model()

def complete_profile(request):
    # Читаем PK пользователя из сессии
    user_pk = request.session.get('profile_user_pk')
    if not user_pk:
        return redirect('login')

    try:
        user = CustomUser.objects.get(pk=user_pk)
    except CustomUser.DoesNotExist:
        return redirect('login')

    if request.method == 'POST':
        form = CompleteProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()

            user.role = "student"

            grp_name = request.POST.get('group_number', '')
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

            messages.success(request, 'Профиль успешно завершен!')
            # Убираем PK из сессии
            request.session.pop('profile_user_pk', None)
            auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('dashboard')
    else:
        form = CompleteProfileForm(instance=user)

    return render(request, 'complete_profile.html', {'form': form})
