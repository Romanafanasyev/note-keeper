# bot/repositories/base_repo.py
from sqlalchemy.orm import Session
from typing import Type, TypeVar, Generic, Optional, List

ModelType = TypeVar('ModelType')

class BaseRepo(Generic[ModelType]):
    def __init__(self, session: Session, model: Type[ModelType]) -> None:
        self.session = session
        self.model = model

    def get(self, id: int) -> Optional[ModelType]:
        return self.session.get(self.model, id)

    def create(self, obj: ModelType) -> ModelType:
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj

    def update(self, obj: ModelType) -> ModelType:
        self.session.commit()
        self.session.refresh(obj)
        return obj

    def delete(self, obj: ModelType) -> None:
        self.session.delete(obj)
        self.session.commit()

    def list_all(self) -> List[ModelType]:
        return self.session.query(self.model).all()
