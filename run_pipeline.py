# -*- coding: utf-8 -*-
"""
一键数据处理管线（本地与 Docker 内通用）。

按顺序执行完整链路：
  1. init_schema                         建库建表 + 字典数据
  2. data/analysis/load_csv_to_mysql     原始 CSV -> air_quality_detail
  3. data/analysis/backfill_primary...   回填首要污染物
  4. data/analysis/cluster_pca_kmeans    PCA + K-Means 三批次聚类
  5. data/analysis/anomaly_iforest       孤立森林异常打分
  6. data/analysis/anomaly_events        异常事件聚合与归因
  7. data/analysis/pca_loadings_report   载荷矩阵 / 结论 / 肘部图

用法：
    python run_pipeline.py                  # 全量跑（默认）
    python run_pipeline.py --skip-ingest    # 跳过原始 CSV 导入
    python run_pipeline.py --from cluster   # 从聚类步骤开始
    python run_pipeline.py --only report    # 只跑报告步骤
"""
import argparse
import os
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 步骤名 -> 脚本相对路径（init_schema 是项目根模块）
STEPS = [
    ("init_schema", os.path.join(PROJECT_ROOT, "init_schema.py")),
    ("ingest", os.path.join(PROJECT_ROOT, "data", "analysis",
                            "load_csv_to_mysql.py")),
    ("backfill", os.path.join(PROJECT_ROOT, "data", "analysis",
                              "backfill_primary_pollutant.py")),
    ("cluster", os.path.join(PROJECT_ROOT, "data", "analysis",
                             "cluster_pca_kmeans.py")),
    ("iforest", os.path.join(PROJECT_ROOT, "data", "analysis",
                             "anomaly_iforest.py")),
    ("events", os.path.join(PROJECT_ROOT, "data", "analysis",
                            "anomaly_events.py")),
    ("report", os.path.join(PROJECT_ROOT, "data", "analysis",
                            "pca_loadings_report.py")),
]
STEP_NAMES = [name for name, _ in STEPS]


def run_step(name: str, script: str) -> None:
    print("\n" + "=" * 64)
    print(f"▶ 步骤 [{name}] -> {os.path.relpath(script, PROJECT_ROOT)}")
    print("=" * 64, flush=True)
    result = subprocess.run([sys.executable, script], cwd=PROJECT_ROOT)
    if result.returncode != 0:
        raise SystemExit(f"步骤 [{name}] 失败（退出码 {result.returncode}），管线中止")


def main():
    parser = argparse.ArgumentParser(description="一键数据处理管线")
    parser.add_argument("--skip-ingest", action="store_true",
                        help="跳过原始 CSV 导入步骤")
    parser.add_argument("--from", dest="from_step", choices=STEP_NAMES,
                        help="从指定步骤开始执行到最后")
    parser.add_argument("--only", dest="only_step", choices=STEP_NAMES,
                        help="只执行指定步骤")
    args = parser.parse_args()

    plan = STEPS
    if args.only_step:
        plan = [(n, s) for n, s in STEPS if n == args.only_step]
    else:
        if args.from_step:
            idx = STEP_NAMES.index(args.from_step)
            plan = STEPS[idx:]
        if args.skip_ingest:
            plan = [(n, s) for n, s in plan if n != "ingest"]

    print(f"本次执行 {len(plan)} 个步骤：{[n for n, _ in plan]}")
    for name, script in plan:
        run_step(name, script)
    print("\n全部步骤执行完成。")


if __name__ == "__main__":
    main()
