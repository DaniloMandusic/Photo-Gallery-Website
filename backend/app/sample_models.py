"""Strict validation at the sample JSON import boundary."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, TypeAdapter, field_validator

SampleId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
VariantRole = Literal["thumbnail", "preview", "viewer"]
ROLES: tuple[VariantRole, ...] = ("thumbnail", "preview", "viewer")


class SampleVariant(BaseModel):
    model_config = ConfigDict(strict=True)

    src: str
    width: Annotated[int, Field(gt=0)]
    height: Annotated[int, Field(gt=0)]


class SamplePhoto(BaseModel):
    model_config = ConfigDict(strict=True)

    id: SampleId
    alt: str
    thumbnail: SampleVariant
    preview: SampleVariant
    viewer: SampleVariant

    def variant(self, role: VariantRole) -> SampleVariant:
        return {"thumbnail": self.thumbnail, "preview": self.preview, "viewer": self.viewer}[role]


class SampleAlbum(BaseModel):
    model_config = ConfigDict(strict=True)

    id: SampleId
    title: str
    photos: list[SamplePhoto]

    @field_validator("title")
    @classmethod
    def require_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Album title is required")
        return value


sample_albums = TypeAdapter(Annotated[list[SampleAlbum], Field(min_length=1)])
