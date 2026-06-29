from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr


class BaseWithoutId(DeclarativeBase):
    __abstract__ = True

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return f"{cls.__name__.lower()}s"


class Base(BaseWithoutId):
    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
