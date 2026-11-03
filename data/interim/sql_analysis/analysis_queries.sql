-- ============================================================
-- 子系统二：多维时空统计分析 SQL 存档
-- 库：air_quality   事实表：air_quality_detail（522,191 行，20 城 × 3 年）
-- 说明：date 为 DATE 类型，hour 为 0-23 整数
-- ============================================================

-- ① 季节性规律：PM2.5 冬高夏低、O3 夏高冬低的反向趋势（多系列柱状图数据）
SELECT CASE WHEN MONTH(date) IN (12,1,2) THEN '冬季'
            WHEN MONTH(date) IN (3,4,5)  THEN '春季'
            WHEN MONTH(date) IN (6,7,8)  THEN '夏季'
            ELSE '秋季' END AS season,
       ROUND(AVG(pm25),1) AS avg_pm25,
       ROUND(AVG(o3),1)   AS avg_o3,
       ROUND(AVG(aqi),1)  AS avg_aqi
FROM air_quality_detail
GROUP BY season
ORDER BY FIELD(season,'春季','夏季','秋季','冬季');

-- ② 昼夜波动：0-23 时平均浓度曲线（折线图数据）
SELECT hour,
       ROUND(AVG(pm25),1) AS pm25,
       ROUND(AVG(aqi),1)  AS aqi,
       ROUND(AVG(o3),1)   AS o3
FROM air_quality_detail
GROUP BY hour ORDER BY hour;

-- ③ 城市污染排行榜（横向条形图数据）
SELECT city,
       ROUND(AVG(aqi),1)  AS avg_aqi,
       ROUND(AVG(pm25),1) AS avg_pm25
FROM air_quality_detail
GROUP BY city ORDER BY avg_aqi DESC;

-- ④ 多城市月度趋势：北方组 4 城 36 个月（多折线图数据）
SELECT city,
       CONCAT(YEAR(date),'-',LPAD(MONTH(date),2,'0')) AS ym,
       ROUND(AVG(aqi),1) AS avg_aqi
FROM air_quality_detail
WHERE city IN ('北京','天津','济南','郑州')
GROUP BY city, ym ORDER BY ym, city;

-- ⑤ 逐年优良天数占比（环形饼图数据；优良 = 日AQI <= 100，先按天聚合再判断）
WITH daily AS (
    SELECT city, date, AVG(aqi) AS day_aqi
    FROM air_quality_detail
    GROUP BY city, date
)
SELECT YEAR(date) AS yr,
       COUNT(*)            AS total_days,
       SUM(day_aqi <= 100) AS good_days,
       ROUND(100*SUM(day_aqi <= 100)/COUNT(*), 1) AS good_ratio_pct
FROM daily
GROUP BY yr ORDER BY yr;

-- ⑥（首要污染物频次）依赖 primary_pollutant 回填，属计划第 2 步，暂缺
