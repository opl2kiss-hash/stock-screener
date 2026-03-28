#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
長線翻倍選股系統 - 主篩選程式
條件：
1. 30~90日內橫盤整理中，有一根漲停
2. 後續橫盤整理中，有向上跳空缺口
3. 股價在90日內新高，並有連續紅K棒
4. 持續量增，量能大於1.2倍以上
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
import time
import warnings
warnings.filterwarnings('ignore')

# ===== 篩選參數設定（可調整）=====
CONFIG = {
    "consolidation_days": 60,        # 橫盤整理天數（30~90）
    "limit_up_threshold": 0.09,      # 漲停門檻（台股約9.5%，設9%）
    "gap_threshold": 0.01,           # 跳空缺口門檻（1%）
    "new_high_days": 90,             # 新高天數
    "consecutive_red": 3,            # 連續紅K棒最低根數
    "volume_ratio": 1.2,             # 量增倍數（1.2倍）
    "volume_avg_days": 20,           # 計算量能均值天數
    "consolidation_range": 0.10,     # 橫盤振幅門檻（10%以內視為橫盤）
}

def get_tw_stock_list():
    """取得台灣上市股票清單"""
    try:
        # 嘗試從 twstock 取得
        import twstock
        stocks = list(twstock.codes.keys())
        # 只取上市股票（4碼數字）
        stocks = [s for s in stocks if s.isdigit() and len(s) == 4]
        return stocks[:500]  # 限制測試數量
    except:
        # 備用清單：主要台灣股票
        return [
            "2330", "2317", "2454", "2308", "2303", "2382", "3711", "2881",
            "2882", "2412", "1303", "1301", "1326", "2002", "2886", "2884",
            "2885", "2891", "2892", "5880", "2357", "2379", "2395", "3034",
            "3231", "4904", "6505", "2207", "1216", "2105", "2327", "2344",
            "2347", "2353", "2356", "2360", "2376", "2377", "2388", "2392",
            "2408", "2409", "2448", "2451", "2458", "2474", "2492", "2498",
            "2542", "2545", "2548", "2603", "2609", "2615", "2618", "2633",
            "2634", "2636", "2637", "2838", "3006", "3008", "3016", "3017",
            "3019", "3022", "3024", "3025", "3026", "3029", "3030", "3031",
            "3032", "3033", "3035", "3036", "3037", "3038", "3039", "3041",
            "3042", "3043", "3044", "3045", "3046", "3047", "3048", "3049",
            "3050", "3051", "3052", "3053", "3054", "3055", "3056", "3057",
            "3058", "3059", "3060", "3061", "3062", "3063", "3064", "3065",
            "6669", "6770", "6789", "6805", "6816", "6823", "6829", "6830",
        ]

def fetch_stock_data(symbol, days=120):
    """抓取股票歷史資料"""
    try:
        tw_symbol = f"{symbol}.TW"
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days + 30)
        
        df = yf.download(tw_symbol, start=start_date, end=end_date, 
                        progress=False, auto_adjust=True)
        
        if df.empty or len(df) < 30:
            return None
            
        df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
        df = df.rename(columns={
            'Open': 'open', 'High': 'high', 'Low': 'low',
            'Close': 'close', 'Volume': 'volume'
        })
        df = df.dropna()
        return df
    except Exception as e:
        return None

def is_consolidation(df, start_idx, end_idx, threshold=None):
    """判斷是否為橫盤整理"""
    if threshold is None:
        threshold = CONFIG["consolidation_range"]
    
    segment = df.iloc[start_idx:end_idx]
    if len(segment) < 5:
        return False
    
    price_range = (segment['high'].max() - segment['low'].min()) / segment['close'].mean()
    return price_range <= threshold

def check_limit_up(df, start_idx, end_idx, threshold=None):
    """檢查是否有漲停（單日漲幅超過門檻）"""
    if threshold is None:
        threshold = CONFIG["limit_up_threshold"]
    
    segment = df.iloc[start_idx:end_idx]
    
    for i in range(1, len(segment)):
        prev_close = segment['close'].iloc[i-1]
        curr_close = segment['close'].iloc[i]
        change = (curr_close - prev_close) / prev_close
        if change >= threshold:
            return True, i + start_idx
    return False, -1

def check_gap_up(df, after_idx, threshold=None):
    """檢查是否有向上跳空缺口"""
    if threshold is None:
        threshold = CONFIG["gap_threshold"]
    
    for i in range(after_idx, len(df) - 1):
        curr_open = df['open'].iloc[i]
        prev_high = df['high'].iloc[i-1]
        if curr_open > prev_high * (1 + threshold):
            return True, i
    return False, -1

def check_new_high(df, days=None):
    """檢查是否在N日內新高"""
    if days is None:
        days = CONFIG["new_high_days"]
    
    if len(df) < days:
        return False
    
    recent = df.tail(days)
    current_close = df['close'].iloc[-1]
    max_high = recent['high'].max()
    
    # 最新收盤價接近或等於N日新高
    return current_close >= max_high * 0.98

