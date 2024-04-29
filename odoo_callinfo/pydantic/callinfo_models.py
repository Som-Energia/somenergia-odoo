import pydantic
from typing import Literal, Optional, Union, List
from pydantic import constr, field_validator
import stdnum.eu.vat

# VatNumber = Annotated[
#     str,
#     pydantic.AfterValidator(stdnum.eu.vat.validate),
# ]
#
# RgbColor = Annotated[str, pydantic.StringConstraints(
#     pattern="^#([a-fA-F0-9]{3}){1,2}$",
#     to_lower=True,
#     strip_whitespace=True,
# )]


class Category(
    pydantic.BaseModel,
):
    id: int
    name: str
    code: str
    keywords: List[str] = []
    # color: Optional[RgbColor] = None
    color: Optional[constr(
        pattern="^#([a-fA-F0-9]{3}){1,2}$",
        to_lower=True,
        strip_whitespace=True)
    ] = None
    enabled: bool = True


class Categories(pydantic.BaseModel):
    categories: List[Category]


class NewCall(pydantic.BaseModel):
    operator: str
    call_timestamp: pydantic.AwareDatetime

    # Optional: not informed when a manual call
    pbx_call_id: str = ''
    phone_number: str = ''

    # Caller: optional when caller not in database
    caller_erp_id: Optional[int] = None
    caller_vat: Union[str, Literal['']] = ''
    caller_name: str = ""

    # Contract: optional when no caller or caller has no contracts
    contract_erp_id: Optional[int] = None
    contract_number: str = ""
    contract_address: str = ""

    category_ids: List[int] = []
    comments: str = ""

    @field_validator('caller_vat')
    def validate_vat(cls, v):
        if not stdnum.eu.vat.is_valid(v):
            raise ValueError('Invalid VAT number')
        return v


class Call(NewCall):
    id: int


class CallLog(pydantic.BaseModel):
    calls: List[Call] # TODO: rename as calls


class UpdatedCallLog(CallLog):
    updated_id: int
