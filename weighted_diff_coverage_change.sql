-- Weighted overall coverage change:
-- Sum of diff_coverage * combined_weight from v_latest_branches_coverage_results.
SELECT
    CAST(
        CASE
            WHEN SUM(combined_weight) = 0 THEN NULL
            ELSE SUM(diff_coverage * combined_weight)
        END AS DECIMAL(11, 10)
    ) AS weighted_diff_coverage_change,
    CAST(SUM(combined_weight) AS DECIMAL(11, 10)) AS weight_sum_used
FROM v_latest_branches_coverage_results
WHERE diff_coverage IS NOT NULL
  AND combined_weight IS NOT NULL;
