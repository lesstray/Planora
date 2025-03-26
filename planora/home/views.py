from django.http import HttpResponseRedirect
from django.shortcuts import render


def root_redirect(request):
    """
    Перенаправляет корневой URL на страницу регистрации.

    :param request: HTTP-запрос от пользователя.
    :return: HTTP-редирект на '/register'.
    """
    return HttpResponseRedirect('/register')


def home_view(request):
    return render(request, 'index.html')
