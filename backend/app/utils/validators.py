"""Small shared validation helpers used across services/endpoints."""


def is_valid_algorithm(name: str) -> bool:
    from app.ml.trainer import AVAILABLE_ALGORITHMS
    return name in AVAILABLE_ALGORITHMS
