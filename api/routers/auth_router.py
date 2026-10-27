from fastapi import APIRouter, Request, Response, Depends
from dependencies import get_db
from sqlalchemy.orm import Session
from schemas.user_schema import UserBase, UserLogin, UserSignup, UserInfo
from services.user_service import (
    login_user,
    google_login,
    google_callback,
    refresh_access_token,
    create_user,
    logout_user
)

router = APIRouter()

@router.get("/google")
async def auth_google(request: Request):
    return await google_login(request)

@router.get("/google/callback")
async def auth_google_callback(request: Request, db: Session = Depends(get_db)):
    return await google_callback(db, request)

@router.post("/login")
def login(request: Request, response: Response, user_login: UserLogin, db: Session = Depends(get_db)):
    return login_user(db, request, response, user_login)

@router.post("/refresh")
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    return refresh_access_token(db, request, response)

@router.post("/signup", response_model=UserInfo)
def signup(new_user: UserSignup, db: Session = Depends(get_db)):
    return create_user(db, new_user)

@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    return logout_user(db, request, response)