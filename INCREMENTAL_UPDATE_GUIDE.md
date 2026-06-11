# RAG 增量更新指南

## 概述

Phase 1 优化已完成，新增以下功能：

1. **增量更新** - 只处理变化的文件，避免全量重建
2. **元数据增强** - 自动提取文档类型、项目、关键词等信息
3. **带过滤搜索** - 按文档类型、项目等条件精准检索

## 新增文件

| 文件 | 功能 |
|------|------|
| incremental_manager.py | 文件变化检测和状态管理 |
| metadata_enricher.py | 元数据增强器 |
| ingest_docs_v2.py | 支持元数据增强的文档摄入 |
| vectorstore_incremental.py | 增量向量库操作 |
| auto_ingest_v2.py | 支持增量更新的自动监听 |
| config_v2.py | 支持新功能的配置加载 |

## 快速开始

### 1. 使用增量更新监听器

启动增量监听器（推荐）:
  python auto_ingest_v2.py

后台运行:
  python auto_ingest_v2.py --daemon

强制全量扫描:
  python auto_ingest_v2.py --full-scan

### 2. 手动增量更新



### 3. 带过滤搜索



## 元数据字段说明

| 字段 | 说明 | 示例值 |
|------|------|--------|
| doc_type | 文档类型 | contract, design, bid, manual, general |
| project | 项目名称 | fujinba, weituo, fujiang, unknown |
| section | 章节标题 | 第一章 总则 |
| keywords | 关键词（逗号分隔） | 合同,条款,工期 |
| dates | 日期（逗号分隔） | 2024年1月1日 |
| amounts | 金额（逗号分隔） | 7.798亿元 |
| source_file | 源文件名 | 合同.docx |
| char_count | 字符数 | 1234 |
| ingested_at | 摄入时间 | 2024-01-01T12:00:00 |

## 配置说明

在 config.yaml 中添加以下配置：



## 性能对比

| 指标 | 全量重建 | 增量更新 |
|------|----------|----------|
| 新增 1 个文件 | 30-60 秒 | 2-5 秒 |
| 修改 1 个文件 | 30-60 秒 | 3-6 秒 |
| 删除 1 个文件 | 30-60 秒 | <1 秒 |
| 无变化 | 30-60 秒 | <1 秒 |

## 迁移指南

从旧版本迁移到新版本：

1. 备份现有数据
   cp -r /mnt/f/RAG_Project/chroma_db /mnt/f/RAG_Project/chroma_db.backup

2. 首次运行全量扫描
   python auto_ingest_v2.py --full-scan

3. 后续使用增量模式
   python auto_ingest_v2.py

## 故障排除

### 问题 1：状态文件损坏

症状：启动时报错 JSON decode error

解决：


### 问题 2：元数据未增强

症状：搜索时 doc_type 字段为空

解决：


### 问题 3：增量更新未生效

症状：文件修改后向量库未更新

解决：


## 下一步优化

Phase 2 优化建议：
1. 混合检索（向量 + BM25）
2. 重排序（Reranking）
3. 查询扩展（Query Expansion）
