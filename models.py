from pydantic import BaseModel
from typing import Optional, List # Import List

class User(BaseModel):
    username: str
    password: str
    role: str # "admin" or "user"

class UserInDB(User):
    hashed_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    roles: List[str] = [] # Use a list for roles
