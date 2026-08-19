"""CSV import validation-report response schema."""

from pydantic import BaseModel


class RowErrorItem(BaseModel):
    row: int
    field: str
    message: str


class ImportReportResponse(BaseModel):
    total_rows: int
    valid_rows: int
    invalid_rows: int
    inserted: int
    skipped_duplicate_matric_no: list[str]
    errors: list[RowErrorItem]
