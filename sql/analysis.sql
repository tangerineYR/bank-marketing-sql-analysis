-- name: overall
SELECT COUNT(*) AS total, SUM(subscribed='yes') AS subscribed,
       100.0 * SUM(subscribed='yes') / COUNT(*) AS rate_percent
FROM campaign_contact;

-- name: job_rates
SELECT j.value AS category, COUNT(*) AS total, SUM(c.subscribed='yes') AS subscribed,
       100.0 * SUM(c.subscribed='yes') / COUNT(*) AS rate_percent
FROM client_record r JOIN campaign_contact c USING (source_row_id)
JOIN job j ON j.id=r.job_id GROUP BY j.value ORDER BY j.value;

-- name: age_band_rates
SELECT CASE WHEN r.age < 30 THEN '<30' WHEN r.age < 40 THEN '30-39'
            WHEN r.age < 50 THEN '40-49' ELSE '50+' END AS category,
       COUNT(*) AS total, SUM(c.subscribed='yes') AS subscribed,
       100.0 * SUM(c.subscribed='yes') / COUNT(*) AS rate_percent
FROM client_record r JOIN campaign_contact c USING (source_row_id)
GROUP BY category ORDER BY MIN(r.age);

-- name: month_rates
SELECT month AS category, COUNT(*) AS total, SUM(subscribed='yes') AS subscribed,
       100.0 * SUM(subscribed='yes') / COUNT(*) AS rate_percent
FROM campaign_contact GROUP BY month ORDER BY MIN(FIELD(month,
'jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'));

-- name: contact_rates
SELECT m.value AS category, COUNT(*) AS total, SUM(c.subscribed='yes') AS subscribed,
       100.0 * SUM(c.subscribed='yes') / COUNT(*) AS rate_percent
FROM campaign_contact c JOIN contact_method m ON m.id=c.contact_method_id
GROUP BY m.value ORDER BY m.value;

-- name: previous_outcome_rates
SELECT p.value AS category, COUNT(*) AS total, SUM(c.subscribed='yes') AS subscribed,
       100.0 * SUM(c.subscribed='yes') / COUNT(*) AS rate_percent
FROM campaign_contact c JOIN previous_outcome p ON p.id=c.previous_outcome_id
GROUP BY p.value ORDER BY p.value;
