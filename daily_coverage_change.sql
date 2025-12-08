-- Compute overall coverage change using v_latest_branches_coverage_results:
-- (latest_hit / latest_total) - (previous_hit / previous_total)
WITH totals AS (
    SELECT
        SUM(latest_hit) AS latest_hit,
        SUM(latest_total) AS latest_total,
        SUM(previous_hit) AS previous_hit,
        SUM(previous_total) AS previous_total
    FROM daily_build.v_latest_branches_coverage_results
)
SELECT
    CAST(
        CASE
            WHEN latest_total IS NULL OR latest_total = 0 OR previous_total IS NULL OR previous_total = 0 THEN NULL
            ELSE (CAST(latest_hit AS DECIMAL(38, 10)) / latest_total)
                 - (CAST(previous_hit AS DECIMAL(38, 10)) / previous_total)
        END AS DECIMAL(11, 10)
    ) AS coverage_change
FROM totals;
