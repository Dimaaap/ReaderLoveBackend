import json
import os

from fastapi import APIRouter, status, HTTPException

router = APIRouter(tags=["Changelog"])

CHANGELOG_FILE_PATH = os.path.join(os.getcwd(), "changelog.json")


@router.get("/")
async def get_changelog():
    if not os.path.exists(CHANGELOG_FILE_PATH):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Changelog is not found"
        )

    try:
        with open(CHANGELOG_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Помилка читання файлу: {str(e)}",
        )
