from sqlalchemy import String, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from app.database import Base


class Car(Base):
    __tablename__ = "cars"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    brand: Mapped[str] = mapped_column(String(128), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    total_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    color: Mapped[str] = mapped_column(String(64), nullable=False)
    transmission: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    mileage_km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mileage_display: Mapped[str | None] = mapped_column(String(64), nullable=True)
    body_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    drive_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    steering: Mapped[str | None] = mapped_column(String(16), nullable=True)
    displacement: Mapped[str | None] = mapped_column(String(32), nullable=True)
    seating_capacity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    engine_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    door_count: Mapped[str | None] = mapped_column(String(8), nullable=True)
    link: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
