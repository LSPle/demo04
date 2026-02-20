from flask import Blueprint, request, jsonify, Response
from ..models import Instance
from ..services.table_analyzer_service import table_analyzer_service
from ..services.sql_advice_service import get_sql_advice
import pymysql
import logging

'''
    SQL审核优化,DeepSeek分析
'''

logger = logging.getLogger(__name__)

#创建蓝图
sql_analyze_bp = Blueprint('sql_analyze', __name__)

# 仅支持MySQL；执行轻量的表采样与EXPLAIN，连同SQL提交给LLM，返回分析与可选重写SQL
@sql_analyze_bp.post('/sql/analyze')
def analyze_sql():
    try:
        data = request.get_json() or {}
        instance_id = int(data.get('instanceId') or 0)
        sql = (data.get('sql') or '').strip()
        database = (data.get('database') or '').strip()
        if not instance_id or not sql or not database:
            return jsonify({"error": "缺少必要参数: instanceId, sql, database"}), 400
        if not sql:
            return jsonify({"error": "SQL不能为空"}), 400

        inst = Instance.query.get(instance_id)
        if not inst:
            return jsonify({"error": "实例不存在"}), 404

        # 解析表名
        table_names = []
        try:
            table_names = table_analyzer_service.extract_table_names(sql) or []
        except Exception:
            table_names = []

        # 获取表的元信息（列/索引/近似行数/主键）
        tables_meta = []
        try:
            for t in table_names:
                ok, meta, msg = table_analyzer_service.getTableMetadata(inst, database, t)
                if ok and meta:
                    tables_meta.append(meta)
        except Exception:
            pass

        # 获取执行计划（传统）
        explain_rows = []
        try:
            ok, plan, msg = table_analyzer_service.getExplain(inst, database, sql)
            if ok:
                explain_rows = list(plan.get('traditional_plan') or [])
        except Exception:
            explain_rows = []

        # 构造摘要并调用DeepSeek
        summary = {
            'sql': sql,
            'tables': tables_meta,
            'explain': explain_rows,
        }
        analysis_text = get_sql_advice(summary)
        return Response(analysis_text or "", mimetype='text/plain')
    except Exception as e:
        return jsonify({"error": f"服务器错误: {e}"}), 500


#SQL窗口页面
@sql_analyze_bp.post('/sql/execute')
def execute_sql():
    """执行 SQL（仅 MySQL）。支持查询类与非查询类，返回结果或受影响行数。"""
    try:
        data = request.get_json() or {}
        instance_id = int(data.get('instanceId') or 0)
        sql = (data.get('sql') or '').strip()
        database = (data.get('database') or '').strip()
        
        max_rows = int(data.get('maxRows') or 100)

        if not instance_id or not sql:
            return jsonify({"error": "缺少必要参数: instanceId, sql"}), 400
        if not database:
            return jsonify({"error": "缺少必要参数: database"}), 400

        # 简单防护：仅允许单条语句执行
        # 仅支持单条语句，避免 EXPLAIN 对多语句报错
        temp_list = sql.split(';')
        statements = []
        for s in temp_list:
            s = s.strip()
            if s:
                statements.append(s)
        if len(statements) != 1:
            return jsonify({"error": "仅支持单条 SQL 语句执行，请去除多余的分号或多语句"}), 400
        sql = statements[0]

        # 直接获取实例连接信息
        inst = Instance.query.get(instance_id)
        if not inst:
            return jsonify({"error": "实例不存在"}), 404

        # 连接并执行
        conn = pymysql.connect(
            host=inst.host,
            port=inst.port,
            user=inst.username or '',
            password=inst.password or '',
            database=database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False
        )
        try:
            with conn.cursor() as cursor:
                sql_lower = sql.lower().lstrip()
                is_query = sql_lower.startswith('select') or sql_lower.startswith('show') \
                    or sql_lower.startswith('desc') or sql_lower.startswith('describe') \
                    or sql_lower.startswith('explain')

                cursor.execute(sql)

                if is_query:
                    rows = cursor.fetchmany(max_rows)
                    columns = []
                    if cursor.description:
                        columns = [desc[0] for desc in cursor.description]
                    result = {
                        'sqlType': 'query',
                        'columns': columns,
                        'rows': rows,
                        'rowCount': len(rows),
                        'limitedTo': max_rows
                    }
                    return jsonify(result), 200
                else:
                    affected = cursor.rowcount
                    conn.commit()
                    result = {
                        'sqlType': 'non_query',
                        'affectedRows': affected
                    }
                    return jsonify(result), 200
        finally:
            conn.close()
    except Exception as e:
        return jsonify({"error": f"执行SQL失败: {e}"}), 500
