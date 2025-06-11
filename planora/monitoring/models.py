from django.db import models

class SystemStats(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    cpu = models.FloatField()
    ram = models.FloatField()
    gpu = models.FloatField()
    disk = models.JSONField()  # Словарь: {"C:/": 32.5, "D:/": 60.0, ...}

    def __str__(self):
        return f"{self.timestamp} | CPU: {self.cpu}% | RAM: {self.ram}%"