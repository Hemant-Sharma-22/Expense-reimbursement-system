from fastapi import HTTPException, status


class DuplicateExpenseException(HTTPException):
    def __init__(self, detail: str = "Duplicate reimbursement request or receipt detected."):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class InvalidStateTransitionException(HTTPException):
    def __init__(self, detail: str = "Invalid status transition for this reimbursement request."):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


class PermissionDeniedException(HTTPException):
    def __init__(self, detail: str = "You do not have permission to perform this action."):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class ResourceNotFoundException(HTTPException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=f"{resource} not found.")
