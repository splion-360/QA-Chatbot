import uuid
from io import BytesIO

from fastapi import UploadFile
from temporalio import activity, workflow

from app.config import (
    TEMPORAL_TASK_QUEUE,
    get_temporal_client,
    setup_logger,
)
from app.services.document_service import process_file


logger = setup_logger()


@activity.defn
async def process_document_activity(
    file_data: bytes, filename: str, user_id: str, title: str = None
) -> str:
    file_obj = UploadFile(filename=filename, file=BytesIO(file_data))
    return await process_file(file_obj, user_id, title)


async def start_workflow(
    workflow: workflow, args: list = None, workflow_id: str = None, **kwargs
) -> str:
    client = await get_temporal_client()

    if not workflow_id:
        workflow_id = str(uuid.uuid4())

    await client.start_workflow(
        workflow.run,
        args=args or [],
        id=workflow_id,
        task_queue=TEMPORAL_TASK_QUEUE,
        **kwargs,
    )

    return workflow_id


async def get_workflow_status(workflow_id: str) -> dict:
    try:
        client = await get_temporal_client()
        handle = client.get_workflow_handle(workflow_id)

        try:
            result = await handle.result()
            return {
                "workflow_id": workflow_id,
                "status": "completed",
                "result": result,
            }
        except Exception:
            return {
                "workflow_id": workflow_id,
                "status": "running",
                "result": None,
            }
    except Exception as e:
        return {"workflow_id": workflow_id, "status": "failed", "error": str(e)}


async def enqueue_task(workflow_class, args: list = None, **kwargs) -> str:
    return await start_workflow(
        workflow_class, args=args or [], **kwargs
    )
