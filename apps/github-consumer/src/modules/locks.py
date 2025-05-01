served_requests: dict[str, bool] = {}


def is_request_served(request_id: str) -> bool:
    return request_id in served_requests


def set_served_request(request_id: str) -> None:
    served_requests[request_id] = True
