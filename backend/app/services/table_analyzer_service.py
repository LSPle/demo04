import re
import logging
from typing import List, Dict, Optional, Tuple, Any
import sqlparse
# from sqlparse.sql import IdentifierList, Identifier
from sqlparse.tokens import Keyword, DML
# import json

"""表数据采样和分析服务：解析SQL中的表名，采样数据，生成执行计划"""

try:
    import pymysql
    import pymysql.cursors
except ImportError:
    pymysql = None

from ..models import Instance

logger = logging.getLogger(__name__)


class TableAnalyzerService:
    
    #限制：最多分析的表数量
    def __init__(self):
        self.timeout = 15  # 秒
        self.max_sample_rows = 50  # 默认最大采样行数
        self.max_tables = 10  # 最多分析的表数量

    #  从SQL中提取表名,返回: 表名列表（去重）
    def extract_table_names(self, sql: str):
      
        try:
            parsed = sqlparse.parse(sql)
            if not parsed:
                return []
            
            tables = set()
            
            def extract_from_token(token):
                if hasattr(token, 'tokens'):
                    for sub_token in token.tokens:
                        extract_from_token(sub_token)
                elif token.ttype is Keyword and token.value.upper() in ('FROM', 'JOIN', 'UPDATE', 'INTO'):
                    # 找下一个标识符
                    parent = token.parent
                    if parent:
                        idx = list(parent.tokens).index(token)
                        for i in range(idx + 1, len(parent.tokens)):
                            next_token = parent.tokens[i]
                            if next_token.ttype is None and str(next_token).strip():
                                # 可能是表名
                                table_name = str(next_token).strip().split()[0]
                                # 清理引号和反引号
                                table_name = table_name.strip('`"\'')
                                if table_name and not any(kw in table_name.upper() for kw in ['WHERE', 'GROUP', 'ORDER', 'LIMIT', 'SELECT']):
                                    tables.add(table_name)
                                break
            
            for stmt in parsed:
                extract_from_token(stmt)
            
            # 更保守的提取方法：使用正则表达式作为补充
            # 匹配 FROM/JOIN 后面的表名
            from_pattern = r'(?:FROM|JOIN)\s+(?:`?)([a-zA-Z_][a-zA-Z0-9_.]*)(?:`?)'
            matches = re.findall(from_pattern, sql, re.IGNORECASE)
            for match in matches:
                if '.' in match:
                    # 处理 database.table 格式
                    table_name = match.split('.')[-1]
                else:
                    table_name = match
                tables.add(table_name)
            
            return list(tables)[:self.max_tables]
            
        except Exception as e:
            logger.warning(f"解析SQL表名失败: {e}")
            return []

    #采样表数据和结构信息，返回: (成功标志, 样本数据字典, 错误信息)
    def sample_table_data(self, instance: Instance, database: str, table_name: str, 
                         sample_rows: int = None) -> Tuple[bool, Dict[str, Any], str]:
        
        if not sample_rows:
            sample_rows = self.max_sample_rows
            
        if not pymysql:
            return False, {}, "MySQL驱动不可用"
        
        try:
            host, port = (getattr(instance, 'host', ''), getattr(instance, 'port', 3306))
            try:
                port = int(port) if port is not None else 3306
            except Exception:
                port = 3306
            conn = pymysql.connect(
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
            
            result = {
                'table_name': table_name,
                'columns': [],
                'sample_data': [],
                'row_count_estimate': 0,
                'indexes': [],
                # 新增的表级信息
                'engine': None,
                'table_rows_approx': None,
                'data_length': None,
                'index_length': None,
                'primary_key': []
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
                        result['engine'] = tbl.get('ENGINE')
                        result['table_rows_approx'] = tbl.get('TABLE_ROWS')
                        result['data_length'] = tbl.get('DATA_LENGTH')
                        result['index_length'] = tbl.get('INDEX_LENGTH')
                except Exception:
                    # 忽略表状态查询失败，不影响后续
                    pass

                # 1. 获取表结构
                cursor.execute(f"DESCRIBE `{table_name}`")
                columns = cursor.fetchall()
                result['columns'] = [
                    {
                        'name': col['Field'], 
                        'type': col['Type'], 
                        'null': col['Null'], 
                        'key': col['Key'],
                        'default': col['Default'],
                        'extra': col.get('Extra')
                    } 
                    for col in columns
                ]
                # 主键列
                result['primary_key'] = [col['Field'] for col in columns if (col.get('Key') or '').upper() == 'PRI']
                
                # 2. 获取行数估计（轻量方式）
                cursor.execute(f"SELECT COUNT(*) as cnt FROM `{table_name}` LIMIT 100000")
                count_result = cursor.fetchone()
                result['row_count_estimate'] = count_result['cnt'] if count_result else 0
                
                # 3. 采样数据（限制采样行数以防止大表性能问题）
                if result['row_count_estimate'] > 0:
                    # 动态确定采样行数：根据表规模（近似行数）自适应
                    try:
                        selected_rows = sample_rows or self.max_sample_rows
                        approx = result.get('table_rows_approx')
                        if isinstance(approx, (int, float)) and approx is not None:
                            if approx > 5_000_000:
                                selected_rows = min(selected_rows, 20)
                            elif approx > 500_000:
                                selected_rows = min(selected_rows, 30)
                            elif approx > 50_000:
                                selected_rows = min(selected_rows, 50)
                        sample_limit = min(int(max(1, selected_rows)), 100)
                    except Exception:
                        sample_limit = min(sample_rows or self.max_sample_rows, 100)
                    cursor.execute(f"SELECT * FROM `{table_name}` LIMIT {sample_limit}")
                    sample_data = cursor.fetchall()
                    # 转换为可序列化的格式
                    result['sample_data'] = [
                        {k: (str(v) if v is not None else None) for k, v in row.items()}
                        for row in sample_data
                    ]
                
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
    
    #获取SQL的执行计划，返回: (成功标志, EXPLAIN结果, 错误信息)
    def get_explain_plan(self, instance: Instance, database: str, sql: str):   
        if not pymysql:
            return False, {}, "MySQL驱动不可用"
        
        try:
            host, port = (getattr(instance, 'host', ''), getattr(instance, 'port', 3306))
            try:
                port = int(port) if port is not None else 3306
            except Exception:
                port = 3306
            conn = pymysql.connect(
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
    def generate_strict_context(self, sql: str, instance: Instance, database: str, enable_explain: bool = True):
       
        parts: List[str] = []
        try:
            temp_db_type = getattr(instance, 'db_type', None)
            db_type = str(temp_db_type) if temp_db_type else 'MySQL'
        except Exception:
            db_type = 'MySQL'
        version_str = '未知'

        if not pymysql:
            parts.append(f"数据库: {db_type}; 版本: {version_str}")
            return "\n".join(parts)

        conn = None
        try:
            host, port = (getattr(instance, 'host', ''), getattr(instance, 'port', 3306))
            try:
                port = int(port) if port is not None else 3306
            except Exception:
                port = 3306
            conn = pymysql.connect(
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
            with conn.cursor() as cursor:
                version_str = "未知"
                try:
                    # 先用 SELECT VERSION()
                    cursor.execute("SELECT VERSION() AS ver")
                    row = cursor.fetchone()
                    if row and row.get('ver'):
                        version_str = str(row['ver'])
                    else:
                        # 再尝试 SHOW VARIABLES LIKE 'version'
                        cursor.execute("SHOW VARIABLES LIKE 'version'")
                        row = cursor.fetchone()
                        if row and row.get('Value'):
                            version_str = str(row['Value'])
                except Exception:
                    pass
            parts.append(f"数据库: {db_type}; 版本: {version_str}")
            
        except Exception as e:
            logger.warning(f"获取数据库版本失败: {e}")
            parts.append(f"数据库: {db_type}; 版本: 未知")
        
        # EXPLAIN（可选）
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
        
        # 提取表，并收集 DDL 与索引
        try:
            # tables = self.extract_table_names(sql) or []
            temp_tables = self .extract_table_names(sql)
            if temp_tables:
                tables = temp_tables
            else:
                tables = []
            if tables:
                # 去重并限制5个数量
                seen = []
                for t in tables:
                    tn = t.split('.')[-1].strip('`"')
                    if tn and tn not in seen:
                        seen.append(tn)
                tables = seen[:5]
           
            #验证是否连接失败
            if conn is None:
                logger.warning(f"连接数据库失败: {e}")
                return "\n".join(parts)
            if tables and conn is not None:
                with conn.cursor() as cursor:
                    for table in tables:
                        # 获取DDL
                        try:
                            cursor.execute(f"SHOW CREATE TABLE `{table}`")
                            row = cursor.fetchone() or {}
                            ddl = row.get('Create Table') or row.get('Create View') or ''
                            if ddl:
                                parts.append(f"\n【DDL - {table}】\n{ddl}")
                        except Exception as e:
                            logger.warning(f"获取DDL失败 {table}: {e}")
                        
                        # 获取INDEXES信息
                        try:
                            cursor.execute(f"SHOW INDEX FROM `{table}`")
                            idx_rows = cursor.fetchall() or []
                            if idx_rows:
                                # 汇总
                                by_name: Dict[str, Dict[str, Any]] = {}
                                for idx in idx_rows:
                                    name = idx.get('Key_name')
                                    if not name:
                                        continue
                                    item = by_name.setdefault(name, {
                                        'unique': not bool(idx.get('Non_unique')),
                                        'columns': [],
                                        'index_type': idx.get('Index_type')
                                    })
                                    col = idx.get('Column_name')
                                    if col and col not in item['columns']:
                                        item['columns'].append(col)
                                # 格式化
                                lines = []
                                for name, item in by_name.items():
                                    uniq = 'UNIQUE' if item.get('unique') else 'NON-UNIQUE'
                                    cols = ','.join(item.get('columns') or [])
                                    itype = item.get('index_type') or 'N/A'
                                    lines.append(f"- {name} ({uniq}, type={itype}): [{cols}]")
                                parts.append(f"\n【INDEXES - {table}】\n" + "\n".join(lines))
                        except Exception as e:
                            logger.warning(f"获取索引失败 {table}: {e}")
        except Exception as e:
            logger.warning(f"解析表与收集DDL/索引失败: {e}")
        finally:
            # try:
            #     if conn:
            #         conn.close()
            # except Exception:
            #     pass
            if conn:
                conn.close()
        
        return "\n".join(parts)
   
    #生成包含表采样和执行计划的上下文摘要
    def generate_context_summary(self, sql: str, instance: Instance, database: str, 
                                sample_rows: int = None, enable_sampling: bool = True, 
                                enable_explain: bool = True):
       
        summary_parts = [
            f"实例: {instance.instance_name} ({instance.host}:{instance.port})",
            f"数据库: {database}"
        ]
        
        # 提取表名
        table_names = self.extract_table_names(sql)
        if table_names:
            summary_parts.append(f"\n涉及表: {', '.join(table_names)}")
            
            for table_name in table_names[:5]:  # 最多分析5张表
                if enable_sampling:
                    # 完整采样（包含样本数据）
                    success, sample_data, error = self.sample_table_data(
                        instance, database, table_name, sample_rows
                    )
                    
                    if success:
                        summary_parts.append(f"\n【表 {table_name}】")
                        # 行数与基础规模
                        summary_parts.append(f"- 行数估计: {sample_data['row_count_estimate']}")
                        if sample_data.get('engine') is not None:
                            # 格式化存储大小
                            data_size = self._format_bytes(sample_data.get('data_length'))
                            index_size = self._format_bytes(sample_data.get('index_length'))
                            summary_parts.append(
                                f"- 存储引擎: {sample_data.get('engine')}, 近似行数: {sample_data.get('table_rows_approx'):,}, "
                                f"数据大小: {data_size}, 索引大小: {index_size}"
                            )
                        # 列信息
                        summary_parts.append(f"- 列数: {len(sample_data['columns'])}")
                        # 主键
                        if sample_data.get('primary_key'):
                            summary_parts.append(f"- 主键: {', '.join(sample_data['primary_key'])}")
                        
                        # 列信息概览（前5列）
                        if sample_data['columns']:
                            cols = sample_data['columns'][:5]
                            col_briefs = [f"{c.get('name')}({c.get('type')})" for c in cols]
                            summary_parts.append(f"- 列信息(前5): {', '.join(col_briefs)}")
                        
                        # 索引摘要（最多3个详细展示）
                        if sample_data['indexes']:
                            index_summaries = []
                            for idx in sample_data['indexes'][:3]:
                                uniq = 'UNIQUE' if idx.get('unique') else 'NON-UNIQUE'
                                cols = ','.join(idx.get('columns') or [])
                                card = idx.get('cardinality')
                                itype = idx.get('index_type')
                                idx_brief = f"{idx.get('name')}({uniq}): [{cols}]"
                                extras = []
                                if itype:
                                    extras.append(f"类型={itype}")
                                if card is not None:
                                    extras.append(f"基数={card:,}")
                                if extras:
                                    idx_brief += " (" + ", ".join(extras) + ")"
                                index_summaries.append(idx_brief)
                            summary_parts.append(f"- 索引: {'; '.join(index_summaries)}")
                        
                        # 数据样本摘要（仅显示行数）
                        if sample_data['sample_data']:
                            sample_count = len(sample_data['sample_data'])
                            summary_parts.append(f"- 样本数据: {sample_count}行（用于类型/分布/值范围的直观判断）")
                    else:
                        summary_parts.append(f"\n【表 {table_name}】采样失败: {error}")
                else:
                    # 仅收集表元信息，不进行数据采样
                    success, table_metadata, error = self._get_table_metadata_only(
                        instance, database, table_name
                    )
                    
                    if success:
                        summary_parts.append(f"\n【表 {table_name}】")
                        
                        # 基础表信息
                        if table_metadata.get('engine'):
                            data_size = self._format_bytes(table_metadata.get('data_length'))
                            index_size = self._format_bytes(table_metadata.get('index_length'))
                            avg_row_length = table_metadata.get('avg_row_length')
                            table_collation = table_metadata.get('table_collation', 'N/A')
                            create_time = table_metadata.get('create_time', 'N/A')
                            update_time = table_metadata.get('update_time', 'N/A')
                            
                            summary_parts.append(f"- 存储引擎: {table_metadata.get('engine')}")
                            summary_parts.append(f"- 近似行数: {table_metadata.get('table_rows_approx'):,}")
                            summary_parts.append(f"- 数据大小: {data_size}, 索引大小: {index_size}")
                            if avg_row_length:
                                summary_parts.append(f"- 平均行长度: {avg_row_length} 字节")
                            summary_parts.append(f"- 字符集: {table_collation}")
                            summary_parts.append(f"- 创建时间: {create_time}, 更新时间: {update_time}")
                        
                        # 获取列信息
                        if table_metadata.get('columns'):
                            summary_parts.append(f"- 列数: {len(table_metadata['columns'])}")
                            # 主键
                            if table_metadata.get('primary_key'):
                                summary_parts.append(f"- 主键: {', '.join(table_metadata['primary_key'])}")
                            
                            # 列详情（所有列）
                            col_details = []
                            for col in table_metadata['columns']:
                                name = col.get('name')
                                typ = col.get('type')
                                key_flag = (col.get('key') or '').upper()
                                suffix = f" [{key_flag}]" if key_flag else ""
                                col_details.append(f"{name}({typ}){suffix}")
                            summary_parts.append(f"- 列详情: {'; '.join(col_details)}")
                        
                        # 索引详情
                        if table_metadata.get('indexes'):
                            index_details = []
                            for idx in table_metadata['indexes']:
                                uniq = 'UNIQUE' if idx.get('unique') else 'NON-UNIQUE'
                                cols = ','.join(idx.get('columns') or [])
                                card = idx.get('cardinality')
                                itype = idx.get('index_type', 'BTREE')
                                comment = idx.get('comment', '')
                                
                                idx_detail = f"{idx.get('name')}({uniq}, {itype}): [{cols}]"
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
        
        return "\n".join(summary_parts)
    #仅获取表的元信息，不进行数据采样,返回: (成功标志, 元信息字典, 错误信息)
    def _get_table_metadata_only(self, instance: Instance, database: str, table_name: str):
        if not pymysql:
            return False, {}, "MySQL驱动不可用"
        
        try:
            conn = pymysql.connect(
                host=instance.host,
                port=instance.port,
                user=instance.username or '',
                password=instance.password or '',
                database=database,
                charset='utf8mb4',
                connect_timeout=self.timeout,
                read_timeout=self.timeout,
                write_timeout=self.timeout,
                cursorclass=pymysql.cursors.DictCursor
            )
            
            result = {
                'table_name': table_name,
                'columns': [],
                'indexes': [],
                'constraints': [],
                'engine': None,
                'table_rows_approx': None,
                'data_length': None,
                'index_length': None,
                'avg_row_length': None,
                'table_collation': None,
                'create_time': None,
                'update_time': None,
                'primary_key': []
            }
            
            with conn.cursor() as cursor:
                # 1. 获取表的详细信息
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

                # 2. 获取列信息
                try:
                    cursor.execute(f"DESCRIBE `{table_name}`")
                    columns = cursor.fetchall()
                    result['columns'] = [
                        {
                            'name': col['Field'], 
                            'type': col['Type'], 
                            'null': col['Null'], 
                            'key': col['Key'],
                            'default': col['Default'],
                            'extra': col.get('Extra')
                        } 
                        for col in columns
                    ]
                    # 主键列
                    result['primary_key'] = [col['Field'] for col in columns if (col.get('Key') or '').upper() == 'PRI']
                except Exception as e:
                    logger.warning(f"获取表列信息失败: {e}")
                
                # 3. 获取索引信息
                try:
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
                                'index_type': None,
                                'comment': None
                            }
                        index_dict[key_name]['columns'].append(idx['Column_name'])
                        # 以最大Cardinality为整体索引基数（粗略）
                        card = idx.get('Cardinality')
                        if card is not None:
                            prev = index_dict[key_name].get('cardinality')
                            index_dict[key_name]['cardinality'] = max(prev or 0, card)
                        if idx.get('Index_type') and not index_dict[key_name].get('index_type'):
                            index_dict[key_name]['index_type'] = idx.get('Index_type')
                        if idx.get('Comment') and not index_dict[key_name].get('comment'):
                            index_dict[key_name]['comment'] = idx.get('Comment')
                    
                    result['indexes'] = list(index_dict.values())
                except Exception as e:
                    logger.warning(f"获取表索引信息失败: {e}")

                # 4. 获取约束信息
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
                    result['constraints'] = [
                        {
                            'constraint_name': constraint['CONSTRAINT_NAME'],
                            'constraint_type': constraint['CONSTRAINT_TYPE'],
                            'column_name': constraint['COLUMN_NAME']
                        }
                        for constraint in constraints
                    ]
                except Exception as e:
                    logger.warning(f"获取表约束信息失败: {e}")
            
            conn.close()
            return True, result, ""
            
        except Exception as e:
            logger.error(f"获取表 {table_name} 元信息失败: {e}")
            return False, {}, f"元信息获取失败: {e}"
    #格式化字节大小为可读格式
    def _format_bytes(self, size_bytes):
        """格式化字节大小为可读字符串"""
        if size_bytes is None or not isinstance(size_bytes, (int, float)):
            return "未知"
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"


# 全局实例
table_analyzer_service = TableAnalyzerService()