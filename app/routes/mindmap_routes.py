from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.mindmap_service import generate_mindmap_for_document

router = APIRouter(prefix="/mindmaps", tags=["Mind Maps"])


class MindMapGenerateRequest(BaseModel):
    document_id: int
    max_depth: int = 3
    max_branches_per_node: int = 5
    generation_mode: str = "mvp"


@router.post("/generate")
async def generate_mindmap(
    payload: MindMapGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await generate_mindmap_for_document(
        user_id=current_user.id,
        document_id=payload.document_id,
        db=db,
        max_depth=payload.max_depth,
        max_branches_per_node=payload.max_branches_per_node,
    )
