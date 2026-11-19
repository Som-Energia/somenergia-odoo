# -*- coding: utf-8 -*-
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError


class CollaboratorLeadPayload(BaseModel):
    """Normalized external contract; database-dependent rules stay in Odoo."""

    model_config = ConfigDict(
        strict=True,
        extra='forbid',
        str_strip_whitespace=True,
        validate_default=True,
        hide_input_in_errors=True,
    )

    id_external_lead: str = Field(min_length=1, max_length=128)
    contact_name: str = Field(min_length=1, max_length=255)
    email: str = Field(default='', max_length=254)
    phone: str = Field(default='', max_length=64)
    lang: str = Field(default='', max_length=5)
    cups: str = Field(default='', max_length=64)
    comments: str = Field(default='', max_length=10000)

    @field_validator('*', mode='before')
    @classmethod
    def prepare_string(cls, value, info):
        if isinstance(value, str):
            if '\x00' in value:
                raise PydanticCustomError(
                    'invalid_data', '{field} contains an unsupported character.',
                    {'field': info.field_name},
                )
            # Preserve Python's original strip semantics before length checks.
            return value.strip()
        return value

    # Run after Field length validation: the existing contract measures lengths
    # after trimming but before case conversion or removing internal spaces.
    @field_validator('contact_name')
    @classmethod
    def normalize_contact_name(cls, value):
        return value.title()

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value):
        # Keep Odoo's email format validation in the adapter, not EmailStr.
        return value.lower()

    @field_validator('phone')
    @classmethod
    def normalize_phone(cls, value):
        return value.replace(' ', '')

    @field_validator('lang')
    @classmethod
    def validate_language(cls, value):
        if value not in ('', 'ca_ES', 'es_ES'):
            raise PydanticCustomError('invalid_language', 'Supported languages: ca_ES, es_ES.')
        return value

    @field_validator('cups')
    @classmethod
    def normalize_cups(cls, value):
        value = ''.join(value.split()).upper()
        if value and not re.fullmatch(r'ES[0-9]{16}[A-Z]{2}([0-9][A-Z])?', value):
            raise PydanticCustomError(
                'invalid_cups', 'CUPS must have a valid 20 or 22 character format.',
            )
        return value

    @model_validator(mode='after')
    def require_contact_method(self):
        if not self.email and not self.phone:
            raise PydanticCustomError('missing_fields', 'An email or phone is required.')
        return self
