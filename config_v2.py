"""
配置加载器 v2 — 支持增量更新和元数据增强

新增配置：
1. incremental: 增量更新配置
2. metadata: 元数据增强配置
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict

# 默认配置（全部硬编码的后备值）
DEFAULT_CONFIG = {
    "paths": {
        "data_dir": "data",
        "persist_dir": "/mnt/f/RAG_Project/chroma_db",
        "skills_dir": "skills",
        "state_file": "incremental_state.json",
    },
    "models": {
        "embedding": "nomic-embed-text",
        "chat": "gemma4:26b",
        "temperature": 0,
    },
    "retrieval": {
        "k": 5,
        "score_threshold": 0.0,
        "chunk_size": 800,
        "chunk_overlap": 100,
    },
    "chat": {
        "max_history": 10,
        "system_prompt": "",
    },
    "auto_ingest": {
        "enabled": True,
        "debounce_seconds": 3,
        "supported_extensions": [".txt", ".pdf", ".md", ".docx", ".xlsx"],
    },
    "incremental": {
        "enabled": True,
        "state_file": "incremental_state.json",
        "full_scan_on_start": True,
    },
    "metadata": {
        "enabled": True,
        "enrich_on_ingest": True,
        "extract_keywords": True,
        "extract_dates": True,
        "extract_amounts": True,
        "max_keywords": 10,
    },
    "skill_learning": {
        "enabled": True,
        "min_rating": 4,
        "auto_save": False,
    },
    "ollama": {
        "base_url": "http://localhost:11434",
        "timeout": 120,
    },
}

# 环境变量映射 (env_var -> config_dotpath)
ENV_OVERRIDES = {
    "RAG_DATA_DIR": "paths.data_dir",
    "RAG_PERSIST_DIR": "paths.persist_dir",
    "RAG_EMBEDDING_MODEL": "models.embedding",
    "RAG_CHAT_MODEL": "models.chat",
    "RAG_TEMPERATURE": "models.temperature",
    "RAG_RETRIEVAL_K": "retrieval.k",
    "RAG_CHUNK_SIZE": "retrieval.chunk_size",
    "RAG_CHUNK_OVERLAP": "retrieval.chunk_overlap",
    "RAG_MAX_HISTORY": "chat.max_history",
    "OLLAMA_BASE_URL": "ollama.base_url",
    "INCREMENTAL_ENABLED": "incremental.enabled",
    "METADATA_ENABLED": "metadata.enabled",
}


def _deep_merge(base: dict, override: dict) -> dict:
    """递归合并两个字典"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _set_dotpath(config: dict, dotpath: str, value: Any):
    """通过 'a.b.c' 路径设置嵌套字典值"""
    keys = dotpath.split(".")
    current = config
    for key in keys[:-1]:
        current = current.setdefault(key, {})
    # 类型转换
    current_key = keys[-1]
    existing = current.get(current_key)
    if isinstance(existing, int):
        value = int(value)
    elif isinstance(existing, float):
        value = float(value)
    elif isinstance(existing, bool):
        value = value.lower() in ("true", "1", "yes")
    current[current_key] = value


def load_config(config_path: str = None) -> dict:
    """
    加载配置：合并 默认值 → YAML 文件 → 环境变量

    Args:
        config_path: 配置文件路径，默认为项目根目录的 config.yaml

    Returns:
        合并后的配置字典
    """
    # 1. 从默认值开始
    config = DEFAULT_CONFIG.copy()

    # 2. 加载 YAML 文件
    if config_path is None:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")

    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f) or {}
        config = _deep_merge(config, yaml_config)

    # 3. 应用环境变量覆盖
    for env_var, dotpath in ENV_OVERRIDES.items():
        value = os.environ.get(env_var)
        if value is not None:
            _set_dotpath(config, dotpath, value)

    return config


def get_config_value(config: dict, dotpath: str, default=None) -> Any:
    """通过 'a.b.c' 路径获取嵌套字典值"""
    keys = dotpath.split(".")
    current = config
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


# 兼容旧代码的 CONFIG 字典格式
def get_legacy_config(config: dict = None) -> dict:
    """将新格式配置转换为 rag_chat_bot.py 使用的旧格式 CONFIG"""
    if config is None:
        config = load_config()

    return {
        "persist_dir": config["paths"]["persist_dir"],
        "embedding_model": config["models"]["embedding"],
        "chat_model": config["models"]["chat"],
        "temperature": config["models"]["temperature"],
        "retrieval_k": config["retrieval"]["k"],
        "score_threshold": config["retrieval"]["score_threshold"],
        "max_history": config["chat"]["max_history"],
    }


def get_incremental_config(config: dict = None) -> dict:
    """获取增量更新配置"""
    if config is None:
        config = load_config()

    return {
        "enabled": config["incremental"]["enabled"],
        "state_file": os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            config["incremental"]["state_file"]
        ),
        "full_scan_on_start": config["incremental"]["full_scan_on_start"],
    }


def get_metadata_config(config: dict = None) -> dict:
    """获取元数据增强配置"""
    if config is None:
        config = load_config()

    return {
        "enabled": config["metadata"]["enabled"],
        "enrich_on_ingest": config["metadata"]["enrich_on_ingest"],
        "extract_keywords": config["metadata"]["extract_keywords"],
        "extract_dates": config["metadata"]["extract_dates"],
        "extract_amounts": config["metadata"]["extract_amounts"],
        "max_keywords": config["metadata"]["max_keywords"],
    }


if __name__ == "__main__":
    # 测试配置加载
    config = load_config()
    
    print("=== 配置测试 ===")
    print(f"向量库路径: {config['paths']['persist_dir']}")
    print(f"增量更新: {config['incremental']['enabled']}")
    print(f"元数据增强: {config['metadata']['enabled']}")
    print(f"状态文件: {config['incremental']['state_file']}")
