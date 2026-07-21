from Collectors import cpu_collector


def metricas_cpu():
    return {
        "uso_percentual": cpu_collector.cpu_usage(),
        "nucleos_logicos": cpu_collector.cpu_nucleos(),
        "frequencia": cpu_collector.cpu_frequency(),
    }
