"""kihon spec fields (drive_type, steering, displacement, etc.)

Revision ID: 004
Revises: 003
Create Date: 2025-03-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("cars", sa.Column("drive_type", sa.String(32), nullable=True))
    op.add_column("cars", sa.Column("steering", sa.String(16), nullable=True))
    op.add_column("cars", sa.Column("displacement", sa.String(32), nullable=True))
    op.add_column("cars", sa.Column("seating_capacity", sa.String(16), nullable=True))
    op.add_column("cars", sa.Column("engine_type", sa.String(32), nullable=True))
    op.add_column("cars", sa.Column("door_count", sa.String(8), nullable=True))


def downgrade() -> None:
    op.drop_column("cars", "door_count")
    op.drop_column("cars", "engine_type")
    op.drop_column("cars", "seating_capacity")
    op.drop_column("cars", "displacement")
    op.drop_column("cars", "steering")
    op.drop_column("cars", "drive_type")
