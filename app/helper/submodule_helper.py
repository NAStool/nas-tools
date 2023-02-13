# -*- coding: utf-8 -*-
import importlib
import pkgutil


class SubmoduleHelper:
    @classmethod
    def import_submodules(cls, package, filter_func=lambda name, obj: True):
        """
        导入子模块
        :param package: 父包名
        :param filter_func: 子模块过滤函数，入参为模块名和模块对象，返回True则导入，否则不导入
        :return:
        """

        submodules = []
        packages = importlib.import_module(package).__path__
        for importer, package_name, _ in pkgutil.iter_modules(packages):
            full_package_name = f'{package}.{package_name}'
            if full_package_name.startswith('_'):
                continue
            module = importlib.import_module(full_package_name)
            for name, obj in module.__dict__.items():
                if name.startswith('_'):
                    continue
                if isinstance(obj, type) and filter_func(name, obj):
                    submodules.append(obj)

        return submodules
