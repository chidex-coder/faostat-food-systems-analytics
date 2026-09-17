-- Q32 How much of each domain is official data versus estimated, imputed or externally sourced?
SELECT o.domain, d.name, o.flag, COALESCE(f.description, 'unspecified') AS description, COUNT(*) AS n
FROM observation o JOIN dim_domain d USING (domain)
LEFT JOIN dim_flag f ON f.domain = o.domain AND f.flag = o.flag
GROUP BY o.domain, o.flag ORDER BY o.domain, n DESC;
