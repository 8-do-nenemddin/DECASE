from pydantic import BaseModel

class MockupResponse(BaseModel):
    message: str
    folder_name: str