#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GITHUB_USER="opl2kiss-hash"
REPO_NAME="stock-screener"
DATE_STR=$(date +"%Y%m%d")

echo "================================================"
echo "  長線翻倍選股 — 掃描 + 部署"
echo "  日期：$DATE_STR"
echo "================================================"

echo ""
echo "▶ [1/3] 開始掃描..."
python3 "$SCRIPT_DIR/run.py" --no-open
if [ $? -ne 0 ]; then
  echo "❌ 掃描失敗"
  exit 1
fi

echo ""
echo "▶ [2/3] 更新報告索引..."
python3 - << 'PYEOF'
import os, json, glob
d = os.path.expanduser("~/長線翻倍/date")
htmls = glob.glob(os.path.join(d, "????????.html"))
dates = sorted([os.path.basename(f).replace(".html","") for f in htmls], reverse=True)
with open(os.path.join(d, "reports.json"), "w") as f:
    json.dump(dates, f)
print(f"  共 {len(dates)} 份報告")
PYEOF

echo ""
echo "▶ [3/3] 推送到 GitHub..."
git add date/"$DATE_STR".html date/reports.json
git commit -m "掃描報告 $DATE_STR"
git push origin main

echo ""
echo "================================================"
echo "  ✅ 完成！"
echo "  🌐 https://$GITHUB_USER.github.io/$REPO_NAME/"
echo "================================================"
