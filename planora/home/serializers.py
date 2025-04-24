from rest_framework import serializers
from .models import Task, Group
from django.contrib.auth import get_user_model

User = get_user_model()

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task  # Указываем, какая модель используется
        fields = '__all__'  # Все поля модели будут в JSON

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = '__all__'