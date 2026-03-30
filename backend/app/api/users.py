from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.auth import UserCreate, UserResponse, UserUpdate
from app.services.auth_service import create_user
from app.dependencies.auth import require_role
from app.models.user import User

router = APIRouter()


@router.post("/", response_model=UserResponse)
def create_new_user(
    request: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Create a new user (admin only)."""
    return create_user(
        db,
        username=request.username,
        email=request.email,
        password=request.password,
        full_name=request.full_name,
        role=request.role,
    )


@router.get("/", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """List all users (admin only)."""
    return db.query(User).order_by(User.created_at.desc()).all()


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    request: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Update user role or status (admin only)."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return user


@router.get("/doctors", response_model=list[UserResponse])
def list_doctors(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "nurse")),
):
    """List all doctors (for assignment dropdowns)."""
    return db.query(User).filter(User.role == "doctor", User.is_active == True).all()
