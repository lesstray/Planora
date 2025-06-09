from django.shortcuts import render
from django.conf import settings

def about_view(request):
    return render(request, 'about.html',{
        "version": settings.GIT_VERSION
    })
