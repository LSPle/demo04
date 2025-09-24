import logging
import json
from typing import Any, Dict, List, Optional, Tuple
import requests
import re
'''
    架构优化页面
'''
try:
    import pymysql
except ImportError:
    pymysql = None

from .deepseek_service import DeepSeekClient, strip_markdown
from flask import current_app
from ..models import Instance

logger = logging.getLogger(__name__)


def _on_off(v: Any) -> str:
    s = str(v).strip().lower()
    if s in ("1", "on", "true", "yes", "enabled"):  # 统一成 ON/OFF
        return "ON"
    return "OFF"


class ArchCollector:
    """采集与复制/可靠性相关的全局配置与复制状态（只读查询）"""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    #无法使用DeepSeek的情况下
    def _connect(self, inst: Instance):
        if not pymysql:
            raise RuntimeError("MySQL驱动不可用")
        return pymysql.connect(
            host=inst.host,
            port=inst.port,
            user=inst.username or '',
            password=inst.password or '',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=self.timeout,
            read_timeout=self.timeout,
            write_timeout=self.timeout
        )

    def collect(self, inst: Instance) -> Tuple[bool, Dict[str, Any], str]:
        """返回 (ok, data, msg)，其中 data 包含 overview 与 replication 两段。"""
        if not inst:
            return False, {}, "实例不存在"
        if (inst.db_type or '').strip() != 'MySQL':
            return False, {}, "仅支持MySQL实例"
        try:
            conn = self._connect(inst)
            try:
                overview: Dict[str, Any] = {}
                replication: Dict[str, Any] = {}
                with conn.cursor() as cur:
                    # 采集关键变量（全局）
                    cur.execute("""
                        SHOW GLOBAL VARIABLES WHERE Variable_name IN (
                            'log_bin','binlog_format','gtid_mode','enforce_gtid_consistency',
                            'read_only','super_read_only',
                            'rpl_semi_sync_master_enabled','rpl_semi_sync_slave_enabled',
                            'sync_binlog','innodb_flush_log_at_trx_commit',
                            'binlog_row_image','binlog_expire_logs_seconds',
                            'master_info_repository','relay_log_info_repository',
                            'expire_logs_days'
                        )
                    """)
                    rows = cur.fetchall()
                    vars_map = {r['Variable_name']: r['Value'] for r in rows}

                    overview = {
                        'log_bin': _on_off(vars_map.get('log_bin')) if vars_map.get('log_bin') is not None else 'N/A',
                        'binlog_format': (vars_map.get('binlog_format') or 'N/A'),
                        'gtid_mode': (vars_map.get('gtid_mode') or 'N/A'),
                        'enforce_gtid_consistency': (vars_map.get('enforce_gtid_consistency') or 'N/A'),
                        'read_only': _on_off(vars_map.get('read_only')) if vars_map.get('read_only') is not None else 'N/A',
                        'super_read_only': _on_off(vars_map.get('super_read_only')) if vars_map.get('super_read_only') is not None else 'N/A',
                        'rpl_semi_sync_master_enabled': _on_off(vars_map.get('rpl_semi_sync_master_enabled')) if vars_map.get('rpl_semi_sync_master_enabled') is not None else 'N/A',
                        'rpl_semi_sync_slave_enabled': _on_off(vars_map.get('rpl_semi_sync_slave_enabled')) if vars_map.get('rpl_semi_sync_slave_enabled') is not None else 'N/A',
                        'sync_binlog': str(vars_map.get('sync_binlog') or 'N/A'),
                        'innodb_flush_log_at_trx_commit': str(vars_map.get('innodb_flush_log_at_trx_commit') or 'N/A'),
                        # 新增概览项
                        'binlog_row_image': str(vars_map.get('binlog_row_image') or 'N/A'),
                        'binlog_expire_logs_seconds': str(vars_map.get('binlog_expire_logs_seconds') or (vars_map.get('expire_logs_days') or 'N/A')),
                        'master_info_repository': str(vars_map.get('master_info_repository') or 'N/A'),
                        'relay_log_info_repository': str(vars_map.get('relay_log_info_repository') or 'N/A'),
                    }

                    # 复制状态：优先尝试 SHOW REPLICA STATUS（兼容新版本），失败或为空再尝试 SHOW SLAVE STATUS
                    repl_row = None
                    try:
                        cur.execute("SHOW REPLICA STATUS")
                        repl_row = cur.fetchone()
                    except Exception:
                        repl_row = None

                    if not repl_row:
                        try:
                            cur.execute("SHOW SLAVE STATUS")
                            repl_row = cur.fetchone()
                        except Exception:
                            repl_row = None

                    if repl_row:
                        # 兼容不同字段名
                        seconds = repl_row.get('Seconds_Behind_Master')
                        if seconds is None:
                            seconds = repl_row.get('Seconds_Behind_Source')
                        io_run = repl_row.get('Slave_IO_Running')
                        if io_run is None:
                            io_run = repl_row.get('Replica_IO_Running')
                        sql_run = repl_row.get('Slave_SQL_Running')
                        if sql_run is None:
                            sql_run = repl_row.get('Replica_SQL_Running')
                        sql_state = repl_row.get('Slave_SQL_Running_State')
                        if sql_state is None:
                            sql_state = repl_row.get('Replica_SQL_Running_State')
                        executed_gtid = repl_row.get('Executed_Gtid_Set')
                        retrieved_gtid = repl_row.get('Retrieved_Gtid_Set')
                        # 错误字段兼容
                        last_error = repl_row.get('Last_Error')
                        if not last_error:
                            # 组合 SQL/IO 错误
                            se = repl_row.get('Last_SQL_Error')
                            ie = repl_row.get('Last_IO_Error')
                            last_error = se or ie

                        def _yes_no(v: Any) -> str:
                            s = str(v).strip().lower()
                            if s in ('yes', 'on', 'running', 'connected', '1', 'true'):
                                return 'Yes'
                            return 'No'

                        replication = {
                            'is_replica': True,
                            'seconds_behind': None if seconds is None else (int(seconds) if str(seconds).isdigit() else seconds),
                            'io_thread': _yes_no(io_run) if io_run is not None else 'Unknown',
                            'sql_thread': _yes_no(sql_run) if sql_run is not None else 'Unknown',
                            # 新增复制细节
                            'Replica_SQL_Running_State': sql_state or 'Unknown',
                            'Executed_Gtid_Set': executed_gtid or '',
                            'Retrieved_Gtid_Set': retrieved_gtid or '',
                            'Last_Error': last_error or '',
                        }
                    else:
                        replication = {
                            'is_replica': False
                        }

                return True, {'overview': overview, 'replication': replication}, 'OK'
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"采集架构配置失败(实例ID={getattr(inst, 'id', None)}): {e}")
            return False, {}, f"连接或查询失败: {e}"


