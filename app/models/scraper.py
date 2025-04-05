from datetime import datetime, timedelta, date
from pydantic import BaseModel, SecretStr, ValidationInfo, field_validator

class Account(BaseModel):
    username: str
    password: SecretStr

class Dates(BaseModel):
    start_date: date
    end_date: date

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, end_date: date, values: ValidationInfo) -> datetime:
        start_date = values.data.get('start_date')
        if (start_date and end_date) and (end_date - start_date) > timedelta(weeks=1):
            raise ValueError('The date range must not exceed 1 week.')
        return end_date

class Row(BaseModel):
    reference_number: str
    status: str
    document_declaration_type: str
    consignee: str
    waybill: str
    number_of_containers: str
    document_number: str
    creation_date: date

    @field_validator('reference_number')
    @classmethod
    def clean_reference_number(cls, reference_number: str) -> str:
        return reference_number.replace('-', '').strip()

    @classmethod
    def from_array(cls, array: list):
        return cls(
            reference_number=array[0],
            status=array[1],
            document_declaration_type=array[2],
            consignee=array[3],
            waybill=array[4],
            number_of_containers=array[5],
            document_number=array[6],
            creation_date=datetime.strptime(array[7], '%m/%d/%Y %I:%M:%S %p').date()
        )

class Document(BaseModel):
    invoice_number: str
    container_type: str
    quantity: str

    @field_validator('quantity')
    @classmethod
    def add_label(cls, quantity: str, values: ValidationInfo) -> str:
        container_type = values.data.get('container_type')
        if container_type == 'LCL':
            return f'{quantity} PK - PACKAGE'
        return quantity

class DataFrameModel(BaseModel):
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