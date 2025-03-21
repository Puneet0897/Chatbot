import functools
import traceback
from log.log import logger


def catch_exception(f):
    @functools.wraps(f)
    def func(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            # print('Exception is', str(e))
            # print('Caught an exception in', f.__name__)
            logger.error('Exception is', exc_info=True)
            logger.error('Caught an exception in', f.__name__)

            return "ERROR"
            pass

    return func
