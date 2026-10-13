import random, string
from uuid import UUID
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Request, Response, status, UploadFile
from sqlalchemy import or_, select, insert, update, delete, or_
from starlette.responses import RedirectResponse
from models.refresh_token_model import RefreshToken
from models.user_model import User
from sqlalchemy.orm import Session
from core.config import settings
from schemas.user_schema import UserInfo, UserLogin, UserSignup
from services.auth_service import (
    generate_access_token,
    verify_password,
    get_password_hash,
    generate_refresh_token,
    hash_token,
    oauth,
)
from core.supabase_client import supabase

REFRESH_TOKEN_TTL_DAYS = 7
IMAGE_BUCKET = "user-avatars"


def check_uuid(id: str):
    try:
        validated_uuid = str(UUID(id))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid UUID format")
    return validated_uuid


def store_refresh_token(db: Session, request: Request, user_id: str, refresh_token: str):
    user_agent = request.headers.get("user-agent", "unknown")
    forwarded = request.headers.get("x-forwarded-for")
    ip_address = forwarded.split(",")[0] if forwarded else request.client.host

    db.execute(
        insert(RefreshToken).values(
            user_id=user_id,
            token_hash=hash_token(refresh_token),
            revoked=False,
            expires_at=(datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_TTL_DAYS)).isoformat(),
            ip_address=ip_address,
            user_agent=user_agent,
        )
    )
    db.commit()


def set_refresh_token_cookie(response: Response, refresh_token: str):
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        secure=True,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
        path="/api/auth",
    )


def login_user(db: Session, request: Request, response: Response, user_login: UserLogin):
    current_user = db.execute(
        select(User).where(or_(User.username == user_login.login_id, User.email == user_login.login_id))
    ).scalar_one_or_none()

    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username/email or password")

    if not verify_password(user_login.password, current_user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username/email or password")

    access_token = generate_access_token(current_user.id, current_user.role)
    refresh_token = generate_refresh_token()
    store_refresh_token(db, request, current_user.id, refresh_token)
    set_refresh_token_cookie(response, refresh_token)

    user_info = UserInfo.model_validate(current_user)

    return {**user_info.model_dump(), "access_token": access_token, "token_type": "bearer"}


async def google_login(request: Request):
    return await oauth.auth_google.authorize_redirect(request, settings.REDIRECT_URI, prompt="select_account")


async def google_callback(db: Session, request: Request):
    token = await oauth.auth_google.authorize_access_token(request)
    userinfo = token.get("userinfo")
    email = userinfo.get("email")

    existing_user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()

    if not existing_user:
        prefix = email.split("@")[0].rstrip("0123456789")
        random_digits = "".join(random.choices(string.digits, k=5))
        username = f"{prefix}{random_digits}"

        result = db.execute(insert(User).values(username=username, email=email).returning(User.id))
        db.commit()

        user_id = result.scalar_one()
    else:
        user_id = existing_user.id
    refresh_token = generate_refresh_token()
    store_refresh_token(db, request, user_id, refresh_token)
    response = RedirectResponse(url=f"{settings.CLIENT_URL}")
    set_refresh_token_cookie(response, refresh_token)
    return response


def refresh_access_token(db: Session, request: Request, response: Response):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")

    token_hash = hash_token(refresh_token)

    result = db.execute(
        select(RefreshToken, User.role)
        .join(User, RefreshToken.user_id == User.id)
        .where(RefreshToken.token_hash == token_hash)
    ).one_or_none()

    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    db_token = result.RefreshToken
    user_role = result.role

    if db_token.revoked:
        time_elapsed = datetime.now(timezone.utc) - db_token.revoked_at

        if time_elapsed > timedelta(seconds=20):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token reuse detected. Please login again."
            )
        else:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Refresh in progress, please retry.")

    if db_token.expires_at < datetime.now(timezone.utc):
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .values(revoked=True, revoked_at=datetime.now(timezone.utc).isoformat())
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Expired refresh token")

    db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .values(revoked=True, revoked_at=datetime.now(timezone.utc).isoformat())
    )

    new_access_token = generate_access_token(db_token.user_id, user_role)
    new_refresh_token = generate_refresh_token()
    store_refresh_token(db, request, db_token.user_id, new_refresh_token)
    set_refresh_token_cookie(response, new_refresh_token)

    return {"access_token": new_access_token, "token_type": "bearer"}


