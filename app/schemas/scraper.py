from datetime import datetime
from pydantic import BaseModel

class Account(BaseModel):
    username: str
    password: bytes

class Dates(BaseModel):
    start_date: datetime = None
    end_date: datetime = None

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