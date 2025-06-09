from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.urls import reverse
from django.core.mail import send_mail
from django.conf import settings

CustomUser = get_user_model()

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser

    list_display = ('username', 'email', 'is_active', 'is_staff', 'is_superuser')
    list_filter  = ('is_active', 'is_staff', 'is_superuser')

    actions = [
        'action_deactivate_users',
        'action_terminate_sessions',
        'action_send_password_reset',
    ]

    @admin.action(description="Завершить все сессии выбранных пользователей")
    def action_terminate_sessions(self, request, queryset):
        terminated = 0
        # Для каждого пользователя удаляются все сессии
        for user in queryset:
            # Выбор неистекших сессий
            qs = Session.objects.filter(expire_date__gte=timezone.now())
            for sess in qs:
                data = sess.get_decoded()
                if data.get('_auth_user_id') == str(user.pk):
                    sess.delete()
                    terminated += 1
        self.message_user(
            request,
            f"Завершено сессий: {terminated}",
            level=messages.SUCCESS
        )

    @admin.action(description="Деактивировать выбранных пользователей")
    def action_deactivate_users(self, request, queryset):
        self.action_terminate_sessions(request, queryset)
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f"Деактивировано пользователей: {updated}",
            level=messages.SUCCESS
        )

    @admin.action(description="Отправить письма со ссылкой на сброс пароля через send_mail")
    def action_send_password_reset(self, request, queryset):
        sent = 0
        for user in queryset:
            if not user.email:
                continue

            # Генерация uid и токена
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            # Абсолютная ссылка
            reset_path = reverse(
                'password_reset_confirm',
                kwargs={'uidb64': uidb64, 'token': token}
            )
            reset_url = request.build_absolute_uri(reset_path)

            # Тема и текст письма
            subject = 'Сброс пароля'
            message = (
                f'Здравствуйте, {user.full_name}!\n\n'
                f'Чтобы сбросить пароль, перейдите по ссылке:\n\n'
                f'{reset_url}\n\n'
                'Если вы не запрашивали сброс пароля, просто проигнорируйте это письмо.\n'
            )

            # Отправка
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            sent += 1

        self.message_user(
            request,
            f'Письма на сброс пароля отправлено: {sent}',
            level=messages.SUCCESS
        )
