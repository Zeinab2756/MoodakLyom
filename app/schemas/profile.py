from pydantic import BaseModel

# Base schema (shared)
class ProfileBase(BaseModel):
    theme: str
    notification_style: str
    reminder_frequency: str
    privacy_toggle: str

# For updating profile
class ProfileUpdate(ProfileBase):
    pass

# For returning profile data
class ProfileResponse(ProfileBase):
    username: str
    avatar: str

    class Config:
        orm_mode = True