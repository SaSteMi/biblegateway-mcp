"""
Core caching infrastructure using Redis

Provides a reusable Redis-based caching client for async applications.
Features:
- JSON serialization/deserialization
- Configurable TTL
- Error handling
- Async-first API
"""

import hashlib
import logging
from typing import Any, Optional, TypeVar, Dict, Callable, cast
from asyncio import TimeoutError

from aiocache import Cache
from aiocache.backends.redis import RedisCache
from aiocache.serializers import JsonSerializer

from .config import RedisCacheConfig

logger = logging.getLogger(__name__)

T = TypeVar('T')


class EnhancedJsonSerializer(JsonSerializer):
    """
    Enhanced JSON serializer with custom object handling
    
    Extends the default JsonSerializer to handle objects with to_dict() methods.
    """
    
    def dumps(self, value: Any) -> bytes:
        """Serialize object to JSON bytes"""
        if hasattr(value, 'to_dict') and callable(value.to_dict):
            value = value.to_dict()
        return super().dumps(value)


class RedisCacheClient:
    """
    Redis cache client for async applications
    
    Features:
    - Simple get/set interface
    - Automatic serialization/deserialization
    - Error handling with graceful fallback
    - MD5 key hashing
    """
    
    def __init__(self, config: RedisCacheConfig):
        """
        Initialize Redis cache client
        
        Args:
            config: Redis configuration
        """
        self.config = config
        self.cache = self._create_cache()
        logger.info(f"Initialized Redis cache client: {config.host}:{config.port}/{config.db}")
    
    def _create_cache(self) -> Optional[Cache]:
        """Create the Redis cache instance"""
        try:
            # Construct connection URL based on whether password is provided
            if self.config.password:
                # Format: redis://:password@host:port/db
                connection_url = f"redis://:{self.config.password}@{self.config.host}:{self.config.port}/{self.config.db}"
            else:
                # Format: redis://host:port/db
                connection_url = f"redis://{self.config.host}:{self.config.port}/{self.config.db}"
            
            # Create Redis cache with proper configuration
            # Note: Cache.from_url doesn't support namespace directly
            cache = Cache(
                RedisCache,
                endpoint=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                namespace=self.config.namespace,
                serializer=EnhancedJsonSerializer(),
                timeout=10.0  # Add timeout for external Redis connections
            )
            
            logger.info(f"Successfully connected to Redis at {self.config.host}:{self.config.port}/{self.config.db}")
            return cache
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis cache: {e}")
            logger.warning("Service will operate without caching")
            return None
    
    def _generate_key(self, key_base: str) -> str:
        """
        Generate a cache key
        
        Args:
            key_base: Base string to generate key from
            
        Returns:
            Normalized and hashed cache key
        """
        # Normalize: lowercase and remove spaces
        normalized = key_base.lower().replace(" ", "")
        # Create MD5 hash
        hash_value = hashlib.md5(normalized.encode()).hexdigest()
        return hash_value
    
    async def get(
        self, 
        key_base: str, 
        deserializer: Optional[Callable[[Dict[str, Any]], T]] = None
    ) -> Optional[T]:
        """
        Get a value from cache
        
        Args:
            key_base: Base string to generate key from
            deserializer: Optional function to deserialize the data
            
        Returns:
            Cached value if found, None otherwise
        """
        if not self.cache:
            logger.debug("Cache not available, skipping get operation")
            return None
            
        key = self._generate_key(key_base)
        
        try:
            data = await self.cache.get(key)
            
            if data is None:
                logger.debug(f"Cache miss for: {key_base}")
                return None
                
            logger.debug(f"Cache hit for: {key_base}")
            
            if deserializer and isinstance(data, dict):
                return deserializer(data)
            return cast(T, data)
            
        except ConnectionError as e:
            logger.error(f"Redis connection error for {key_base}: {e}")
            return None
        except TimeoutError as e:
            logger.error(f"Redis timeout error for {key_base}: {e}")
            return None
        except Exception as e:
            logger.error(f"Cache get error for {key_base}: {e}")
            return None
    
    async def set(
        self, 
        key_base: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set a value in cache
        
        Args:
            key_base: Base string to generate key from
            value: Value to cache
            ttl: Optional TTL override in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.cache:
            logger.debug("Cache not available, skipping set operation")
            return False
            
        key = self._generate_key(key_base)
        
        try:
            # Use explicit TTL if provided, otherwise use config default
            await self.cache.set(key, value, ttl=ttl or self.config.ttl)
            logger.debug(f"Cached value for: {key_base} (TTL: {ttl or self.config.ttl}s)")
            return True
            
        except ConnectionError as e:
            logger.error(f"Redis connection error for {key_base}: {e}")
            logger.warning("Continuing without caching")
            return False
        except TimeoutError as e:
            logger.error(f"Redis timeout error for {key_base}: {e}")
            logger.warning("Continuing without caching")
            return False
        except Exception as e:
            logger.error(f"Cache set error for {key_base}: {e}")
            return False
    
    async def delete(self, key_base: str) -> bool:
        """
        Delete a value from cache
        
        Args:
            key_base: Base string to generate key from
            
        Returns:
            True if deleted, False otherwise
        """
        if not self.cache:
            return False
            
        key = self._generate_key(key_base)
        
        try:
            deleted = await self.cache.delete(key)
            if deleted:
                logger.debug(f"Deleted cache for: {key_base}")
            return bool(deleted)
            
        except Exception as e:
            logger.error(f"Cache delete error for {key_base}: {e}")
            return False
            
    async def clear_namespace(self) -> bool:
        """
        Clear all keys in the current namespace
        
        Returns:
            True if successful, False otherwise
        """
        if not self.cache:
            return False
            
        try:
            await self.cache.clear()
            logger.info(f"Cleared cache namespace: {self.config.namespace}")
            return True
            
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False