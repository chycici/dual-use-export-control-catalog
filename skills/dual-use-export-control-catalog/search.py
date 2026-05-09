#!/usr/bin/env python3
"""两用物项进出口许可证管理目录 — 检索工具

用法：
  python3 search.py "查询词"
  python3 search.py "查询词" --type 出口
  python3 search.py "查询词" --limit 5
  python3 search.py "查询词" --detail
  python3 search.py "8479899955"          # HS编码查询
  python3 search.py "1B101"               # 管制编码前缀查询
"""

import argparse
import json
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent
INDEX_PATH = SKILL_DIR / "data/2026年度两用物项进出口许可证检索索引.json"
MAIN_PATH = SKILL_DIR / "data/2026年度两用物项进出口许可证统一知识库.json"

# ---------- 常量 ----------
THRESHOLD_HIT = 80
THRESHOLD_SUSPECT = 40
DEFAULT_LIMIT = 10
NOISE = {'的', '和', '或', '及', '以', '用', '为', '与', '在', '从', '到', '被'}

# ---------- 行业词映射 ----------
INDUSTRY_MAP: dict[str, list[str]] = {
    "碳纤维": ["碳纤维", "碳纤维浸渍树脂材料", "纤维或纤丝材料"],
    "预浸料": ["预浸件", "预浸件和预成型件", "预成型件"],
    "复合材": ["复合材料", "复合材料结构件", "复合材料编织机", "复合材料层压板材"],
    "缠绕机": ["纤维缠绕机", "绕线机", "缠绕机", "多轴绕线机"],
    "推进剂": ["推进剂", "液体推进剂", "固体推进剂"],
    "离心机": ["离心机", "离心分离机", "离心压缩机"],
    "蒸馏塔": ["蒸馏塔", "氢-低温蒸馏塔"],
    "同位素": ["同位素分离器", "电磁同位素分离器"],
    "辐射屏蔽": ["辐射屏蔽窗", "高密度辐射屏蔽窗"],
    "化学武器": ["化学武器", "监控化学品", "可作为化学武器的化学品"],
    "芥子气": ["芥子气", "硫芥气", "氮芥气"],
    "沙林": ["沙林", "甲基氟膦酸异丙酯"],
    "梭曼": ["梭曼", "甲基氟膦酸频那酯"],
    "VX": ["VX", "甲基硫代膦酸乙基-S-2-二异丙氨基乙酯"],
    "铀": ["铀", "铀同位素"],
    "半导": ["半导体", "半导体设备"],
    "航空": ["航空器结构件", "航空发动机"],
    "航天": ["航天器结构件", "航天发动机"],
    "无人机": ["无人机", "无人航空器"],
    "导航": ["导航", "惯性导航", "GPS"],
    "陀螺仪": ["陀螺仪", "惯性导航"],
    "卫星": ["卫星", "卫星设备"],
    "导弹": ["导弹", "火箭", "弹道导弹"],
    "雷达": ["雷达", "雷达系统"],
    "红外": ["红外", "红外探测器"],
    "隐身": ["隐身材料", "隐身涂层"],
    "密码": ["密码技术", "密码设备", "密码产品"],
    "加密": ["密码技术", "密码设备", "密码产品"],
    "毒素": ["毒素", "蓖麻毒素", "石房蛤毒素"],
    "水下": ["水下设备", "水下系统"],
    "光谱": ["光谱仪", "光谱分析"],
    "激光器": ["激光器", "激光", "激光系统"],
    "电池": ["锂电池", "电池"],
    "数控": ["数控系统", "编程控制"],
    "液压": ["液压系统", "液压"],
    "焊接": ["焊接设备", "扩散连接", "焊接机"],
    "核电": ["核材料", "核设备", "核反应堆"],
    "炸药": ["炸药", "爆炸物"],
    "涂层": ["隐身材料", "隐身涂层", "涂层"],
    "铸": ["铸造", "铸件"],
    "锻": ["锻造", "锻件"],
    "生物": ["生物", "生物制剂", "毒素"],
    # DESIGN.md 建议补充
    "氟化氢": ["氟化氢", "无水氟化氢", "氟化氢钾", "氟化氢铵"],
    "氯化物": ["氯化磷酰", "三氯化磷", "氯化硫酰"],
    "丙酮": ["丙酮", "亚磷酸三甲酯"],
    "硝酸": ["硝酸", "红发烟硝酸", "四氧化二氮"],
    "钛合金": ["钛", "钛合金", "钛合金金属粉末"],
    "铀化合物": ["铀", "铀同位素", "六氟化铀"],
    "锆合金": ["锆", "锆合金"],
    "闪烁体": ["闪烁体", "闪烁探测器"],
    "压力传感器": ["压力传感器", "压力表"],
    "频率合成器": ["频率合成器", "信号发生器"],
    "质谱仪": ["质谱仪", "磁场质谱仪", "离子源"],
    "气体扩散": ["气体扩散分离", "扩散屏障"],
    "磁控管": ["磁控管", "行波管"],
    "涡轮泵": ["涡轮泵", "液体推进剂泵"],
    "电子束": ["电子束焊接机", "电子束蒸发源"],
}


