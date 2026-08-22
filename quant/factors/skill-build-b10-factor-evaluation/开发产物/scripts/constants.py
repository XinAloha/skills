from __future__ import annotations


BUILD_ID = "B10"
BUILD_NAME = "IC测试与因子评估体系"

COLUMN_ALIASES = {
    "date": "trade_date",
    "asset": "ts_code",
    "factor": "factor_value",
    "return": "forward_return",
}

REQUIRED_COLUMNS = {"trade_date", "ts_code", "factor_value", "forward_return"}
VALID_FACTOR_DIRECTIONS = {"positive", "negative", "auto"}
VALID_TARGET_KINDS = {"return", "binary_success"}

STOCK_POOL_LABELS = {
    "all_a": "全A股",
    "hs300": "沪深300",
    "zz500": "中证500",
    "zz1000": "中证1000",
    "zz2000": "中证2000",
}

STOCK_POOL_ALIASES = {
    "all": "all_a",
    "all_a": "all_a",
    "全a": "all_a",
    "全a股": "all_a",
    "全A股": "all_a",
    "a股": "all_a",
    "hs300": "hs300",
    "沪深300": "hs300",
    "000300": "hs300",
    "zz500": "zz500",
    "中证500": "zz500",
    "000905": "zz500",
    "zz1000": "zz1000",
    "中证1000": "zz1000",
    "000852": "zz1000",
    "zz2000": "zz2000",
    "中证2000": "zz2000",
    "932000": "zz2000",
}

OUTPUT_COLUMNS = [
    "trade_date",
    "build_id",
    "build_name",
    "target_id",
    "result_type",
    "result_value",
    "result_json",
    "source_data_date",
    "data_version",
    "update_time",
]

CHART_COLORS = ["#1f4e79", "#2a9d8f", "#e76f51", "#6a4c93", "#f4a261", "#457b9d", "#8ab17d"]
