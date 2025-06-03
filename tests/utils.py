from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bot.models.models import Base


def get_test_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()
