from loguru import logger
from fastapi import status, HTTPException
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.models import (
    BookSelection,
    BookSelectionAssociation,
    Book,
    UserBookAssociation,
)
from entities.book_selections.schema import (
    BookSelectionSchema,
    BookSelectionCreate,
    BookSelectionUpdate,
    BookSelectionUpdatePartial,
    BookSelectionSummarySchema,
    BookSelectionWithDetailsSchema,
    BookWithUserStatusSchema,
)
from entities.books.schema import BookSchema


async def get_all_book_selections(
    session: AsyncSession, is_active: bool | None = None, limit: int | None = None
) -> list[BookSelectionSchema]:
    logger.info(
        f"Try to get all book selections with params: is_active={is_active}, limit={limit}"
    )

    statement = select(BookSelection).order_by(desc(BookSelection.created_at))

    if is_active is not None:
        statement = statement.where(BookSelection.is_active == is_active)

    if limit is not None:
        statement = statement.limit(limit)

    result = await session.execute(statement)
    selections = result.scalars().all()

    return [BookSelectionSchema.model_validate(selection) for selection in selections]


async def get_book_selections_with_summaries(
    session: AsyncSession, is_active: bool | None = None, limit: int | None = None
) -> list[BookSelectionSummarySchema]:
    logger.info(
        f"Try to get all book selections with summaries (is_active={is_active}, limit={limit})"
    )

    statement = select(BookSelection).order_by(desc(BookSelection.created_at))

    if is_active is not None:
        statement = statement.where(BookSelection.is_active == is_active)

    if limit is not None:
        statement = statement.limit(limit)

    result = await session.execute(statement)
    selections = list(result.scalars().all())

    if not selections:
        return []

    selection_ids = [s.id for s in selections]

    count_statement = (
        select(
            BookSelectionAssociation.book_selection_id,
            func.count(BookSelectionAssociation.book_id).label("total_books"),
        )
        .where(BookSelectionAssociation.book_selection_id.in_(selection_ids))
        .group_by(BookSelectionAssociation.book_selection_id)
    )

    count_res = await session.execute(count_statement)
    counts_map = dict(count_res.all())

    results = []
    for selection in selections:
        base_data = BookSelectionSchema.model_validate(selection).model_dump()
        total_books = counts_map.get(selection.id, 0)

        summary = BookSelectionSummarySchema(**base_data, books_count=total_books)
        results.append(summary)

    return results


async def get_book_selection_by_id_or_slug(
    session: AsyncSession,
    identifier: int | str,
    user_id: str | None = None,
    with_details: bool = False,
) -> BookSelectionWithDetailsSchema | BookSelectionSchema | None:
    logger.info(
        f"Try to get book selection '{identifier} (with_details={with_details}, user_id={user_id})'"
    )

    if isinstance(identifier, int) or (
        isinstance(identifier, str) and identifier.isdigit()
    ):
        statement = select(BookSelection).where(BookSelection.id == int(identifier))
    else:
        statement = select(BookSelection).where(BookSelection.slug == identifier)

    if with_details:
        statement = statement.options(
            selectinload(BookSelection.books).options(
                selectinload(Book.authors), selectinload(Book.genres)
            )
        )

    result = await session.execute(statement)
    selection = result.scalar_one_or_none()

    if not selection:
        logger.error(f"Failed to get book selection '{identifier}' - not found in db")
        return None

    if not with_details:
        return BookSelectionSchema.model_validate(selection)

    user_statuses: dict[int, str] = {}

    if user_id and selection.books:
        book_ids = [b.id for b in selection.books]
        status_statement = select(
            UserBookAssociation.book_id, UserBookAssociation.status
        ).where(
            UserBookAssociation.user_id == user_id,
            UserBookAssociation.book_id.in_(book_ids),
        )
        status_res = await session.execute(status_statement)
        user_statuses = dict(status_res.all())

    books_with_status = []
    for book in selection.books:
        book_schema_data = BookSchema.model_validate(book).model_dump()
        books_with_status.append(
            BookWithUserStatusSchema(
                **book_schema_data,
                user_read_status=user_statuses.get(book.id),
            )
        )

    base_data = BookSelectionSchema.model_validate(selection).model_dump()
    return BookSelectionWithDetailsSchema(**base_data, books=books_with_status)


async def create_book_selection(
    session: AsyncSession, data: BookSelectionCreate
) -> BookSelectionSchema:
    logger.info(f"Try to create book selection with title '{data.title}'")

    existing_statement = select(BookSelection.id).where(BookSelection.slug == data.slug)
    existing_res = await session.execute(existing_statement)

    if existing_res.scalar_one_or_none():
        logger.error(f"Book selection with slug '{data.slug}' already exists")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Book selection already exists",
        )

    selection_data = data.model_dump(exclude={"book_ids"})
    selection = BookSelection(**selection_data)

    session.add(selection)
    await session.flush()

    if data.book_ids:
        associations = [
            BookSelectionAssociation(
                book_selection_id=selection.id,
                book_id=book_id,
            )
            for _, book_id in enumerate(data.book_ids)
        ]
        session.add_all(associations)

    await session.commit()
    await session.refresh(selection)

    logger.info(f"Successfully created book selection with id {selection.id}")
    return BookSelectionSchema.model_validate(selection)


async def update_book_selection(
    session: AsyncSession,
    selection_id: int,
    data: BookSelectionUpdate | BookSelectionUpdatePartial,
    partial: bool = False,
) -> BookSelectionSchema:
    logger.info(f"Try to update book selection {selection_id}")

    statement = select(BookSelection).where(BookSelection.id == selection_id)
    result = await session.execute(statement)
    selection = result.scalar_one_or_none()

    if not selection:
        logger.error(f"Failed to update book selection {selection_id} - not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Добірку не знайдено"
        )

    update_data = data.model_dump(exclude_unset=partial, exclude={"book_ids"})

    for key, value in update_data.items():
        setattr(selection, key, value)

    if hasattr(data, "book_ids") and data.book_ids is not None:
        del_stmt = select(BookSelectionAssociation).where(
            BookSelectionAssociation.book_selection_id == selection_id
        )
        old_assocs = (await session.execute(del_stmt)).scalars().all()
        for assoc in old_assocs:
            await session.delete(assoc)

        new_assocs = [
            BookSelectionAssociation(
                book_selection_id=selection_id, book_id=book_id, position=idx
            )
            for idx, book_id in enumerate(data.book_ids)
        ]
        session.add_all(new_assocs)

    await session.commit()
    await session.refresh(selection)

    logger.info(f"Successfully updated book selection {selection_id}")
    return BookSelectionSchema.model_validate(selection)


async def delete_book_selection(session: AsyncSession, selection_id: int) -> bool:
    logger.info(f"Try to delete book selection with id {selection_id}")

    statement = select(BookSelection).where(BookSelection.id == selection_id)
    result = await session.execute(statement)
    selection = result.scalar_one_or_none()

    if not selection:
        logger.error(f"Failed to delete book selection {selection_id} - not found")
        return False

    await session.delete(selection)
    await session.commit()
    logger.info(f"Successfully deleted book selection with id {selection_id}")
    return True
