import peewee
import typing as t
from constants import ResponseCode

from datetime import datetime, date

from flask import request, jsonify


Proc = t.Callable[[dict], None]

__all__ = (
    "success",
    "fail",
    "paginate",
)


def fail(msg: str = "fail", code: int = ResponseCode.FAIL):
    return jsonify({"code": code, "msg": msg})


def success(
    msg: str = "success",
    resp=None,
):
    return jsonify({"code": ResponseCode.SUCCESS, "msg": msg, "resp": resp})


def paginate(
    query: peewee.BaseQuery | list[dict],
    total_count: int,
    dft_page: int = 1,
    dft_page_size: int = 10,
    *,
    proc: Proc = None,
    datetime_fields: set[str] = None,
    date_fields: set[str] = None,
    extra: dict = None,
    return_all: bool = False,
    fields: dict[str, t.Callable[[t.Any], t.Any]] = None,
    datetime_fmt: str = "%Y/%m/%d %H:%M:%S",
    date_fmt: str = "%Y/%m/%d",
):
    """
    分页查询结果处理函数
    """
    try:
        js = request.json or {}
    except:
        js = {}
    page = int(request.args.get("page") or js.get("page") or dft_page)
    page_size = int(
        request.args.get("page_size") or js.get("page_size") or dft_page_size
    )
    is_query = isinstance(query, peewee.BaseQuery)
    if not return_all:
        if is_query:
            list_data = list(
                query.limit(page_size).offset((page - 1) * page_size).dicts()
            )
        else:
            list_data = query  # type: list[dict]
    else:
        if is_query:
            list_data = list(query.dicts())
        else:
            list_data = query  # type: list[dict]

    idx = 0
    for v in list_data:
        idx += 1
        v["__order"] = page_size * (page - 1) + idx
        if proc:
            proc(v)
        if d := v.get("create_time"):
            if isinstance(d, datetime):
                v["create_time"] = d.strftime(datetime_fmt)
        if datetime_fields:
            for field in datetime_fields:
                if d := v.get(field):
                    if isinstance(d, datetime):
                        v[field] = d.strftime(datetime_fmt)
        if date_fields:
            for field in date_fields:
                if d := v.get(field):
                    if isinstance(d, date):
                        v[field] = d.strftime(date_fmt)
        if fields:
            for k, f in fields.items():
                try:
                    v[k] = f(v[k])
                except:
                    pass
    resp = {
        "list": list_data,
        "page": page,
        "total_count": total_count,
    }
    if extra:
        resp.update(extra)
    return success(resp=resp)
