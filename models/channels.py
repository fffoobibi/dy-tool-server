from peewee import (
    CharField,
    BooleanField,
    SmallIntegerField,
    IntegerField
)
from datetime import datetime
from models import BaseModel

__all__ = ("Channel", )


class Channel(BaseModel):
    platform = SmallIntegerField(default=0, index=True, help_text="Platform ID, 0 douyin")
    room_id = CharField(max_length=20, null=False, index=True, help_text="Room ID on the platform")
    user_id = IntegerField(null=False, index=True)
    is_active = BooleanField(default=True)
    name = CharField(max_length=50, null=True, default=None)
    description = CharField(max_length=255, null=True, default=None)
    proxy_url = CharField(max_length=255, null=True, default=None)
    
    class Meta:
        indexes = (
            (("platform", "room_id"), True),
        )


