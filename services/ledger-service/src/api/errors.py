"""Translation of domain and validation errors into HTTP responses."""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.domain.exceptions import (
    AccountNotFoundError,
    CurrencyMismatchError,
    DomainError,
    InactiveAccountError,
    InsufficientFundsError,
    InvalidAmountError,
)

_STATUS_BY_ERROR: dict[type[DomainError], int] = {
    AccountNotFoundError: status.HTTP_404_NOT_FOUND,
    InsufficientFundsError: status.HTTP_409_CONFLICT,
    InactiveAccountError: status.HTTP_409_CONFLICT,
    InvalidAmountError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    CurrencyMismatchError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


async def _handle_domain_error(_: Request, error: Exception) -> JSONResponse:
    # An unmapped DomainError is a programming mistake: let it become a 500.
    if type(error) not in _STATUS_BY_ERROR:
        raise error
    return JSONResponse({"detail": str(error)}, _STATUS_BY_ERROR[type(error)])


async def _handle_validation_error(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, RequestValidationError)
    # Do not echo the input back: values such as NaN cannot be serialized.
    detail = [
        {"loc": list(item["loc"]), "msg": item["msg"], "type": item["type"]}
        for item in error.errors()
    ]
    return JSONResponse({"detail": detail}, status.HTTP_422_UNPROCESSABLE_CONTENT)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _handle_domain_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
