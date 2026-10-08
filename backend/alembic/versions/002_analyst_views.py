"""Analyst views: flatten YoY JSON and debrief JSON."""

from typing import Sequence, Union

from alembic import op

revision: str = "002_analyst_views"
down_revision: Union[str, Sequence[str], None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ANALYST_YOY_SQL = """
CREATE VIEW analyst_yoy AS
SELECT
    c.ticker,
    c.name AS company,
    r.period_type,
    r.period_end,
    r.prior_period_end,
    r.filing_date,
    m.metric->>'label' AS metric,
    (m.metric->>'current')::numeric AS current_amount,
    (m.metric->>'prior')::numeric AS prior_amount,
    (m.metric->>'dollar_change')::numeric AS dollar_change,
    (m.metric->>'pct_change')::numeric AS pct_change,
    m.ordinality::integer AS metric_order
FROM reports AS r
JOIN companies AS c ON c.id = r.company_id
CROSS JOIN LATERAL jsonb_array_elements(r.yoy_data->'metrics')
    WITH ORDINALITY AS m(metric, ordinality)
"""

ANALYST_DEBRIEF_SQL = """
CREATE VIEW analyst_debrief AS
SELECT
    c.ticker,
    c.name AS company,
    r.filing_date,
    d.debrief_json->>'headline' AS headline,
    d.debrief_json->>'overall_assessment' AS overall_assessment,
    d.debrief_json->>'margin_analysis' AS margin_analysis,
    takeaways.items AS takeaways,
    watch.items AS items_to_watch
FROM debriefs AS d
JOIN reports AS r ON r.id = d.report_id
JOIN companies AS c ON c.id = r.company_id
LEFT JOIN LATERAL (
    SELECT string_agg(item.value, chr(10) ORDER BY item.ordinality) AS items
    FROM jsonb_array_elements_text(
        COALESCE(d.debrief_json->'key_takeaways', '[]'::jsonb)
    ) WITH ORDINALITY AS item(value, ordinality)
) AS takeaways ON true
LEFT JOIN LATERAL (
    SELECT string_agg(item.value, chr(10) ORDER BY item.ordinality) AS items
    FROM jsonb_array_elements_text(
        COALESCE(d.debrief_json->'items_to_watch', '[]'::jsonb)
    ) WITH ORDINALITY AS item(value, ordinality)
) AS watch ON true
WHERE r.period_type = 'quarterly'
"""


def upgrade() -> None:
    op.execute(ANALYST_YOY_SQL)
    op.execute(ANALYST_DEBRIEF_SQL)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS analyst_debrief")
    op.execute("DROP VIEW IF EXISTS analyst_yoy")