# ---------- 分词 ----------
def tokenize(query: str) -> list[str]:
    tokens: set[str] = set()
    q = query.strip()
    tokens.add(q)

    # 1. 按常见分隔符切分
    segments = re.split(r'[\s，,、/／]+', q)
    segments = [s.strip() for s in segments if len(s.strip()) >= 2]
    tokens.update(segments)

    # 2. 对完整查询词和每个片段生成 2-4 字 n-gram
    for seg in [q] + segments:
        for n in (2, 3, 4):
            for i in range(len(seg) - n + 1):
                gram = seg[i:i + n]
                if not re.search(r'[^一-鿿\w]', gram):
                    tokens.add(gram)

    # 3. 去掉噪音词
    tokens = {t for t in tokens if len(t) >= 2 and t not in NOISE}

    return list(tokens)


# ---------- 行业词扩展 ----------
def expand_industry(tokens: list[str]) -> list[str]:
    """对 token 集合进行行业词扩展，追加对应的目录规范词"""
    expanded: set[str] = set()
    for token in tokens:
        if token in INDUSTRY_MAP:
            expanded.update(INDUSTRY_MAP[token])
    return list(expanded)


# ---------- 加载 ----------
def load_index():
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def load_main():
    data = json.loads(MAIN_PATH.read_text(encoding="utf-8"))
    return {r["序号"]: r for r in data["records"]}


# ---------- 核心搜索 ----------
def search(query: str, cat_type: str | None = None,
           limit: int = DEFAULT_LIMIT, detail: bool = False):
    if not query or len(query.strip()) < 2:
        return {"error": "查询词至少2个字符"}

    query = query.strip()
    index = load_index()

    # --- HS编码/管制编码快速通道 ---
    if re.match(r'^\d{10}$', query):
        return _search_by_hs(query, index, cat_type, limit, detail)
    if re.match(r'^\d+[A-Za-z]\d+', query):
        return _search_by_code_prefix(query, index, cat_type, limit, detail)
    # 纯数字短码（非10位）也按HS编码前缀匹配
    if re.match(r'^\d{4,9}$', query):
        return _search_by_hs_prefix(query, index, cat_type, limit, detail)

    # --- 正常分词搜索 ---
    tokens = tokenize(query)
    industry_expansions = expand_industry(tokens)

    # 过滤目录类型
    candidates = index
    if cat_type:
        candidates = [r for r in index if r.get("目录类型") == cat_type]

    # 多层评分
    scored: list[dict] = []
    for r in candidates:
        score, reasons = _score_record(query, tokens, industry_expansions, r)
        if score >= THRESHOLD_SUSPECT:
            scored.append({
                "score": score,
                "match_reasons": reasons,
                "record": r,
            })

    # 排序 + 截断
    scored.sort(key=lambda x: x["score"], reverse=True)
    truncated = len(scored) > limit
    top = scored[:limit]

    # 组装结果
    results = []
    for item in top:
        r = item["record"]
        hit_status = "✅" if item["score"] >= THRESHOLD_HIT else "⚠️"
        entry = {
            "rank": len(results) + 1,
            "hit_status": hit_status,
            "score": item["score"],
            "目录类型": r.get("目录类型", ""),
            "序号": r.get("序号"),
            "管制编码": r.get("管制编码", ""),
            "推荐产品名称": r.get("推荐产品名称", ""),
            "参考HS编码": r.get("参考HS编码", []),
            "监管条件": r.get("监管条件", ""),
            "match_reasons": item["match_reasons"],
            "目录原文摘要": None,
        }
        if detail:
            entry["目录原文摘要"] = _get_detail(r.get("序号"), r.get("管制编码", ""))
        results.append(entry)

    return {
        "query": query,
        "tokens": tokens,
        "industry_expansions": industry_expansions,
        "total_hits": len(scored),
        "truncated": truncated,
        "results": results,
        "note": "进口条目无管制编码属正常。HS编码为空表示原目录未列明，不代表不受管制。",
    }


