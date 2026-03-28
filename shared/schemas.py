"""Common Pydantic models used across Infra microservices."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Standard health check payload."""

    status: str = Field(default="ok", description="Service health status")
    service: str = Field(..., description="Logical service name")
