import time
import logging
import functools
from typing import List, Type, Callable, Any

def retry(max_tries: int = 3, delay: float = 1.0,
          backoff: float = 2.0, exceptions: List[Type[Exception]] = None):
    """
    同步函数的重试装饰器

    参数:
        max_tries: 最大尝试次数
        delay: 初始延迟（秒）
        backoff: 延迟增长系数
        exceptions: 需要重试的异常类型列表，默认为所有异常
    """
    exceptions = exceptions or [Exception]

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            mtries, mdelay = max_tries, delay
            last_exception = None

            while mtries > 0:
                try:
                    return func(*args, **kwargs)
                except tuple(exceptions) as e:
                    last_exception = e
                    mtries -= 1
                    if mtries == 0:
                        logging.error(f"函数 {func.__name__} 执行失败，已达到最大重试次数: {e}")
                        raise

                    logging.warning(f"函数 {func.__name__} 执行出错，将在 {mdelay} 秒后重试 (剩余 {mtries} 次): {e}")
                    time.sleep(mdelay)
                    mdelay *= backoff

            if last_exception:
                raise last_exception
            return None
        return wrapper
    return decorator