def _search_by_hs(hs_code: str, index: list, cat_type, limit, detail):
    """HS编码精确匹配"""
    matched = []
    for r in index:
        hs_list = r.get("参考HS编码", [])
        if hs_code in hs_list:
            if cat_type and r.get("目录类型") != cat_type:
                continue
            matched.append(r)

    results = []
    for i, r in enumerate(matched[:limit]):
        entry = {
            "rank": i + 1,
            "hit_status": "✅",
            "score": 100,
            "目录类型": r.get("目录类型", ""),
            "序号": r.get("序号"),
            "管制编码": r.get("管制编码", ""),
            "推荐产品名称": r.get("推荐产品名称", ""),
            "参考HS编码": r.get("参考HS编码", []),
            "监管条件": r.get("监管条件", ""),
            "match_reasons": [f"HS编码「{hs_code}」精确命中"],
            "目录原文摘要": None,
        }
        if detail:
            entry["目录原文摘要"] = _get_detail(r.get("序号"), r.get("管制编码", ""))
        results.append(entry)

    return {
        "query": hs_code,
        "tokens": [hs_code],
        "industry_expansions": [],
        "total_hits": len(matched),
        "truncated": len(matched) > limit,
        "results": results,
        "note": "进口条目无管制编码属正常。HS编码为空表示原目录未列明，不代表不受管制。",
    }


def _search_by_hs_prefix(query: str, index: list, cat_type, limit, detail):
    """HS编码前缀匹配"""
    matched = []
    for r in index:
        hs_list = r.get("参考HS编码", [])
        if any(hs.startswith(query) for hs in hs_list):
            if cat_type and r.get("目录类型") != cat_type:
                continue
            matched.append(r)

    results = []
    for i, r in enumerate(matched[:limit]):
        entry = {
            "rank": i + 1,
            "hit_status": "✅" if len(matched) <= 3 else "⚠️",
            "score": 90,
            "目录类型": r.get("目录类型", ""),
            "序号": r.get("序号"),
            "管制编码": r.get("管制编码", ""),
            "推荐产品名称": r.get("推荐产品名称", ""),
            "参考HS编码": r.get("参考HS编码", []),
            "监管条件": r.get("监管条件", ""),
            "match_reasons": [f"HS编码前缀「{query}」命中"],
            "目录原文摘要": None,
        }
        if detail:
            entry["目录原文摘要"] = _get_detail(r.get("序号"), r.get("管制编码", ""))
        results.append(entry)

    return {
        "query": query,
        "tokens": [query],
        "industry_expansions": [],
        "total_hits": len(matched),
        "truncated": len(matched) > limit,
        "results": results,
        "note": "进口条目无管制编码属正常。HS编码为空表示原目录未列明，不代表不受管制。",
    }


def _search_by_code_prefix(code_prefix: str, index: list, cat_type, limit, detail):
    """管制编码前缀匹配"""
    matched = []
    for r in index:
        code = r.get("管制编码", "")
        if code and str(code).startswith(code_prefix):
            if cat_type and r.get("目录类型") != cat_type:
                continue
            matched.append(r)

    results = []
    for i, r in enumerate(matched[:limit]):
        entry = {
            "rank": i + 1,
            "hit_status": "✅",
            "score": 100,
            "目录类型": r.get("目录类型", ""),
            "序号": r.get("序号"),
            "管制编码": r.get("管制编码", ""),
            "推荐产品名称": r.get("推荐产品名称", ""),
            "参考HS编码": r.get("参考HS编码", []),
            "监管条件": r.get("监管条件", ""),
            "match_reasons": [f"管制编码前缀「{code_prefix}」命中"],
            "目录原文摘要": None,
        }
        if detail:
            entry["目录原文摘要"] = _get_detail(r.get("序号"), r.get("管制编码", ""))
        results.append(entry)

    return {
        "query": code_prefix,
        "tokens": [code_prefix],
        "industry_expansions": [],
        "total_hits": len(matched),
        "truncated": len(matched) > limit,
        "results": results,
        "note": "进口条目无管制编码属正常。HS编码为空表示原目录未列明，不代表不受管制。",
    }


