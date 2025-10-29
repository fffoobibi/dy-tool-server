"""通用注册器基类 - 提供实现类发现和管理功能"""

from abc import ABC
from typing import Dict, Any, Optional, List, Set
from loguru import logger


class BaseRegistry(ABC):
    """通用注册器基类，提供实现类的自动发现和管理功能"""

    @classmethod
    def getImpls(
        cls, auto_import: bool = True, scan_dirs: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """获取所有可用的实现类 - 简化版，使用 __subclasses__() 方法

        Args:
            auto_import: 是否自动导入实现模块，默认为 True
            scan_dirs: 要扫描的目录列表，仅在 auto_import=True 时生效

        Returns:
            Dict[str, Any]: 包含所有实现的字典
        """
        implementations = []
        seen_classes = set()  # 用于去重

        try:
            if auto_import:
                cls._auto_import_implementations(scan_dirs)

            # 使用 __subclasses__() 递归获取所有子类
            def get_all_subclasses(base_class):
                subclasses = set()
                for subclass in base_class.__subclasses__():
                    subclasses.add(subclass)
                    subclasses.update(get_all_subclasses(subclass))
                return subclasses

            all_subclasses = get_all_subclasses(cls)

            for impl_class in all_subclasses:
                # 去重：确保同一个类只被添加一次
                class_id = f"{impl_class.__module__}.{impl_class.__name__}"
                if class_id in seen_classes:
                    continue
                seen_classes.add(class_id)

                # 过滤掉抽象基类和中间类
                if getattr(impl_class, "__abstractmethods__", None):
                    continue

                description = impl_class.__doc__ or f"{impl_class.__name__} 实现"

                # 尝试多种类型属性命名方式
                base_name = cls.__name__.lower()
                if base_name.startswith("base"):
                    base_name = base_name[4:]  # 移除 'base' 前缀

                impl_type = (
                    getattr(impl_class, f"_{base_name}_type", None)
                    or getattr(impl_class, "_type", None)
                    or getattr(impl_class, "_impl_type", None)
                    or impl_class.__name__.lower()
                    .replace(base_name, "")
                    .replace("implementation", "")
                    .replace("impl", "")
                )

                implementations.append(
                    {
                        "name": impl_class.__name__,
                        "class": impl_class,
                        "module": impl_class.__module__,
                        "description": (
                            description.strip().split("\n")[0]
                            if description
                            else f"{impl_class.__name__} 实现"
                        ),
                        "type": impl_type,
                        "base_class": cls.__name__,
                        "class_id": class_id,
                    }
                )

            logger.info(f"发现 {len(implementations)} 个 {cls.__name__} 实现")

        except Exception as e:
            logger.error(f"扫描 {cls.__name__} 实现时出错: {e}")

        return {
            "implementations": implementations,
            "count": len(implementations),
            "base_class": cls.__name__,
            "auto_import": auto_import,
            "scan_dirs": scan_dirs,
        }    @classmethod
    def _auto_import_implementations(cls, scan_dirs: Optional[List[str]] = None):
        """自动导入实现模块 - 超简化版，只负责导入模块"""
        import os
        import sys

        # 根据基类名自动推断扫描目录
        if scan_dirs is None:
            base_name = cls.__name__.lower()
            if base_name.startswith("base"):
                base_name = base_name[4:]  # 移除 'base' 前缀
            scan_dirs = [f"impls/{base_name}"]

        try:
            # 获取项目根目录
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

            for scan_dir in scan_dirs:
                impls_dir = os.path.join(current_dir, scan_dir)

                if os.path.exists(impls_dir):
                    logger.debug(f"自动导入目录: {impls_dir}")

                    for filename in os.listdir(impls_dir):
                        if filename.endswith(".py") and not filename.startswith("__"):
                            module_name = filename[:-3]  # 移除 .py 后缀
                            module_path = scan_dir.replace("/", ".").replace("\\", ".")
                            full_module_name = f"{module_path}.{module_name}"                            # 检查模块是否已经导入，避免重复导入
                            if full_module_name in sys.modules:
                                logger.debug(f"模块已导入: {full_module_name}")
                                continue

                            try:
                                # 简单导入模块即可，__subclasses__() 会自动发现子类
                                __import__(full_module_name)
                                logger.debug(f"成功导入模块: {full_module_name}")

                            except Exception as e:
                                logger.debug(f"导入模块 {full_module_name} 时出错: {e}")
                                continue
                else:
                    logger.debug(f"目录不存在: {impls_dir}")

        except Exception as e:
            logger.error(f"自动导入实现模块时出错: {e}")

    @classmethod
    def get_implementation_by_name(cls, name: str, **kwargs) -> Optional[Any]:
        """根据名称获取特定的实现类"""
        impls = cls.getImpls(**kwargs)
        for impl in impls["implementations"]:
            if impl["name"].lower() == name.lower():
                return impl["class"]
        return None

    @classmethod
    def get_implementation_by_type(cls, impl_type: str, **kwargs) -> Optional[Any]:
        """根据类型获取特定的实现类"""
        impls = cls.getImpls(**kwargs)
        for impl in impls["implementations"]:
            if impl["type"].lower() == impl_type.lower():
                return impl["class"]
        return None

    @classmethod
    def list_implementations(cls, **kwargs) -> None:
        """打印所有可用的实现信息"""
        impls = cls.getImpls(**kwargs)

        if impls["count"] == 0:
            print(f"未找到任何 {impls['base_class']} 实现")
            return

        print(f"发现 {impls['count']} 个 {impls['base_class']} 实现:")
        if impls.get("auto_import"):
            print(f"自动导入目录: {impls.get('scan_dirs', [])}")
        print("-" * 60)

        for i, impl in enumerate(impls["implementations"], 1):
            print(f"{i}. {impl['name']}")
            print(f"   模块: {impl['module']}")
            print(f"   类型: {impl['type']}")
            print(f"   描述: {impl['description']}")
            print()

    @classmethod
    def create_instance(cls, impl_name: str, *args, **kwargs):
        """根据实现名称创建实例"""
        # 分离 getImpls 相关的参数
        getimpls_kwargs = {}
        instance_kwargs = {}

        getimpls_params = {"auto_import", "scan_dirs"}
        for key, value in kwargs.items():
            if key in getimpls_params:
                getimpls_kwargs[key] = value
            else:
                instance_kwargs[key] = value

        impl_class = cls.get_implementation_by_name(impl_name, **getimpls_kwargs)
        if impl_class:
            return impl_class(*args, **instance_kwargs)
        else:
            raise ValueError(f"未找到实现: {impl_name}")

    @classmethod
    def create_instance_by_type(cls, impl_type: str, *args, **kwargs):
        """根据实现类型创建实例"""
        # 分离 getImpls 相关的参数
        getimpls_kwargs = {}
        instance_kwargs = {}

        getimpls_params = {"auto_import", "scan_dirs"}
        for key, value in kwargs.items():
            if key in getimpls_params:
                getimpls_kwargs[key] = value
            else:
                instance_kwargs[key] = value

        impl_class = cls.get_implementation_by_type(impl_type, **getimpls_kwargs)
        if impl_class:
            return impl_class(*args, **instance_kwargs)
        else:
            raise ValueError(f"未找到类型为 {impl_type} 的实现")

    @classmethod
    def get_available_types(cls, **kwargs) -> List[str]:
        """获取所有可用的实现类型"""
        impls = cls.getImpls(**kwargs)
        return [impl["type"] for impl in impls["implementations"]]

    @classmethod
    def get_available_names(cls, **kwargs) -> List[str]:
        """获取所有可用的实现名称"""
        impls = cls.getImpls(**kwargs)
        return [impl["name"] for impl in impls["implementations"]]
