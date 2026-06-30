import psutil

def temperature():
    return psutil.sensors_temperatures()


print(temperature())