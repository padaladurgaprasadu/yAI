import sqlite3
import os
import json
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class KnowledgeGraphStore:
    def __init__(self, db_path="knowledge_graph.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS project_memory (
                        project_id TEXT,
                        key TEXT,
                        value TEXT,
                        PRIMARY KEY (project_id, key)
                    )
                ''')
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize Knowledge Graph DB: {e}")

    def store_knowledge(self, project_id: str, key: str, value: dict):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO project_memory (project_id, key, value)
                    VALUES (?, ?, ?)
                ''', (project_id, key, json.dumps(value)))
                conn.commit()
                logger.info(f"Knowledge Graph: Stored {key} for {project_id}")
        except Exception as e:
            logger.error(f"Failed to store knowledge: {e}")

    def get_knowledge(self, project_id: str) -> dict:
        knowledge = {}
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT key, value FROM project_memory WHERE project_id = ?
                ''', (project_id,))
                rows = cursor.fetchall()
                for key, value in rows:
                    knowledge[key] = json.loads(value)
        except Exception as e:
            logger.error(f"Failed to retrieve knowledge: {e}")
        return knowledge
