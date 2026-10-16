from fastapi import APIRouter

from entities.users.tasks import send_bulk_promotions_task

router = APIRouter(tags=["Admin Endpoints"])


@router.post("/send-promotions")
async def trigger_bulk_promotions(subject: str, content: str):
    task = send_bulk_promotions_task.delay(subject, content)

    return {
        "status": "success",
        "message": "Bulk promotion task has been queued successfully.",
        "task_id": task.id,
    }
