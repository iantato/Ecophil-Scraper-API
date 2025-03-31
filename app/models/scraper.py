from datetime import datetime, timedelta
from pydantic import BaseModel, SecretStr, PastDate, ValidationInfo, field_validator

class Account(BaseModel):
    username: str
    password: SecretStr

class Dates(BaseModel):
    start_date: PastDate
    end_date: PastDate

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, end_date: PastDate, values: ValidationInfo) -> datetime:
        start_date = values.data.get('start_date')
        if (start_date and end_date) and (end_date - start_date) > timedelta(weeks=1):
            raise ValueError('The date range must not exceed 1 week.')
        return end_date

class Row(BaseModel):
    reference_number: str
    status: str
    document_declaration_type: str
    consignee: str
    waybill: str = None
    number_of_containers: str
    document_number: str
    creation_date: datetime

class Document(BaseModel):
    invoice_number: str
    container_type: str
    quantity: str

class Pandas(BaseModel):
    reference_number: str
    document_number: str
    invoice_number: str
    container_number: str
    container_type: str
    quantity: str
    creation_date: datetime
    document_status: str
    release_status: str

    checked_date: datetime = None