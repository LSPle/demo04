// 简单的分析文本格式化工具：将后端返回的纯文本按版块与要点拆分
// 目标：不引入新依赖，在前端做“弱结构化”的展示

// 关键词默认表，用于前端高亮（可按需扩展）
const DEFAULT_HIGHLIGHT_KEYWORDS = [
  '全表扫', '全表扫描', 'ALL', '索引', '覆盖索引', '联合索引', 'WHERE', '筛选', '过滤',
  '执行计划', 'EXPLAIN', '成本', '扫描行', 'ROWS', 'Rows_examined', 'Rows_sent', 'LIMIT',
  '分区', '分表', '读写分离', '慢查询', '慢日志', '缓存', 'IO', '内存', '排序', '临时表'
];

// 将原始文本切成三个常见小节：问题分析 / 优化建议 / 执行计划说明
function extractSections(text) {
  const t = String(text || '').trim();
  if (!t) return [];

  const patterns = [
    { key: '问题分析', regex: /问题分析[：:]\s*([\s\S]*?)(?=优化建议[：:]|执行计划说明[：:]|$)/ },
    { key: '优化建议', regex: /优化建议[：:]\s*([\s\S]*?)(?=问题分析[：:]|执行计划说明[：:]|$)/ },
    { key: '执行计划说明', regex: /执行计划说明[：:]\s*([\s\S]*?)(?=问题分析[：:]|优化建议[：:]|$)/ }
  ];

  const sections = [];
  for (const p of patterns) {
    const m = t.match(p.regex);
    if (m && m[1]) {
      const raw = m[1].trim();
      const items = toBullets(raw);
      if (items.length) {
        sections.push({ title: p.key, items });
      }
    }
  }

  // 若三个小节都没匹配到，则整体当做一个“分析与建议”
  if (!sections.length) {
    const items = toBullets(t);
    sections.push({ title: '分析与建议', items: items.length ? items : [t] });
  }
  return sections;
}

// 将段落拆成要点：优先识别 1. / 1、 / - 这种列表，其次按句号/分号/换行切分
function toBullets(raw) {
  const s = String(raw || '').replace(/\r/g, '').trim();
  if (!s) return [];

  // 尝试识别编号列表：如 1. xxx 2. yyy 或 1、xxx 2、yyy
  const numbered = s.split(/(?:^|\n)\s*(?:-|•|·|\d+[\.、）)\]])\s*/).map(x => x.trim()).filter(Boolean);
  // split 会把第一段前缀也算进去，若切分后数量明显>1，则采用
  if (numbered.length > 1) return numbered;

  // 否则按换行、分号、句号做弱切分
  return s
    .split(/\n+|；|；\s*|。/)
    .map(x => x.trim())
    .filter(Boolean)
    .filter(x => x.length > 1);
}

export function formatAnalysis(text) {
  return { sections: extractSections(text) };
}

export function getHighlightKeywords() {
  return DEFAULT_HIGHLIGHT_KEYWORDS.slice();
}