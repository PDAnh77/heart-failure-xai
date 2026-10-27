from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class UserBase(BaseModel):
    username: str
    email: str | None = Field(None)
    display_name: str | None = Field(None)


class UserLogin(BaseModel):
    login_id: str
    password: str


class UserSignup(UserBase):
    password: str


class UserInfo(UserBase):
    id: UUID
    role: str
    avatar_url: str | None = Field(None)
    model_config = ConfigDict(from_attributes=True)


class UserPasswordUpdate(BaseModel):
    password: str


class UserUpdateAdmin(UserBase):
    username: str | None = Field(None)
    role: str | None = Field(None)


class UserUpdateMe(BaseModel):
    display_name: str | None = Field(None)
    avatar_url: str | None = Field(None)
