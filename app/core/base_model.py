# app/core/base_model.py
import types
import typing
from datetime import date, datetime

from pydantic import BaseModel, field_serializer, field_validator


def _unwrap_optional(annotation):
    origin = typing.get_origin(annotation)
    # typing.Union[X, None]  -> origin is typing.Union
    # X | None (PEP 604)     -> origin is types.UnionType
    if origin is typing.Union or origin is types.UnionType:
        args = [a for a in typing.get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return annotation


class AppBaseModel(BaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def _parse_us_dates(cls, value, info):
        if not isinstance(value, str):
            return value

        raw_type = cls.model_fields[info.field_name].annotation
        field_type = _unwrap_optional(raw_type)

        if field_type is date:
            try:
                return datetime.strptime(value, "%m/%d/%Y").date()
            except ValueError:
                return value
        if field_type is datetime:
            try:
                return datetime.strptime(value, "%m/%d/%Y %H:%M:%S")
            except ValueError:
                try:
                    return datetime.strptime(value, "%m/%d/%Y")
                except ValueError:
                    return value
        return value

    @field_serializer("*", when_used="json")
    def _serialize_dates(self, value, _info):
        if isinstance(value, datetime):
            return value.strftime("%m/%d/%Y %H:%M:%S")
        if isinstance(value, date):
            return value.strftime("%m/%d/%Y")
        return value
