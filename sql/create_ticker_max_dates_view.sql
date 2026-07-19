-- SQL Script to create a View for finding the latest date for each ticker

CREATE OR REPLACE VIEW ticker_max_dates AS
SELECT ticker, MAX(date) AS max_date
FROM dse_market_snapshots
GROUP BY ticker;
