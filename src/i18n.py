"""
DSB Tournament · 国际化支持
"""
import json
import os
from fastapi import Request

I18N_DIR = os.path.join(os.path.dirname(__file__), "i18n")

# 默认翻译缓存
_translations = {}

def load_translations(lang: str = "zh") -> dict:
    """加载语言文件"""
    if lang in _translations:
        return _translations[lang]
    path = os.path.join(I18N_DIR, f"{lang}.json")
    if not os.path.exists(path):
        path = os.path.join(I18N_DIR, "en.json")
        if not os.path.exists(path):
            return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            _translations[lang] = json.load(f)
        return _translations[lang]
    except:
        return {}

def detect_language(request: Request) -> str:
    """从浏览器请求头检测语言"""
    accept = request.headers.get("accept-language", "")
    if "zh" in accept:
        return "zh"
    return "en"
