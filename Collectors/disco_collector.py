import psutil


def disk_usage(mount_point: str = "/"):
    return psutil.disk_usage(mount_point)
