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
        return InjectorProxy(Injector(self, **kwargs))

    @property
    def child_count(self):
        return sum([s.child_count + 1 for s in self.___subs])

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
        if self.___closed:
            return

        for sub in self.___subs:
            sub.close()

        for call in self.___close_list:
            call()

        if self.___parent is not None:
            self.___parent.___subs.remove(self)

        self.___closed = True

    def __getattr__(self, name):
        try:
            return self.get_argument(name)
        except KeyError:
            raise AttributeError(name)


class InjectorProxy(Injector):
    """
    Proxy to circumvent the circular dependency between parent and child.
    This proxy acts as a strong reference, ensuring that when it is deleted,
    the real injector will be closed and removed from the list of references
    in the parent.

    Without this proxy, close() would need to be called manually on the sub
    injectors.
    """

    def __init__(self, real_injector):
        self.___real = real_injector

    def __del__(self):
        self.close()

    def sub(self, **kwargs):
        return self.___real.sub(**kwargs)

    @property
    def child_count(self):
        return self.___real.child_count

    def wrap(self, function):
        return self.__real.wrap(function)

    def get_argument(self, arg):
        raise NotImplemented()  # This is private anyways

    def call(self, func, *args, **kwargs):
        return self.___real.call(func, *args, **kwargs)

    def create(self, *args, **kwargs):
        return self.___real.call(*args, **kwargs)

    def close(self):
        if self.___real is not None:
            self.___real.close()
            self.___real = None

    def __getattr__(self, name):
        return self.___real.__getattr__(name)
