from flask import Blueprint, request
from utils.jwt import verify_auth
from utils.response import success, fail
from openai import OpenAI
from loguru import logger
import settings
from services.language_detect import LanguageDetectService

bp = Blueprint("translate", __name__)


@bp.before_request
def verify():
    verify_auth()


@bp.post("/create")
def translate():
    """文本翻译接口
    ---
    tags:
      - translate
    summary: 使用LLM进行文本翻译
    description: 将输入的文本翻译成指定的目标语言
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - text
            - target_language
            - llm
          properties:
            text:
              type: string
              description: 需要翻译的文本
              example: "Hello, how are you?"
            target_language:
              type: string
              description: 目标语言(如：中文、英文、日文、法文等)
              example: "中文"
            llm:
                type: string
                description: 使用的语言模型
                example: "gpt-4o"
    responses:
      200:
        description: 翻译成功
        schema:
          type: object
          properties:
            code:
              type: integer
              example: 200
            msg:
              type: string
              example: "success"
            resp:
              type: object
              properties:
                original_text:
                  type: string
                  description: 原始文本
                translated_text:
                  type: string
                  description: 翻译后的文本
                target_language:
                  type: string
                  description: 目标语言
    """
    try:
        data = request.get_json()
        text = data.get("text", "").strip()
        target_language = data.get("target_language", "").strip()  # 目标语言
        chat_model = data.get("llm", settings.OPENAI_MODEL).strip()

        if not text:
            return fail("文本不能为空", 400)

        if target_language.lower() in ["中文", "chinese", "zh", "zh-cn", "中"]:
            # 综合检测原始文本是否为中文
            detection_result = LanguageDetectService.is_chinese_comprehensive(text)
            is_zh = detection_result["is_chinese"]
            logger.debug(
                f"语言检测结果: is_chinese={is_zh}, method={detection_result['method']}, "
                f"chinese_ratio={detection_result['chinese_ratio']:.2%}, "
                f"fasttext_lang={detection_result['fasttext_lang']}, "
                f"fasttext_confidence={detection_result['fasttext_confidence']:.4f}"
            )
            if is_zh:
                logger.debug(f"原文已经是中文，无需翻译")
                return success(
                    resp={
                        "original_text": text,
                        "translated_text": text,
                        "target_language": target_language,
                        "detection": detection_result,
                        "skipped": True,
                        "reason": "原文已经是中文",
                    }
                )

        client = OpenAI(
            api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL
        )
        prompt = f"这是一个直播间的弹幕内容, 请将以下文本翻译成{target_language}，只返回翻译结果，不要添加任何解释或格式：\n\n{text}"
        response = client.chat.completions.create(
            model=chat_model,
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的翻译助手，请准确翻译用户提供的文本。",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=2000,
            temperature=0.3,  # 降低随机性，提高翻译一致性
        )
        # 获取翻译结果
        translated_text = response.choices[0].message.content.strip()
        return success(
            resp={
                "original_text": text,
                "translated_text": translated_text,
                "target_language": target_language,
                "detection": detection_result,
                "skipped": False,
            }
        )
    except Exception as e:
        logger.error(f"翻译失败: {e}")
        return fail(f"翻译失败: {str(e)}", 500)
