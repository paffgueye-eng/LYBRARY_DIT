"""
Modèles SQLAlchemy alignés sur les tables Django (apps: users, books, loans).
"""
from sqlalchemy import Date, DateTime, ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254))
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(default=True)

    loans: Mapped[list["Loan"]] = relationship(back_populates="user")


class Category(Base):
    __tablename__ = "books_category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")

    books: Mapped[list["Book"]] = relationship(back_populates="category")


class Book(Base):
    __tablename__ = "books_book"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    author: Mapped[str] = mapped_column(String(200))
    isbn: Mapped[str] = mapped_column(String(17))
    description: Mapped[str] = mapped_column(Text, default="")
    cover: Mapped[str | None] = mapped_column(String(100), nullable=True)
    keywords: Mapped[str] = mapped_column(String(300), default="")
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("books_category.id"), nullable=True
    )
    year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    available_copies: Mapped[int] = mapped_column(Integer, default=0)

    category: Mapped[Category | None] = relationship(back_populates="books")
    loans: Mapped[list["Loan"]] = relationship(back_populates="book")


class Loan(Base):
    __tablename__ = "loans_loan"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users_user.id"))
    book_id: Mapped[int] = mapped_column(ForeignKey("books_book.id"))
    borrowed_at: Mapped[object] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[object | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[User] = relationship(back_populates="loans")
    book: Mapped[Book] = relationship(back_populates="loans")
