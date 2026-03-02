from pydantic import BaseModel


class CarOut(BaseModel):
    id: int
    brand: str
    model: str
    year: int
    price: int
    color: str
    link: str
    total_price: int | None = None
    transmission: str | None = None
    title: str | None = None
    mileage_km: int | None = None
    mileage_display: str | None = None
    body_type: str | None = None
    drive_type: str | None = None
    steering: str | None = None
    displacement: str | None = None
    seating_capacity: str | None = None
    engine_type: str | None = None
    door_count: str | None = None

    model_config = {"from_attributes": True}
