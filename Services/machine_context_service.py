import os

VALID_MACHINE_TYPES = frozenset({"host", "vm"})


def get_machine_tags() -> dict[str, str]:
    machine_type = os.getenv("SENTINELA_MACHINE_TYPE", "host").strip().lower()

    if machine_type not in VALID_MACHINE_TYPES:
        allowed = ", ".join(sorted(VALID_MACHINE_TYPES))
        raise ValueError(
            f"SENTINELA_MACHINE_TYPE must be one of: {allowed}."
        )

    return {
        "host_id": os.getenv("SENTINELA_HOST_ID", "local-host"),
        "machine_type": machine_type,
        "environment": os.getenv("SENTINELA_ENV", "development"),
    }
