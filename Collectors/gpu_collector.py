import random


def gpu_temp() -> float:
    return round(random.uniform(40.0, 55.0), 1)


def gpu_usage() -> float:
    return round(random.uniform(5.0, 35.0), 1)


def gpu_vram() -> dict[str, int]:
    return {
        "used_mb": random.randint(500, 1200),
        "total_mb": 4096,
    }
