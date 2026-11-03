# -*- coding: utf-8 -*-
"""
第二阶段收尾补充（不改表、不改已有脚本）：
  1. city_mean_profile.csv   20 城 × 15 指标历史均值（计划动作1 的"导出一份"）
  2. pca_loadings.csv        前 2 个主成分的载荷矩阵（动作3 结论的凭据）
  3. pca_conclusion.txt      PC1/PC2 因子解读结论（自动汇总前几大载荷）
  4. sse_elbow.png           肘部法则 SSE 图，标注选定 K=3（动作4）
口径与 cluster_pca_kmeans.py 保持一致：全期 batch、StandardScaler、前 2 主成分
连接参数走环境变量（见 pipeline_common.py）。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans

from pipeline_common import MEASURE, OUTPUT_DIR, get_engine

# 字体：Windows 用 SimHei/雅黑；Linux 容器用 Noto CJK（Dockerfile 安装）
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei",
                                   "Noto Sans CJK SC", "Noto Sans CJK JP"]
plt.rcParams["axes.unicode_minus"] = False

engine = get_engine()
K = 3
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 指标 -> 污染来源归类（用于把"载荷高的指标组"翻译成因子名）
SOURCE = {
    "pm25": "燃煤/扬尘颗粒物", "pm25_24h": "燃煤/扬尘颗粒物",
    "pm10": "燃煤/扬尘颗粒物", "pm10_24h": "燃煤/扬尘颗粒物",
    "so2": "燃煤", "so2_24h": "燃煤",
    "co": "不完全燃烧", "co_24h": "不完全燃烧",
    "no2": "机动车尾气", "no2_24h": "机动车尾气",
    "o3": "光化学(臭氧)", "o3_8h": "光化学(臭氧)",
    "o3_24h": "光化学(臭氧)", "o3_8h_24h": "光化学(臭氧)",
    "aqi": "综合污染指数",
}

print("读取 MySQL 明细...")
df = pd.read_sql(
    "SELECT city, {} FROM air_quality_detail".format(",".join(MEASURE)), engine)

# ---------- 1) 城市均值画像（动作1） ----------
pic = df.groupby("city")[MEASURE].mean().round(2)
pic.to_csv(os.path.join(OUTPUT_DIR, "city_mean_profile.csv"), encoding="utf-8-sig")
print(f"city_mean_profile.csv：{pic.shape[0]} 城 × {pic.shape[1]} 指标")

# ---------- 2) 标准化 + PCA 前 2 主成分 ----------
X = StandardScaler().fit_transform(pic)
pca = PCA(n_components=2, random_state=42).fit(X)
evr = pca.explained_variance_ratio_

# 载荷矩阵：变量与主成分的相关系数 = components_.T * sqrt(特征值)
loadings = pca.components_.T * np.sqrt(pca.explained_variance_)
ld = pd.DataFrame(loadings, index=MEASURE, columns=["PC1", "PC2"]).round(3)
ld["PC1占比%"] = (ld["PC1"] ** 2 / (ld["PC1"] ** 2 + ld["PC2"] ** 2) * 100).round(1)
ld = ld.reindex(ld["PC1"].abs().sort_values(ascending=False).index)
ld.to_csv(os.path.join(OUTPUT_DIR, "pca_loadings.csv"), encoding="utf-8-sig")
print("pca_loadings.csv：")
print(ld.to_string())

# ---------- 3) 结论自动汇总（动作3） ----------
# 肘部数据（供结论引用，图在第 4 节绘制）
inertias = [KMeans(n_clusters=k, n_init=10, random_state=42).fit(X).inertia_
            for k in range(2, 8)]

def factor_line(pc):
    top = ld[pc].abs().sort_values(ascending=False).head(5)
    names = [f"{v}({ld.loc[v, pc]:+.2f})" for v in top.index]
    srcs = pd.Series([SOURCE[v] for v in top.index]).value_counts()
    return "、".join(names), {k: int(v) for k, v in srcs.items()}

l1, s1 = factor_line("PC1")
l2, s2 = factor_line("PC2")

# 燃烧源污染物（pm25/pm10/no2/co/so2）在 PC1 上的同向性
burn = ["pm25", "pm10", "no2", "co", "so2"]
burn_pos = [v for v in burn if ld.loc[v, "PC1"] > 0.4]

# 与聚类互证：从 city_cluster_result 动态取簇均值（避免手写数字出错）
cr = pd.read_sql(
    "SELECT batch, cluster_label, AVG(pc1) AS pc1, AVG(pc2) AS pc2 "
    "FROM city_cluster_result GROUP BY batch, cluster_label", engine)
cross = []
for b, g in cr.groupby("batch"):
    row = g.loc[g["pc1"].idxmax()]
    cross.append(f"    {b}：PC1 均值最高的簇 = {row['cluster_label']}"
                 f"（{row['pc1']:+.2f}）")
oz = cr[cr.batch == "all"]
oz_hi = oz.loc[oz["pc2"].idxmax()]
oz_lo = oz.loc[oz["pc2"].idxmin()]
cross.append(f"    全期 PC2：{oz_hi['cluster_label']} 最高（{oz_hi['pc2']:+.2f}），"
             f"{oz_lo['cluster_label']} 最低（{oz_lo['pc2']:+.2f}）")

# 肘部下降幅度
drop23 = (inertias[0] - inertias[1]) / inertias[0] * 100
drop34 = (inertias[1] - inertias[2]) / inertias[0] * 100

lines = [
    "PCA 载荷矩阵分析结论（全期 20 城 × 15 指标，标准化后）",
    "=" * 56,
    f"PC1 方差贡献 {evr[0]:.1%}，PC2 方差贡献 {evr[1]:.1%}，"
    f"前 2 主成分累计 {evr.sum():.1%}。",
    "",
    f"PC1 载荷绝对值前 5：{l1}",
    f"    归类占比：{s1}",
    f"    此外 {'、'.join(burn_pos)} 载荷均 >+0.4 同向为正，"
    "说明 PC1 汇聚了颗粒物与 NO2/CO/SO2 等燃烧源指标，",
    "    → PC1 代表「燃煤/机动车复合污染强度因子」，得分越高污染越重。",
    "",
    f"PC2 载荷绝对值前 5：{l2}",
    f"    归类占比：{s2}",
    "    → PC2 为「臭氧(光化学) vs SO2/CO(燃煤燃烧)」对比轴："
    "得分高代表臭氧型污染，得分低代表燃煤型污染。",
    "",
    "与 K-Means 聚类互证（city_cluster_result 簇均值）：",
    *cross,
    "    → PC1 是区分污染程度的主轴、PC2 区分污染类型，与簇划分语义一致。",
    "",
    f"肘部法则：SSE 从 k=2 的 {inertias[0]:.1f} 降到 k=3 的 {inertias[1]:.1f}"
    f"（降幅 {drop23:.1f}%），k=3→4 仅再降 {drop34:.1f}%，边际收益明显放缓；",
    f"且 K={K} 与三类污染画像（颗粒物主导/臭氧主导/清洁）语义对应，故选定 K=3。",
]
with open(os.path.join(OUTPUT_DIR, "pca_conclusion.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("pca_conclusion.txt 已写出")

# ---------- 4) 肘部法则 SSE 图（动作4） ----------
plt.figure(figsize=(7, 4.5))
plt.plot(range(2, 8), inertias, "o-", lw=2, color="#2b6cb0")
plt.annotate(f"选定 K={K}", xy=(K, inertias[K - 2]), xytext=(K + 0.8, inertias[K - 2] + 8),
             arrowprops=dict(arrowstyle="->", color="#c0392b"),
             fontsize=11, color="#c0392b")
plt.xlabel("簇数 k")
plt.ylabel("SSE（簇内平方和 inertia）")
plt.title("K-Means 肘部法则：SSE 随 k 变化（全期 20 城画像）")
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "sse_elbow.png"), dpi=150)
print("sse_elbow.png 已写出；inertia(k2..7)：",
      {k: round(v, 1) for k, v in zip(range(2, 8), inertias)})
