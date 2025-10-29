from flask import Blueprint, request
from utils import current_user
from utils.jwt import verify_auth
from utils.response import success, fail
from openai import OpenAI
from loguru import logger
import settings

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
        # 获取请求参数
        data = request.get_json()
        text = data.get("text", "").strip()
        target_language = data.get("target_language", "").strip() # 目标语言
        chat_model = data.get("llm", settings.OPENAI_MODEL).strip()

        # 初始化OpenAI客户端
        client = OpenAI(
            api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL
        )
        prompt = f"这是一个直播间的弹幕内容, 请将以下文本翻译成{target_language}，只返回翻译结果，不要添加任何解释或格式：\n\n{text}"
        # 调用OpenAI API
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
            }
        )
    except Exception as e:
        logger.error(f"翻译失败: {e}")
        return fail(f"翻译失败: {str(e)}", 500)
