from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth import authenticate, login as user_login, logout as user_logout
from django.http import HttpResponseRedirect
import requests
from django.conf import settings
from django.contrib import messages
# Create your views here.

def verify_recaptcha(token):
    data = {
        'secret': settings.RECAPTCHA_PRIVATE_KEY,
        'response': token
    }
    response = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data)
    return response.json().get('success', False)

def index(request):
    return render(request, 'checkwork/index.html')

def root_redirect(request):
    return HttpResponseRedirect('register')

def about(request):
    return render(request, 'checkwork/about.html')

def home_view(request):
    return render(request, 'checkwork/index.html')

def login_view(request):
    if request.method == "POST":
        # Проверка reCAPTCHA
        recaptcha_token = request.POST.get('g-recaptcha-response')
        if not verify_recaptcha(recaptcha_token):
            messages.error(request, 'Пожалуйста, подтвердите, что вы не робот')
            return render(request, 'checkwork/login.html', {'captcha_error': 'Проверка reCAPTCHA не пройдена'})
        user_name = request.POST.get('login')
        user_password = request.POST.get('password')
        # здесь логика сверки пользователя с БД
        # usr = authenticate(request, username=user_name, password=user_password)
        # if usr is not None:
        #     user_login(request, usr)
        #     return HttpResponseRedirect('/')
        # else:
        #     return render(request, 'checkwork/login.html')
    return render(request, 'checkwork/login.html')

def reg_view(request):
    if request.method == "POST":
        # Проверка reCAPTCHA
        recaptcha_token = request.POST.get('g-recaptcha-response')
        if not verify_recaptcha(recaptcha_token):
            messages.error(request, 'Пожалуйста, подтвердите, что вы не робот')
            return render(request, 'checkwork/reg.html', {'captcha_error': 'Проверка reCAPTCHA не пройдена'})
        user_name = request.POST.get('login')
        user_password1 = request.POST.get('password1')
        user_password2 = request.POST.get('password2')
        email = request.POST.get('email')
        full_name = request.POST.get('full_name')
        if user_password1 == user_password2:
            # здесь должна быть логика добавления пользователя в БД и тд
            return HttpResponseRedirect('home')
        else:
            return HttpResponseRedirect('login')
            # CustomUser.objects.create_user(user_name, user_password2)
            #
            # usr = authenticate(request, username=user_name, password=user_password)
            # if usr is not None:
            #     user_login(request, usr)
            #     return HttpResponseRedirect('/')
            # else:
            #     return render(request, 'checkwork/login.html')



    return render(request, 'checkwork/reg.html')

