from peewee import (
    CharField,
    BooleanField,
    IntegerField,
)
from datetime import datetime
from models import BaseModel
from playhouse.mysql_ext import JSONField

__all__ = ("User",)


class User(BaseModel):
    username = CharField(max_length=12, null=False)
    passwd = CharField(null=False)
    locked = BooleanField(default=False)

    email = CharField(max_length=50, null=True, default=None)
    phone = CharField(max_length=20, null=True, default=None)

    @classmethod
    def create_user(cls, username, password):
        from passlib.hash import pbkdf2_sha256

        user = cls(
            username=username,
            passwd=pbkdf2_sha256.hash(password),
            create_time=datetime.now(),
        )
        user.save()
        return user

    def verify_password(self, password) -> bool:
        from passlib.hash import pbkdf2_sha256

        return pbkdf2_sha256.verify(password, self.passwd)


class UserConfig(BaseModel):
    user_id = IntegerField(null=False, index=True)
    config_value = JSONField(null=False, default=dict)
