from flask import Blueprint, request, jsonify
from ..models import Instance
from ..services.deepseek_service import get_deepseek_client
from ..services.table_analyzer_service import table_analyzer_service
import pymysql
import logging
import re
import sqlparse as _sp

'''
    SQL审核优化,DeepSeek分析
'''

logger = logging.getLogger(__name__)

#创建蓝图
sql_analyze_bp = Blueprint('sql_analyze', __name__)

@sql_analyze_bp.post('/sql/analyze')
def analyze_sql():
    """仅支持MySQL；执行轻量的表采样与EXPLAIN，连同SQL提交给LLM，返回分析与可选重写SQL。"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400
            
        # 验证instanceId
        instance_id = data.get('instanceId')
        if not instance_id or instance_id <= 0:
            return jsonify({"error": "请提供有效的实例ID"}), 400
            
        # 验证SQL
        sql = (data.get('sql') or '').strip()
        if not sql:
            return jsonify({"error": "SQL语句不能为空"}), 400

        #使用sqlparse库智能解析SQL语句(可能不需要)
        try:   
            split_result = _sp.split(sql)
            statements = []
            for s in split_result:
                cleaned_s = s.strip()
                if cleaned_s:
                    statements.append(cleaned_s)
        #获取所有错误
        except Exception:
            split_result = sql.spilt(';')
            statements = []
            for s in split_result:
                cleaned_s = s.strip()
                if cleaned_s:
                    statements.append(cleaned_s)
        if len(statements) != 1:
            return jsonify({"error": "仅支持单条 SQL 语句分析，请去除多余的分号或多语句"}), 400
        sql = statements[0]
        
        # 验证数据库名称
        database = (data.get('database') or '').strip()
        if not database:
            return jsonify({"error": "数据库名称不能为空"}), 400
        # 简单的数据库名称格式验证（防止SQL注入）
        
        if not re.match(r'^[a-zA-Z0-9_]+$', database):
            return jsonify({"error": "数据库名称只能包含字母、数字和下划线"}), 400
            
        # 后端默认策略：启用执行计划分析
        enable_explain = True

        # 按 userId 过滤实例归属
        user_id = request.args.get('userId')
        q = Instance.query
        if user_id is not None:
            q = q.filter_by(user_id=user_id)
        inst = q.filter_by(id=instance_id).first()
        if not inst:
            return jsonify({"error": "实例不存在"}), 404
        if (inst.db_type or '').strip() != 'MySQL':
            return jsonify({"error": "仅支持MySQL实例"}), 400

        # 构造严格上下文：仅包含 原始SQL、数据库类型与版本、EXPLAIN、表DDL、现有索引
        try:
            context_summary = table_analyzer_service.generate_strict_context(
                sql=sql,
                instance=inst,
                database=database,
                enable_explain=enable_explain,
            )
        except Exception as e:
            logger.warning(f"严格上下文生成失败 (实例ID: {instance_id}): {e}")
            context_summary = ""

        #调用deepseek分析
        client = get_deepseek_client()
        logger.info(f"DeepSeek客户端配置: enabled={client.enabled}, api_key_set={bool(client.api_key)}, base_url={client.base_url}")
        
        # 使用增强的分析接口，拿到分析文本
        try:
            llm_result = client.analyze_sql(sql, context_summary)
            logger.info(f"DeepSeek分析结果: {bool(llm_result)}")
        except Exception as llm_e:
            logger.error(f"DeepSeek分析异常: {llm_e}")
            llm_result = None

        if not llm_result:
            logger.warning("DeepSeek分析失败，尝试降级到基础分析功能")
            # 降级：使用基础分析功能
            try:
                analysis_result = client.rewrite_sql(sql, context_summary)
                logger.info(f"DeepSeek基础分析结果: {bool(analysis_result)}")
            except Exception as rewrite_e:
                logger.error(f"DeepSeek基础分析异常: {rewrite_e}")
                analysis_result = None
            
            return jsonify({
                "analysis": analysis_result if analysis_result else "DeepSeek分析服务暂时不可用，请稍后重试",
                "rewrittenSql": None
            }), 200

        return jsonify({
            "analysis": llm_result.get("analysis"),
            "rewrittenSql": None
        }), 200

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
        max_rows = int(data.get('maxRows') or 1000)

        if not instance_id or not sql:
            return jsonify({"error": "缺少必要参数: instanceId, sql"}), 400
        if not database:
            return jsonify({"error": "缺少必要参数: database"}), 400

        # 简单防护：仅允许单条语句执行
        # 仅支持单条语句，避免 EXPLAIN 对多语句报错
        statements = [s.strip() for s in sql.split(';') if s.strip()]
        if len(statements) != 1:
            return jsonify({"error": "仅支持单条 SQL 语句执行，请去除多余的分号或多语句"}), 400
        sql = statements[0]

        # 按 userId 过滤实例归属
        user_id = request.args.get('userId')
        q = Instance.query
        if user_id is not None:
            q = q.filter_by(user_id=user_id)
        inst = q.filter_by(id=instance_id).first()
        if not inst:
            return jsonify({"error": "实例不存在"}), 404
        if (inst.db_type or '').strip() != 'MySQL':
            return jsonify({"error": "仅支持MySQL实例"}), 400

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