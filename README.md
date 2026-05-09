# dual-use-export-control-catalog — 两用物项进出口许可证知识库

基于2026年度《两用物项和技术进出口许可证管理目录》PDF，提供906条进口/出口管制物项的快速查询。

> **来源**：中华人民共和国商务部/海关总署  
> **数据版本**：1.0  
> **生成时间**：2026-05-06

## 功能

- 🔍 **快速初筛** — 输入产品名称，判断是否落入两用物项目录
- 📋 **推荐HS编码** — 匹配目录列明的海关商品编号
- 🏷️ **行业叫法映射** — 71条常见行业叫法→目录规范术语映射
- 📝 **深度判读** — 检索原文摘要做二次确认
- 🐍 **内置搜索脚本** — 直接运行 `python3 search.py` 即可查询

## 数据规模

| 类别 | 条目数 |
|------|-------|
| 出口管制条目 | 754 |
| 进口管制条目 | 152 |
| **合计** | **906** |
| 含行业叫法映射 | ~345条（37种行业常用词） |

## 安装（Hermes Agent）

```bash
# 方式1：一键安装
bash <(curl -fsSL https://raw.githubusercontent.com/chycici/dual-use-export-control-catalog/main/install.sh)

# 方式2：手动复制
git clone --depth=1 https://github.com/chycici/dual-use-export-control-catalog.git /tmp/repo
cp -r /tmp/repo/skills/dual-use-export-control-catalog ~/.hermes/skills/
rm -rf /tmp/repo
```

安装后重启 Hermes Agent 或在会话中使用 `/refresh` 即可使用。

## 使用方法

在 Hermes Agent 中对助理说：
- "帮我查查碳纤维缠绕机是不是两用物项"
- "这个产品要不要办出口许可证？"
- "查一下离心机在不在管制目录里"

也可以直接在终端独立查询：
```bash
cd ~/.hermes/skills/dual-use-export-control-catalog
python3 search.py "碳纤维缠绕机"
python3 search.py "碳纤维缠绕机" --detail
```

## 查询结果格式

```
产品名称：xxx
目录类型：出口 / 进口 / 可能同时涉及
知识库结果：✅ 命中 / ⚠️ 疑似命中 / ❌ 未命中
推荐HS编码：xxxxxx
对应管制编码：1Axxx / 1Bxxx
监管条件：两用物项和技术许可证
风险提示：...
目录原文摘要：...
```

## 文件结构

```
skills/dual-use-export-control-catalog/
├── SKILL.md                                                  # 技能入口（详细使用方法）
├── search.py                                                 # 核心搜索脚本
└── data/
    ├── 2026年度两用物项进出口许可证检索索引.json    # 轻量检索（524KB）
    └── 2026年度两用物项进出口许可证统一知识库.json  # 完整主库（1.3MB）
```

## 注意事项

- **初筛为主**：本库适合做初筛/知识检索，不替代正式商品归类
- **参数敏感**：许多条目按技术参数/性能阈值管制，需结合规格书确认
- **未列HS编码仍需办理**：目录说明明确写入，即使未列明海关商品编号，仍应依法办理许可证

## License

MIT
