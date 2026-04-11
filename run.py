#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
長線翻倍選股系統 — 主執行入口
用法：
  python run.py                    # 完整掃描（上市+上櫃，排除ETF）
  python run.py --twse             # 只掃上市
  python run.py --tpex             # 只掃上櫃
  python run.py --demo             # 快速 Demo（不需網路）
  python run.py --list 2330 2317   # 只篩選指定股票
  python run.py --refresh          # 強制更新股票清單快取後再掃描
  python run.py --no-open          # 掃完不自動開瀏覽器
"""

import resource as _resource
try:
    _soft, _hard = _resource.getrlimit(_resource.RLIMIT_NOFILE)
    _resource.setrlimit(_resource.RLIMIT_NOFILE, (min(_hard, 65536), _hard))
except Exception:
    pass

import sys
import os
import json
import subprocess
import argparse
from datetime import datetime

# 確保可以 import 同目錄的模組
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
os.chdir(_HERE)

def parse_args():
    parser = argparse.ArgumentParser(description='長線翻倍選股系統')
    parser.add_argument('--demo', action='store_true', help='使用示範資料（不需網路）')
    parser.add_argument('--list', nargs='+', help='指定股票代碼清單')
    parser.add_argument('--twse', action='store_true', help='只掃上市股票')
    parser.add_argument('--tpex', action='store_true', help='只掃上櫃股票')
    parser.add_argument('--refresh', action='store_true', help='強制重新抓取股票清單')
    parser.add_argument('--no-open', action='store_true', help='生成後不自動開啟瀏覽器')
    
    # 條件參數
    parser.add_argument('--consolidation-days', type=int, default=60, help='橫盤整理天數 (預設60)')
    parser.add_argument('--limit-up', type=float, default=0.09, help='漲停門檻 (預設0.09=9%%)')
    parser.add_argument('--gap', type=float, default=0.01, help='跳空門檻 (預設0.01=1%%)')
    parser.add_argument('--new-high-days', type=int, default=90, help='新高天數 (預設90)')
    parser.add_argument('--consecutive-red', type=int, default=3, help='連續紅K棒數 (預設3)')
    parser.add_argument('--volume-ratio', type=float, default=1.2, help='量增倍數 (預設1.2)')
    
    return parser.parse_args()

def get_demo_data():
    """示範資料"""
    return [
        {
            "symbol": "2330", "name": "台積電", "close": 920.0, "change": 2.34,
            "passed_count": 4, "passed": True,
            "conditions": {"c1_limit_up": True, "c2_gap_up": True, "c3_new_high": True, "c4_volume": True},
            "details": {"limit_up_date": "2025-01-15", "gap_date": "2025-01-22", "consecutive_red": 5, "volume_ratio": 1.8}
        },
        {
            "symbol": "2317", "name": "鴻海", "close": 185.5, "change": -0.54,
            "passed_count": 3, "passed": True,
            "conditions": {"c1_limit_up": True, "c2_gap_up": False, "c3_new_high": True, "c4_volume": True},
            "details": {"limit_up_date": "2025-01-10", "consecutive_red": 3, "volume_ratio": 1.45}
        },
        {
            "symbol": "2454", "name": "聯發科", "close": 1250.0, "change": 3.12,
            "passed_count": 4, "passed": True,
            "conditions": {"c1_limit_up": True, "c2_gap_up": True, "c3_new_high": True, "c4_volume": True},
            "details": {"limit_up_date": "2025-01-08", "gap_date": "2025-01-18", "consecutive_red": 4, "volume_ratio": 2.1}
        },
        {
            "symbol": "3034", "name": "聯詠", "close": 410.0, "change": 1.23,
            "passed_count": 3, "passed": True,
            "conditions": {"c1_limit_up": True, "c2_gap_up": True, "c3_new_high": False, "c4_volume": True},
            "details": {"limit_up_date": "2025-01-12", "gap_date": "2025-01-20", "volume_ratio": 1.65}
        },
        {
            "symbol": "6669", "name": "緯穎", "close": 2200.0, "change": 4.5,
            "passed_count": 4, "passed": True,
            "conditions": {"c1_limit_up": True, "c2_gap_up": True, "c3_new_high": True, "c4_volume": True},
            "details": {"limit_up_date": "2025-01-05", "gap_date": "2025-01-14", "consecutive_red": 6, "volume_ratio": 2.4}
        },
        {
            "symbol": "3661", "name": "世芯-KY", "close": 3200.0, "change": -1.23,
            "passed_count": 3, "passed": True,
            "conditions": {"c1_limit_up": True, "c2_gap_up": False, "c3_new_high": True, "c4_volume": True},
            "details": {"limit_up_date": "2025-01-03", "consecutive_red": 4, "volume_ratio": 1.9}
        },
        {
            "symbol": "2382", "name": "廣達", "close": 295.0, "change": 0.68,
            "passed_count": 3, "passed": True,
            "conditions": {"c1_limit_up": False, "c2_gap_up": True, "c3_new_high": True, "c4_volume": True},
            "details": {"gap_date": "2025-01-16", "consecutive_red": 3, "volume_ratio": 1.35}
        },
        {
            "symbol": "3529", "name": "力旺", "close": 1800.0, "change": 5.6,
            "passed_count": 4, "passed": True,
            "conditions": {"c1_limit_up": True, "c2_gap_up": True, "c3_new_high": True, "c4_volume": True},
            "details": {"limit_up_date": "2025-01-07", "gap_date": "2025-01-15", "consecutive_red": 5, "volume_ratio": 2.8}
        },
    ]

TOP50_STOCKS = [
    "2330", "2317", "2454", "2308", "2382", "2303", "3711",
    "2881", "2882", "2412", "1303", "1301", "1326", "2002",
    "2886", "2884", "2885", "2891", "2892", "5880", "2357",
    "2379", "2395", "3034", "3231", "4904", "6505", "2207",
    "1216", "2105", "2327", "2344", "6669", "6670", "3008",
    "3037", "6488", "3443", "4938", "6415", "3529", "3661",
    "5274", "6271", "2301", "2385", "5483", "3406", "4958", "6196",
]

def main():
    args = parse_args()
    
    config = {
        "consolidation_days": args.consolidation_days,
        "limit_up_threshold": args.limit_up,
        "gap_threshold": args.gap,
        "new_high_days": args.new_high_days,
        "consecutive_red": args.consecutive_red,
        "volume_ratio": args.volume_ratio,
    }
    
    print("=" * 60)
    print("  長線翻倍選股系統")
    print(f"  執行時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print(f"  參數設定：")
    print(f"    橫盤整理天數：{config['consolidation_days']} 日")
    print(f"    漲停門檻：{config['limit_up_threshold']*100:.1f}%")
    print(f"    跳空門檻：{config['gap_threshold']*100:.1f}%")
    print(f"    新高天數：{config['new_high_days']} 日")
    print(f"    連續紅K：{config['consecutive_red']} 根")
    print(f"    量增倍數：{config['volume_ratio']}x")
    print("=" * 60)
    
    if args.demo:
        print("\n[示範模式] 使用內建示範資料...")
        results = get_demo_data()
    else:
        from stock_screener import run_screening
        from stock_names import get_all_stock_list, get_twse_list, get_tpex_list, get_stock_name
        
        if args.refresh:
            from stock_names import clear_cache
            clear_cache()

        if args.list:
            stock_list = args.list
        elif args.twse:
            stock_list = get_twse_list()
        elif args.tpex:
            stock_list = get_tpex_list()
        else:
            stock_list = get_all_stock_list()

        print(f"  掃描範圍：{len(stock_list)} 檔股票")
        results = run_screening(stock_list, config)

        # 補上股票名稱
        for r in results:
            r["name"] = get_stock_name(r["symbol"])
    
    # 生成 HTML
    from html_generator import generate_html_report
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, "data")
    
    filepath = generate_html_report(results, config, output_dir)
    
    # 儲存 JSON 結果
    json_path = filepath.replace('.html', '.json')
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({"config": config, "results": results,
                       "generated": datetime.now().isoformat()}, f,
                      ensure_ascii=False, indent=2)
        print(f"📊 JSON 資料已儲存：{json_path}")
    except Exception as e:
        print(f"⚠️  JSON 儲存失敗（不影響後續部署）：{e}")
    
    # 自動開啟瀏覽器
    if not args.no_open:
        print(f"\n🌐 正在開啟瀏覽器...")
        try:
            if sys.platform == 'darwin':
                subprocess.run(['open', filepath])
            elif sys.platform == 'win32':
                os.startfile(filepath)
            else:
                subprocess.run(['xdg-open', filepath])
        except:
            print(f"請手動開啟：{filepath}")
    
    print(f"\n✅ 完成！共找到 {len(results)} 檔符合條件的股票")
    print(f"📁 檔案位置：{filepath}")

    # ── 自動部署到 GitHub Pages ──
    import shutil, json, glob
    git_dir = os.path.dirname(os.path.abspath(__file__))

    if os.path.isdir(os.path.join(git_dir, ".git")):
        try:
            today_str = datetime.now().strftime("%Y%m%d")
            date_dir  = os.path.join(git_dir, "date")
            os.makedirs(date_dir, exist_ok=True)

            # 複製到 date/ 資料夾（GitHub Pages 索引頁讀取此處）
            dest = os.path.join(date_dir, f"{today_str}.html")
            shutil.copy2(filepath, dest)
            print(f"📋 已複製報告到 date/{today_str}.html")

            # 更新 reports.json 清單
            htmls = glob.glob(os.path.join(date_dir, "????????.html"))
            dates = sorted(
                [os.path.basename(f).replace(".html", "") for f in htmls],
                reverse=True
            )
            json_path = os.path.join(date_dir, "reports.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(dates, f)

            print(f"\n📤 正在上傳到 GitHub Pages...")

            # git add
            r_add = subprocess.run(
                ["git", "-C", git_dir, "add",
                 f"date/{today_str}.html", "date/reports.json"],
                capture_output=True, text=True
            )
            if r_add.returncode != 0:
                print(f"⚠️  git add 失敗：{r_add.stderr.strip()}")

            # git commit（若無新變更會回傳 1，屬正常）
            r_commit = subprocess.run(
                ["git", "-C", git_dir, "commit", "-m", f"掃描報告 {today_str}"],
                capture_output=True, text=True
            )
            if r_commit.returncode == 0:
                print(f"📝 已建立 commit：掃描報告 {today_str}")
            else:
                # nothing to commit 也算正常
                if "nothing to commit" in r_commit.stdout or "nothing to commit" in r_commit.stderr:
                    print(f"ℹ️  無新變更需要 commit（可能已是最新）")
                else:
                    print(f"⚠️  git commit 警告：{r_commit.stderr.strip() or r_commit.stdout.strip()}")

            # git push（最多重試 2 次）
            push_ok = False
            for attempt in range(1, 3):
                r = subprocess.run(
                    ["git", "-C", git_dir, "push", "origin", "main"],
                    capture_output=True, text=True, timeout=60
                )
                if r.returncode == 0:
                    push_ok = True
                    break
                else:
                    print(f"⚠️  推送嘗試 {attempt}/2 失敗：{r.stderr.strip()}")

            if push_ok:
                print(f"✅ 上傳成功！1~2分鐘後可在此查看：")
                print(f"   https://opl2kiss-hash.github.io/stock-screener/")
            else:
                print(f"❌ 推送失敗，請手動執行桌面的「推送最新報告到GitHub.command」")

        except Exception as e:
            print(f"⚠️  自動部署錯誤：{e}")
            print(f"   請手動執行桌面的「推送最新報告到GitHub.command」")
    else:
        print("ℹ️  找不到 git 設定，跳過自動上傳")

if __name__ == "__main__":
    main()
