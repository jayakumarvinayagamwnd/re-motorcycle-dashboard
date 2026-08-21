from pydantic import BaseModel


class DBCheckRow(BaseModel):
    """Model for a row in the db_check table."""
    id: int
    check_date: str
    created_by: str


class DBHealthResponse(BaseModel):
    """Successful database health check response."""
    status: str = "healthy"
    database: str = "sqlite"
    check_date: str
    created_by: str


class DBHealthError(BaseModel):
    """Failed database health check response."""
    status: str = "unhealthy"
    database: str = "sqlite"
    error: str