class ArchAdvisor:
    """基于规则的稳定建议，不依赖 LLM"""

    def advise(self, overview: Dict[str, Any], replication: Dict[str, Any]) -> List[Dict[str, Any]]:
        risks: List[Dict[str, Any]] = []

        def add(category: str, item: str, current: str, level: str, recommendation: str):
            risks.append({
                'category': category,
                'item': item,
                'current': current,
                'level': level,
                'recommendation': recommendation,
            })

        # binlog/GTID
        if overview.get('log_bin') == 'OFF':
            add('复制与高可用', 'binlog', 'log_bin=OFF', 'error', '建议开启 log_bin 以支持复制与基于 binlog 的恢复。')
        if str(overview.get('binlog_format', '')).upper() != 'ROW':
            add('复制一致性', 'binlog_format', f"{overview.get('binlog_format')}", 'warning', '建议将 binlog_format 设置为 ROW 以确保复制一致性与审计精度。')
        if str(overview.get('gtid_mode', '')).upper() != 'ON':
            add('复制一致性', 'gtid_mode', f"{overview.get('gtid_mode')}", 'warning', '建议开启 GTID（gtid_mode=ON 且 enforce_gtid_consistency=ON），利于复制管理与故障切换。')

        # 同步策略
        sync_binlog = str(overview.get('sync_binlog'))
        trx_commit = str(overview.get('innodb_flush_log_at_trx_commit'))
        if sync_binlog != '1' or trx_commit != '1':
            add('崩溃恢复策略', 'sync策略组合', f"sync_binlog={sync_binlog} / innodb_flush_log_at_trx_commit={trx_commit}", 'warning', '高可靠场景建议 sync_binlog=1 且 innodb_flush_log_at_trx_commit=1；若为性能优先，可保留并加强备份。')

        # 半同步
        if replication.get('is_replica') or overview.get('rpl_semi_sync_master_enabled') in ('ON', 'OFF'):
            if _on_off(overview.get('rpl_semi_sync_master_enabled')) == 'OFF':
                add('复制与高可用', '半同步(主)', f"rpl_semi_sync_master_enabled={overview.get('rpl_semi_sync_master_enabled')}", 'warning', '如需提升主库提交可靠性，可启用半同步复制（需安装相应插件并在主从两端配置）。')

        # 复制只读保护
        if replication.get('is_replica'):
            if _on_off(overview.get('read_only')) == 'OFF' or _on_off(overview.get('super_read_only')) == 'OFF':
                add('复制与高可用', '从库只读保护', f"read_only={overview.get('read_only')} / super_read_only={overview.get('super_read_only')}", 'error', '建议在所有从库开启 read_only 与 super_read_only，避免误写风险。')

        # 复制延迟与线程
        if replication.get('is_replica'):
            sec = replication.get('seconds_behind')
            if isinstance(sec, int):
                if sec >= 300:
                    add('复制与高可用', '复制延迟', f"{sec}s", 'error', '复制延迟超过5分钟，建议排查从库资源瓶颈、慢 SQL 或网络问题。')
                elif sec >= 60:
                    add('复制与高可用', '复制延迟', f"{sec}s", 'warning', '复制延迟超过1分钟，建议关注从库负载并优化耗时事务。')
            io_t = replication.get('io_thread')
            sql_t = replication.get('sql_thread')
            if io_t and io_t != 'Yes':
                add('复制与高可用', 'IO线程状态', f"{io_t}", 'error', '复制 IO 线程未运行，请检查与主库的网络连通与权限设置。')
            if sql_t and sql_t != 'Yes':
                add('复制与高可用', 'SQL线程状态', f"{sql_t}", 'error', '复制 SQL 线程未运行，请检查从库错误日志并尝试跳过异常事务。')

        # ========= 新增：将补充信号纳入规则引擎（偏保守） =========
        # 1) binlog_row_image：非 FULL 提醒
        row_img = str(overview.get('binlog_row_image') or '').upper()
        if row_img and row_img != 'FULL':
            add('审计与回放', 'binlog_row_image', f"{row_img}", 'warning', '建议设置为 FULL，以确保 binlog 中包含完整列值，利于审计、CDC 与按事件回放。需关注磁盘与带宽消耗上升。')
    
        # 2) binlog_expire_logs_seconds：过短风险（<1小时：error，<1天：warning）
        def _to_int(v: Any) -> Optional[int]:
            try:
                return int(str(v))
            except Exception:
                return None
        expire_sec = _to_int(overview.get('binlog_expire_logs_seconds'))
        if expire_sec is not None and expire_sec > 0:
            if expire_sec < 3600:
                add('备份与恢复', 'binlog保留时长', f"{expire_sec}s", 'error', 'binlog 保留不足 1 小时，可能导致搭建新从库或按时间点恢复失败。建议至少覆盖全量备份间隔 + 复制最大延迟。')
            elif expire_sec < 86400:
                add('备份与恢复', 'binlog保留时长', f"{expire_sec}s", 'warning', 'binlog 保留不足 1 天，恢复与建从容错能力较弱。建议结合备份策略、SLA 与延迟上限适当提高。')
    
        # 3) master/relay info repository：FILE -> 建议切换 TABLE（版本支持时）
        mir = str(overview.get('master_info_repository') or '').upper()
        rir = str(overview.get('relay_log_info_repository') or '').upper()
        if mir == 'FILE':
            add('崩溃恢复策略', 'master_info_repository', 'FILE', 'warning', '建议使用 TABLE 存储 master info（版本支持时），提升崩溃一致性与元数据持久化能力。')
        if rir == 'FILE':
            add('崩溃恢复策略', 'relay_log_info_repository', 'FILE', 'warning', '建议使用 TABLE 存储 relay log info（版本支持时），提升崩溃一致性与元数据持久化能力。')
    
        # 4) Replica_SQL_Running_State：异常/等待态提醒
        state = str(replication.get('Replica_SQL_Running_State') or '').strip()
        if replication.get('is_replica') and state and state.lower() not in ('', 'unknown'):
            low_s = state.lower()
            if ('error' in low_s) or ('stopp' in low_s):
                add('复制与高可用', 'SQL线程状态(细节)', state, 'error', '复制 SQL 线程出现错误/停止，请结合 Last_Error、错误日志与延迟情况排查并恢复。')
            elif ('wait' in low_s) or ('queue' in low_s):
                add('复制与高可用', 'SQL线程状态(细节)', state, 'warning', '复制 SQL 线程处于等待/排队状态，可能有大事务、锁争用或资源瓶颈，建议检查从库负载与慢日志。')
    
        # 5) Last_Error：非空即给出强提醒
        last_err = str(replication.get('Last_Error') or '').strip()
        if last_err:
            add('复制与高可用', '复制错误', last_err, 'error', '请按错误提示定位根因：权限/连通性、表结构差异、重复键/外键约束、坏事务等。修复后重启复制（START REPLICA/SLAVE）。')
    
        # 6) GTID相关提示：在 gtid_mode=ON 下的合理性检查
        if str(overview.get('gtid_mode') or '').upper() == 'ON':
            ex_gtid = replication.get('Executed_Gtid_Set') or ''
            rt_gtid = replication.get('Retrieved_Gtid_Set') or ''
            if replication.get('is_replica') and not ex_gtid:
                add('复制一致性', 'Executed_Gtid_Set', '空', 'warning', '已开启 GTID，但从库 Executed_Gtid_Set 为空，请确认复制正常应用并检查权限/错误日志。')
            sec = replication.get('seconds_behind')
            if isinstance(sec, int) and sec >= 60 and ex_gtid and rt_gtid and ex_gtid != rt_gtid:
                add('复制与高可用', 'GTID应用积压', 'Retrieved 与 Executed 存在差异', 'warning', '从库已下载但未完全应用 GTID，存在应用积压。建议排查从库执行瓶颈、长事务或DDL。')
    
        return risks


