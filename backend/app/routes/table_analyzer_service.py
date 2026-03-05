import re
import logging
from typing import List, Dict, Optional, Tuple, Any
import sqlparse
import pymysql
from humanize import naturalsize
from ..models import Instance

logger = logging.getLogger(__name__)


class tableAnalyzerService:
    
    def __init__(self):
        self.timeout = 15
        self.max_sample_rows = 50
        self.max_tables = 10
    
    def mysql_connection(self, instance: Instance, database: str):
        return pymysql.connect(
            host=instance.host,
            port=instance.port or 3306,
            user=instance.username or '',
            password=instance.password or '',
            database=database,
            charset='utf8mb4',
            connect_timeout=self.timeout,
            read_timeout=self.timeout,
            write_timeout=self.timeout,
            cursorclass=pymysql.cursors.DictCursor
        )

    def extract_table_names(self, sql: str):
        try:
            tables = set()
            
            patterns = [
                r'FROM\s+`?(\w+)`?',
                r'JOIN\s+`?(\w+)`?',
                r'UPDATE\s+`?(\w+)`?',
                r'INTO\s+`?(\w+)`?',
                r'TABLE\s+`?(\w+)`?',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, sql, re.IGNORECASE)
                for table_name in matches:
                    if table_name.upper() not in ('SELECT', 'WHERE', 'SET', 'VALUES', 'ON', 'AND', 'OR', 'LIMIT'):
                        tables.add(table_name)
            
            return list(tables)
            
        except Exception as e:
            logger.warning(f"解析SQL表名失败: {e}")
            return []

    def getExplain(self, instance: Instance, database: str, sql: str):          
        conn = None
        try:
            conn = self.mysql_connection(instance, database)
            
            with conn.cursor() as cursor:
                cursor.execute(f"EXPLAIN {sql}")
                traditional_plan = cursor.fetchall()
            
            return traditional_plan

        except Exception as e:
            logger.error(f"获取执行计划失败: {e}")
            return False, {}, f"执行计划获取失败: {e}"
        finally:
            try:
                if conn:
                    conn.close()
            except Exception:
                pass

    def getTableMetadata(self, instance, database, table_name):
        conn = None
        try:
            conn = self.mysql_connection(instance, database)
            
            result = {
                'table_name': table_name,
                'columns': [],
                'indexes': [],
                'table_rows_approx': None,
                'primary_key': []
            }
            
            with conn.cursor() as cursor:
                try:
                    cursor.execute(
                        """
                        SELECT ENGINE, TABLE_ROWS, DATA_LENGTH, INDEX_LENGTH, 
                               AVG_ROW_LENGTH, TABLE_COLLATION, CREATE_TIME, UPDATE_TIME
                        FROM information_schema.TABLES
                        WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s
                        """,
                        (database, table_name)
                    )
                    table_info = cursor.fetchone()
                    if table_info:
                        result['table_rows_approx'] = table_info.get('TABLE_ROWS')
                except Exception as e:
                    logger.warning(f"获取表基础信息失败: {e}")

                try:
                    cursor.execute(f"DESCRIBE `{table_name}`")
                    columns = cursor.fetchall()
                    result['columns'] = [
                        {
                            'name': col['Field'],
                            'type': col['Type'],
                            'null': col['Null'],
                            'key': col['Key']
                        }
                        for col in columns
                    ]
                    primary_key_columns = []
                    for col in columns:
                        key_type = col.get('Key') or ''
                        if key_type.upper() == 'PRI':
                            primary_key_columns.append(col['Field'])
                    result['primary_key'] = primary_key_columns
                except Exception as e:
                    logger.warning(f"获取表列信息失败: {e}")
                
                try:
                    cursor.execute(f"SHOW INDEX FROM `{table_name}`")
                    indexes = cursor.fetchall()
                    index_dict = {}
                    for idx in indexes:
                        key_name = idx['Key_name']
                        if key_name not in index_dict:
                            index_dict[key_name] = {
                                'name': key_name,
                                'unique': not bool(idx['Non_unique']),
                                'columns': [],
                                'index_type': None
                            }
                        
                        index_dict[key_name]['columns'].append(idx['Column_name'])
                        
                        if idx.get('Index_type') and not index_dict[key_name].get('index_type'):
                            index_dict[key_name]['index_type'] = idx.get('Index_type')
                    
                    result['indexes'] = list(index_dict.values())
                    
                except Exception as e:
                    logger.warning(f"获取表索引信息失败: {e}")

            return True, result, ""
            
        except Exception as e:
            logger.error(f"获取表 {table_name} 元信息失败: {e}")
            return False, {}, f"元信息获取失败: {e}"
        finally:
            try:
                if conn:
                    conn.close()
            except Exception:
                pass


table_analyzer_service = tableAnalyzerService()
