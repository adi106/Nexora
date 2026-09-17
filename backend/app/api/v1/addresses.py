import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.dependencies import get_db
from backend.app.models.address import Address
from backend.app.models.user import User
from backend.app.schemas.address import AddressCreate, AddressResponse, AddressUpdate

router = APIRouter(prefix="/addresses", tags=["Addresses"])


def _get_owned_address(db: Session, address_id: uuid.UUID, user_id: uuid.UUID) -> Address:
    address = (
        db.query(Address)
        .filter(Address.id == address_id, Address.user_id == user_id)
        .first()
    )

    if address is None:
        raise HTTPException(status_code=404, detail="Address not found")

    return address


@router.get("", response_model=list[AddressResponse])
def list_addresses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Address)
        .filter(Address.user_id == current_user.id)
        .order_by(Address.is_default.desc(), Address.created_at.desc())
        .all()
    )


@router.post("", response_model=AddressResponse, status_code=status.HTTP_201_CREATED)
def create_address(
    address_data: AddressCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if address_data.is_default:
        db.query(Address).filter(Address.user_id == current_user.id).update(
            {"is_default": False}
        )

    has_existing = (
        db.query(Address.id).filter(Address.user_id == current_user.id).first()
        is not None
    )

    address = Address(
        user_id=current_user.id,
        address_line1=address_data.address_line1,
        address_line2=address_data.address_line2,
        city=address_data.city,
        region=address_data.region,
        postal_code=address_data.postal_code,
        country_code=address_data.country_code.upper(),
        is_default=address_data.is_default or not has_existing,
    )

    db.add(address)
    db.commit()
    db.refresh(address)

    return address


@router.get("/{address_id}", response_model=AddressResponse)
def get_address(
    address_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_owned_address(db, address_id, current_user.id)


@router.put("/{address_id}", response_model=AddressResponse)
def update_address(
    address_id: uuid.UUID,
    address_data: AddressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    address = _get_owned_address(db, address_id, current_user.id)
    update_data = address_data.model_dump(exclude_unset=True)

    if update_data.get("is_default") is True:
        db.query(Address).filter(Address.user_id == current_user.id).update(
            {"is_default": False}
        )

    if "country_code" in update_data and update_data["country_code"] is not None:
        update_data["country_code"] = update_data["country_code"].upper()

    for field, value in update_data.items():
        setattr(address, field, value)

    db.commit()
    db.refresh(address)

    return address


@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_address(
    address_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    address = _get_owned_address(db, address_id, current_user.id)
    was_default = address.is_default

    db.delete(address)
    db.flush()

    if was_default:
        next_address = (
            db.query(Address)
            .filter(Address.user_id == current_user.id)
            .order_by(Address.created_at.asc())
            .first()
        )
        if next_address is not None:
            next_address.is_default = True

    db.commit()
