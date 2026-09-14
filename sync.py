#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 模型价格同步与倍率生成工具 (pricing-sync)
- 精准管理：默认仅包含你配置的官方厂商核心模型，避免杂乱冗余
- 干净纯粹：支持单厂商测试（--provider），方便测试特定官网
- 汇率自适应：自动折算国内人民币模型
- 规范产出：输出符合 New API 标准的 ratio_config.json
"""

import os
import sys
import json
import time
import argparse
from typing import Dict, Any, Tuple, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROVIDERS_FILE = os.path.join(BASE_DIR, "providers.json")
OVERRIDES_FILE = os.path.join(BASE_DIR, "overrides.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "ratio_config.json")

# 汇率配置 (1 USD 兑换多少 RMB，默认 7.2)
DEFAULT_USD_TO_CNY = float(os.getenv("USD_CNY_RATE", "7.2"))
CNY_TO_USD = 1.0 / DEFAULT_USD_TO_CNY

# ==============================================================================
# 官方核心厂商模型基准 (Google-Gemini 最新模型列表)
# ==============================================================================
OFFICIAL_MODELS = {
    # Gemini 3.8 / 3.7 / 3.6 Flash (享受 2026-12-31 前促销半价)
    "gemini-3.8-flash": {
        "provider": "Google-Gemini",
        "in": 0.75,
        "out": 3.75,
        "cache": 0.075,
    },
    "gemini-3.7-flash": {
        "provider": "Google-Gemini",
        "in": 0.75,
        "out": 3.75,
        "cache": 0.075,
    },
    "gemini-3.6-flash": {
        "provider": "Google-Gemini",
        "in": 0.75,
        "out": 3.75,
        "cache": 0.075,
    },
    # Gemini 3.5 系列
    "gemini-3.5-flash": {
        "provider": "Google-Gemini",
        "in": 1.50,
        "out": 9.00,
        "cache": 0.15,
    },
    "gemini-3.5-flash-lite": {
        "provider": "Google-Gemini",
        "in": 0.30,
        "out": 2.50,
        "cache": 0.03,
    },
    # Gemini 3.1 系列
    "gemini-3.1-flash-lite": {
        "provider": "Google-Gemini",
        "in": 0.25,
        "out": 1.50,
        "cache": 0.025,
    },
    "gemini-3.1-pro-preview": {
        "provider": "Google-Gemini",
        "in": 2.00,
        "out": 12.00,
        "cache": 0.20,
    },
    # Gemini 3 Flash Preview
    "gemini-3-flash-preview": {
        "provider": "Google-Gemini",
        "in": 0.50,
        "out": 3.00,
        "cache": 0.05,
    },
    # Gemini 2.5 系列
    "gemini-2.5-pro": {
        "provider": "Google-Gemini",
        "in": 1.25,
        "out": 10.00,
        "cache": 0.125,
    },
    "gemini-2.5-flash": {
        "provider": "Google-Gemini",
        "in": 0.30,
        "out": 2.50,
        "cache": 0.03,
    },
    "gemini-2.5-flash-lite": {
        "provider": "Google-Gemini",
        "in": 0.10,
        "out": 0.40,
        "cache": 0.01,
    },
    # 向量嵌入
    "gemini-embedding-2": {
        "provider": "Google-Gemini",
        "in": 0.20,
        "out": 0.00,
        "cache": 0.00,
    },
    # --------------------------------------------------------------------------
    # OpenAI 官方核心模型
    # --------------------------------------------------------------------------
    # GPT-6 系列
    "gpt-6-astra": {
        "provider": "OpenAI",
        "in": 10.0,
        "out": 12.5,
        "cache": 1.0,
    },
    # GPT-5 系列
    "gpt-5.6-sol": {
        "provider": "OpenAI",
        "in": 4.0,
        "out": 5.0,
        "cache": 0.4,
    },
    "gpt-5.6-terra": {
        "provider": "OpenAI",
        "in": 2.0,
        "out": 2.5,
        "cache": 0.2,
    },
    "gpt-5.6-luna": {
        "provider": "OpenAI",
        "in": 0.2,
        "out": 0.25,
        "cache": 0.02,
    },
    "gpt-5.4-mini": {
        "provider": "OpenAI",
        "in": 0.75,
        "out": 4.5,
        "cache": 0.075,
    },
    "gpt-5.2": {
        "provider": "OpenAI",
        "in": 1.75,
        "out": 14.0,
        "cache": 0.175,
    },
    "gpt-5": {
        "provider": "OpenAI",
        "in": 1.25,
        "out": 10.0,
        "cache": 0.125,
    },
    "gpt-5-mini": {
        "provider": "OpenAI",
        "in": 0.25,
        "out": 2.0,
        "cache": 0.025,
    },
    "gpt-5-nano": {
        "provider": "OpenAI",
        "in": 0.05,
        "out": 0.40,
        "cache": 0.005,
    },
    "gpt-5.3-codex": {
        "provider": "OpenAI",
        "in": 1.75,
        "out": 14.0,
        "cache": 0.175,
    },
    # 推理模型 (o-Series)
    "o4-mini": {
        "provider": "OpenAI",
        "in": 1.10,
        "out": 4.40,
        "cache": 0.275,
    },
    "o3-mini": {
        "provider": "OpenAI",
        "in": 1.10,
        "out": 4.40,
        "cache": 0.55,
    },
    "o3": {
        "provider": "OpenAI",
        "in": 2.00,
        "out": 8.00,
        "cache": 0.50,
    },
    "o3-pro": {
        "provider": "OpenAI",
        "in": 20.0,
        "out": 80.0,
        "cache": 0.0,
    },
    "o1": {
        "provider": "OpenAI",
        "in": 15.0,
        "out": 60.0,
        "cache": 7.5,
    },
    "o1-pro": {
        "provider": "OpenAI",
        "in": 150.0,
        "out": 600.0,
        "cache": 0.0,
    },
    # GPT-4.1 系列
    "gpt-4.1": {
        "provider": "OpenAI",
        "in": 2.00,
        "out": 8.00,
        "cache": 0.50,
    },
    "gpt-4.1-mini": {
        "provider": "OpenAI",
        "in": 0.40,
        "out": 1.60,
        "cache": 0.10,
    },
    "gpt-4.1-nano": {
        "provider": "OpenAI",
        "in": 0.10,
        "out": 0.40,
        "cache": 0.025,
    },
    # 经典主力模型
    "gpt-4o": {
        "provider": "OpenAI",
        "in": 2.50,
        "out": 10.00,
        "cache": 1.25,
    },
    "gpt-4o-mini": {
        "provider": "OpenAI",
        "in": 0.15,
        "out": 0.60,
        "cache": 0.075,
    },
    "gpt-4-turbo": {
        "provider": "OpenAI",
        "in": 10.0,
        "out": 30.0,
        "cache": 0.0,
    },
    "gpt-3.5-turbo": {
        "provider": "OpenAI",
        "in": 0.50,
        "out": 1.50,
        "cache": 0.0,
    },
    # 向量嵌入
    "text-embedding-3-small": {
        "provider": "OpenAI",
        "in": 0.02,
        "out": 0.0,
        "cache": 0.0,
    },
    "text-embedding-3-large": {
        "provider": "OpenAI",
        "in": 0.13,
        "out": 0.0,
        "cache": 0.0,
    },
}


def load_json(filepath: str, default: Any = None) -> Any:
    if not os.path.exists(filepath):
        return default if default is not None else {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ 读取 {filepath} 失败: {e}", file=sys.stderr)
        return default if default is not None else {}


def calculate_ratios(raw_price: Dict[str, Any]) -> Tuple[float, float, float]:
    currency = raw_price.get("cur", "USD")
    rate = CNY_TO_USD if currency == "CNY" else 1.0

    inp_usd = raw_price["in"] * rate
    out_usd = raw_price["out"] * rate
    cache_usd = raw_price.get("cache", 0.0) * rate

    if inp_usd == 0:
        return 0.0, 0.0, 0.0

    model_ratio = round(inp_usd / 2.0, 6)
    completion_ratio = round(out_usd / inp_usd, 4)
    cache_ratio = round(cache_usd / inp_usd, 4) if cache_usd > 0 else 0.0

    return model_ratio, completion_ratio, cache_ratio


def main():
    parser = argparse.ArgumentParser(description="New API 价格同步工具")
    parser.add_argument("--provider", type=str, default=None, help="仅测试或更新指定的厂商（例如 DeepSeek, OpenAI 等）")
    parser.add_argument("--with-external", action="store_true", help="是否拉取外部全部开源库模型（默认关闭，保持纯净）")
    args = parser.parse_args()

    target_provider = args.provider.lower() if args.provider else None

    print("🚀 启动 New API 价格同步工具 (pricing-sync)...")
    if target_provider:
        print(f"🎯 单厂商测试模式: [{args.provider}]")
    else:
        print(f"📦 官方核心厂商模式 (已配置厂商: {len(load_json(PROVIDERS_FILE, []))} 家)")
    print(f"💵 汇率基准: 1 USD = {DEFAULT_USD_TO_CNY} RMB")

    # 1. 过滤模型池
    models_to_process = {}
    for model_name, info in OFFICIAL_MODELS.items():
        if target_provider:
            if info.get("provider", "").lower() == target_provider:
                models_to_process[model_name] = info
        else:
            models_to_process[model_name] = info

    if target_provider and not models_to_process:
        print(f"⚠️ 未找到厂商 [{args.provider}] 的内置模型！支持的厂商名称有:")
        available_providers = set(i.get("provider") for i in OFFICIAL_MODELS.values())
        for p in sorted(available_providers):
            print(f"  - {p}")
        return

    # 2. 计算各模型的比率
    model_ratio_map: Dict[str, float] = {}
    completion_ratio_map: Dict[str, float] = {}
    cache_ratio_map: Dict[str, float] = {}

    for model_name, raw in models_to_process.items():
        m_ratio, c_ratio, ca_ratio = calculate_ratios(raw)
        model_ratio_map[model_name] = m_ratio
        if c_ratio > 0:
            completion_ratio_map[model_name] = c_ratio
        if ca_ratio > 0:
            cache_ratio_map[model_name] = ca_ratio

    # 3. 合并本地 overrides.json
    overrides = load_json(OVERRIDES_FILE, default={})
    model_price_map: Dict[str, float] = {}
    
    # 只有在全局模式下才写入通用按次计费模型，单厂商测试时保持绝对纯净
    if not target_provider:
        model_price_map = overrides.get("model_price", {})
        if "model_ratio" in overrides:
            model_ratio_map.update(overrides["model_ratio"])
        if "completion_ratio" in overrides:
            completion_ratio_map.update(overrides["completion_ratio"])
        if "cache_ratio" in overrides:
            cache_ratio_map.update(overrides["cache_ratio"])

    # 4. 排序字典
    sorted_model_ratio = dict(sorted(model_ratio_map.items()))
    sorted_completion_ratio = dict(sorted(completion_ratio_map.items()))
    sorted_cache_ratio = dict(sorted(cache_ratio_map.items()))
    sorted_model_price = dict(sorted(model_price_map.items()))

    # 5. 构建标准输出载荷
    output_payload = {
        "success": True,
        "message": f"Updated at {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "data": {
            "model_ratio": sorted_model_ratio,
            "completion_ratio": sorted_completion_ratio,
            "cache_ratio": sorted_cache_ratio,
            "model_price": sorted_model_price
        }
    }

    # 6. 比对旧数据并输出差异简报
    old_data = load_json(OUTPUT_FILE, default={}).get("data", {})
    old_model_ratios = old_data.get("model_ratio", {})

    new_models = []
    changed_models = []

    for m, ratio in sorted_model_ratio.items():
        if m not in old_model_ratios:
            new_models.append((m, ratio))
        elif abs(old_model_ratios[m] - ratio) > 1e-6:
            changed_models.append((m, old_model_ratios[m], ratio))

    # 7. 写入结果文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 成功输出目标文件: {OUTPUT_FILE}")
    print(f"📊 统计总览: 当前保留按量模型 {len(sorted_model_ratio)} 个，按次模型 {len(sorted_model_price)} 个")

    # 8. 打印核对简报
    print("\n" + "="*55)
    print("📋【模型价格与倍率清单】")
    print("="*55)
    for m, r in sorted_model_ratio.items():
        comp = sorted_completion_ratio.get(m, 1.0)
        cache = sorted_cache_ratio.get(m, 0.0)
        print(f"  * {m:<30} 输入: {r:<10} 补全: {comp:<8} 缓存: {cache}")

    if sorted_model_price:
        print(f"\n🎁 [按次计费模型 ({len(sorted_model_price)} 个)]:")
        for m, price in sorted_model_price.items():
            print(f"  $ {m:<30} 单次价格: ${price}")

    print("="*55)
    print("💡 状态: 数据已精简，完全受你掌控，随时准备接受单官网测试！\n")


if __name__ == "__main__":
    main()
