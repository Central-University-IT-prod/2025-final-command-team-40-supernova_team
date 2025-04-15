import logging
from collections.abc import MutableMapping
from typing import Any


def pytest_tavern_beta_before_every_request(request_args: MutableMapping) -> None:
    msg = f"Request: {request_args['method']} {request_args['url']}"

    params = request_args.get("params", None)
    if params:
        msg += f"\nQuery parameters: {params}"

    msg += f"\nRequest body: {request_args.get('json', '<no body>')}"

    logging.info(msg)  # noqa: LOG015


def pytest_tavern_beta_after_every_response(expected: Any, response: Any) -> None:  # noqa: ANN401
    msg = f"Response: {response.status_code} {response.text}\n"

    logging.info(msg)  # noqa: LOG015
