from django.contrib import admin
from django.utils.html import mark_safe
from .models import SystemStats
import matplotlib.pyplot as plt
import base64
import io


@admin.register(SystemStats)
class SystemStatsAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'cpu', 'ram', 'gpu')
    readonly_fields = ('timestamp',)

    def metrics_plot(self, obj=None):
        # Берём последние 20 записей для отображения графика
        stats = SystemStats.objects.order_by('-timestamp')[:20][::-1]
        times = [s.timestamp.strftime('%H:%M:%S') for s in stats]
        cpu_vals = [s.cpu for s in stats]
        ram_vals = [s.ram for s in stats]
        gpu_vals = [s.gpu for s in stats]

        # Строим график
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(times, cpu_vals, label='CPU')
        ax.plot(times, ram_vals, label='RAM')
        ax.plot(times, gpu_vals, label='GPU')
        ax.set_xlabel('Время')
        ax.set_ylabel('Процент (%)')
        ax.legend()
        ax.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()

        # Сохраняем в буфер и кодируем в base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100)
        plt.close(fig)
        buffer.seek(0)
        image_png = buffer.getvalue()
        buffer.close()
        img_b64 = base64.b64encode(image_png).decode('utf-8')

        # Встраиваем в HTML
        html = f'<img src="data:image/png;base64,{img_b64}" width="800" />'
        return mark_safe(html)

    metrics_plot.short_description = 'График загрузки CPU, RAM, GPU'