def get_user_by_id(db: Session, user_id: str):
    user_uuid = check_uuid(user_id)

    result = db.execute(select(User).where(User.id == user_uuid)).scalar_one_or_none()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return result


def create_user(db: Session, new_user: UserSignup):
    user = db.execute(select(User.id).where(User.username == new_user.username)).scalar_one_or_none()
    if user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already existed")
    new_user.password = get_password_hash(new_user.password)
    user_dict = new_user.model_dump()
    if not user_dict.get("role"):
        user_dict["role"] = "user"
    result = db.execute(insert(User).values(user_dict).returning(User))
    user_obj = result.scalar_one()
    db.commit()
    db.refresh(user_obj)
    return user_obj


def logout_user(db: Session, request: Request, response: Response):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        token_hash = hash_token(refresh_token)
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .values(revoked=True, revoked_at=datetime.now(timezone.utc).isoformat())
        )
        db.commit()
    response.delete_cookie(key="refresh_token", path="/api/auth")
    return {"detail": "Logged out successfully"}


def update_user_by_id(db: Session, user_id: str, user_update):
    user_uuid = check_uuid(user_id)
    update_data = user_update.model_dump(exclude_unset=True)

    result = db.execute(update(User).where(User.id == user_uuid).values(update_data).returning(User))
    
    updated_user = result.scalar_one_or_none()

    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")

    db.commit()
    return updated_user


def update_user_password(db: Session, user_id: str, new_password: str):
    user_uuid = check_uuid(user_id)
    hashed_password = get_password_hash(new_password)

    result = db.execute(update(User).where(User.id == user_uuid).values(password=hashed_password).returning(User.id))

    updated_user = result.scalar_one_or_none()

    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")

    db.commit()
    return {"detail": "Update password successfully"}


def update_user_avatar(db: Session, user_id: str, file: UploadFile):
    user_uuid = check_uuid(user_id)
    user = db.execute(select(User).where(User.id == user_uuid)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    allowed_extensions = {".jpg", ".jpeg", ".png"}
    max_file_size = 5 * 1024 * 1024  # 5MB

    # Validate file extension
    file_ext = None
    if file.filename:
        file_ext = "." + file.filename.rsplit(".", 1)[-1].lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Only .jpg, .jpeg, and .png files are allowed"
        )

    # Read file content
    try:
        file_content = file.file.read()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to read file")

    if len(file_content) > max_file_size:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File size must not exceed 5MB")

    # Generate unique filename
    filename = f"{uuid.uuid4()}{file_ext}"
    storage_path = f"{user_uuid}/{filename}"

    # Upload to Supabase
    try:
        supabase.storage.from_(IMAGE_BUCKET).upload(
            path=storage_path, file=file_content, file_options={"content-type": file.content_type, "upsert": "true"}
        )
        avatar_url = supabase.storage.from_(IMAGE_BUCKET).get_public_url(storage_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to upload avatar: {str(e)}"
        )

    # Update user's avatar_url in database
    try:
        db.execute(update(User).where(User.id == user_uuid).values(avatar_url=avatar_url))
        db.commit()
        updated_user = db.execute(select(User).where(User.id == user_uuid)).scalar_one()
        return updated_user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update avatar: {str(e)}"
        )


def delete_user_by_id(db: Session, user_id: str):
    user_uuid = check_uuid(user_id)

    result = db.execute(delete(User).where(User.id == user_uuid).returning(User.id))
    deleted_user = result.scalar_one_or_none()

    if not deleted_user:
        raise HTTPException(status_code=404, detail="User not found")

    db.commit()
    return {"detail": "Delete user successfully"}
