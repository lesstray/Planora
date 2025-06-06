from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin


class SessionInfoMiddleware(MiddlewareMixin):
    """Сохраняет дополнительную информацию о сессии"""
    def process_request(self, request):
        if request.user.is_authenticated:
            session = request.session
            if not session.get('ip'):
                session['ip'] = self.get_client_ip(request)
                session['user_agent'] = request.META.get('HTTP_USER_AGENT', '')

    @staticmethod
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        return x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')