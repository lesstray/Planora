from django.shortcuts import render

def login_view(request):
    return render(request, 'auth/login.html')
