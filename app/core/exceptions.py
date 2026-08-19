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


def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.detail}},
    )


def generic_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    msg = str(exc) if exc is not None else "An unexpected error occurred"
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_SERVER_ERROR", "message": msg}},
    )


class AppException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

    @property
    def extra(self) -> dict:
        """Optional additional fields to merge into the error response.
        Subclasses override this to expose extra context (e.g. attemptsRemaining).
        Defaults to empty so unrelated exceptions are unaffected."""
        return {}


class AuthException(AppException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401)


class SSHostError(AppException):
    def __init__(self, message: str = "SSHost unreachable") -> None:
        super().__init__(message, status_code=503)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, status_code=403)


class NotFoundException(AppException):
    def __init__(self, message: str = "Not found"):
        super().__init__(message, status_code=404)


class UserNotFoundError(AppException):
    def __init__(self, detail: str = "User not found."):
        super().__init__(status_code=404, message=detail)


class InvalidCredentialsError(AppException):
    def __init__(self, detail: str = "Invalid username or password."):
        super().__init__(status_code=401, message=detail)


class UserInactiveError(AppException):
    def __init__(
        self,
        detail: str = "Your account is inactive. Please contact the administrator.",
    ):
        super().__init__(status_code=403, message=detail)


class TooManyLoginAttemptsError(AppException):
    def __init__(
        self,
        detail: str = "Too many login attempts.Please try after 15 minutes.",
        attempts_remaining: int = 0,
    ):
        self.attempts_remaining = attempts_remaining
        super().__init__(status_code=429, message=detail)

    @property
    def extra(self) -> dict:
        return {"loginAttemptsRemaining": self.attempts_remaining}


class TooManyOTPVerificationAttemptsError(AppException):
    def __init__(
        self,
        detail: str = "Maximum OTP verification attempts exceeded. Please login again to request a new OTP.",
        attempts_remaining: int = 0,
    ):
        self.attempts_remaining = attempts_remaining
        super().__init__(status_code=429, message=detail)

    @property
    def extra(self) -> dict:
        return {"otpVerificationAttemptsRemaining": self.attempts_remaining}


class InvalidOrExpiredOtpError(AppException):
    """Used for both 'wrong OTP' and 'expired/not found' — don't leak which."""

    def __init__(
        self,
        detail: str = "Invalid or expired OTP.",
        otp_verification_attempts_remaining: int | None = None,
    ):
        self.otp_verification_attempts_remaining = otp_verification_attempts_remaining
        super().__init__(status_code=401, message=detail)

    @property
    def extra(self) -> dict:
        if self.otp_verification_attempts_remaining is None:
            return {}
        return {
            "otpVerificationAttemptsRemaining": self.otp_verification_attempts_remaining
        }


class OtpResendRateLimitedError(AppException):
    def __init__(
        self,
        detail: str = "Maximum OTP resend rate exceeded. Please wait before trying again.",
    ):
        super().__init__(status_code=429, message=detail)


class OtpResendLimitExceedError(AppException):
    def __init__(
        self,
        detail: str = "Maximum OTP resend attempts exceeded. Please login again to request a new OTP.",
        otp_resend_attempts_remaining: int = 0,
    ):
        self.otp_resend_attempts_remaining = otp_resend_attempts_remaining
        super().__init__(status_code=429, message=detail)

    @property
    def extra(self) -> dict:
        return {"otpResendAttemptsRemaining": self.otp_resend_attempts_remaining}


class MemberNotFoundException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=404)


class InvalidMemberDataException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=422)


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


class InvalidSearchCriteriaException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=400)


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


class PriorAuthNotFoundException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=404)
        self.code = "PA_NOT_FOUND"


class PriorAuthNotEditableException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=403)
        self.code = "FORBIDDEN"


class CardRequestNotFoundException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=404)
        self.code = "CARD_REQUEST_NOT_FOUND"


class CardRequestNotCancellableException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=409)
        self.code = "CONFLICT"


class InvalidStatusTransitionException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=422)
        self.code = "VALIDATION_ERROR"
