#!/bin/bash
# ================================================
# 長線翻倍選股系統 — 快速啟動腳本
# ================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================"
echo "  長線翻倍選股系統 - 快速選單"
echo "================================================"
echo ""
echo "  [1] 完整掃描（上市 + 上櫃，排除ETF）"
echo "  [2] 只掃上市股票"
echo "  [3] 只掃上櫃股票"
echo "  [4] 指定股票篩選"
echo "  [5] 快速示範（不需網路，馬上看結果）"
echo "  [6] 開啟最新報告"
echo "  [7] 強制更新股票清單後掃描"
echo "  [0] 離開"
echo ""
read -p "請選擇 [0-7]: " choice

case $choice in
  1)
    echo ""
    echo "▶ 完整掃描上市＋上櫃（排除ETF）..."
    python3 run.py
    ;;
  2)
    echo ""
    echo "▶ 掃描上市股票..."
    python3 run.py --twse
    ;;
  3)
    echo ""
    echo "▶ 掃描上櫃股票..."
    python3 run.py --tpex
    ;;
  4)
    echo ""
    read -p "請輸入股票代碼（空格分隔，例如：2330 2317 2454）: " codes
    python3 run.py --list $codes
    ;;
  5)
    echo ""
    echo "▶ 示範模式..."
    python3 run.py --demo
    ;;
  6)
    LATEST=$(ls -t "$SCRIPT_DIR/date/"*.html 2>/dev/null | head -1)
    if [ -z "$LATEST" ]; then
      echo "找不到報告，請先執行篩選"
    else
      echo "開啟：$LATEST"
      if [[ "$OSTYPE" == "darwin"* ]]; then
        open "$LATEST"
      elif [[ "$OSTYPE" == "msys"* ]] || [[ "$OSTYPE" == "cygwin"* ]]; then
        start "$LATEST"
      else
        xdg-open "$LATEST" 2>/dev/null || python3 -m webbrowser "$LATEST"
      fi
    fi
    ;;
  7)
    echo ""
    echo "▶ 強制更新股票清單後完整掃描..."
    python3 run.py --refresh
    ;;
  0)
    echo "再見！"
    exit 0
    ;;
  *)
    echo "無效選項"
    ;;
esac
