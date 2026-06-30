from Collectors.Host import cpu

def metricas_cpu():
    return {
        "uso_percentual": cpu.cpu_usage(),
        "nucleos_logicos": cpu.cpu_nucleos(),
        "frequencia": cpu.cpu_frequency(),
    }
