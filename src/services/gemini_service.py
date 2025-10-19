"""
Gemini AI Service для рерайта текстов RSS постов.
Простая функция для рерайта текста с использованием Gemini Flash Latest.
"""

import logging
from typing import Optional

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

logger = logging.getLogger(__name__)


async def rewrite_with_gemini(
    text: str,
    api_key: str,
    custom_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048
) -> str:
    """
    Простая функция для рерайта текста с использованием Gemini Flash Latest.
    
    Args:
        text: Исходный текст для рерайта
        api_key: API ключ Google Gemini
        custom_prompt: Кастомный промпт (опционально)
        temperature: Температура генерации (0.0-2.0), по умолчанию 0.7
        max_tokens: Максимальное количество токенов, по умолчанию 2048
        
    Returns:
        Рерайченный текст
        
    Raises:
        ImportError: Если библиотека google-genai не установлена
        Exception: При ошибках API
    """
    if genai is None:
        raise ImportError(
            "Библиотека google-genai не установлена. "
            "Установите: pip install google-genai"
        )
    
    # Дефолтный промпт для рерайта RSS новостей
    if custom_prompt is None:
        custom_prompt = """
        As a rewriting expert, your task is to improve the clarity and conciseness of the provided text. This will involve assessing the existing content, identifying areas that can be simplified or clarified, and restructuring sentences where necessary. Make sure you maintain the original meaning while reducing verbosity and ensuring the text is easy to understand. The final product should be a clear, concise, and coherent version of the original text. think english, answer russian. 
        """
    
    try:
        # Инициализация клиента
        client = genai.Client(api_key=api_key)
        
        # Формируем полный промпт
        full_prompt = f"{custom_prompt}\n\nИсходный текст:\n{text}\n\nРерайченный текст:"
        
        # Настройки генерации для Gemini Flash Latest
        gen_config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            top_p=0.95,
            top_k=40,
        )
        
        # Генерация
        response = client.models.generate_content(
            model='gemini-2.0-flash-001',  # Latest Flash model
            contents=full_prompt,
            config=gen_config
        )
        
        rewritten_text = response.text.strip()
        
        # Логируем статистику использования
        if hasattr(response, 'usage_metadata'):
            logger.info(
                f"Gemini рерайт: {response.usage_metadata.total_token_count} токенов"
            )
        
        logger.debug(f"Текст успешно рерайчен: {len(text)} -> {len(rewritten_text)} символов")
        
        return rewritten_text
        
    except Exception as e:
        logger.error(f"Ошибка при рерайте с Gemini: {e}", exc_info=True)
        # В случае ошибки возвращаем оригинальный текст
        logger.warning("Возвращаем оригинальный текст из-за ошибки")
        return text
