# 城市空气质量分析系统

基于 2022–2024 年全国 20 个城市小时级空气质量数据的毕业设计项目。完整覆盖 **数据清洗 → 离线算法（PCA / K-Means / Isolation Forest）→ MySQL 落库 → FastAPI 接口 → ECharts 可视化仪表盘** 的端到端链路，并提供 **Docker 一键处理数据集与部署**，读者无需手动逐个运行脚本。

- 数据规模：约 52 万行小时级观测，15 项污染物指标，7 张业务表
- 后端：FastAPI + SQLAlchemy + PyMySQL，共 15 个业务接口 + 1 个健康检查
- 前端：原生 HTML / CSS / JavaScript + ECharts 5，本地化依赖，无需外网
- 算法：PCA 降维、K-Means 聚类（K=3）、Isolation Forest 异常检测与事件归因
- 工程化：一条命令完成建库、数据导入、算法计算与报告生成

## 功能特性

**统计分析（6 张图）**

- 四季均值对比、24 小时昼夜变化曲线
- 城市 AQI 排行（官方等级配色）、月度走势
- 优良天数统计、首要污染物频次分布

**算法分析（5 张图）**

- 聚类散点（支持三个时间批次切换）、PCA 载荷矩阵
- 簇画像雷达图、异常分数时间线（异常时刻红柱标注）
- 异常事件表（KPI + 起止时间 / 峰值 / 归因）

**地图与钻取（2 张图）**

- 全国 AQI 地图（点击城市联动全局筛选）
- 城市单站钻取（跨度 > 31 天自动聚合为日均值）

**三层联动**：顶部筛选栏（城市 / 年份 / 批次）、地图点击、卡片内控件，所有图表随筛选实时刷新。

## 技术栈

| 层次 | 技术 |
| --- | --- |
| 数据处理 | Python 3.12、pandas、NumPy |
| 机器学习 | scikit-learn、Matplotlib |
| 数据存储 | MySQL 8、SQLAlchemy、PyMySQL |
| 后端接口 | FastAPI、Uvicorn、Pydantic |
| 前端展示 | 原生 HTML/CSS/JS、ECharts 5、GeoJSON（均本地化） |
| 容器化 | Docker、Docker Compose |

## 目录结构

```
skyinsight/
├── main.py                  # FastAPI 启动入口
├── run_pipeline.py          # 一键数据处理管线（编排 7 个步骤）
├── init_schema.py           # 建库建表初始化器（Python 执行 schema.sql）
├── pipeline_common.py       # 统一配置：数据库连接 / 路径 / 常量（唯一权威来源）
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example             # 环境变量示例（复制为 .env 使用）
├── app/                     # 后端
│   ├── config.py            # 从 pipeline_common 读取连接
│   ├── database.py          # SQLAlchemy engine 与连通性检查
│   ├── queries.py           # 全部 SQL（按图表编号分段）
│   └── routers/             # meta / stats / analysis / mapview / ai 路由
├── frontend/                # 前端（无外网依赖）
│   ├── index.html
│   ├── css/style.css
│   └── js/                  # api.js / china.json / echarts.min.js / charts/
└── data/
    ├── schema.sql           # 7 张表 + 字典数据
    ├── raw/                 # 原始 CSV（不入库，读者自行下载放回）
    ├── processed/           # 最终处理数据（不入库）
    ├── interim/             # 历史中间产物（不入库；保留 .md/.sql 文档）
    └── analysis/            # 数据处理脚本（6 个）+ output/（运行后生成）
```

## 环境要求

- Docker Desktop（推荐方式，自带 MySQL、Python 环境，无需另装 Java/Spark）
- 本地开发方式另需：Python 3.12+、MySQL 8.x

## 快速开始（Docker 一键，推荐）

### 1. 下载数据集

