from pydantic import BaseModel


class CamaraPosition(BaseModel):
    camera: str


class CamaraSaveStatus(BaseModel):
    success: bool
    message: str
    camera: str
    filename: str
