"""
Data models for get_passage feature
"""

from typing import Optional
from pydantic import BaseModel, Field


class GetPassageRequest(BaseModel):
    """Request model for getting a Bible passage"""
    passage: str = Field(description="Bible reference(s) (e.g., 'John 3:16', 'Romans 8', or 'John 3:16; Romans 8:28')", min_length=1)
    version: str = Field(
        default="ESV",
        description="Bible translation version (e.g., 'ESV', 'NIV', 'KJV', 'CSB', 'LUTH1545', or any valid BibleGateway version code)"
    )


class GetPassageResponse(BaseModel):
    """Response model for Bible passage retrieval"""
    success: bool = Field(description="Whether the request was successful")
    passage: str = Field(description="The requested Bible reference")
    version: str = Field(description="The Bible version used")
    text: Optional[str] = Field(default=None, description="The passage text")
    error: Optional[str] = Field(default=None, description="Error message if request failed")