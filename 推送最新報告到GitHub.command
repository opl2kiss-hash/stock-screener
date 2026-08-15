#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================"
echo "  長線翻倍 — 推送最新報告到 GitHub"
echo "================================================"
echo ""

# 顯示目前待推送狀態
echo "📋 待推送的 commit："
git log origin/main..HEAD --oneline 2>/dev/null || echo "（無待推送 commit）"
echo ""
echo "📋 date/ 資料夾最新日期："
ls date/????????.html 2>/dev/null | sort | tail -3 | xargs -I{} basename {} .html
echo ""

# 確認 date/ 裡有沒有比 origin 新的 HTML
LATEST_DATE=$(ls date/????????.html 2>/dev/null | sort | tail -1 | xargs basename 2>/dev/null | sed 's/.html//')
if [ -z "$LATEST_DATE" ]; then
    echo "❌ date/ 資料夾沒有報告"
    read -p "按 Enter 關閉..." ; exit 1
fi

echo "▶ 最新報告日期：$LATEST_DATE"
echo ""

# 確認此日期是否已在 git 追蹤
if git ls-files --error-unmatch "date/${LATEST_DATE}.html" &>/dev/null; then
    echo "ℹ️  date/${LATEST_DATE}.html 已在 git 中"
    # 確認是否需要推送
    AHEAD=$(git log origin/main..HEAD --oneline 2>/dev/null | wc -l | tr -d ' ')
    if [ "$AHEAD" -eq "0" ]; then
        echo "✅ 已是最新，無需推送"
        read -p "按 Enter 關閉..." ; exit 0
    fi
else
    # 新增到 git
    git add "date/${LATEST_DATE}.html" date/reports.json
    git commit -m "掃描報告 ${LATEST_DATE}"
fi

# 推送
echo "▶ 推送到 GitHub..."
git push origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 推送成功！"
    echo "🌐 https://opl2kiss-hash.github.io/stock-screener/"
else
    echo ""
    echo "❌ 推送失敗，請檢查網路連線"
fi

echo ""
read -p "按 Enter 關閉視窗..."
