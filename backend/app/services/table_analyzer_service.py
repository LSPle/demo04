import re
import logging
from typing import List, Dict, Optional, Tuple, Any
# sqlparse 是解析和分析 SQL 语句的 Python 第三方库
import sqlparse
# pymysql用于连接 MySQL
import pymysql
# naturalsize 是 humanize 库中的一个函数，用于将字节大小转换为更易读的格式
from humanize import naturalsize
from ..models import Instance
from ..utils.db_connection import db_connection_manager

"""表数据采样和分析服务：解析SQL中的表名，采样数据，生成执行计划"""

logger = logging.getLogger(__name__)


class tableAnalyzerService:
    
    #限制：最多分析的表数量
    def __init__(self):
        self.timeout = 15          # 秒
        self.max_sample_rows = 50  # 默认最大采样行数
        self.max_tables = 10       # 最多分析的表数量
    
    #  连接MySQL数据库
    def mysql_connection(self, instance: Instance, database: str):
        return db_connection_manager.create_connection(
            instance,
            database=database,
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=self.timeout,
            read_timeout=self.timeout,
            write_timeout=self.timeout
        )

    #  从SQL中提取表名,返回: 表名列表（去重）
    def extract_table_names(self, sql: str):
        try:
            tables = set()
            
            # 简单的正则匹配常见SQL模式
            # 匹配 FROM table, JOIN table, UPDATE table, INSERT INTO table
            # 增加 TABLE table 匹配 (覆盖 TRUNCATE/DROP/ALTER/CREATE TABLE)
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
                    # 排除 SQL 关键字误判 (简单过滤)
                    if table_name.upper() not in ('SELECT', 'WHERE', 'SET', 'VALUES', 'ON', 'AND', 'OR', 'LIMIT'):
                        tables.add(table_name)
            
            return list(tables)
            
        except Exception as e:
            logger.warning(f"解析SQL表名失败: {e}")
            return []

    #采样表数据和结构信息
    # def sample_table_data(self, instance: Instance, database: str, table_name: str, sample_rows: int = None):
        
    #     if not sample_rows:
    #         sample_rows = self.max_sample_rows
            
        
    #     conn = None
    #     try:
    #         # 使用统一连接方法，去除重复代码
    #         conn = self.mysql_connection(instance, database)
            
    #         # 初始化表分析结果字典，包含表的各种元数据信息
    #         result = {
    #             'table_name': table_name,
    #             'columns': [],
    #             'indexes': [],
    #             'table_rows_approx': None,
    #             'primary_key': []
    #         }
            
    #         with conn.cursor() as cursor:
    #             # 0. 表状态信息（引擎、大小、行数估计）
    #             try:
    #                 cursor.execute(
    #                     """
    #                     SELECT ENGINE, TABLE_ROWS, DATA_LENGTH, INDEX_LENGTH
    #                     FROM information_schema.TABLES
    #                     WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s
    #                     """,
    #                     (database, table_name)
    #                 )
    #                 tbl = cursor.fetchone()
    #                 if tbl:
    #                     result['table_rows_approx'] = tbl.get('TABLE_ROWS')
    #             except Exception:
    #                 pass

    #             # 1. 获取表结构
    #             cursor.execute(f"DESCRIBE `{table_name}`")
    #             columns = cursor.fetchall()
    #             result['columns'] = [
    #                 {
    #                     'name': col['Field'],
    #                     'type': col['Type'],
    #                     'null': col['Null'],
    #                     'key': col['Key']
    #                 }
    #                 for col in columns
    #             ]
    #             # 查找主键列
    #             primary_keys = []
    #             for col in columns:
    #                 key_type = col.get('Key') or ''
    #                 if key_type.upper() == 'PRI':
    #                     primary_keys.append(col['Field'])
    #             result['primary_key'] = primary_keys
                
                
                
    #             # 4. 获取索引信息（含列、唯一性、基数、类型）
    #             cursor.execute(f"SHOW INDEX FROM `{table_name}`")
    #             indexes = cursor.fetchall()
    #             index_dict: Dict[str, Dict[str, Any]] = {}
    #             for idx in indexes:
    #                 key_name = idx['Key_name']
    #                 if key_name not in index_dict:
    #                     index_dict[key_name] = {
    #                         'name': key_name,
    #                         'unique': not bool(idx['Non_unique']),
    #                         'columns': [],
    #                         'cardinality': None,
    #                         'index_type': None
    #                     }
    #                 index_dict[key_name]['columns'].append(idx['Column_name'])
    #                 # 以最大Cardinality为整体索引基数（粗略）
    #                 card = idx.get('Cardinality')
    #                 if card is not None:
    #                     prev = index_dict[key_name].get('cardinality')
    #                     index_dict[key_name]['cardinality'] = max(prev or 0, card)
    #                 if idx.get('Index_type') and not index_dict[key_name].get('index_type'):
    #                     index_dict[key_name]['index_type'] = idx.get('Index_type')
                
    #             result['indexes'] = list(index_dict.values())
    #         return True, result, ""
            
    #     except Exception as e:
    #         logger.error(f"采样表 {table_name} 失败: {e}")
    #         return False, {}, f"采样失败: {e}"
    #     finally:
    #         try:
    #             if conn:
    #                 conn.close()
    #         except Exception:
    #             pass
    
    #获取SQL的EXPLAIN执行计划
    def getExplain(self, instance: Instance, database: str, sql: str):          
        conn = None
        try:
            # 使用统一连接方法，去除重复代码
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

   
    
    # 仅获取表的元信息，不进行数据采样
    def getTableMetadata(self, instance, database, table_name):
        conn = None
        try:
            conn = self.mysql_connection(instance, database)
            
            # 初始化表元数据结果字典，包含表的完整结构和统计信息
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

                # 2. 获取表的列信息
                try:
                    cursor.execute(f"DESCRIBE `{table_name}`")
                    columns = cursor.fetchall()
                    # 构建列信息字典列表，包含每列的详细属性
                    result['columns'] = [
                        {
                            'name': col['Field'],
                            'type': col['Type'],
                            'null': col['Null'],
                            'key': col['Key']
                        }
                        for col in columns
                    ]
                    # 提取主键列名列表
                    primary_key_columns = []
                    for col in columns:
                        # 获取列的键类型，如果为空则设为空字符串
                        key_type = col.get('Key') or ''
                        # 检查是否为主键（PRI表示PRIMARY KEY）
                        if key_type.upper() == 'PRI':
                            primary_key_columns.append(col['Field'])
                    result['primary_key'] = primary_key_columns
                except Exception as e:
                    logger.warning(f"获取表列信息失败: {e}")
                
                # 3. 获取表的索引信息
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
                        
                        # 将当前列添加到索引的列列表中
                        index_dict[key_name]['columns'].append(idx['Column_name'])
                        
                        # 设置索引类型（如果还没有设置的话）
                        if idx.get('Index_type') and not index_dict[key_name].get('index_type'):
                            index_dict[key_name]['index_type'] = idx.get('Index_type')
                        
                        
                    
                    # 将索引字典转换为列表
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




# 全局实例
table_analyzer_service = tableAnalyzerService()
