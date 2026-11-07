from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class LegalDocumentMeta(BaseModel):
    doc_type: str
    title: str
    version: str
    updated_at: str
    url: str


class LegalDocumentOut(LegalDocumentMeta):
    content: str


class LegalPoliciesOut(BaseModel):
    version: str
    documents: List[LegalDocumentMeta]


class ConsentIn(BaseModel):
    privacy_version: str = Field(min_length=1, max_length=20)
    terms_version: str = Field(min_length=1, max_length=20)
    guardian_confirmed: bool = False


class ConsentOut(BaseModel):
    privacy_version: str
    terms_version: str
    accepted_at: datetime


class LegalConsentStatus(BaseModel):
    privacy_version: str = ""
    terms_version: str = ""
    needs_reconsent: bool = True
