from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class AppError(HTTPException):
    """Base application exception — carries a machine-readable code."""

    def __init__(self, status_code: int, code: str, detail: str) -> None:
        super().__init__(status_code=status_code, detail=detail)
        self.code = code


class NotFoundError(AppError):
    def __init__(self, resource: str = "Resource") -> None:
        super().__init__(404, "NOT_FOUND", f"{resource} not found")


class UnauthorizedError(AppError):
    def __init__(self, detail: str = "Unauthorized") -> None:
        super().__init__(401, "UNAUTHORIZED", detail)


class ForbiddenError(AppError):
    def __init__(self, detail: str = "Forbidden") -> None:
        super().__init__(403, "FORBIDDEN", detail)


class ConflictError(AppError):
    def __init__(self, detail: str = "Conflict") -> None:
        super().__init__(409, "CONFLICT", detail)


class ValidationError(AppError):
    def __init__(self, detail: str = "Validation error") -> None:
        super().__init__(422, "VALIDATION_ERROR", detail)


# ── Global exception handlers ─────────────────────────────────────────────────


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.detail},
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
        },
    )


class AppException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AuthException(AppException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, status_code=403)


class NotFoundException(AppException):
    def __init__(self, message: str = "Not found"):
        super().__init__(message, status_code=404)


class MemberNotFoundException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=404)


class PlanNotFoundException(AppException):
    def __init__(self, plan_id: str) -> None:
        super().__init__(f"Plan '{plan_id}' not found.", status_code=404)
        self.plan_id = plan_id


class DuplicateSpouseException(AppException):
    def __init__(self, subscriber_member_id: str) -> None:
        super().__init__(
            f"Subscriber '{subscriber_member_id}' already has a spouse. "
            "Only one spouse is allowed per family.",
            status_code=409,
        )
        self.subscriber_member_id = subscriber_member_id


class InvalidFamilyRelationshipException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=422)


class InvalidEligibilityException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=422)


class MissingSearchCriteriaException(AppException):
    def __init__(
        self, message: str = "At least one search criterion must be provided."
    ) -> None:
        super().__init__(message, status_code=400)


class DrugNotFoundException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=404)
        self.code = "DRUG_NOT_FOUND"


class ClaimNotFoundException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=404)


class InvalidDateRangeException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=422)


class NoSearchCriteriaException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=400)


class PharmacyNotFoundException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=404)
        self.code = "PHARMACY_NOT_FOUND"


class PrescriberNotFoundException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=404)
        self.code = "PRESCRIBER_NOT_FOUND"