def check_consecutive_red(df, min_count=None):
    """檢查是否有連續紅K棒"""
    if min_count is None:
        min_count = CONFIG["consecutive_red"]
    
    recent = df.tail(20)
    max_consecutive = 0
    current_consecutive = 0
    
    for i in range(len(recent)):
        if recent['close'].iloc[i] > recent['open'].iloc[i]:
            current_consecutive += 1
            max_consecutive = max(max_consecutive, current_consecutive)
        else:
            current_consecutive = 0
    
    return max_consecutive >= min_count, max_consecutive

def check_volume_increase(df, ratio=None, avg_days=None):
    """檢查是否持續量增"""
    if ratio is None:
        ratio = CONFIG["volume_ratio"]
    if avg_days is None:
        avg_days = CONFIG["volume_avg_days"]
    
    if len(df) < avg_days + 5:
        return False, 0
    
    # 前期均量
    prev_vol = df['volume'].iloc[-(avg_days+5):-5].mean()
    # 近期均量
    recent_vol = df['volume'].tail(5).mean()
    
    if prev_vol == 0:
        return False, 0
    
    vol_ratio = recent_vol / prev_vol
    return vol_ratio >= ratio, round(vol_ratio, 2)

def screen_stock(symbol, config=None):
    """對單一股票進行篩選"""
    if config:
        CONFIG.update(config)
    
    df = fetch_stock_data(symbol, days=120)
    if df is None:
        return None
    
    n = len(df)
    if n < 40:
        return None
    
    result = {
        "symbol": symbol,
        "name": symbol,
        "close": round(float(df['close'].iloc[-1]), 2),
        "change": 0,
        "conditions": {
            "c1_limit_up": False,
            "c2_gap_up": False,
            "c3_new_high": False,
            "c4_volume": False,
        },
        "details": {},
        "passed": False
    }
    
    # 計算漲跌幅
    if n >= 2:
        prev = float(df['close'].iloc[-2])
        curr = float(df['close'].iloc[-1])
        result["change"] = round((curr - prev) / prev * 100, 2)
    
    # 條件1：橫盤整理中有漲停
    lookback = min(CONFIG["consolidation_days"], n - 10)
    start_idx = max(0, n - lookback)
    
    has_limit, limit_idx = check_limit_up(df, start_idx, n - 5,
                                           CONFIG["limit_up_threshold"])
    
    if has_limit:
        # 確認漲停前後有橫盤
        pre_start = max(0, limit_idx - 20)
        if is_consolidation(df, pre_start, limit_idx):
            result["conditions"]["c1_limit_up"] = True
            result["details"]["limit_up_idx"] = int(limit_idx)
            result["details"]["limit_up_date"] = str(df.index[limit_idx].date())
    
    # 條件2：後續橫盤中有向上跳空缺口
    search_from = result["details"].get("limit_up_idx", n - 30)
    has_gap, gap_idx = check_gap_up(df, search_from)
    
    if has_gap:
        result["conditions"]["c2_gap_up"] = True
        result["details"]["gap_idx"] = int(gap_idx)
        result["details"]["gap_date"] = str(df.index[gap_idx].date())
    
    # 條件3：90日內新高 + 連續紅K
    is_new_high = check_new_high(df, CONFIG["new_high_days"])
    has_red, red_count = check_consecutive_red(df, CONFIG["consecutive_red"])
    
    if is_new_high and has_red:
        result["conditions"]["c3_new_high"] = True
        result["details"]["consecutive_red"] = red_count
        result["details"]["is_new_high"] = True
    
    # 條件4：持續量增
    has_vol, vol_ratio = check_volume_increase(df, CONFIG["volume_ratio"],
                                                CONFIG["volume_avg_days"])
    if has_vol:
        result["conditions"]["c4_volume"] = True
        result["details"]["volume_ratio"] = vol_ratio
    
    # 判斷是否通過所有條件
    passed_count = sum(result["conditions"].values())
    result["passed_count"] = passed_count
    result["passed"] = passed_count >= 3  # 至少通過3項
    
    return result

def run_screening(stock_list=None, config=None):
    """執行篩選"""
    if stock_list is None:
        stock_list = get_tw_stock_list()
    
    results = []
    total = len(stock_list)
    
    print(f"開始篩選 {total} 檔股票...")
    
    for i, symbol in enumerate(stock_list):
        if (i + 1) % 20 == 0:
            print(f"進度：{i+1}/{total} ({(i+1)/total*100:.1f}%)")
        
        result = screen_stock(symbol, config)
        if result and result["passed"]:
            results.append(result)
        
        time.sleep(0.3)  # 避免過於頻繁請求
    
    # 依通過條件數排序
    results.sort(key=lambda x: x["passed_count"], reverse=True)
    
    print(f"\n篩選完成！共找到 {len(results)} 檔符合條件的股票")
    return results

if __name__ == "__main__":
    results = run_screening()
    print("\n=== 篩選結果 ===")
    for r in results:
        conds = r["conditions"]
        flags = "".join(["✓" if v else "✗" for v in conds.values()])
        print(f"{r['symbol']} | 收:{r['close']} | {r['change']:+.2f}% | [{flags}]")
