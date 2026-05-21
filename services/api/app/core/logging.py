import logging


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    # Reduce verbosity of server access logs (uvicorn)
    # Keep app logs at INFO but silence frequent access entries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    # Suppress noisy Paramiko logs (including transport errors)
    try:
        logging.getLogger("paramiko").setLevel(logging.CRITICAL)
        logging.getLogger("paramiko.transport").setLevel(logging.CRITICAL)
    except Exception:
        pass
