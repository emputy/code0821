# 无线专网情报监测系统（450MHz / 配电无线专网）

监测 450MHz 无线专网领域（配电/电力、友商动态、重点国家频谱）的行业情报，自动采集、过滤、整理并产出报告。

## 当前阶段（阶段一：采集跑通）

- 从固定数据源采集最新动态（RSS + 网页抓取）
- 关键词过滤 + URL 去重
- 存入 SQLite 数据库（data/intel.db）

## 目录结构

    .
    ├── app/                  # 主程序
    │   ├── main.py           # 命令行入口
    │   ├── collector/        # 采集模块（RSS / 网页）
    │   ├── storage/          # SQLite 存储
    │   └── filter/           # 关键词过滤
    ├── config/
    │   └── sources.json      # 数据源与关键词配置
    ├── data/                 # 数据库与原始文件（运行时生成）
    └── requirements.txt      # Python 依赖

## 安装

    pip install -r requirements.txt

## 使用

    python -m app.main

首次运行会抓取各数据源，打印采集数量并存入数据库。数据源配置见 config/sources.json。

## 说明

- 数据源类型：rss（RSS 订阅）或 html（网页链接提取）
- 当前已配置来源：450 MHz Alliance、诺基亚、爱立信、中兴、UBBA
- 重点国家频谱监管机构来源待补充（名单确认后加入 sources.json）
- 各来源的 RSS/页面地址需在首次运行后逐一验证有效性
