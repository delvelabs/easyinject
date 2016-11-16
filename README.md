EasyInject
==========

[![Build Status](https://travis-ci.org/delvelabs/easyinject.svg?branch=master)](https://travis-ci.org/delvelabs/easyinject)
[![PyPi](https://badge.fury.io/py/easyinject.svg)](https://badge.fury.io/py/easyinject)

A pythonic, reflection driven, dependency injection container.

When writing small components, initializing objects and calling functions can
become tedious. So many arguments! Other injection containers require to add
even more code to set things up.

With EasyInject, if the name fits, it should be right. No configuration.
Objects are created on the fly and preserved for other uses.

```python
from easyinject import Injector
# We'll just skip some of these imports

# Callable entries will execute once and store the resulting value.
# Parameters will be resolved through the container. Circular dependencies
# won't work.
app = Injector(loop=asyncio.get_event_loop,
               cache_engine=MyCacheEngine,
               config=lambda: ConfigurationLoader('file.ini'),
               logger=lambda config: logging.getLogger(config.logger))


# More code, obviously

def my_function(arg1, arg2, *, logger):
    logger.info("Sum: %s" % (arg1 + arg2))
    return arg1 + arg2


# Few options...

# One time
app.call(my_function, 1, 2)

# Re-usable
my_function = app.wrap(my_function)

my_function(1, 2)
my_function(2, 3)

# Just get what you need
app.logger.info("Hello World!)

# Finally

# Call close() on all managed objects, closing your loops, database connections, ...
# Async close() coroutines will be called using the loop key.
app.close()
```

Scopes are also managed. When using sub-injectors, resources will be closed properly
for the sub-injectors and leave the parent ones intact.

```python
from easyinject import Injector

global_scope = Injector(logger=logger.getLogger('test'))

# ...

request_scope = global_score.sub(connection=connect)

```

# Requirements

Tested under Python 3.5.

No external dependencies.

# License

Provided under the MIT license. Copyright is held by Delve Labs inc.

See the LICENSE file for details.
