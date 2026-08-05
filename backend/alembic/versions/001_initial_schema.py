"""Initial schema: companies, reports, debriefs."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("cik", sa.String(length=10), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cik"),
        sa.UniqueConstraint("ticker"),
    )
    op.create_index(op.f("ix_companies_cik"), "companies", ["cik"], unique=False)
    op.create_index(op.f("ix_companies_ticker"), "companies", ["ticker"], unique=False)

    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("period_type", sa.String(length=16), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("prior_period_end", sa.Date(), nullable=True),
        sa.Column("yoy_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("filing_date", sa.String(length=10), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reports_company_id"), "reports", ["company_id"], unique=False)
    op.create_index(
        "ix_reports_company_filing_period",
        "reports",
        ["company_id", "filing_date", "period_type"],
        unique=False,
    )

    op.create_table(
        "debriefs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("debrief_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model_used", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_id", name="uq_debriefs_report_id"),
    )
    op.create_index(op.f("ix_debriefs_report_id"), "debriefs", ["report_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_debriefs_report_id"), table_name="debriefs")
    op.drop_table("debriefs")
    op.drop_index("ix_reports_company_filing_period", table_name="reports")
    op.drop_index(op.f("ix_reports_company_id"), table_name="reports")
    op.drop_table("reports")
    op.drop_index(op.f("ix_companies_ticker"), table_name="companies")
    op.drop_index(op.f("ix_companies_cik"), table_name="companies")
    op.drop_table("companies")
