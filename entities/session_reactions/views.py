from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import db_helper
from core.redis_config import redis_client
from entities.reading_sessions import crud as reading_sessions_crud
from entities.session_reactions import crud as reactions_crud
from entities.session_reactions.schema import (
    SessionReactionBase,
    SessionReactionToggleResponse,
)

router = APIRouter(prefix="/session_reactions", tags=["Session Reactions"])


@router.post("/{session_id}", response_model=SessionReactionToggleResponse)
async def toggle_session_reaction(
    session_id: int,
    username: str = Query(..., description="Session Reaction Username"),
    reaction_data: SessionReactionBase = None,
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    db_session = await reading_sessions_crud.get_reading_session_by_id(
        session, session_id
    )

    if not db_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reading Session not found"
        )

    user_id = await reading_sessions_crud.get_user_id_by_username(session, username)

    action = await reactions_crud.toggle_session_reaction(
        session=session,
        session_id=session_id,
        user_id=user_id,
        emoji=reaction_data.emoji,
    )

    await redis_client.delete(f"reading_session:{session_id}")
    await redis_client.delete("reading_sessions:all")

    return SessionReactionToggleResponse(
        status=action, emoji=reaction_data.emoji, session_id=session_id
    )
