-- Update modules: change 'rendering' to 'framework' across coverage_results.
UPDATE daily_build.coverage_results
SET module = 'framework'
WHERE module = 'rendering';
