from rest_framework import serializers
from .models import Group, Lesson, StudentPlan, AttendanceStats
from django.contrib.auth import get_user_model

User = get_user_model()

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = '__all__'

class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = '__all__'

class StudentPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentPlan
        fields = '__all__'

class AttendanceStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceStats
        fields = '__all__'