# ---------- 多层评分 ----------
def _score_record(query: str, tokens: list[str],
                  expansions: list[str], record: dict) -> tuple[int, list[str]]:
    """多层评分：分值可叠加，每层有上限。总分用于判定 hit/suspect/miss。"""
    score = 0
    reasons: list[str] = []

    name = record.get("推荐产品名称", "")
    industry_raw = record.get("行业叫法", [])
    keywords = record.get("关键词", [])

    # L1: 原始查询词与推荐产品名称完全相等 → 100 (immediate)
    if query == name:
        return (100, [f"产品名称完全匹配「{name}」"])

    # L2: 原始查询词出现在别名/关键词中 → 95
    l2_hit = False
    for kw in keywords:
        if kw == query and not re.match(r'^\d[A-Z]', kw):
            score = 95
            reasons.append(f"别名完全匹配「{query}」")
            l2_hit = True
            break

    # L3: token 与行业叫法精确匹配 → 80/项, 本层贡献上限90
    #     单次 L3 命中即表示用户查询词落入行业叫法覆盖范围
    l3_hits = 0
    l3_seen: set[str] = set()
    for token in tokens:
        if token in l3_seen:
            continue
        for ind in industry_raw:
            if isinstance(ind, str) and token == ind:
                l3_hits += 1
                l3_seen.add(token)
                reasons.append(f"行业叫法「{token}」命中")
                break
    l3_score = min(l3_hits * 80, 90)

    # L4: 扩展词出现在关键词中 → 65/项, 本层贡献上限75
    #     故意设上限75，使纯概念映射命中保持在 ⚠️ 范围，需要L3或L2配合才能到 ✅
    l4_hits = 0
    l4_seen: set[str] = set()
    for exp_word in expansions:
        if exp_word in l4_seen:
            continue
        for kw in keywords:
            if exp_word in kw:
                l4_hits += 1
                l4_seen.add(exp_word)
                reasons.append(f"行业词扩展「{exp_word}」命中关键词")
                break
    l4_score = min(l4_hits * 65, 75)

    # L5: token 与关键词完全匹配 → 15/项, 本层贡献上限60
    l5_hits = 0
    l5_seen: set[str] = set()
    for token in tokens:
        if token in l5_seen:
            continue
        for kw in keywords:
            if token == kw:
                l5_hits += 1
                l5_seen.add(token)
                reasons.append(f"关键词「{token}」命中")
                break
    l5_score = min(l5_hits * 15, 60)

    # L6: token 是产品名称或关键词的子串 → 40/token, 本层贡献上限60
    l6_count = 0
    search_in = [name] + keywords
    for token in tokens:
        if len(token) >= 2:
            for text in search_in:
                if token in text:
                    l6_count += 1
                    break
    l6_score = min(l6_count * 40, 60)
    if l6_count > 0:
        reasons.append(f"产品名称/关键词部分匹配 (×{l6_count})")

    # L7: token 是关键词的子串（非完全匹配）→ 8/项, 上限20
    l7_count = 0
    for token in tokens:
        if len(token) >= 2:
            for kw in keywords:
                if token in kw and token != kw:
                    l7_count += 1
                    break
    l7_score = min(l7_count * 8, 20)

    # 总分：取 L2 和 (L3..L7 累加) 的最大值
    # L2 (别名匹配=95) 是强信号，直接返回 ✅
    # L3-L7 叠加：取各层贡献的最大值（非累加），确保只有强匹配才上80+
    accum = max(l3_score, l4_score, l5_score, l6_score, l7_score)

    score = max(score, accum)

    return (min(score, 100), reasons)


# ---------- 详情补充 ----------
_main_cache: dict | None = None


def _get_main():
    global _main_cache
    if _main_cache is None:
        _main_cache = load_main()
    return _main_cache


def _get_detail(seq_num: int, code: str) -> str | None:
    """从主库中按序号精准读取原文摘要"""
    main = _get_main()
    # 主库以序号为key，但由于有重复序号（不同目录类型），
    # 需要用序号+管制编码组合定位
    for key, rec in main.items():
        r = rec if isinstance(rec, dict) else None
        if r and r.get("序号") == seq_num:
            if code and r.get("管制编码") == code:
                return r.get("目录原文摘要")
    # fallback: just match by seq
    for key, rec in main.items():
        r = rec if isinstance(rec, dict) else None
        if r and r.get("序号") == seq_num:
            return r.get("目录原文摘要")
    return None


# ---------- CLI ----------
def main():
    parser = argparse.ArgumentParser(
        description="两用物项进出口许可证管理目录 — 检索工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 search.py "碳纤维缠绕机"
  python3 search.py "碳纤维缠绕机" --type 出口
  python3 search.py "碳纤维缠绕机" --limit 5 --detail
  python3 search.py "8479899955"
  python3 search.py "1B101"
        """,
    )
    parser.add_argument("query", help="查询词（产品名称、HS编码或管制编码）")
    parser.add_argument("--type", choices=["出口", "进口"], help="限定目录类型")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help=f"返回条数上限（默认{DEFAULT_LIMIT}）")
    parser.add_argument("--detail", action="store_true", help="返回完整原文摘要和报关要求")
    args = parser.parse_args()

    result = search(args.query, cat_type=args.type, limit=args.limit, detail=args.detail)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
