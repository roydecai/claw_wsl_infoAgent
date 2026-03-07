"""重试机制"""

import asyncio
from functools import wraps
from typing import Callable, Type, Tuple
import structlog

from ..config import get_settings

logger = structlog.get_logger(__name__)


def with_retry(
    max_retries: int = None,
    delay: float = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 重试延迟（秒）
        exceptions: 需要重试的异常类型
        
    Returns:
        装饰器函数
    """
    settings = get_settings()
    max_retries = max_retries or settings.max_retries
    delay = delay or settings.retry_delay_seconds
    
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        wait_time = delay * (2 ** attempt)  # 指数退避
                        logger.warning(
                            "retry_attempt",
                            func=func.__name__,
                            attempt=attempt + 1,
                            max_retries=max_retries,
                            delay=wait_time,
                            error=str(e)
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            "retry_exhausted",
                            func=func.__name__,
                            attempts=max_retries + 1,
                            error=str(e)
                        )
            
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        import time
                        wait_time = delay * (2 ** attempt)
                        logger.warning(
                            "retry_attempt",
                            func=func.__name__,
                            attempt=attempt + 1,
                            max_retries=max_retries,
                            delay=wait_time,
                            error=str(e)
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(
                            "retry_exhausted",
                            func=func.__name__,
                            attempts=max_retries + 1,
                            error=str(e)
                        )
            
            raise last_exception
        
        # 根据函数类型返回不同的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
