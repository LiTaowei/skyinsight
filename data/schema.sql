-- ============================================================
-- 城市空气质量分析系统 —— 数据库建库脚本（MySQL 8.x）
-- 用法：mysql -u root -p < data/schema.sql
-- 内容：7 张业务表 + city_info / aqi_level 字典数据
-- ============================================================

CREATE DATABASE IF NOT EXISTS air_quality DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE air_quality;

-- ---------- 1. 小时明细事实表 ----------
CREATE TABLE IF NOT EXISTS `air_quality_detail` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `date` date NOT NULL COMMENT '日期（入库时由 YYYYMMDD 转 DATE）',
  `hour` tinyint NOT NULL COMMENT '0-23',
  `city` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `aqi` double DEFAULT NULL COMMENT 'AQI',
  `pm25` double DEFAULT NULL COMMENT 'PM2.5，μg/m³',
  `pm25_24h` double DEFAULT NULL COMMENT 'PM2.5 24小时均值',
  `pm10` double DEFAULT NULL COMMENT 'PM10，μg/m³',
  `pm10_24h` double DEFAULT NULL COMMENT 'PM10 24小时均值',
  `so2` double DEFAULT NULL COMMENT 'SO2，μg/m³',
  `so2_24h` double DEFAULT NULL COMMENT 'SO2 24小时均值',
  `no2` double DEFAULT NULL COMMENT 'NO2，μg/m³',
  `no2_24h` double DEFAULT NULL COMMENT 'NO2 24小时均值',
  `o3` double DEFAULT NULL COMMENT 'O3，μg/m³',
  `o3_8h` double DEFAULT NULL COMMENT 'O3 8小时滑动均值',
  `o3_24h` double DEFAULT NULL COMMENT 'O3 24小时均值',
  `o3_8h_24h` double DEFAULT NULL COMMENT 'O3 8小时滑动均值槽24h',
  `co` double DEFAULT NULL COMMENT 'CO，mg/m³',
  `co_24h` double DEFAULT NULL COMMENT 'CO 24小时均值',
  `pm25_24h_rolling` double DEFAULT NULL COMMENT '自算的 PM2.5 24h 滚动均值',
  `primary_pollutant` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '首要污染物（后续 ETL 回填，可空）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_dhc` (`date`,`hour`,`city`),
  KEY `idx_city` (`city`),
  KEY `idx_date` (`date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='空气质量小时明细（事实表，20 城 × 3 年）';

-- ---------- 2. 城市维度表 ----------
CREATE TABLE IF NOT EXISTS `city_info` (
  `city` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '城市名（与监测数据列名一致）',
  `province` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '省份',
  `longitude` decimal(9,6) NOT NULL COMMENT '经度',
  `latitude` decimal(9,6) NOT NULL COMMENT '纬度',
  `region` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '区域：华北/华东/中南/西南/西北/东北',
  PRIMARY KEY (`city`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='城市维度表';

-- ---------- 3. AQI 分级字典 ----------
CREATE TABLE IF NOT EXISTS `aqi_level` (
  `level_name` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '等级名',
  `lower` int NOT NULL COMMENT '区间下限（含）',
  `upper` int NOT NULL COMMENT '区间上限（含；301 以上用 99999 表示）',
  `color` varchar(7) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '可视化着色（国标色）',
  PRIMARY KEY (`level_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AQI 分级字典';

-- ---------- 4. 城市聚类结果 ----------
CREATE TABLE IF NOT EXISTS `city_cluster_result` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `batch` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '聚类批次',
  `city` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `cluster_id` int NOT NULL COMMENT '簇编号 0..k-1',
  `cluster_label` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '画像名',
  `pc1` double DEFAULT NULL COMMENT '主成分1得分（散点图 x）',
  `pc2` double DEFAULT NULL COMMENT '主成分2得分（散点图 y）',
  `pc3` double DEFAULT NULL COMMENT '主成分3得分',
  `k` int NOT NULL COMMENT '本次聚类的 K 值',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_batch_city` (`batch`,`city`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='城市污染画像聚类结果';

-- ---------- 5. 簇中心画像 ----------
CREATE TABLE IF NOT EXISTS `cluster_center` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `batch` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `cluster_id` int NOT NULL,
  `cluster_label` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `aqi` double DEFAULT NULL,
  `pm25` double DEFAULT NULL,
  `pm25_24h` double DEFAULT NULL,
  `pm10` double DEFAULT NULL,
  `pm10_24h` double DEFAULT NULL,
  `so2` double DEFAULT NULL,
  `so2_24h` double DEFAULT NULL,
  `no2` double DEFAULT NULL,
  `no2_24h` double DEFAULT NULL,
  `o3` double DEFAULT NULL,
  `o3_8h` double DEFAULT NULL,
  `o3_24h` double DEFAULT NULL,
  `o3_8h_24h` double DEFAULT NULL,
  `co` double DEFAULT NULL,
  `co_24h` double DEFAULT NULL,
  `k` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_batch_cluster` (`batch`,`cluster_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='各簇指标均值画像';

-- ---------- 6. 小时级异常分数 ----------
CREATE TABLE IF NOT EXISTS `anomaly_hourly` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `city` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `date` date NOT NULL,
  `hour` tinyint NOT NULL,
  `score` double NOT NULL COMMENT '孤立森林分数，越小越异常',
  `is_anomaly` tinyint NOT NULL DEFAULT '0' COMMENT '1=异常',
  `model_version` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_city_dh` (`city`,`date`,`hour`),
  KEY `idx_date` (`date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='小时级异常分数';

-- ---------- 7. 异常事件 ----------
CREATE TABLE IF NOT EXISTS `anomaly_events` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `city` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `start_time` datetime NOT NULL COMMENT '事件起始',
  `end_time` datetime NOT NULL COMMENT '事件结束',
  `duration_hours` int NOT NULL COMMENT '持续小时数',
  `peak_pm25` double DEFAULT NULL COMMENT '事件内 PM2.5 峰值',
  `peak_aqi` double DEFAULT NULL COMMENT '事件内 AQI 峰值',
  `peak_time` datetime DEFAULT NULL COMMENT '峰值时刻',
  `main_pollutant` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '主控污染物',
  `attribution` json DEFAULT NULL COMMENT '归因卡片',
  `model_version` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_city_time` (`city`,`start_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='异常事件窗口 + 结构化归因';

-- ============================================================
-- 字典数据
-- ============================================================
INSERT INTO `city_info` (`city`,`province`,`longitude`,`latitude`,`region`) VALUES
('上海','上海市',121.473000,31.230000,'华东'),
('乌鲁木齐','新疆',87.617000,43.793000,'西北'),
('北京','北京市',116.407000,39.904000,'华北'),
('南京','江苏省',118.796000,32.060000,'华东'),
('哈尔滨','黑龙江省',126.642000,45.756000,'东北'),
('天津','天津市',117.190000,39.125000,'华北'),
('广州','广东省',113.264000,23.129000,'中南'),
('成都','四川省',104.066000,30.572000,'西南'),
('昆明','云南省',102.832000,24.880000,'西南'),
('杭州','浙江省',120.155000,30.274000,'华东'),
('武汉','湖北省',114.305000,30.593000,'中南'),
('沈阳','辽宁省',123.431000,41.805000,'东北'),
('济南','山东省',117.120000,36.651000,'华东'),
('深圳','广东省',114.058000,22.543000,'中南'),
('苏州','江苏省',120.585000,31.298000,'华东'),
('西安','陕西省',108.940000,34.341000,'西北'),
('郑州','河南省',113.625000,34.746000,'中南'),
('重庆','重庆市',106.550000,29.563000,'中南'),
('长沙','湖南省',112.938000,28.228000,'中南'),
('青岛','山东省',120.382000,36.067000,'华东')
ON DUPLICATE KEY UPDATE `city`=VALUES(`city`);

INSERT INTO `aqi_level` (`level_name`,`lower`,`upper`,`color`) VALUES
('优',0,50,'#00e400'),
('良',51,100,'#ffff00'),
('轻度污染',101,150,'#ff7e00'),
('中度污染',151,200,'#ff0000'),
('重度污染',201,300,'#99004c'),
('严重污染',301,99999,'#7e0023')
ON DUPLICATE KEY UPDATE `lower`=VALUES(`lower`), `upper`=VALUES(`upper`), `color`=VALUES(`color`);
