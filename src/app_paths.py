"""Спільні шляхи до ресурсів і кешу Hugging Face (без захардкоджених дисків)."""
import os
import sys


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def hf_hub_cache_dir() -> str:
    """Каталог знімків Hugging Face Hub: у збірці — поруч із бандлом; у розробці — env або стандартний кеш."""
    if is_frozen():
        return os.path.join(sys._MEIPASS, "transformers_cache")  # type: ignore[attr-defined]
    override = (os.environ.get("HUGGINGFACE_HUB_CACHE") or "").strip()
    if override:
        return override
    hf_home = os.environ.get("HF_HOME") or os.path.join(
        os.path.expanduser("~"), ".cache", "huggingface"
    )
    return os.path.join(hf_home, "hub")
