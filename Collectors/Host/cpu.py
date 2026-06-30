import psutil

def cpu_usage():
    return psutil.cpu_percent(interval=1)

def cpu_nucleos():
    return psutil.cpu_count(logical=True)

def cpu_frequency():
    return psutil.cpu_freq(percpu=False)

