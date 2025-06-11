import psutil
import time
from monitoring.models import SystemStats
import GPUtil

def run():
    print("Сбор метрик и запись в БД...")

    partitions = [p.mountpoint for p in psutil.disk_partitions() if p.fstype]
    has_gpu = bool(GPUtil.getGPUs())

    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent

    usage = {}
    for partition in partitions:
        try:
            usage[partition] = psutil.disk_usage(partition).percent
        except:
            usage[partition] = 0

    gpu = 0
    if has_gpu:
        try:
            gpu = GPUtil.getGPUs()[0].load * 100
        except:
            pass

    SystemStats.objects.create(cpu=cpu, ram=ram, gpu=gpu, disk=usage)
    print("Успешно записано.")
