# Copyright 2016 Delve Labs inc. <info@delvelabs.ca>

import inspect
import weakref
from functools import wraps


class Injector:

    def __init__(self, parent=None, **kwargs):
        self.___parent = parent
        self.___subs = []
        self.___args = kwargs
        self.___close_list = []
        self.___closed = False
        self.___initialized = set()

        for item in kwargs.values():
            self.record_closeable(item)

        if parent:
            parent.___subs.append(weakref.ref(self))

    def __del__(self):
        self.close()

    def sub(self, **kwargs):
        return Injector(self, **kwargs)

    @property
    def child_count(self):
        return sum([ref().child_count + 1 for ref in self.___subs if ref() is not None])

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

            if arg not in self.___initialized and self.requires_processing(value):
                self.___args[arg] = self.block_recursion
                value = self.create(value)
                self.___args[arg] = value

                self.record_closeable(value)
                if inspect.isroutine(value) or inspect.isclass(value):
                    value = self.wrap(value)

                self.___initialized.add(arg)

            return value
        except KeyError:
            if self.___parent:
                return self.___parent.get_argument(arg)
            else:
                raise

    def requires_processing(self, value):
        return inspect.isroutine(value) or inspect.isclass(value)

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
        if self.___closed:
            return

        for ref in self.___subs:
            sub = ref()
            if sub is not None:
                sub.close()

        for call in self.___close_list:
            call()

        self.___closed = True

    def __getattr__(self, name):
        try:
            return self.get_argument(name)
        except KeyError:
            raise AttributeError(name)
