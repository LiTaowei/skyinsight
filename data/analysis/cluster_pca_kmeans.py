# -*- coding: utf-8 -*-
"""
子系统三：PCA 降维 + K-Means 城市污染画像聚类
填充表：city_cluster_result（城市归属）、cluster_center（簇画像）

流程（每个 batch 重复）：
  1. 从 air_quality_detail 聚合 20 城 × 15 指标画像矩阵
  2. StandardScaler Z-score 标准化
  3. PCA（累计方差 >=85% 自动定维；散点图用前两个成分）
  4. K-Means（k=3，脚本同时打印肘部法则数据供核对）
  5. 按簇中心画像自动命名（颗粒物主导型 / 臭氧主导型 / 清洁型）
batch：all=全期；winter=12,1,2 月；summer=6,7,8 月
连接参数走环境变量（见 pipeline_common.py）。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

import numpy as np
import pandas as pd
from sqlalchemy import text
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans

from pipeline_common import MEASURE, get_engine

engine = get_engine()
K = 3

print("读取 MySQL 明细...")
df = pd.read_sql(
    "SELECT city, MONTH(date) AS m, {} FROM air_quality_detail".format(
        ",".join(MEASURE)), engine)
print("明细行数：", len(df))

# 幂等：清空两张结果表
with engine.begin() as c:
    c.execute(text("TRUNCATE TABLE city_cluster_result"))
    c.execute(text("TRUNCATE TABLE cluster_center"))

BATCHES = {"all": df,
           "winter": df[df["m"].isin([12, 1, 2])],
           "summer": df[df["m"].isin([6, 7, 8])]}

for batch, d in BATCHES.items():
    # 1) 画像矩阵：每城 15 指标均值
    pic = d.groupby("city")[MEASURE].mean()
    X = StandardScaler().fit_transform(pic)

    # 2) 肘部法则参考数据（人审 k 是否合理）
    inertias = {k: round(KMeans(n_clusters=k, n_init=10, random_state=42).fit(X).inertia_, 1)
                for k in range(2, 7)}
    print(f"[{batch}] 肘部 inertia(k2..6): {inertias}")

    # 3) PCA：累计方差 >=85% 自动定维
    pca = PCA(n_components=0.85, random_state=42)
    pcs = pca.fit_transform(X)
    evr = np.cumsum(pca.explained_variance_ratio_)
    print(f"[{batch}] PCA 维数={pca.n_components_} 累计方差={evr[-1]:.1%}")
    pc1, pc2 = pcs[:, 0], pcs[:, 1]
    pc3 = pcs[:, 2] if pcs.shape[1] > 2 else None

    # 4) K-Means
    km = KMeans(n_clusters=K, n_init=10, random_state=42)
    labels = km.fit_predict(X)
    centers_z = km.cluster_centers_          # 标准化空间的簇中心

    # 5) 簇命名：标准化尺度下 pm25 最高 -> 颗粒物主导；其次 o3 最高 -> 臭氧主导；最低 -> 清洁
    i_pm = MEASURE.index("pm25")
    i_o3 = MEASURE.index("o3")
    order_pm = np.argsort(-centers_z[:, i_pm])       # pm25 从高到低的簇
    name_map = {int(order_pm[0]): "颗粒物主导型"}
    rest = [c for c in range(K) if c != order_pm[0]]
    rest_sorted = sorted(rest, key=lambda c: -centers_z[c][i_o3])
    name_map[rest_sorted[0]] = "臭氧主导型"
    name_map[rest_sorted[1]] = "清洁型"
    print(f"[{batch}] 簇命名：{name_map}")

    # 写 city_cluster_result
    rows = pd.DataFrame({
        "batch": batch,
        "city": pic.index,
        "cluster_id": labels,
        "cluster_label": [name_map[int(l)] for l in labels],
        "pc1": pc1, "pc2": pc2, "pc3": pc3,
        "k": K,
    })
    rows.to_sql("city_cluster_result", engine, if_exists="append", index=False)

    # 写 cluster_center（逆标准化回原量纲的画像：直接用真实均值）
    cen = pic.copy()
    cen["cluster_id"] = labels
    cen = cen.groupby("cluster_id")[MEASURE].mean().reset_index()
    cen.insert(0, "batch", batch)
    cen.insert(2, "cluster_label", cen["cluster_id"].map(lambda c: name_map[int(c)]))
    cen["k"] = K
    cen.to_sql("cluster_center", engine, if_exists="append", index=False)

    # 控制台摘要
    print(f"[{batch}] 城市归属：")
    for c in range(K):
        members = sorted(rows.loc[rows.cluster_id == c, "city"].tolist())
        print(f"    {name_map[c]}({c}): {members}")

with engine.connect() as c:
    n1 = c.execute(text("SELECT COUNT(*) FROM city_cluster_result")).scalar()
    n2 = c.execute(text("SELECT COUNT(*) FROM cluster_center")).scalar()
print(f"写入完成：city_cluster_result {n1} 行，cluster_center {n2} 行")
