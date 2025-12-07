-- Weighted coverage percentage based on v_latest_branches_coverage_results.
-- For each row:
--   - If latest_status = 'pass', score = 1
--   - Else score = 1 - latest_gap_to_target / (latest_total * 0.8)
-- Rows are weighted by latest_total; the final value is the weighted average as a percentage.
SELECT
    CASE
        WHEN SUM(weight) = 0 THEN NULL
        ELSE SUM(weighted_score) / SUM(weight) * 100
    END AS weighted_latest_coverage_percent
FROM (
    SELECT
        COALESCE(l.latest_total, 0) AS weight,
        CASE
            WHEN l.latest_status = 'pass' THEN 1.0
            ELSE
                LEAST(
                    1.0,
                    GREATEST(
                        0.0,
                        1.0 - COALESCE(l.latest_gap_to_target, 0) / NULLIF(l.latest_total * 0.8, 0)
                    )
                )
        END * COALESCE(l.latest_total, 0) AS weighted_score
    FROM v_latest_branches_coverage_results l
    WHERE l.latest_total IS NOT NULL
) t;
