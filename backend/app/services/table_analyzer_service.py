import re
import logging
from typing import List, Dict, Optional, Tuple, Any
import sqlparse
# from sqlparse.sql import IdentifierList, Identifier
from sqlparse.tokens import Keyword, DML
# import json
import pymysql
from humanize import naturalsize
from ..models import Instance

"""表数据采样和分析服务：解析SQL中的表名，采样数据，生成执行计划"""

logger = logging.getLogger(__name__)


class TableAnalyzerService:
    
    #限制：最多分析的表数量
    def __init__(self):
        self.timeout = 15          # 秒
        self.max_sample_rows = 50  # 默认最大采样行数
        self.max_tables = 10       # 最多分析的表数量

    def mysql_connection(self, instance: Instance, database: str):
        """
        统一的 MySQL 连接方法，避免在各函数中重复拼接连接参数。
        保持与原有连接参数一致，便于后续维护。
        """
        host = getattr(instance, 'host', '')
        port = getattr(instance, 'port', 3306)
        return pymysql.connect(
            host=host,
            port=port,
            user=instance.username or '',
            password=instance.password or '',
            database=database,
            charset='utf8mb4',
            connect_timeout=self.timeout,
            read_timeout=self.timeout,
            write_timeout=self.timeout,
            cursorclass=pymysql.cursors.DictCursor
        )

    #  从SQL中提取表名,返回: 表名列表（去重）
    def extract_table_names(self, sql: str):
        try:
            # 解析SQL
            parsed = sqlparse.parse(sql)
            if not parsed:
                return []
            
            tables = set()
            
            # 将SQL转换为字符串并用正则提取
            # 这样既用了sqlparse的解析能力，又保持代码简单
            for statement in parsed:
                sql_text = str(statement)
                
                # 用正则表达式找表名
                patterns = [
                    r'FROM\s+`?(\w+)`?',           # FROM table
                    r'JOIN\s+`?(\w+)`?',           # JOIN table  
                    r'UPDATE\s+`?(\w+)`?',         # UPDATE table
                    r'INTO\s+`?(\w+)`?',           # INSERT INTO table
                ]
                
                # 用每个模式去匹配表名
                for pattern in patterns:
                    matches = re.findall(pattern, sql_text, re.IGNORECASE)
                    # 把找到的表名加到集合里
                    for table_name in matches:
                        tables.add(table_name)
            
            # 转换为列表并返回
            result = list(tables)
            return result
            
        except Exception as e:
            logger.warning(f"解析SQL表名失败: {e}")
            return []

    #采样表数据和结构信息
    def sample_table_data(self, instance: Instance, database: str, table_name: str, sample_rows: int = None):
        
        if not sample_rows:
            sample_rows = self.max_sample_rows
            
        if not pymysql:
            return False, {}, "MySQL驱动不可用"
        
        try:
            # 使用统一连接方法，去除重复代码
            conn = self.mysql_connection(instance, database)
            
            # 初始化表分析结果字典，包含表的各种元数据信息
            result = {
                'table_name': table_name,           # 表名
                'columns': [],                      # 列信息列表，包含每列的名称、类型、是否为空等
                'sample_data': [],                  # 表的样本数据，用于预览表内容
                'row_count_estimate': 0,            # 表的估计行数
                'indexes': [],                      # 索引信息列表，包含索引名称、类型、列等
                # 新增的表级信息
                'engine': None,                     # 存储引擎
                'table_rows_approx': None,          # 表的近似行数（从information_schema获取）
                'data_length': None,                # 数据文件大小（字节）
                'index_length': None,               # 索引文件大小（字节）
                'primary_key': []                   # 主键列名列表
            }
            
            with conn.cursor() as cursor:
                # 0. 表状态信息（引擎、大小、行数估计）
                try:
                    cursor.execute(
                        """
                        SELECT ENGINE, TABLE_ROWS, DATA_LENGTH, INDEX_LENGTH
                        FROM information_schema.TABLES
                        WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s
                        """,
                        (database, table_name)
                    )
                    tbl = cursor.fetchone()
                    if tbl:
                        result['engine'] = tbl.get('ENGINE')                 # 存储引擎
                        result['table_rows_approx'] = tbl.get('TABLE_ROWS')  # 近似行数
                        result['data_length'] = tbl.get('DATA_LENGTH')       # 数据大小
                        result['index_length'] = tbl.get('INDEX_LENGTH')     # 索引大小
                except Exception:
                    pass

                # 1. 获取表结构
                cursor.execute(f"DESCRIBE `{table_name}`")
                columns = cursor.fetchall()
                result['columns'] = [
                    {
                        'name': col['Field'],        # 列名
                        'type': col['Type'],         # 数据类型
                        'null': col['Null'],         # 是否允许NULL
                        'key': col['Key'],           # 键类型(PRI/UNI/MUL)
                        'default': col['Default'],   # 默认值
                        'extra': col.get('Extra')    # 额外属性(auto_increment等)
                    } 
                    for col in columns
                ]
                # 查找主键列
                primary_keys = []
                for col in columns:
                    key_type = col.get('Key') or ''
                    if key_type.upper() == 'PRI':
                        primary_keys.append(col['Field'])
                result['primary_key'] = primary_keys
                
                # 2. 获取行数估计（轻量方式）
                cursor.execute(f"SELECT COUNT(*) as cnt FROM `{table_name}` LIMIT 100000")
                count_result = cursor.fetchone()
                # 获取表的行数估计
                if count_result:
                    result['row_count_estimate'] = count_result['cnt']
                else:
                    result['row_count_estimate'] = 0
                
                # 3. 采样数据（限制采样行数以防止大表性能问题）
                # 3. 采样数据（如果表有数据才采样）
                if result['row_count_estimate'] > 0:
                    # 确定采样行数
                    if sample_rows:
                        sample_limit = sample_rows
                    else:
                        sample_limit = self.max_sample_rows
                    
                    # 根据表大小调整采样行数，避免大表性能问题
                    table_rows = result.get('table_rows_approx')
                    if table_rows and isinstance(table_rows, (int, float)):
                        if table_rows > 5000000:  # 超过500万行
                            sample_limit = 20
                        elif table_rows > 500000:  # 超过50万行
                            sample_limit = 30
                        elif table_rows > 50000:   # 超过5万行
                            sample_limit = 50
                    
                    # 限制最大采样行数为100
                    if sample_limit > 100:
                        sample_limit = 100
                    if sample_limit < 1:
                        sample_limit = 1
                    
                    # 执行采样查询
                    cursor.execute(f"SELECT * FROM `{table_name}` LIMIT {sample_limit}")
                    sample_data = cursor.fetchall()
                    
                    # 将数据转换为可序列化的格式
                    converted_data = []
                    for row in sample_data:
                        converted_row = {}
                        for key, value in row.items():
                            if value is not None:
                                converted_row[key] = str(value)
                            else:
                                converted_row[key] = None
                        converted_data.append(converted_row)
                    result['sample_data'] = converted_data
                
                # 4. 获取索引信息（含列、唯一性、基数、类型）
                cursor.execute(f"SHOW INDEX FROM `{table_name}`")
                indexes = cursor.fetchall()
                index_dict: Dict[str, Dict[str, Any]] = {}
                for idx in indexes:
                    key_name = idx['Key_name']
                    if key_name not in index_dict:
                        index_dict[key_name] = {
                            'name': key_name,
                            'unique': not bool(idx['Non_unique']),
                            'columns': [],
                            'cardinality': None,
                            'index_type': None
                        }
                    index_dict[key_name]['columns'].append(idx['Column_name'])
                    # 以最大Cardinality为整体索引基数（粗略）
                    card = idx.get('Cardinality')
                    if card is not None:
                        prev = index_dict[key_name].get('cardinality')
                        index_dict[key_name]['cardinality'] = max(prev or 0, card)
                    if idx.get('Index_type') and not index_dict[key_name].get('index_type'):
                        index_dict[key_name]['index_type'] = idx.get('Index_type')
                
                result['indexes'] = list(index_dict.values())
            
            conn.close()
            return True, result, ""
            
        except Exception as e:
            logger.error(f"采样表 {table_name} 失败: {e}")
            return False, {}, f"采样失败: {e}"
    
    #获取SQL的执行计划
    def get_explain_plan(self, instance: Instance, database: str, sql: str):   
        if not pymysql:
            return False, {}, "MySQL驱动不可用"
        
        try:
            # 使用统一连接方法，去除重复代码
            conn = self.mysql_connection(instance, database)
            
            with conn.cursor() as cursor:
                # 使用 EXPLAIN FORMAT=JSON 获得更详细的信息
                explain_sql = f"EXPLAIN FORMAT=JSON {sql}"
                cursor.execute(explain_sql)
                explain_result = cursor.fetchone()
                
                # 同时获取传统 EXPLAIN 作为后备
                cursor.execute(f"EXPLAIN {sql}")
                traditional_explain = cursor.fetchall()
            
            conn.close()
            
            return True, {
                'json_plan': explain_result.get('EXPLAIN') if explain_result else None,
                'traditional_plan': traditional_explain
            }, ""
            
        except Exception as e:
            logger.error(f"获取执行计划失败: {e}")
            return False, {}, f"执行计划获取失败: {e}"

    #生成严格受限的上下文，仅包含：数据库类型与版本,DDL（SHOW CREATE TABLE）,现有索引（SHOW INDEX 摘要）      
    def generate_strict_context(self, sql, instance, database, enable_explain=True):
        """生成SQL分析的详细上下文信息"""
        parts = []  # 存储结果的各个部分
        
        # 1. 获取数据库类型
        db_type = 'MySQL'  # 默认数据库类型
        
        version_str = '未知'  # 默认版本信息
        
        # 检查是否有pymysql模块
        if not pymysql:
            parts.append(f"数据库: {db_type}; 版本: {version_str}")
            result = ""
            for part in parts:
                result += part + "\n"
            return result.strip()
        
        # 2. 连接数据库获取版本信息
        conn = None
        # 尝试连接数据库
        try:
            conn = self.mysql_connection(instance, database)
            
            # 获取数据库版本
            cursor = conn.cursor()
            try:
                # 获取数据库版本
                cursor.execute("SELECT VERSION() AS ver")
                row = cursor.fetchone()
                if row and 'ver' in row and row['ver']:
                    version_str = str(row['ver'])
            except:
                pass  # 获取版本失败，使用默认值
            cursor.close()
            
        except Exception as e:
            logger.warning(f"获取数据库版本失败: {e}")
        
        # 添加数据库基本信息
        parts.append(f"数据库: {db_type}; 版本: {version_str}")
        
        # 3. 获取EXPLAIN执行计划（可选）
        if enable_explain:
            try:
                ok, plan, _ = self.get_explain_plan(instance, database, sql)
                if ok:
                    if plan.get('json_plan'):
                        parts.append("\n【EXPLAIN FORMAT=JSON】\n" + str(plan['json_plan']))
                    if plan.get('traditional_plan'):
                        parts.append("\n【EXPLAIN】\n" + str(plan['traditional_plan']))
                else:
                    parts.append("\n【EXPLAIN】\n未获取到执行计划")
            except Exception as e:
                logger.warning(f"获取EXPLAIN失败: {e}")
        
        # 4. 提取表名并收集DDL与索引信息
        try:
            # 提取SQL中的表名
            tables = self.extract_table_names(sql)
            # if temp_tables:
            #     tables = temp_tables
            # else:
            #     tables = []
            
            # 处理表名：去重并限制数量
            if tables:
                seen = []  # 已处理的表名
                for t in tables:
                    # 提取表名（去掉数据库前缀和引号）
                    table_name = t.split('.')[-1].strip('`"')
                    if table_name and table_name not in seen:
                        seen.append(table_name)
                tables = seen[:5]  # 最多处理5个表
            
            # 检查数据库连接
            # if conn is None:
            #     logger.warning("连接数据库失败")
            #     result = ""
            #     for part in parts:
            #         result += part + "\n"
            #     return result.strip()
            
            # 获取每个表的详细信息
            if tables and conn is not None:
                cursor = conn.cursor()
                
                for table in tables:
                    # 获取表的DDL（建表语句）
                    try:
                        cursor.execute(f"SHOW CREATE TABLE `{table}`")
                        row = cursor.fetchone()
                        if row:
                            ddl = ""
                            if 'Create Table' in row:
                                ddl = row['Create Table']
                            elif 'Create View' in row:
                                ddl = row['Create View']
                            
                            if ddl:
                                parts.append(f"\n【DDL - {table}】\n{ddl}")
                    except Exception as e:
                        logger.warning(f"获取DDL失败 {table}: {e}")
                    
                    # 获取表的索引信息
                    try:
                        cursor.execute(f"SHOW INDEX FROM `{table}`")
                        idx_rows = cursor.fetchall()
                        
                        if idx_rows:
                            # 按索引名分组
                            by_name = {}  # 索引名 -> 索引信息
                            
                            for idx in idx_rows:
                                name = idx.get('Key_name')
                                if not name:
                                    continue
                                
                                # 初始化索引信息
                                if name not in by_name:
                                    by_name[name] = {
                                        'unique': not bool(idx.get('Non_unique')),
                                        'columns': [],
                                        'index_type': idx.get('Index_type')
                                    }
                                
                                # 添加列名
                                col = idx.get('Column_name')
                                if col and col not in by_name[name]['columns']:
                                    by_name[name]['columns'].append(col)
                            
                            # 格式化索引信息
                            lines = []
                            for name, item in by_name.items():
                                if item.get('unique'):
                                    uniq = 'UNIQUE'
                                else:
                                    uniq = 'NON-UNIQUE'
                                
                                cols = ','.join(item.get('columns') or [])
                                itype = item.get('index_type') or 'N/A'
                                lines.append(f"- {name} ({uniq}, type={itype}): [{cols}]")
                            
                            parts.append(f"\n【INDEXES - {table}】\n" + "\n".join(lines))
                    except Exception as e:
                        logger.warning(f"获取索引失败 {table}: {e}")
                
                cursor.close()
                
        except Exception as e:
            logger.warning(f"解析表与收集DDL/索引失败: {e}")
        
        # 5. 关闭数据库连接
        if conn:
            conn.close()
        
        # 6. 组合所有结果
        result = ""
        for part in parts:
            result += part + "\n"
        return result.strip()
   
    # 生成包含表采样和执行计划的上下文摘要
    def generate_context_summary(self, sql, instance, database, sample_rows=None, enable_sampling=True, enable_explain=True):
        # 初始化结果列表
        summary_parts = []
        summary_parts.append(f"实例: {instance.instance_name} ({instance.host}:{instance.port})")
        summary_parts.append(f"数据库: {database}")
        
        # 提取表名
        table_names = self.extract_table_names(sql)
        if table_names:
            summary_parts.append(f"\n涉及表: {', '.join(table_names)}")
            
            # 处理每个表（最多5个）
            for table_name in table_names[:5]:
                if enable_sampling:
                    # 获取表的完整采样数据
                    success, sample_data, error = self.sample_table_data(instance, database, table_name, sample_rows)
                    
                    if success:
                        # 添加表名标题
                        summary_parts.append(f"\n【表 {table_name}】")
                        
                        # 添加行数估计
                        summary_parts.append(f"- 行数估计: {sample_data['row_count_estimate']}")
                        
                        # 添加存储引擎信息
                        if sample_data.get('engine') is not None:
                            data_size = self._format_bytes(sample_data.get('data_length'))
                            index_size = self._format_bytes(sample_data.get('index_length'))
                            table_rows_approx = sample_data.get('table_rows_approx')
                            engine = sample_data.get('engine')
                            
                            summary_parts.append(f"- 存储引擎: {engine}, 近似行数: {table_rows_approx:,}, 数据大小: {data_size}, 索引大小: {index_size}")
                        
                        # 添加列数信息
                        summary_parts.append(f"- 列数: {len(sample_data['columns'])}")
                        
                        # 添加主键信息
                        if sample_data.get('primary_key'):
                            primary_keys = ', '.join(sample_data['primary_key'])
                            summary_parts.append(f"- 主键: {primary_keys}")
                        
                        # 添加列信息概览（前5列）
                        if sample_data['columns']:
                            cols = sample_data['columns'][:5]
                            col_briefs = []
                            for c in cols:
                                name = c.get('name')
                                type_info = c.get('type')
                                col_briefs.append(f"{name}({type_info})")
                            summary_parts.append(f"- 列信息(前5): {', '.join(col_briefs)}")
                        
                        # 添加索引摘要（最多3个）
                        if sample_data['indexes']:
                            index_summaries = []
                            for idx in sample_data['indexes'][:3]:
                                # 判断是否唯一索引
                                if idx.get('unique'):
                                    uniq = 'UNIQUE'
                                else:
                                    uniq = 'NON-UNIQUE'
                                
                                # 获取索引列
                                cols = ','.join(idx.get('columns') or [])
                                idx_name = idx.get('name')
                                idx_brief = f"{idx_name}({uniq}): [{cols}]"
                                
                                # 添加额外信息
                                extras = []
                                itype = idx.get('index_type')
                                if itype:
                                    extras.append(f"类型={itype}")
                                
                                card = idx.get('cardinality')
                                if card is not None:
                                    extras.append(f"基数={card:,}")
                                
                                if extras:
                                    idx_brief += " (" + ", ".join(extras) + ")"
                                
                                index_summaries.append(idx_brief)
                            
                            summary_parts.append(f"- 索引: {'; '.join(index_summaries)}")
                        
                        # 添加数据样本摘要
                        if sample_data['sample_data']:
                            sample_count = len(sample_data['sample_data'])
                            summary_parts.append(f"- 样本数据: {sample_count}行（用于类型/分布/值范围的直观判断）")
                    else:
                        # 采样失败的情况
                        summary_parts.append(f"\n【表 {table_name}】采样失败: {error}")
                else:
                    # 仅收集表元信息，不进行数据采样
                    success, table_metadata, error = self._get_table_metadata_only(instance, database, table_name)
                    
                    if success:
                        # 添加表名标题
                        summary_parts.append(f"\n【表 {table_name}】")
                        
                        # 基础表信息
                        if table_metadata.get('engine'):
                            data_size = self._format_bytes(table_metadata.get('data_length'))
                            index_size = self._format_bytes(table_metadata.get('index_length'))
                            avg_row_length = table_metadata.get('avg_row_length')
                            table_collation = table_metadata.get('table_collation', 'N/A')
                            create_time = table_metadata.get('create_time', 'N/A')
                            update_time = table_metadata.get('update_time', 'N/A')
                            engine = table_metadata.get('engine')
                            table_rows_approx = table_metadata.get('table_rows_approx')
                            
                            summary_parts.append(f"- 存储引擎: {engine}")
                            summary_parts.append(f"- 近似行数: {table_rows_approx:,}")
                            summary_parts.append(f"- 数据大小: {data_size}, 索引大小: {index_size}")
                            
                            if avg_row_length:
                                summary_parts.append(f"- 平均行长度: {avg_row_length} 字节")
                            
                            summary_parts.append(f"- 字符集: {table_collation}")
                            summary_parts.append(f"- 创建时间: {create_time}, 更新时间: {update_time}")
                        
                        # 获取列信息
                        if table_metadata.get('columns'):
                            columns = table_metadata['columns']
                            summary_parts.append(f"- 列数: {len(columns)}")
                            
                            # 主键信息
                            if table_metadata.get('primary_key'):
                                primary_keys = ', '.join(table_metadata['primary_key'])
                                summary_parts.append(f"- 主键: {primary_keys}")
                            
                            # 列详情（所有列）
                            col_details = []
                            for col in columns:
                                name = col.get('name')
                                typ = col.get('type')
                                key_flag = (col.get('key') or '').upper()
                                
                                if key_flag:
                                    suffix = f" [{key_flag}]"
                                else:
                                    suffix = ""
                                
                                col_details.append(f"{name}({typ}){suffix}")
                            
                            summary_parts.append(f"- 列详情: {'; '.join(col_details)}")
                        
                        # 索引详情
                        if table_metadata.get('indexes'):
                            index_details = []
                            for idx in table_metadata['indexes']:
                                # 判断是否唯一索引
                                if idx.get('unique'):
                                    uniq = 'UNIQUE'
                                else:
                                    uniq = 'NON-UNIQUE'
                                
                                cols = ','.join(idx.get('columns') or [])
                                card = idx.get('cardinality')
                                itype = idx.get('index_type', 'BTREE')
                                comment = idx.get('comment', '')
                                idx_name = idx.get('name')
                                
                                idx_detail = f"{idx_name}({uniq}, {itype}): [{cols}]"
                                
                                if card is not None:
                                    idx_detail += f" 基数={card:,}"
                                
                                if comment:
                                    idx_detail += f" 备注={comment}"
                                
                                index_details.append(idx_detail)
                            
                            summary_parts.append(f"- 索引详情: {'; '.join(index_details)}")
                        
                        # 表约束信息
                        if table_metadata.get('constraints'):
                            constraints = []
                            for constraint in table_metadata['constraints']:
                                constraint_type = constraint.get('constraint_type', 'UNKNOWN')
                                constraint_name = constraint.get('constraint_name', 'unnamed')
                                column_name = constraint.get('column_name', '')
                                constraints.append(f"{constraint_name}({constraint_type}): {column_name}")
                            
                            if constraints:
                                summary_parts.append(f"- 约束: {'; '.join(constraints)}")
                        
                    else:
                        # 元信息获取失败的情况
                        summary_parts.append(f"\n【表 {table_name}】元信息获取失败: {error}")

        # 获取执行计划
        if enable_explain:
            success, explain_data, error = self.get_explain_plan(instance, database, sql)
            
            if success and explain_data.get('traditional_plan'):
                summary_parts.append(f"\n【执行计划摘要】")
                
                for i, row in enumerate(explain_data['traditional_plan']):
                    table = row.get('table', 'N/A')
                    type_val = row.get('type', 'N/A')
                    key = row.get('key') or 'None'
                    key_len = row.get('key_len') or 'N/A'
                    rows = row.get('rows', 0)
                    filtered = row.get('filtered')
                    extra = row.get('Extra', '')
                    
                    # 构建执行计划行
                    plan_line = f"- 步骤{i+1} 表={table}, 访问类型={type_val}, 使用索引={key}"
                    
                    if key_len != 'N/A':
                        plan_line += f"(长度={key_len})"
                    
                    plan_line += f", 扫描行数≈{rows:,}"
                    
                    if filtered:
                        plan_line += f", 过滤率={filtered}%"
                    
                    if extra:
                        plan_line += f", 额外信息={extra}"
                    
                    summary_parts.append(plan_line)
            elif not success:
                summary_parts.append(f"\n【执行计划】获取失败: {error}")
        
        # 将所有部分组合成最终结果
        return "\n".join(summary_parts)
    
    # 仅获取表的元信息，不进行数据采样
    def _get_table_metadata_only(self, instance, database, table_name):
        # 检查MySQL驱动是否可用
        if not pymysql:
            return False, {}, "MySQL驱动不可用"
        
        try:
            conn = self.mysql_connection(instance, database)
            
            # 初始化表元数据结果字典，包含表的完整结构和统计信息
            result = {
                'table_name': table_name,           # 表名
                'columns': [],                      # 列信息列表：包含列名、类型、是否为空、键类型等
                'indexes': [],                      # 索引信息列表：包含索引名、类型、列、唯一性等
                'constraints': [],                  # 约束信息列表：外键、检查约束等
                'engine': None,                     # 存储引擎：InnoDB、MyISAM等
                'table_rows_approx': None,          # 表的近似行数（来自information_schema统计）
                'data_length': None,                # 数据文件大小（字节）
                'index_length': None,               # 索引文件大小（字节）
                'avg_row_length': None,             # 平均行长度（字节）
                'table_collation': None,            # 表的字符集排序规则
                'create_time': None,                # 表创建时间
                'update_time': None,                # 表最后更新时间
                'primary_key': []                   # 主键列名列表
            }
            
            with conn.cursor() as cursor:
                # 1. 获取表的基础信息
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
                        result['engine'] = table_info.get('ENGINE')
                        result['table_rows_approx'] = table_info.get('TABLE_ROWS')
                        result['data_length'] = table_info.get('DATA_LENGTH')
                        result['index_length'] = table_info.get('INDEX_LENGTH')
                        result['avg_row_length'] = table_info.get('AVG_ROW_LENGTH')
                        result['table_collation'] = table_info.get('TABLE_COLLATION')
                        result['create_time'] = table_info.get('CREATE_TIME')
                        result['update_time'] = table_info.get('UPDATE_TIME')
                except Exception as e:
                    logger.warning(f"获取表基础信息失败: {e}")

                # 2. 获取表的列信息
                try:
                    cursor.execute(f"DESCRIBE `{table_name}`")
                    columns = cursor.fetchall()
                    # 构建列信息字典列表，包含每列的详细属性
                    result['columns'] = [
                        {
                            'name': col['Field'],           # 列名
                            'type': col['Type'],            # 数据类型（如 varchar(255), int(11) 等）
                            'null': col['Null'],            # 是否允许NULL（YES/NO）
                            'key': col['Key'],              # 键类型（PRI=主键, UNI=唯一键, MUL=普通索引）
                            'default': col['Default'],      # 默认值
                            'extra': col.get('Extra')       # 额外属性（如 auto_increment, on update CURRENT_TIMESTAMP）
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
                    index_dict: Dict[str, Dict[str, Any]] = {}
                    for idx in indexes:
                        key_name = idx['Key_name']
                        if key_name not in index_dict:
                            index_dict[key_name] = {
                                'name': key_name,
                                'unique': not bool(idx['Non_unique']),  # Non_unique为0表示唯一索引
                                'columns': [],
                                'cardinality': None,
                                'index_type': None,
                                'comment': None
                            }
                        
                        # 将当前列添加到索引的列列表中
                        index_dict[key_name]['columns'].append(idx['Column_name'])
                        
                        # 更新索引基数，取最大值作为整体索引基数（粗略估算）
                        card = idx.get('Cardinality')
                        if card is not None:
                            prev = index_dict[key_name].get('cardinality')
                            index_dict[key_name]['cardinality'] = max(prev or 0, card)
                        
                        # 设置索引类型（如果还没有设置的话）
                        if idx.get('Index_type') and not index_dict[key_name].get('index_type'):
                            index_dict[key_name]['index_type'] = idx.get('Index_type')
                        
                        # 设置索引注释（如果还没有设置的话）
                        if idx.get('Comment') and not index_dict[key_name].get('comment'):
                            index_dict[key_name]['comment'] = idx.get('Comment')
                    
                    # 将索引字典转换为列表
                    result['indexes'] = list(index_dict.values())
                    
                except Exception as e:
                    logger.warning(f"获取表索引信息失败: {e}")

                # 4. 获取表的约束信息
                try:
                    cursor.execute(
                        """
                        SELECT CONSTRAINT_NAME, CONSTRAINT_TYPE, COLUMN_NAME
                        FROM information_schema.KEY_COLUMN_USAGE kcu
                        JOIN information_schema.TABLE_CONSTRAINTS tc 
                        ON kcu.CONSTRAINT_NAME = tc.CONSTRAINT_NAME 
                        AND kcu.TABLE_SCHEMA = tc.TABLE_SCHEMA
                        WHERE kcu.TABLE_SCHEMA = %s AND kcu.TABLE_NAME = %s
                        """,
                        (database, table_name)
                    )
                    constraints = cursor.fetchall()
                    
                    # 使用基础for循环处理约束信息，替代列表推导式
                    constraint_list = []
                    for constraint in constraints:
                        # 构建每个约束的信息字典
                        constraint_info = {
                            'constraint_name': constraint['CONSTRAINT_NAME'],
                            'constraint_type': constraint['CONSTRAINT_TYPE'],
                            'column_name': constraint['COLUMN_NAME']
                        }
                        constraint_list.append(constraint_info)
                    
                    result['constraints'] = constraint_list
                    
                except Exception as e:
                    logger.warning(f"获取表约束信息失败: {e}")
            
            # 关闭数据库连接
            conn.close()
            return True, result, ""
            
        except Exception as e:
            logger.error(f"获取表 {table_name} 元信息失败: {e}")
            return False, {}, f"元信息获取失败: {e}"


    # 格式化字节大小为可读格式
    def _format_bytes(self, size_bytes):
        
        # 检查输入是否有效
        if size_bytes is None:
            return "未知"
        
        # 检查输入是否为数字类型
        if not isinstance(size_bytes, (int, float)):
            return "未知"
        
        # 使用 humanize 库格式化字节大小
        # naturalsize 会自动选择合适的单位（B, KB, MB, GB, TB等）
        return naturalsize(size_bytes, binary=True)


# 全局实例
table_analyzer_service = TableAnalyzerService()
