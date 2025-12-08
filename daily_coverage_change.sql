-- Compute overall coverage change using v_latest_branches_coverage_results:
-- (latest_hit / latest_total) - (previous_hit / previous_total)
WITH totals AS (
    SELECT
        SUM(latest_hit) AS latest_hit,
        SUM(latest_total) AS latest_total,
        SUM(previous_hit) AS previous_hit,
        SUM(previous_total) AS previous_total
    FROM v_latest_branches_coverage_results
)
SELECT
    CASE
        WHEN latest_total IS NULL OR latest_total = 0 THEN NULL
        ELSE latest_hit / latest_total
    END AS latest_coverage,
    CASE
        WHEN previous_total IS NULL OR previous_total = 0 THEN NULL
        ELSE previous_hit / previous_total
    END AS previous_coverage,
    CASE
        WHEN latest_total IS NULL OR latest_total = 0 OR previous_total IS NULL OR previous_total = 0 THEN NULL
        ELSE (latest_hit / latest_total) - (previous_hit / previous_total)
    END AS coverage_change
FROM totals;
