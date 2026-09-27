"""
REST API routes for get_passage feature
"""

import logging
from fastapi import APIRouter, HTTPException

from mcp_bible.core.utils import load_instruction
from mcp_bible.bible_service import BibleService
from mcp_bible.features.get_passage.models import GetPassageRequest, GetPassageResponse
from mcp_bible.shared.models import ErrorResponse

logger = logging.getLogger(__name__)


def create_router(bible_service: BibleService) -> APIRouter:
    """
    Create router for Bible passage REST endpoints

    Args:
        bible_service: Bible service instance

    Returns:
        Configured APIRouter
    """
    router = APIRouter(prefix="/passage", tags=["Bible Passage"])

    @router.post(
        "",
        response_model=GetPassageResponse,
        summary="Get Bible Passage",
        description=load_instruction("instructions.md", __file__),
        responses={
            400: {"model": ErrorResponse},
            500: {"model": ErrorResponse}
        }
    )
    async def get_passage_endpoint(request: GetPassageRequest):
        """Get a Bible passage using the comprehensive documentation from instructions.md"""
        try:
            result = await bible_service.fetch_passage(
                passage=request.passage,
                version=request.version
            )
            return result
        except ValueError as e:
            logger.warning(f"Validation error: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Passage retrieval error: {e}")
            raise HTTPException(status_code=500, detail="Passage retrieval failed")

    return router