# 新增：基于 DeepSeek 的架构建议
def llm_advise_architecture(
    overview: dict,
    replication: dict | None,
    rule_based_risks: list[dict] | None,
    slowlog_summary: dict | None = None,
    metrics_summary: dict | None = None,
) -> dict:
    """简化的DeepSeek架构分析服务"""
    client = DeepSeekClient()
    
    # 简化提示词 - 直接要求结构化输出
    system_prompt = (
        "你是MySQL架构优化专家。请分析数据库架构并给出简洁的优化建议。"
        "输出格式：\n"
        "【健康状态】：\n"
        "【主要问题】：\n- 问题1\n- 问题2\n"
        "【优化建议】：\n- 建议1\n- 建议2\n"
        "【行动计划】：\n- 步骤1\n- 步骤2"
    )
    
    # 简化数据拼接
    data_summary = f"""
架构概览：{overview.get('version', 'Unknown')} | 连接数：{overview.get('connections', 'N/A')}
复制状态：{replication.get('status', 'Unknown') if replication else '未配置'}
风险数量：{len(rule_based_risks) if rule_based_risks else 0}个
慢查询：{slowlog_summary.get('total_count', 0) if slowlog_summary else 0}条
"""
    
    user_prompt = f"请分析以下MySQL实例：\n{data_summary}"
    
    # DeepSeek未启用时的简单处理
    if not getattr(client, "enabled", True) or not getattr(client, "api_key", None):
        return {
            "llm_advice": None,  # 明确返回None表示未启用
            "error": "DeepSeek未配置"
        }
    
    try:
        # 调用DeepSeek API
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        response = client._make_api_call(messages)
        
        # 简单清洗 - 只移除多余空行和特殊字符
        cleaned_text = clean_deepseek_response(response)
        
        return {
            "llm_advice": cleaned_text,
            "error": None
        }
        
    except Exception as e:
        return {
            "llm_advice": None,
            "error": f"DeepSeek分析失败：{str(e)}"
        }


def clean_deepseek_response(text: str) -> str:
    """简化的响应清洗函数"""
    if not text:
        return ""
    
    # 基础清洗：移除多余空行和特殊符号
    text = text.strip()
    text = re.sub(r'\n{3,}', '\n\n', text)  # 多个换行变成两个
    text = re.sub(r'[*#`]+', '', text)     # 移除markdown符号
    text = text.replace('**', '').replace('__', '')  # 移除粗体标记
    
    return text
arch_collector = ArchCollector()
arch_advisor = ArchAdvisor()