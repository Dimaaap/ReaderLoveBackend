from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import db_helper

from . import crud
from .schema import (
    ReadingCycleCreate,
    ReadingCycleUpdate,
    ReadingCycleSchema,
    ReadingCycleHistorySchema,
)

router = APIRouter(tags=["Reading Cycles"])


@router.get("/{username}", response_model=list[ReadingCycleSchema])
async def get_user_reading_cycles(
    username: str, session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    return await crud.get_user_reading_cycles(session=session, username=username)


@router.get("/{username}/books/{book_id}", response_model=ReadingCycleHistorySchema)
async def get_book_reading_cycles(
    username: str,
    book_id: int,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    return await crud.get_book_reading_cycles(
        session=session, username=username, book_id=book_id
    )


@router.get(
    "/{username}/books/{book_id}/active", response_model=ReadingCycleSchema | None
)
async def get_active_reading_cycle(
    username: str,
    book_id: int,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    return await crud.get_active_reading_cycle(
        session=session, username=username, book_id=book_id
    )


@router.get("/{username}/{cycle_id}", response_model=ReadingCycleSchema)
async def get_reading_cycle_by_id(
    username: str,
    cycle_id: int,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cycle = await crud.get_reading_cycle_by_id(
        session=session,
        cycle_id=cycle_id,
    )

    if not cycle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reading cycle not found",
        )

    return cycle


@router.post(
    "/{username}/books/{book_id}",
    response_model=ReadingCycleSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_reading_cycle(
    username: str,
    book_id: int,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cycle = await crud.create_reading_cycle(
        session=session,
        username=username,
        book_id=book_id,
    )

    await session.commit()
    await session.refresh(cycle)

    return cycle


@router.post(
    "/{username}/books/{book_id}/reread",
    response_model=ReadingCycleSchema,
    status_code=status.HTTP_201_CREATED,
)
async def reread_book(
    username: str,
    book_id: int,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cycle = await crud.reread_book(
        session=session,
        username=username,
        book_id=book_id,
    )

    await session.commit()
    await session.refresh(cycle)

    return cycle


@router.patch(
    "/{username}/{cycle_id}",
    response_model=ReadingCycleSchema,
)
async def update_reading_cycle(
    username: str,
    cycle_id: int,
    data: ReadingCycleUpdate,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cycle = await crud.get_reading_cycle_by_id(
        session=session,
        username=username,
        cycle_id=cycle_id,
    )

    if not cycle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reading cycle not found",
        )

    cycle = await crud.update_reading_cycle_progress(
        session=session,
        cycle=cycle,
        page=data.last_read_page,
        percent=data.last_read_percent,
    )

    await session.commit()
    await session.refresh(cycle)

    return cycle


@router.post(
    "/{username}/{cycle_id}/complete",
    response_model=ReadingCycleSchema,
)
async def complete_reading_cycle(
    username: str,
    cycle_id: int,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    cycle = await crud.get_reading_cycle_by_id(
        session=session,
        username=username,
        cycle_id=cycle_id,
    )

    if not cycle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reading cycle not found",
        )

    cycle = await crud.complete_reading_cycle(
        session=session,
        cycle=cycle,
    )

    await session.commit()
    await session.refresh(cycle)

    return cycle
