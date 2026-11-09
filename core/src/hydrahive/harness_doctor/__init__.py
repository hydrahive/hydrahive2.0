def run_doctor(hours: int) -> dict:
    from hydrahive.harness_doctor.collector import run_doctor as _run
    return _run(hours)


__all__ = ["run_doctor"]
