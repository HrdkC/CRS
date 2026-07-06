from contextlib import contextmanager

from sqlalchemy import (
    create_engine,
    text
)

from sqlalchemy.engine import (
    make_url
)

from sqlalchemy.orm import (
    declarative_base,
    scoped_session,
    sessionmaker
)

from config.settings import (
    DATABASE_URL
)


def build_connect_args():

    url = make_url(
        DATABASE_URL
    )

    if url.drivername.startswith(
        "sqlite"
    ):

        return {
            "check_same_thread": False
        }

    return {}


engine = create_engine(

    DATABASE_URL,

    future=True,

    pool_pre_ping=True,

    connect_args=build_connect_args()

)

SessionLocal = scoped_session(
    sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True
    )
)

Base = declarative_base()


@contextmanager
def session_scope():

    session = SessionLocal()

    try:

        yield session

        session.commit()

    except Exception:

        session.rollback()

        raise

    finally:

        session.close()


def remove_session():

    SessionLocal.remove()


def check_connection():

    with engine.connect() as connection:

        return connection.execute(
            text(
                "SELECT 1"
            )
        ).scalar_one()