到数据来源站点 [https://quotsoft.net/air/](https://quotsoft.net/air/) 下载
`china_cities_YYYYMMDD.csv` 文件（本项目使用 2022-01-01 至 2024-12-31），
放到 `data/raw/` 下即可。**目录层级不限**，管线会递归查找所有
`china_cities_*.csv`，因此解压后的嵌套目录（含中文目录名）可以直接使用，无需调整。

> 文件名以 `._` 开头的是 macOS 解压产生的垃圾文件，会被自动忽略。

### 2. （可选）配置环境变量

```powershell
Copy-Item .env.example .env
```

然后编辑 `.env` 修改 MySQL 密码等；不配置则使用默认密码 `123456`。

### 3. 一键处理数据集

```powershell
docker compose run --rm pipeline
```

该命令会自动启动 MySQL，并**按顺序完成全部 7 个步骤**：建库建表 → 导入原始
CSV → 回填首要污染物 → PCA/K-Means 聚类 → 异常检测 → 事件归因 → 生成报告。
算法产物（载荷矩阵、肘部图、结论等）会回写到 `data/analysis/output/`。

### 4. 启动 Web 服务

```powershell
docker compose up -d web
```

- 可视化仪表盘：<http://127.0.0.1:8000/>
- 接口文档（Swagger UI）：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/api/health>

停止服务：`docker compose down`（数据由命名卷 `mysql_data` 持久化保留）。

## 本地开发（不使用 Docker）

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 通过环境变量指定数据库连接（默认 localhost:3306 / root / 123456）
$env:MYSQL_PASS = "你的MySQL密码"

# 一键跑完整管线（内部会自动建库）
python run_pipeline.py

# 启动服务
uvicorn main:app --reload
```

## 数据处理管线

`run_pipeline.py` 按以下顺序编排，全部幂等、可重复执行：

| 顺序 | 步骤 / 脚本 | 作用 |
| --- | --- | --- |
| ① | `init_schema.py` | 执行 `schema.sql`：建库、7 张表、字典数据 |
| ② | `load_csv_to_mysql.py` | 原始宽表 CSV → 长表写入 `air_quality_detail`（UPSERT 幂等） |
| ③ | `backfill_primary_pollutant.py` | 按 HJ 633-2012 六参数 IAQI 回填首要污染物 |
| ④ | `cluster_pca_kmeans.py` | 三批次（all/winter/summer）PCA + KMeans（K=3） |
| ⑤ | `anomaly_iforest.py` | Isolation Forest 全量打分，写入 `anomaly_hourly` |
| ⑥ | `anomaly_events.py` | 连续异常合并为事件（起止 / 峰值 / 归因） |
| ⑦ | `pca_loadings_report.py` | 载荷矩阵、因子结论、肘部图写入 `output/` |

常用参数：

```powershell
python run_pipeline.py                  # 全量执行
python run_pipeline.py --skip-ingest    # 跳过 CSV 导入（复用已有明细）
python run_pipeline.py --from cluster   # 从聚类步骤开始
python run_pipeline.py --only report    # 只重新生成报告
```

### 数据库表结构（7 张表）

| 表名 | 说明 |
| --- | --- |
| `air_quality_detail` | 小时级明细（约 52 万行，含 `uk_dhc` 唯一索引） |
| `city_info` | 20 个城市元数据 |
| `aqi_level` | AQI 等级与官方配色 |
| `city_cluster_result` | 每条记录的聚类归属 |
| `cluster_center` | 各簇中心向量 |
| `anomaly_hourly` | 小时级异常分数 |
| `anomaly_events` | 合并后的异常事件与归因 |

## 数据说明

**数据来源**：[空气质量历史数据](https://quotsoft.net/air/)。该站点按日提供全国
城市站点的小时级 CSV，文件名形如 `china_cities_YYYYMMDD.csv`；本项目采集其中
20 个城市 2022-01-01 至 2024-12-31 的数据，经清洗后得到约 52 万行明细。

仓库**不包含**原始数据（约 420 MB）、中间产物与算法输出，均已在 `.gitignore`
中忽略，由上述管线在本地重新生成。连接参数全部通过环境变量注入，代码中不保存
任何密码或 API 密钥。

## 接口一览

| 分组 | 数量 | 典型接口 |
| --- | --- | --- |
| 元数据 | 2 | 城市名单、年份与批次列表 |
| 统计 | 6 | 四季均值、昼夜曲线、AQI 排行等 |
| 算法 | 5 | 聚类散点、PCA 载荷、异常事件等 |
| 地图 | 2 | 全国 AQI 地图、城市钻取 |
| 系统 | 1 | `/api/health` 健康检查 |

所有接口均支持在 `/docs` 页面在线调试。

## 常见问题

- **8000 端口启动失败（WinError 10013 / 10048）**：端口被占用，先停止旧容器，或修改 compose 中端口映射。
- **pipeline 提示找不到 CSV**：确认数据已放入 `data/raw`，且文件名匹配 `china_cities_*.csv`。
- **重新处理数据**：管线全部步骤幂等，直接再次执行 `docker compose run --rm pipeline` 即可。
- **报告 PNG 中文显示为方块**：镜像已内置 Noto CJK 字体；本地运行时请确认系统装有中文字体（SimHei / 微软雅黑）。

## 许可证

本项目基于 [MIT License](LICENSE) 发布。
