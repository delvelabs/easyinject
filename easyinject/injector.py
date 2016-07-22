# Copyright 2016 Delve Labs inc. <info@delvelabs.ca>

import inspect
from functools import wraps


class Injector:

    def __init__(self, parent=None, **kwargs):
        self.___parent = parent
        self.___subs = []
        self.___args = kwargs
        self.___close_list = []
        self.___closed = False

        for item in kwargs.values():
            self.record_closeable(item)

        if parent:
            parent.___subs.append(self)

    def __del__(self):
        self.close()

    def sub(self, **kwargs):
        return Injector(self, **kwargs)

    def wrap(self, function):
        func = inspect.getfullargspec(function)
        needed_arguments = func.args + func.kwonlyargs

        @wraps(function)
        def wrapper(*args, **kwargs):
            arguments = kwargs.copy()
            missing_arguments = needed_arguments - arguments.keys()
            for arg in missing_arguments:
                try:
                    arguments[arg] = self.get_argument(arg)
                except KeyError:
                    pass
            return function(*args, **arguments)

        return wrapper

    def get_argument(self, arg):
        try:
            value = self.___args[arg]

            if inspect.isroutine(value) or inspect.isclass(value):
                self.___args[arg] = self.block_recursion
                value = self.create(value)
                self.___args[arg] = value

                self.record_closeable(value)

            return value
        except KeyError:
            if self.___parent:
                return self.___parent.get_argument(arg)
            else:
                raise

    def block_recursion(self):
        raise RecursionError()

    def call(self, func, *args, **kwargs):
        wrapped = self.wrap(func)
        return wrapped(*args, **kwargs)

    def create(self, *args, **kwargs):
        return self.call(*args, **kwargs)

    def record_closeable(self, value):
        if not inspect.isclass(value) and hasattr(value, 'close') and inspect.isroutine(value.close):
            self.___close_list.append(value.close)

    def close(self):
        if not self.___closed:
            for sub in self.___subs:
                sub.close()

            for call in self.___close_list:
                call()

            self.___closed = True

    def __getattr__(self, name):
        try:
            return self.get_argument(name)
        except KeyError:
            raise AttributeError(name)
