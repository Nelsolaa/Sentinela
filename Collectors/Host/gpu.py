import random

def gpu_temp():
    return ("temperatura: " + str(round(random.uniform(40.0, 55.0), 1)))

def gpu_usage():
    return ("uso_percentual: " + str(round(random.uniform(5.0, 35.0), 1)))

def gpu_vram():
    return ("vram_usada_mb: " + str(random.randint(500, 1200)) + " / vram_total_mb: 4096")

