from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from functools import lru_cache
from shared.config import get_settings


class Base(DeclarativeBase):
    pass


@lru_cache(maxsize=1)
def _get_engine():
    settings = get_settings()
    return create_async_engine(settings.db_url, echo=settings.debug)


def get_engine():
    return _get_engine()


def get_async_session():
    engine = get_engine()
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    from shared.models import Report, User  # noqa
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session():
    factory = get_async_session()
    async with factory() as session:
        yield session


def reset_engine():
    _get_engine.cache_clear()
