#!/bin/bash
# fetch_data.sh — 抓取东方财富真实数据写入 data/ 目录
# 每次执行抓取所有数据并保存为JSON
set -e

DATA_DIR="$(dirname "$0")/data"
mkdir -p "$DATA_DIR"

# 1. A股行情列表
curl -s --max-time 10 "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=200&po=1&np=1&fltt=2&invt=2&fid=f6&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f2,f3,f4,f5,f6,f8,f9,f10,f12,f14,f20,f23" > "$DATA_DIR/stock_list.json" 2>/dev/null || echo '{"data":{"diff":[]}}' > "$DATA_DIR/stock_list.json"

# 2. 大盘指数
for secid in "1.000001" "0.399001" "0.399006" "1.000688"; do
  curl -s --max-time 5 "https://push2.eastmoney.com/api/qt/stock/get?secid=$secid&fields1=f43,f44,f45,f46,f47,f48,f57,f58" > "$DATA_DIR/index_${secid}.json" 2>/dev/null || echo '{}' > "$DATA_DIR/index_${secid}.json"
done

# 3. 涨幅榜(筛选用)
curl -s --max-time 10 "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=200&po=0&np=1&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f2,f3,f4,f5,f6,f8,f9,f10,f12,f14,f20,f23" > "$DATA_DIR/stock_by_pct.json" 2>/dev/null || echo '{"data":{"diff":[]}}' > "$DATA_DIR/stock_by_pct.json"

echo "OK $(date +%H:%M:%S)"
