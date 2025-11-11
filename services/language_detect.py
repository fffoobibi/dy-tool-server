"""
语言检测服务

提供多种语言检测方法：
1. 基于正则表达式的中文字符统计（快速、准确）
2. 基于 FastText 的机器学习检测（准确率高、支持多语言）
"""

import re
import warnings
from pathlib import Path
from loguru import logger
from typing import Dict, Optional, Tuple

# 抑制 NumPy 兼容性警告
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*np.array.*copy.*")

import fasttext

__all__ = ["LanguageDetectService"]


class LanguageDetectService:
    """语言检测服务类"""

    # 全局变量存储 fasttext 模型
    _fasttext_model = None

    @classmethod
    def get_fasttext_model(cls):
        """
        懒加载 FastText 模型

        Returns:
            FastText 模型实例，如果加载失败返回 None
        """
        if cls._fasttext_model is None:
            try:
                # 模型文件路径：项目根目录/.models/lid.176.bin
                model_path = Path(__file__).parent.parent / ".models" / "lid.176.bin"

                # 检查模型是否存在
                if not model_path.exists():
                    logger.error(f"FastText 模型不存在: {model_path}")
                    logger.error(
                        "请将 lid.176.bin 模型文件放置到项目根目录的 .models/ 文件夹下"
                    )
                    return None

                # 加载模型
                logger.info(f"正在加载 FastText 模型: {model_path}")
                cls._fasttext_model = fasttext.load_model(str(model_path))
                logger.info("FastText 模型加载成功")
            except Exception as e:
                logger.error(f"加载 FastText 模型失败: {e}")
                cls._fasttext_model = None

        return cls._fasttext_model

    @staticmethod
    def is_chinese_text(text: str, threshold: float = 0.5) -> Tuple[bool, float]:
        """
        检测文本是否为中文（基于字符统计）

        Args:
            text: 待检测文本
            threshold: 中文字符比例阈值，默认0.5（50%）

        Returns:
            (是否为中文, 中文字符比例)
        """
        if not text:
            return False, 0.0

        # 匹配中文字符（包括中文标点）
        chinese_pattern = re.compile(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]")
        chinese_chars = chinese_pattern.findall(text)

        # 计算中文字符比例
        total_chars = len(text.replace(" ", "").replace("\n", "").replace("\t", ""))
        if total_chars == 0:
            return False, 0.0

        chinese_ratio = len(chinese_chars) / total_chars
        is_chinese = chinese_ratio >= threshold

        return is_chinese, chinese_ratio

    @classmethod
    def detect_language_with_fasttext(cls, text: str) -> Tuple[Optional[str], float]:
        """
        使用 FastText 检测语言

        Args:
            text: 待检测文本

        Returns:
            (语言代码, 置信度)，如果失败返回 (None, 0.0)
        """
        try:
            model = cls.get_fasttext_model()
            if model is None:
                return None, 0.0

            # FastText 需要替换换行符
            text_clean = text.replace("\n", " ").replace("\r", " ")

            # 预测语言，返回格式: (('__label__zh',), array([0.99]))
            predictions = model.predict(text_clean, k=1)
            lang_label = predictions[0][0].replace("__label__", "")
            confidence = float(predictions[1][0])

            logger.debug(f"FastText 检测: {lang_label}, 置信度: {confidence:.4f}")
            return lang_label, confidence
        except Exception as e:
            logger.warning(f"FastText 语言检测失败: {e}")
            return None, 0.0

    @classmethod
    def is_chinese_comprehensive(cls, text: str) -> Dict:
        """
        综合判断文本是否为中文

        策略：
        1. 先用字符统计快速判断（is_chinese_text）
        2. 如果不是中文，再用 FastText 二次判断

        Args:
            text: 待检测文本

        Returns:
            {
                "is_chinese": bool,
                "method": str,  # "regex" 或 "fasttext" 或 "both_negative"
                "chinese_ratio": float,  # 字符统计的中文比例
                "fasttext_lang": str,  # FastText 检测的语言
                "fasttext_confidence": float  # FastText 置信度
            }
        """
        result = {
            "is_chinese": False,
            "method": None,
            "chinese_ratio": 0.0,
            "fasttext_lang": None,
            "fasttext_confidence": 0.0,
        }

        # 第一步：字符统计判断
        # is_zh_regex, zh_ratio = cls.is_chinese_text(text, threshold=0.5)
        # result["chinese_ratio"] = zh_ratio

        # if is_zh_regex:
        #     # 字符统计判定为中文，直接返回
        #     result["is_chinese"] = True
        #     result["method"] = "regex"
        #     logger.info(f"字符统计判定为中文(占比: {zh_ratio:.2%})")
        #     return result

        # 第二步：字符统计不是中文，使用 FastText 二次判断
        # logger.info(
        #     f"字符统计判定为非中文(中文占比: {zh_ratio:.2%})，使用 FastText 二次判断"
        # )
        fasttext_lang, fasttext_conf = cls.detect_language_with_fasttext(text)
        result["fasttext_lang"] = fasttext_lang
        result["fasttext_confidence"] = fasttext_conf

        # FastText 判断为中文（置信度 > 0.7）
        if fasttext_lang == "zh" and fasttext_conf > 0.7:
            result["is_chinese"] = True
            result["method"] = "fasttext"
            logger.info(f"FastText 判定为中文(置信度: {fasttext_conf:.4f})")
        else:
            result["is_chinese"] = False
            result["method"] = "both_negative"
            logger.info(
                f"综合判定为非中文 (FastText: {fasttext_lang}, 置信度: {fasttext_conf:.4f})"
            )

        return result

    @classmethod
    def detect_language(cls, text: str, target_language: Optional[str] = None) -> Dict:
        """
        通用语言检测方法

        Args:
            text: 待检测文本
            target_language: 目标语言（可选），如果提供且为中文，会使用综合检测

        Returns:
            语言检测结果字典
        """
        if not text:
            return {
                "is_chinese": False,
                "method": "empty",
                "chinese_ratio": 0.0,
                "fasttext_lang": None,
                "fasttext_confidence": 0.0,
            }

        # 如果目标语言是中文，使用综合检测
        if target_language and target_language.lower() in [
            "中文",
            "chinese",
            "zh",
            "zh-cn",
            "中",
        ]:
            return cls.is_chinese_comprehensive(text)

        # 否则只用 FastText 检测
        lang, conf = cls.detect_language_with_fasttext(text)
        return {
            "is_chinese": lang == "zh",
            "method": "fasttext",
            "chinese_ratio": 0.0,
            "fasttext_lang": lang,
            "fasttext_confidence": conf,
        }
