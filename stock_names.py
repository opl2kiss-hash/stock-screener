#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
台灣股票清單動態抓取模組
來源：
  - 上市 ISIN：https://isin.twse.com.tw/isin/C_public.jsp?strMode=2
  - 上櫃 ISIN：https://isin.twse.com.tw/isin/C_public.jsp?strMode=4
  - 備用 TWSE openAPI / TPEX openAPI

ETF 識別邏輯：
  - 代碼以 00 開頭（ETF主流格式）
  - 代碼結尾為 B（債券ETF）
  - 代碼為6碼
  - 名稱含 ETF / 反1 / 正2 / 槓桿 / 反向 / 基金 等
"""

import urllib.request
import ssl
import certifi

# Mac SSL 修正：建立忽略憑證驗證的 context
_SSL_CTX = ssl.create_default_context(cafile=certifi.where())

def _open_url(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        return urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX)
    except Exception:
        # 備用：完全略過憑證驗證
        ctx = ssl._create_unverified_context()
        return urllib.request.urlopen(req, timeout=timeout, context=ctx)
import json
import os
import time
import re
from datetime import datetime, timedelta

CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".stock_list_cache.json")
CACHE_DAYS = 3

ETF_NAME_KEYWORDS = [
    "ETF", "etf", "反1", "正2", "槓桿", "反向",
    "基金", "債券", "期貨", "黃金", "原油", "指數",
    "永續", "存託憑證",
]

def is_etf_by_code(code):
    code = code.strip()
    if code.startswith("00") and len(code) >= 4:
        return True
    if code.upper().endswith("B") and len(code) >= 5:
        return True
    if len(code) == 6:
        return True
    return False

def is_etf_by_name(name):
    name_upper = name.upper()
    for kw in ETF_NAME_KEYWORDS:
        if kw.upper() in name_upper:
            return True
    return False

def is_etf(code, name):
    return is_etf_by_code(code) or is_etf_by_name(name)

def fetch_from_isin(mode):
    """
    mode=2 上市, mode=4 上櫃
    ISIN 頁面格式：<td>代碼　名稱</td>
    """
    url = f"https://isin.twse.com.tw/isin/C_public.jsp?strMode={mode}"
    result = {}
    try:
        with _open_url(url, timeout=20) as resp:
            raw = resp.read().decode("big5", errors="ignore")

        # 匹配 "代碼\u3000名稱" 的 td 欄位
        pattern = r'<td[^>]*>([A-Za-z0-9]{4,6})\u3000([^\t<]+)</td>'
        rows = re.findall(pattern, raw)
        for code, name in rows:
            code = code.strip()
            name = name.strip()
            if not code or not name:
                continue
            # 上市限4碼數字；上櫃允許4~5碼數字
            if mode == 2 and not re.match(r'^\d{4}$', code):
                continue
            if mode == 4 and not re.match(r'^\d{4,5}$', code):
                continue
            if is_etf(code, name):
                continue
            if any(x in name for x in ["特", "DR", "存託", "認購", "認售", "權證"]):
                continue
            result[code] = name
        label = "上市" if mode == 2 else "上櫃"
        print(f"  [ISIN-{label}] 抓到 {len(result)} 檔普通股")
    except Exception as e:
        print(f"  [ISIN mode={mode}] 失敗：{e}")
    return result

def fetch_twse_openapi():
    """備用：TWSE openAPI"""
    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    result = {}
    try:
        with _open_url(url, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for item in data:
            code = item.get("Code", "").strip()
            name = item.get("Name", "").strip()
            if not re.match(r'^\d{4}$', code):
                continue
            if is_etf(code, name):
                continue
            result[code] = name
        print(f"  [TWSE-openAPI] 抓到 {len(result)} 檔")
    except Exception as e:
        print(f"  [TWSE-openAPI] 失敗：{e}")
    return result

def fetch_tpex_openapi():
    """備用：TPEX openAPI"""
    url = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes"
    result = {}
    try:
        with _open_url(url, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for item in data:
            code = item.get("SecuritiesCompanyCode", "").strip()
            name = item.get("CompanyName", "").strip()
            if not re.match(r'^\d{4,5}$', code):
                continue
            if is_etf(code, name):
                continue
            result[code] = name
        print(f"  [TPEX-openAPI] 抓到 {len(result)} 檔")
    except Exception as e:
        print(f"  [TPEX-openAPI] 失敗：{e}")
    return result

# ── 快取 ───────────────────────────────────────────────────
def load_cache():
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        cached_at = datetime.fromisoformat(data["cached_at"])
        if datetime.now() - cached_at > timedelta(days=CACHE_DAYS):
            print(f"  [快取] 已逾 {CACHE_DAYS} 天，重新抓取...")
            return None
        return data
    except Exception:
        return None

def save_cache(all_stocks, twse, tpex):
    try:
        data = {
            "cached_at": datetime.now().isoformat(),
            "all_stocks": all_stocks,
            "twse": twse,
            "tpex": tpex,
        }
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        print(f"  [快取] 寫入失敗：{e}")

_runtime_cache = None

def _load_all(force_refresh=False):
    global _runtime_cache
    if _runtime_cache and not force_refresh:
        return _runtime_cache

    cached = load_cache()
    if cached and not force_refresh:
        _runtime_cache = cached
        print(f"  [快取] 使用 {cached['cached_at'][:10]} 的清單（上市+上櫃共 {len(cached['all_stocks'])} 檔）")
        return _runtime_cache

    print("  ▶ 正在從官方來源抓取完整上市＋上櫃股票清單，並剔除ETF...")

    # 先嘗試 ISIN 頁面（最完整）
    twse = fetch_from_isin(2)
    time.sleep(1)
    if not twse:
        print("  ISIN上市失敗，改用openAPI...")
        twse = fetch_twse_openapi()

    tpex = fetch_from_isin(4)
    time.sleep(1)
    if not tpex:
        print("  ISIN上櫃失敗，改用openAPI...")
        tpex = fetch_tpex_openapi()

    all_stocks = {}
    all_stocks.update(tpex)
    all_stocks.update(twse)   # 上市優先（若代碼重疊以上市為準）

    print(f"  ✅ 合計 {len(all_stocks)} 檔（上市 {len(twse)} + 上櫃 {len(tpex)}），已剔除ETF/特別股")
    save_cache(all_stocks, twse, tpex)

    _runtime_cache = {
        "all_stocks": all_stocks,
        "twse": twse,
        "tpex": tpex,
        "cached_at": datetime.now().isoformat(),
    }
    return _runtime_cache

# ── 公開介面 ───────────────────────────────────────────────
def get_stock_name(symbol, force_refresh=False):
    data = _load_all(force_refresh)
    return data["all_stocks"].get(symbol, symbol)

def get_all_stock_list(force_refresh=False):
    """全部上市+上櫃普通股代碼（已排除ETF）"""
    data = _load_all(force_refresh)
    return sorted(data["all_stocks"].keys())

def get_twse_list(force_refresh=False):
    data = _load_all(force_refresh)
    return sorted(data["twse"].keys())

def get_tpex_list(force_refresh=False):
    data = _load_all(force_refresh)
    return sorted(data["tpex"].keys())

def clear_cache():
    global _runtime_cache
    _runtime_cache = None
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
    print("  快取已清除")

if __name__ == "__main__":
    print("=== 上市櫃股票清單測試 ===\n")
    all_list = get_all_stock_list()
    print(f"\n總計：{len(all_list)} 檔")
    print(f"上市：{len(get_twse_list())} 檔")
    print(f"上櫃：{len(get_tpex_list())} 檔")
    print(f"\n前20檔：")
    for code in all_list[:20]:
        print(f"  {code}  {get_stock_name(code)}")
