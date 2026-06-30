import psutil

def memory_usage():
    return psutil.virtual_memory()
