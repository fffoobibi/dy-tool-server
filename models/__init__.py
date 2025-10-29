import peewee
from peewee import *
from typing import Type
from datetime import datetime
from playhouse.shortcuts import model_to_dict
from playhouse.pool import PooledSqliteDatabase, PooledMySQLDatabase
from playhouse.mysql_ext import JSONField as MysqlJsonField


from peewee import fn, DateTimeField

__all__ = (
    "db",
    "BaseModel",
)

db: PooledMySQLDatabase | PooledSqliteDatabase = DatabaseProxy()


def JSONField(*args, **kwargs):
    return MysqlJsonField(*args, **kwargs)


def get_models() -> list[Type[Model]]:
    return BaseModel.__subclasses__()


class BaseModel(Model):
    create_time = DateTimeField(default=datetime.now, index=True)
    is_deleted = BooleanField(default=False, index=True)

    class Meta:
        database = db
        abstract = True

    def get_dt(self, field: DateTimeField) -> datetime:
        value = getattr(self, field.name)
        if isinstance(value, datetime):
            return value
        for format in field.formats:
            try:
                return datetime.strptime(value, format)
            except ValueError:
                pass

    @classmethod
    def get_field_names(cls, expt={"create_time", "is_deleted", "id"}) -> list[str]:
        value = set(cls._meta.fields.keys())
        return list(value - expt)

    @classmethod
    def get_fields(
        cls, expt: set[str] = None, prefix: str = None, only: set[str] = None
    ) -> list[peewee.Field] | list[peewee.Alias]:
        """
        获取model 查询field列表
        """
        fields = cls._meta.fields
        value = set(fields.keys())
        if only:
            value = value & only
        rs = list(value - (expt or set()))
        r = []
        for k, v in fields.items():
            if k in rs:
                if prefix:
                    r.append(v.alias(prefix + k))
                else:
                    r.append(v)
        return r

    def to_dict(self) -> dict:
        return model_to_dict(self)



def batch_insert_ignore(data: list[BaseModel]) -> list[int]:
    """
    批量忽略插入并返回 id
    """
    ids = []
    with db.atomic():
        for d in data:
            try:
                d.save()
                ids.append(d.id)
            except Exception:
                pass
    return ids
