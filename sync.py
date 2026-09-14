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
        "tier": {
            "threshold": 200000,
            "in": 4.00,
            "out": 18.00,
            "cache": 0.40,
        },
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
        "tier": {
            "threshold": 200000,
            "in": 2.50,
            "out": 15.00,
            "cache": 0.25,
        },
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
    "gemini-omni-flash": {
        "provider": "Google-Gemini",
        "in": 1.50,
        "out": 9.00,
        "cache": 0.15,
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
        "out": 50.0,
        "cache": 1.0,
        "cache_write": 12.5,
    },
    # GPT-5 系列
    "gpt-5.6-sol": {
        "provider": "OpenAI",
        "in": 4.0,
        "out": 20.0,
        "cache": 0.4,
        "cache_write": 5.0,
        "tier": {
            "threshold": 272000,
            "in": 8.0,
            "out": 30.0,
            "cache": 0.8,
            "cache_write": 10.0,
        },
    },
    "gpt-5.6-terra": {
        "provider": "OpenAI",
        "in": 2.0,
        "out": 12.0,
        "cache": 0.2,
        "cache_write": 2.5,
        "tier": {
            "threshold": 272000,
            "in": 4.0,
            "out": 18.0,
            "cache": 0.4,
            "cache_write": 5.0,
        },
    },
    "gpt-5.6-luna": {
        "provider": "OpenAI",
        "in": 0.2,
        "out": 1.2,
        "cache": 0.02,
        "cache_write": 0.25,
        "tier": {
            "threshold": 272000,
            "in": 0.4,
            "out": 1.8,
            "cache": 0.04,
            "cache_write": 0.5,
        },
    },
    "gpt-5.6-cyber": {
        "provider": "OpenAI",
        "in": 12.5,
        "out": 75.0,
        "cache": 1.25,
        "cache_write": 15.625,
    },
    "gpt-5.5": {
        "provider": "OpenAI",
        "in": 5.0,
        "out": 30.0,
        "cache": 0.5,
        "tier": {
            "threshold": 272000,
            "in": 10.0,
            "out": 45.0,
            "cache": 1.0,
        },
    },
    "gpt-5.5-pro": {
        "provider": "OpenAI",
        "in": 30.0,
        "out": 180.0,
        "cache": 0.0,
        "tier": {
            "threshold": 272000,
            "in": 60.0,
            "out": 270.0,
            "cache": 0.0,
        },
    },
    "gpt-5.4": {
        "provider": "OpenAI",
        "in": 2.5,
        "out": 15.0,
        "cache": 0.25,
        "tier": {
            "threshold": 272000,
            "in": 5.0,
            "out": 22.5,
            "cache": 0.5,
        },
    },
    "gpt-5.4-pro": {
        "provider": "OpenAI",
        "in": 30.0,
        "out": 180.0,
        "cache": 0.0,
        "tier": {
            "threshold": 272000,
            "in": 60.0,
            "out": 270.0,
            "cache": 0.0,
        },
    },
    "gpt-5.4-mini": {
        "provider": "OpenAI",
        "in": 0.75,
        "out": 4.5,
        "cache": 0.075,
    },
    "gpt-5.4-nano": {
        "provider": "OpenAI",
        "in": 0.20,
        "out": 1.25,
        "cache": 0.02,
    },
    "gpt-5.2": {
        "provider": "OpenAI",
        "in": 1.75,
        "out": 14.0,
        "cache": 0.175,
    },
    "gpt-5.1": {
        "provider": "OpenAI",
        "in": 1.25,
        "out": 10.0,
        "cache": 0.125,
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
    "text-embedding-ada-002": {
        "provider": "OpenAI",
        "in": 0.10,
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


def calculate_ratios(raw_price: Dict[str, Any]) -> Tuple[float, float, float, float]:
    currency = raw_price.get("cur", "USD")
    rate = CNY_TO_USD if currency == "CNY" else 1.0

    inp_usd = raw_price["in"] * rate
    out_usd = raw_price["out"] * rate
    cache_usd = raw_price.get("cache", 0.0) * rate
    cache_write_usd = raw_price.get("cache_write", 0.0) * rate

    if inp_usd == 0:
        return 0.0, 0.0, 0.0, 0.0

    model_ratio = round(inp_usd / 2.0, 6)
    completion_ratio = round(out_usd / inp_usd, 4)
    cache_ratio = round(cache_usd / inp_usd, 4) if cache_usd > 0 else 0.0
    create_cache_ratio = round(cache_write_usd / inp_usd, 4) if cache_write_usd > 0 else 0.0

    return model_ratio, completion_ratio, cache_ratio, create_cache_ratio


def fmt_num(val: float) -> str:
    """格式化单价值，整数转为 int 去掉多余 .0，小数去除无效尾随 0"""
    if val == int(val):
        return str(int(val))
    return f"{val:.6f}".rstrip("0").rstrip(".")


def generate_billing_expr(raw_price: Dict[str, Any]) -> Optional[str]:
    """
    根据 New API (QuantumNous/new-api) 官方规范 (pkg/billingexpr/expr.md)
    为具备长上下文阶梯特性的模型生成自包含的 expr-lang 规范表达式
    规范标准：
      - 判断条件使用 len（上下文输入总长度），而非会被自动扣减的 p
      - 必须由 tier("标签名", 公式) 函数包裹，用于审计与日志记录档位
      - 变量规范：p(输入), c(补全), cr(缓存读), cc(缓存创建/写)
      - 单价为官方 $/1M tokens 真实价格，不需要且严禁外层除以 1000000
    示例：
      len <= 272000 ? tier("0_272k", p * 4 + c * 20 + cr * 0.4 + cc * 5) : tier("272k_plus", p * 8 + c * 30 + cr * 0.8 + cc * 10)
    """
    tier = raw_price.get("tier")
    if not tier:
        return None

    currency = raw_price.get("cur", "USD")
    rate = CNY_TO_USD if currency == "CNY" else 1.0

    threshold = tier["threshold"]
    t_k = int(threshold / 1000)
    tier1_name = f"0_{t_k}k"
    tier2_name = f"{t_k}k_plus"

    p1 = raw_price["in"] * rate
    c1 = raw_price["out"] * rate
    cr1 = raw_price.get("cache", 0.0) * rate
    cc1 = raw_price.get("cache_write", 0.0) * rate

    p2 = tier["in"] * rate
    c2 = tier["out"] * rate
    cr2 = tier.get("cache", 0.0) * rate
    cc2 = tier.get("cache_write", 0.0) * rate

    def build_tier_expr(p_val: float, c_val: float, cr_val: float, cc_val: float) -> str:
        parts = [f"p * {fmt_num(p_val)}", f"c * {fmt_num(c_val)}"]
        if cr_val > 0:
            parts.append(f"cr * {fmt_num(cr_val)}")
        if cc_val > 0:
            parts.append(f"cc * {fmt_num(cc_val)}")
        return " + ".join(parts)

    cost1 = build_tier_expr(p1, c1, cr1, cc1)
    cost2 = build_tier_expr(p2, c2, cr2, cc2)

    expr = f'len <= {threshold} ? tier("{tier1_name}", {cost1}) : tier("{tier2_name}", {cost2})'
    return expr


def main():
    parser = argparse.ArgumentParser(description="New API 价格同步工具")
    parser.add_argument("--provider", type=str, default=None, help="仅测试或更新指定的厂商（例如 DeepSeek, OpenAI 等）")
    parser.add_argument("--with-external", action="store_true", help="是否拉取外部全部开源库模型（默认关闭，保持纯净）")
    args = parser.parse_args()

    target_provider = args.provider.lower() if args.provider else None

    print("🚀 启动 New API 价格同步工具 (pricing-sync)...")
    providers = load_json(PROVIDERS_FILE, [])
    if target_provider:
        print(f"🎯 单厂商测试模式: [{args.provider}]")
    else:
        print(f"📦 官方核心厂商模式 (已配置厂商: {len(providers)} 家)")
        for p in providers:
            print(f"  🌐 官网数据源: {p.get('provider')} -> {p.get('url')}")
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

    # 2. 计算各模型的比率与阶梯表达式
    model_ratio_map: Dict[str, float] = {}
    completion_ratio_map: Dict[str, float] = {}
    cache_ratio_map: Dict[str, float] = {}
    create_cache_ratio_map: Dict[str, float] = {}
    billing_mode_map: Dict[str, str] = {}
    billing_expr_map: Dict[str, str] = {}

    for model_name, raw in models_to_process.items():
        m_ratio, c_ratio, ca_ratio, cc_ratio = calculate_ratios(raw)
        model_ratio_map[model_name] = m_ratio
        if c_ratio > 0:
            completion_ratio_map[model_name] = c_ratio
        if ca_ratio > 0:
            cache_ratio_map[model_name] = ca_ratio
        if cc_ratio > 0:
            create_cache_ratio_map[model_name] = cc_ratio

        # 检查是否包含阶梯定义并生成表达式
        expr = generate_billing_expr(raw)
        if expr:
            billing_mode_map[model_name] = "tiered_expr"
            billing_expr_map[model_name] = expr

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
        if "create_cache_ratio" in overrides:
            create_cache_ratio_map.update(overrides["create_cache_ratio"])
        if "billing_mode" in overrides:
            billing_mode_map.update(overrides["billing_mode"])
        if "billing_expr" in overrides:
            billing_expr_map.update(overrides["billing_expr"])

    # 4. 排序字典
    sorted_model_ratio = dict(sorted(model_ratio_map.items()))
    sorted_completion_ratio = dict(sorted(completion_ratio_map.items()))
    sorted_cache_ratio = dict(sorted(cache_ratio_map.items()))
    sorted_create_cache_ratio = dict(sorted(create_cache_ratio_map.items()))
    sorted_model_price = dict(sorted(model_price_map.items()))
    sorted_billing_mode = dict(sorted(billing_mode_map.items()))
    sorted_billing_expr = dict(sorted(billing_expr_map.items()))

    # 5. 构建标准输出载荷
    output_payload = {
        "success": True,
        "message": f"Updated at {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "data": {
            "model_ratio": sorted_model_ratio,
            "completion_ratio": sorted_completion_ratio,
            "cache_ratio": sorted_cache_ratio,
            "create_cache_ratio": sorted_create_cache_ratio,
            "model_price": sorted_model_price,
            "billing_mode": sorted_billing_mode,
            "billing_expr": sorted_billing_expr,
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
    print(f"📊 统计总览: 当前保留按量模型 {len(sorted_model_ratio)} 个，阶梯表达式模型 {len(sorted_billing_expr)} 个，按次模型 {len(sorted_model_price)} 个")

    # 8. 打印核对简报
    print("\n" + "="*55)
    print("📋【模型价格与倍率清单 (默认/基础阶梯)】")
    print("="*55)
    for m, r in sorted_model_ratio.items():
        comp = sorted_completion_ratio.get(m, 1.0)
        cache_r = sorted_cache_ratio.get(m, 0.0)
        cache_w = sorted_create_cache_ratio.get(m, 0.0)
        mode = f"[{sorted_billing_mode.get(m)}]" if m in sorted_billing_mode else ""
        cw_str = f"写: {cache_w:<6}" if cache_w > 0 else " "*11
        print(f"  * {m:<28} 输入: {r:<7} 补全: {comp:<6} 读: {cache_r:<6} {cw_str} {mode}")

    if sorted_billing_expr:
        print(f"\n⚡ [New API 阶梯计费表达式 ({len(sorted_billing_expr)} 个)]:")
        for m, expr in sorted_billing_expr.items():
            print(f"  ⚡ {m}:\n     -> {expr}")

    if sorted_model_price:
        print(f"\n🎁 [按次计费模型 ({len(sorted_model_price)} 个)]:")
        for m, price in sorted_model_price.items():
            print(f"  $ {m:<28} 单次价格: ${price}")

    print("="*55)
    print("💡 状态: 阶梯表达式与静态倍率双重支持已就绪！\n")


if __name__ == "__main__":
    main()
