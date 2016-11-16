# Copyright 2016 Delve Labs inc. <info@delvelabs.ca>

import inspect
import weakref
from functools import wraps


class Injector:

    def __init__(self, parent=None, **kwargs):
        """
        Creates a new injector. All provided keys will be injectable.

        Arguments:
        parent -- Reserved name, used for sub-injectors.
        """
        self.___parent = parent
        self.___subs = []
        self.___args = kwargs
        self.___close_list = []
        self.___closed = False
        self.___initialized = set()

        for item in kwargs.values():
            self._record_closeable(item)

        if parent:
            parent.___subs.append(weakref.ref(self))

    def __del__(self):
        self.close()

    def sub(self, **kwargs):
        """
        Create a new sub-injector scope. All provided keys will be injectable.
        Sub-injectors can access the parent keys, but not the other way around.
        """
        return Injector(self, **kwargs)

    @property
    def child_count(self):
        """
        Primarily for testing purposes. Recursively counts the amount of child
        injectors.
        """
        return sum([ref().child_count + 1 for ref in self.___subs if ref() is not None])

    def wrap(self, function):
        """
        Wraps a function so that all unspecified arguments will be injected if
        possible. Specified arguments always have precedence.
        """
        func = inspect.getfullargspec(function)
        needed_arguments = func.args + func.kwonlyargs

        @wraps(function)
        def wrapper(*args, **kwargs):
            arguments = kwargs.copy()
            missing_arguments = needed_arguments - arguments.keys()
            for arg in missing_arguments:
                try:
                    arguments[arg] = self._get_argument(arg)
                except KeyError:
                    pass
            return function(*args, **arguments)

        return wrapper

    def _get_argument(self, arg):
        try:
            value = self.___args[arg]

            if arg not in self.___initialized and self._requires_processing(value):
                self.___args[arg] = self._block_recursion
                value = self.create(value)
                self.___args[arg] = value

                self._record_closeable(value)
                if inspect.isroutine(value) or inspect.isclass(value):
                    value = self.wrap(value)

                self.___initialized.add(arg)

            return value
        except KeyError:
            if self.___parent:
                return self.___parent._get_argument(arg)
            else:
                raise

    def _requires_processing(self, value):
        return inspect.isroutine(value) or inspect.isclass(value)

    def _block_recursion(self):
        raise RecursionError()

    def call(self, func, *args, **kwargs):
        """
        Calls a specified function using the provided arguments and injectable
        arguments.

        If the function must be called multiple times, it may be best to use
        wrap().
        """
        wrapped = self.wrap(func)
        return wrapped(*args, **kwargs)

    def create(self, *args, **kwargs):
        """
        Direct alias to call(). In place for caller clarity.
        """
        return self.call(*args, **kwargs)

    def _record_closeable(self, value):
        if not inspect.isclass(value) and hasattr(value, 'close') and inspect.isroutine(value.close):
            self.___close_list.append(value.close)

    def close(self):
        """
        Closes the injector and all sub-injectors. This is also called on
        destruction.

        close() will be called on all managed objects.
        """
        if self.___closed:
            return

        for ref in self.___subs:
            sub = ref()
            if sub is not None:
                sub.close()

        # Destroy in reverse order as first elements created have more components depending on them
        for call in self.___close_list[::-1]:
            if inspect.iscoroutinefunction(call):
                self.loop.run_until_complete(call())
            else:
                call()

        self.___closed = True

    def __getattr__(self, name):
        """
        Directly access a property.
        """
        try:
            return self._get_argument(name)
        except KeyError:
            raise AttributeError(name)
