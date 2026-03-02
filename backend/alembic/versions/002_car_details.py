"""car details

Revision ID: 002
Revises: 001
Create Date: 2025-03-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("cars", sa.Column("total_price", sa.Integer(), nullable=True))
    op.add_column("cars", sa.Column("transmission", sa.String(64), nullable=True))
    op.add_column("cars", sa.Column("title", sa.Text(), nullable=True))
    op.add_column("cars", sa.Column("mileage_km", sa.Integer(), nullable=True))
    op.add_column("cars", sa.Column("body_type", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("cars", "body_type")
    op.drop_column("cars", "mileage_km")
    op.drop_column("cars", "title")
    op.drop_column("cars", "transmission")
    op.drop_column("cars", "total_price")
