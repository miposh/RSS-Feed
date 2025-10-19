"""
Repository для работы с промптами Gemini в базе данных.
"""

import logging
from typing import Optional, List, Dict, Any

from repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class GeminiPromptRepository(BaseRepository):
    """Репозиторий для управления промптами Gemini"""

    async def create_prompt(
        self,
        name: str,
        prompt_text: str,
        description: Optional[str] = None,
        model: str = "gemini-2.0-flash-001",
        temperature: float = 0.7,
        max_output_tokens: int = 2048,
        top_p: float = 0.95,
        top_k: int = 40,
        response_format: str = "text",
        system_instruction: Optional[str] = None,
        is_chain: bool = False,
        chain_order: Optional[int] = None,
        parent_chain_id: Optional[int] = None,
        created_by: Optional[int] = None
    ) -> int:
        """
        Создание нового промпта.
        
        Returns:
            ID созданного промпта
        """
        query = """
            INSERT INTO gemini_prompts (
                name, prompt_text, description, model, temperature,
                max_output_tokens, top_p, top_k, response_format,
                system_instruction, is_chain, chain_order, 
                parent_chain_id, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        async with self.transaction() as cursor:
            await cursor.execute(query, (
                name, prompt_text, description, model, temperature,
                max_output_tokens, top_p, top_k, response_format,
                system_instruction, 1 if is_chain else 0, chain_order,
                parent_chain_id, created_by
            ))
            prompt_id = cursor.lastrowid
            
        logger.info(f"Создан новый промпт: {name} (ID: {prompt_id})")
        return prompt_id

    async def get_prompt_by_id(self, prompt_id: int) -> Optional[Dict[str, Any]]:
        """Получение промпта по ID"""
        query = "SELECT * FROM gemini_prompts WHERE id = ?"
        
        async with self.connection() as conn:
            cursor = await conn.execute(query, (prompt_id,))
            row = await cursor.fetchone()
            
        if row:
            return self._row_to_dict(row)
        return None

    async def get_prompt_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Получение промпта по имени"""
        query = "SELECT * FROM gemini_prompts WHERE name = ?"
        
        async with self.connection() as conn:
            cursor = await conn.execute(query, (name,))
            row = await cursor.fetchone()
            
        if row:
            return self._row_to_dict(row)
        return None

    async def list_prompts(
        self,
        is_chain: Optional[bool] = None,
        created_by: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Получение списка промптов с фильтрацией.
        
        Args:
            is_chain: Фильтр по цепочкам
            created_by: Фильтр по создателю
            limit: Максимальное количество результатов
            
        Returns:
            Список промптов
        """
        query = "SELECT * FROM gemini_prompts WHERE 1=1"
        params = []
        
        if is_chain is not None:
            query += " AND is_chain = ?"
            params.append(1 if is_chain else 0)
        
        if created_by is not None:
            query += " AND created_by = ?"
            params.append(created_by)
        
        query += " ORDER BY usage_count DESC, created_at DESC LIMIT ?"
        params.append(limit)
        
        async with self.connection() as conn:
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            
        return [self._row_to_dict(row) for row in rows]

    async def get_chain_prompts(self, parent_chain_id: int) -> List[Dict[str, Any]]:
        """
        Получение всех промптов в цепочке.
        
        Args:
            parent_chain_id: ID родительской цепочки
            
        Returns:
            Список промптов, отсортированных по chain_order
        """
        query = """
            SELECT * FROM gemini_prompts 
            WHERE parent_chain_id = ? 
            ORDER BY chain_order ASC
        """
        
        async with self.connection() as conn:
            cursor = await conn.execute(query, (parent_chain_id,))
            rows = await cursor.fetchall()
            
        return [self._row_to_dict(row) for row in rows]

    async def update_prompt(
        self,
        prompt_id: int,
        **kwargs
    ) -> bool:
        """
        Обновление промпта.
        
        Args:
            prompt_id: ID промпта
            **kwargs: Поля для обновления
            
        Returns:
            True если обновление успешно
        """
        allowed_fields = {
            'name', 'prompt_text', 'description', 'model', 'temperature',
            'max_output_tokens', 'top_p', 'top_k', 'response_format',
            'system_instruction', 'is_chain', 'chain_order', 'parent_chain_id'
        }
        
        fields_to_update = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not fields_to_update:
            logger.warning("Нет полей для обновления")
            return False
        
        # Преобразуем булевы значения
        if 'is_chain' in fields_to_update:
            fields_to_update['is_chain'] = 1 if fields_to_update['is_chain'] else 0
        
        set_clause = ", ".join([f"{k} = ?" for k in fields_to_update.keys()])
        values = list(fields_to_update.values()) + [prompt_id]
        
        query = f"UPDATE gemini_prompts SET {set_clause} WHERE id = ?"
        
        async with self.transaction() as cursor:
            await cursor.execute(query, values)
            
        logger.info(f"Промпт {prompt_id} обновлен")
        return True

    async def delete_prompt(self, prompt_id: int) -> bool:
        """Удаление промпта"""
        query = "DELETE FROM gemini_prompts WHERE id = ?"
        
        async with self.transaction() as cursor:
            await cursor.execute(query, (prompt_id,))
            
        logger.info(f"Промпт {prompt_id} удален")
        return True

    async def increment_usage(self, prompt_id: int) -> None:
        """Увеличение счетчика использования промпта"""
        query = "UPDATE gemini_prompts SET usage_count = usage_count + 1 WHERE id = ?"
        
        async with self.transaction() as cursor:
            await cursor.execute(query, (prompt_id,))

    async def save_history(
        self,
        prompt_id: int,
        chat_id: int,
        user_id: Optional[int],
        input_text: str,
        output_text: str,
        tokens_used: Optional[int] = None,
        execution_time_ms: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> int:
        """
        Сохранение истории использования промпта.
        
        Returns:
            ID записи истории
        """
        query = """
            INSERT INTO gemini_prompt_history (
                prompt_id, chat_id, user_id, input_text, output_text,
                tokens_used, execution_time_ms, success, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        async with self.transaction() as cursor:
            await cursor.execute(query, (
                prompt_id, chat_id, user_id, input_text, output_text,
                tokens_used, execution_time_ms, 1 if success else 0, error_message
            ))
            history_id = cursor.lastrowid
            
        return history_id

    async def get_prompt_history(
        self,
        prompt_id: Optional[int] = None,
        chat_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Получение истории использования промптов.
        
        Args:
            prompt_id: Фильтр по промпту
            chat_id: Фильтр по чату
            limit: Максимальное количество записей
            
        Returns:
            Список записей истории
        """
        query = "SELECT * FROM gemini_prompt_history WHERE 1=1"
        params = []
        
        if prompt_id is not None:
            query += " AND prompt_id = ?"
            params.append(prompt_id)
        
        if chat_id is not None:
            query += " AND chat_id = ?"
            params.append(chat_id)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        async with self.connection() as conn:
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            
        return [self._row_to_dict(row) for row in rows]

    async def get_usage_stats(self, prompt_id: int) -> Dict[str, Any]:
        """
        Получение статистики использования промпта.
        
        Returns:
            Dict со статистикой
        """
        query = """
            SELECT 
                COUNT(*) as total_uses,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_uses,
                SUM(tokens_used) as total_tokens,
                AVG(execution_time_ms) as avg_execution_time_ms
            FROM gemini_prompt_history
            WHERE prompt_id = ?
        """
        
        async with self.connection() as conn:
            cursor = await conn.execute(query, (prompt_id,))
            row = await cursor.fetchone()
            
        if row:
            return self._row_to_dict(row)
        
        return {
            'total_uses': 0,
            'successful_uses': 0,
            'total_tokens': 0,
            'avg_execution_time_ms': 0
        }

    async def search_prompts(self, search_term: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Поиск промптов по названию или описанию.
        
        Args:
            search_term: Строка поиска
            limit: Максимальное количество результатов
            
        Returns:
            Список найденных промптов
        """
        query = """
            SELECT * FROM gemini_prompts 
            WHERE name LIKE ? OR description LIKE ?
            ORDER BY usage_count DESC, created_at DESC
            LIMIT ?
        """
        
        search_pattern = f"%{search_term}%"
        
        async with self.connection() as conn:
            cursor = await conn.execute(query, (search_pattern, search_pattern, limit))
            rows = await cursor.fetchall()
            
        return [self._row_to_dict(row) for row in rows]

    def _row_to_dict(self, row) -> Dict[str, Any]:
        """Преобразование строки БД в словарь"""
        if not row:
            return {}
        
        keys = row.keys()
        result = dict(zip(keys, row))
        
        # Преобразуем булевы значения
        if 'is_chain' in result:
            result['is_chain'] = bool(result['is_chain'])
        if 'success' in result:
            result['success'] = bool(result['success'])
            
        return result
