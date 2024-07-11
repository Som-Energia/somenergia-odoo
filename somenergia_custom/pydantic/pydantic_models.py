import pydantic
from typing import Literal, Optional, Union, List
from pydantic import constr, field_validator
from datetime import date
import stdnum.eu.vat


class WorkRegister(
    pydantic.BaseModel,
):
    worked_week_id: int
    area_project_id: int
    additional_project_id: Optional[int] = None
    description: Optional[str] = "/"
    hours: float
