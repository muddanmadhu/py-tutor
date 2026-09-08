"""Federated identity: firebase_uid, and password_hash becomes optional.

Revision ID: 0002_firebase_identity
Revises: 0001_initial

Adding an external identity provider means an account no longer necessarily has
a password of ours. ``password_hash`` is therefore relaxed to nullable, and
``firebase_uid`` joins the local learning record to the Firebase credential.

Both changes are additive and backwards-compatible: the previous release's code
keeps working against this schema, because every existing row still has a
password hash and simply ignores the new column.

The steps are guarded by an inspection rather than applied blindly. The baseline
revision builds the schema with ``Base.metadata.create_all``, so a *fresh*
database already arrives with both changes in place and would otherwise fail on
a duplicate column; a database created before this release genuinely needs them.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0002_firebase_identity"
down_revision: str | None = "0001_initial"
branch_labels: str | None = None
depends_on: str | None = None


def _has_firebase_uid() -> bool:
    """Whether the live ``users`` table already carries the column."""
    inspector = sa.inspect(op.get_bind())
    return any(column["name"] == "firebase_uid" for column in inspector.get_columns("users"))


def upgrade() -> None:
    """Add firebase_uid and make password_hash optional."""
    if not _has_firebase_uid():
        op.add_column("users", sa.Column("firebase_uid", sa.String(length=128), nullable=True))
        op.create_index("ix_users_firebase_uid", "users", ["firebase_uid"], unique=True)
        with op.batch_alter_table("users") as batch:
            batch.alter_column("password_hash", existing_type=sa.String(length=255), nullable=True)


def downgrade() -> None:
    """Drop firebase_uid and require a password again.

    Accounts that only ever signed in through Firebase have no password to
    restore, so they are deactivated rather than given a guessable placeholder.
    """
    if not _has_firebase_uid():
        return

    users = sa.table(
        "users",
        sa.column("password_hash", sa.String),
        sa.column("is_active", sa.Boolean),
    )
    op.execute(
        users.update()
        .where(users.c.password_hash.is_(None))
        .values(password_hash="", is_active=False)
    )
    with op.batch_alter_table("users") as batch:
        batch.alter_column("password_hash", existing_type=sa.String(length=255), nullable=False)
    op.drop_index("ix_users_firebase_uid", table_name="users")
    op.drop_column("users", "firebase_uid")
