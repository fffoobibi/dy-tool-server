import fnmatch
import time
import jmespath
import typing as t

from collections.abc import Mapping
from functools import wraps

T = t.TypeVar("T", bound=Mapping)


def unique_by(iterable: t.Iterable[T], key: t.Callable[[T], t.Any]) -> t.Iterator[T]:
    """
    返回一个迭代器，包含唯一元素，基于提供的键函数
    """
    seen = set()
    for item in iterable:
        k = key(item)
        if k not in seen:
            seen.add(k)
            yield item


class pipex(t.Generic[T]):
    _offset_flag = object()
    _limit_flag = object()
    _null_flag = object()

    """
    通过实例提供装饰器,或者显示构造来自动构建计算图 
    """

    @classmethod
    def empty(cls) -> "pipex[T]":
        """
        创建一个空的管道实例
        """
        return cls.from_data([])

    @classmethod
    def from_data(cls, data: t.Iterable[T]) -> "pipex[T]":
        """
        从数据创建一个管道实例
        :param data: 输入数据，可以是列表或其他可迭代对象
        """

        def func(*args, **kwargs):
            if func.__iflag__:
                yield from args[1]
            else:
                yield from args[0]

        instance = cls(func)
        return instance.mount(data)

    def __init__(self, func):
        self._func = func
        self._instance = None
        self._records: t.List[T] = None
        self._steps = [self._create_main_step(func)]
        self.end = self.__call
        self._where_conditions: list[str] = []
        self._distinct_keys: list[str] = []
        self._order_keys: list[str] = []
        self._take_count: int = None
        self._take_offset: int = 0
        self._peek_fields: list[str] = []
        self._exclude_fields: list[str] = []
        self._modify_fns = []
        wraps(func)(self)

    def _create_main_step(self, func):
        """创建主入口步骤的包装函数"""

        @wraps(func)
        def main_wrapper(pipe_instance, records, *args, **kwargs):
            func.__is_main__ = True
            if self.__is_decorate_instance_method(pipe_instance, func):
                func.__iflag__ = True
                yield from enumerate(
                    func(pipe_instance._instance, records, *args, **kwargs), 0
                )
            else:
                func.__iflag__ = False
                yield from enumerate(func(records, *args, **kwargs), 0)

        return main_wrapper

    def __get__(self, instance, owner):
        """描述符协议，用于绑定类实例"""
        if instance is None:
            return self
        self._instance = instance
        return self

    def __is_decorate_instance_method(self, pipe_instance, func):
        """检查当前函数是否需要实例作为第一个参数"""
        return pipe_instance._instance is not None

    def modify_fn(self, func):
        """装饰器：添加一个修改步骤"""

        @wraps(func)
        def modify_wrapper(pipe_instance, record, *args, **kwargs):
            if self.__is_decorate_instance_method(pipe_instance, func):
                return func(pipe_instance._instance, record)

            return func(record)

        self._modify_fns.append(modify_wrapper)
        return func

    def where_fn(self, condition: t.Callable[[T], bool]):
        """
        添加一个条件过滤步骤
        :param condition: 一个函数，接受单个记录并返回布尔值
        """

        def where_fn_wrapper(pipe_instance, records, idx, *args, **kwargs):
            for record in records:
                if condition(record):
                    return record

        self._steps.append(where_fn_wrapper)
        return self

    def select(self, *fields):
        """
        选择要的字段, 支持通配符*
        """
        pattern_cache = {}  # 缓存通配符字段到实际key列表的映射

        def select_wrapper(pipe_instance, r, idx, *args, **kwargs):
            if not fields:
                return r
            else:
                selected = {}
                keys = r.keys()
                for field in fields:
                    if field == "*":
                        selected.update(r)
                    elif "*" in field or "?" in field or "[" in field:
                        # 缓存通配符展开结果
                        cache_key = (field, tuple(sorted(keys)))
                        if cache_key in pattern_cache:
                            matched_keys = pattern_cache[cache_key]
                        else:
                            matched_keys = [
                                k for k in keys if fnmatch.fnmatch(k, field)
                            ]
                            pattern_cache[cache_key] = matched_keys
                        for k in matched_keys:
                            selected[k] = r[k]
                    elif field in r:
                        selected[field] = r[field]
                return selected

        self._steps.append(select_wrapper)
        return self

    def where(self, *jmes_conditions: str):
        """
        添加一个条件过滤步骤，支持多个条件
        :param conditions: 条件列表，每个条件是一个字符串，表示字段名或表达式
        """

        def where_wrapper(pipe_instance, record, idx, *args, **kwargs):
            if all(
                jmespath.search(condition, record)[0] for condition in jmes_conditions
            ):
                return record
            return self._null_flag

        self._steps.append(where_wrapper)
        return self

    filter = where

    def distinct(self, *keys):
        """
        返回唯一记录，基于指定的键
        :param keys: 键列表，用于确定唯一性
        """
        self._distinct_keys.extend(keys)
        return self

    def limit(self, n: int):
        """限制输出记录的数量"""
        self._take_count = max(n, self._take_count or 0)
        if self._take_count == 0:
            self._take_count = None

        return self

    def offset(self, n: int):
        """索引偏移, 0"""
        self._take_offset = n
        return self

    def order_by(self, *keys):
        """
        可以根据多个字段排序，支持负号表示降序
        :param keys: 排序键列表，可以是单个字段或以 '-' 开头的降序字段
        :example:
            pipe_instance.order_by('price', '-price')  # 升序和降序排序
        :example:
            pipe_instance.order_by('price')  # 仅升序排序
        """
        self._order_keys.extend(keys)
        return self

    def peek_fields(self, *fields: str, exclude_fields: t.List[str] = None):
        """
        仅返回指定字段的记录
        """
        self._peek_fields.extend(fields)
        if exclude_fields:
            self._exclude_fields.extend(exclude_fields)
        return self

    def count(self) -> int:
        """
        返回管道处理后的记录数量
        """
        return len(list(self.__call()))

    def desc(self):
        """返回计算图中每个步骤的描述列表"""
        return [f"{step.__wrapped__.__name__}" for step in self._steps]

    def mount(self, records: t.Iterable[T]):
        """
        设置数据源，供管道使用
        """
        self._records = records
        return self

    def to_list(self):
        """
        执行管道并返回结果列表
        """
        return list(self.__call())

    def iterator(self):
        return self.__call()

    def __iter__(self):
        return iter(self.__call())

    def __call(self, records: t.Iterable[T] = None) -> t.Iterator[T]:
        """计算流程"""

        def sort(item):
            result = []
            idx, record = item
            for key in self._order_keys:
                if key.startswith("-"):
                    v = record.get(key[1:], 0)
                    if isinstance(v, str):
                        v = len(v)
                    elif isinstance(v, (list, tuple)):
                        v = len(v)
                    elif isinstance(v, dict):
                        v = len(v)
                    elif isinstance(v, (int, float)):
                        pass
                    try:
                        v = -v
                    except Exception:
                        v = v
                    result.append(v)
                else:
                    result.append(record.get(key, 0))
            return tuple(result)

        def computed():
            result = records or self._records or []
            step_main_func = self._steps[0]
            step_length = len(self._steps)
            step_funcs = self._steps[1:]

            has_orderby = bool(self._order_keys)
            has_modify = bool(self._modify_fns)

            main_records = step_main_func(self, result)

            if has_modify:
                for fn in self._modify_fns:
                    main_records = (
                        (idx, fn(self, record)) for idx, record in main_records
                    )

            if has_orderby:
                main_records = sorted(main_records, key=sort)

            if step_length > 1:
                for idx, record in main_records:
                    item = record
                    for step_func in step_funcs:
                        item = step_func(self, item, idx)
                        if (
                            item is self._offset_flag
                            or item is self._limit_flag
                            or item is self._null_flag
                        ):
                            break
                    else:
                        yield item
            else:
                for idx, record in main_records:
                    yield record

        vals = computed()

        offset_n = self._take_offset or 0
        limit_n = self._take_count

        if self._distinct_keys:
            vals = unique_by(
                vals, key=lambda x: str(tuple(x[k] for k in self._distinct_keys))
            )

        def offset_limit_iter(vals, offset_n, limit_n):
            skipped = 0
            yielded = 0
            sf = list(unique_by(self._peek_fields, key=lambda x: x))
            for v in vals:
                if skipped < offset_n:
                    skipped += 1
                    continue
                if limit_n is not None and yielded >= limit_n:
                    break
                it = v
                if self._peek_fields:
                    it = {k: v[k] for k in sf if k in v}
                if self._exclude_fields:
                    it = {k: v[k] for k in it if k not in self._exclude_fields}
                yield it
                yielded += 1

        yield from offset_limit_iter(vals, offset_n, limit_n)


if __name__ == "__main__":

    ## demo1
    class PipexDataProcessor(object):
        process = pipex.empty()

        @process.modify_fn
        def process_record(self, record):
            # 处理记录的逻辑
            record["processed"] = True
            record["create_time"] = time.time()
            return record

    ## demo2
    records = [
        {
            "title": f"Product {i}",
            "brand": f"Brand {i}",
            "stars": i * 2 + 1,
        }
        for i in range(10)
    ]

    pipe = pipex.from_data(records)

    @pipe.modify_fn
    def edit(record):
        record["fuck"] = "fuck"
        return record

    dataset = (
        pipe.select("stars", "title", "brand", "fuck")
        .distinct("brand")
        .order_by("stars")
        .where("[stars > `5`]")
        # .offset(10)
        .limit(3)
        # .count()
        # .peek_fields("title").peek_fields("brand").peek_fields("title")
        .to_list()
    )
    print(dataset)
