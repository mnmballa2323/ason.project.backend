"""
Authentication & Authorization System
Simulates JWT issuance and Role-Based Access Control (RBAC).
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import Optional
import time

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Simulated User Database
USERS = {
    "emp01": {"username": "emp01", "role": "Employee", "password": "password"},
    "admin01": {"username": "admin01", "role": "Admin", "password": "password"},
    "board01": {"username": "board01", "role": "Shareholder", "password": "password"}
}

class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

def create_token(username: str, role: str) -> str:
    # In a real app, this would sign a JWT.
    # Here we just create a dummy string payload.
    return f"eyJhbGciOiJIUzI1NiJ9.{username}.{role}.{int(time.time())}"

def decode_token(token: str):
    try:
        parts = token.split(".")
        return {"username": parts[1], "role": parts[2]}
    except:
        return None

async def verify_token(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload

def require_role(required_role: str):
    def role_checker(payload: dict = Depends(verify_token)):
        if payload["role"] != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: Requires {required_role} role"
            )
        return payload
    return role_checker

@router.post("/login", response_model=Token)
async def login(creds: LoginRequest):
    user = USERS.get(creds.username)
    if not user or user["password"] != creds.password:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    token = create_token(user["username"], user["role"])
    return {"access_token": token, "token_type": "bearer", "role": user["role"]}
