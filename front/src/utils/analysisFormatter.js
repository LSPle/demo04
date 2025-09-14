// 简单的分析文本格式化工具：将后端返回的纯文本按版块与要点拆分
// 目标：不引入新依赖，在前端做“弱结构化”的展示

// 关键词默认表，用于前端高亮（可按需扩展）
const DEFAULT_HIGHLIGHT_KEYWORDS = [
  '全表扫', '全表扫描', 'ALL', '索引', '覆盖索引', '联合索引', 'WHERE', '筛选', '过滤',
  '执行计划', 'EXPLAIN', '成本', '扫描行', 'ROWS', 'Rows_examined', 'Rows_sent', 'LIMIT',
  '分区', '分表', '读写分离', '慢查询', '慢日志', '缓存', 'IO', '内存', '排序', '临时表'
];

// 将段落拆成要点：优先识别 1. / 1、 / - 这种列表，其次按句号/分号/换行切分
function toBullets(raw) {
  const s = String(raw || '').replace(/\r/g, '').trim();
  if (!s) return [];

  // 尝试识别编号/项目符号列表：如 1. xxx / 1、xxx / - xxx / • xxx
  const numbered = s
    .split(/(?:^|\n)\s*(?:-|•|·|\d+[\.、）)\]])\s*/).map(x => x.trim()).filter(Boolean);
  if (numbered.length > 1) return numbered;

  // 否则按换行、分号、句号做弱切分
  return s
    .split(/\n+|；|；\s*|。/)
    .map(x => x.trim())
    .filter(Boolean)
    .filter(x => x.length > 1);
}

// 新增：将不同标题规范化为统一展示（例如“主要问题” -> “问题分析”）
function normalizeTitle(title) {
  const t = String(title || '').trim();
  if (!t) return '分析与建议';
  const map = {
    '主要问题': '问题分析',
    '问题': '问题分析',
    '健康状态': '健康状态',
    '优化建议': '优化建议',
    '行动计划': '行动计划',
    '执行计划说明': '执行计划说明',
    '结论': '结论',
  };
  return map[t] || t;
}

// 将原始文本切成小节：优先识别【标题】结构，其次识别常见中文标题，最后兜底为"分析与建议"
function extractSections(text) {
  const t = String(text || '').replace(/\r/g, '').trim();
  if (!t) return [];

  // 1) 优先解析 "【标题】内容" 结构（DeepSeek 常见输出）
  const bracketRe = /【\s*([^\]：:]+?)\s*】[：:]?\s*([\s\S]*?)(?=(?:\n?\s*【)|$)/g;
  const bracketSections = [];
  let m;
  while ((m = bracketRe.exec(t)) !== null) {
    const rawTitle = (m[1] || '').trim();
    const body = (m[2] || '').trim();
    const items = toBullets(body);
    if (items.length) {
      bracketSections.push({ title: normalizeTitle(rawTitle), items });
    }
  }
  if (bracketSections.length) {
    return bracketSections;
  }

  // 2) 解析无括号的标题格式（如："健康状态 \n Attention\n\n 问题分析"）
  const titleRe = /^\s*(健康状态|问题分析|优化建议|行动计划|执行计划说明)\s*\n([\s\S]*?)(?=\n\s*(?:健康状态|问题分析|优化建议|行动计划|执行计划说明)|$)/gm;
  const titleSections = [];
  let m2;
  while ((m2 = titleRe.exec(t)) !== null) {
    const rawTitle = (m2[1] || '').trim();
    const body = (m2[2] || '').trim();
    const items = toBullets(body);
    if (items.length) {
      titleSections.push({ title: normalizeTitle(rawTitle), items });
    }
  }
  if (titleSections.length) {
    return titleSections;
  }

  // 3) 回退：解析带冒号的标题（兼容现有 SQL 审核优化逻辑）
  const patterns = [
    { key: '问题分析', regex: /问题分析[：:]\s*([\s\S]*?)(?=优化建议[：:]|执行计划说明[：:]|行动计划[：:]|健康状态[：:]|$)/ },
    { key: '优化建议', regex: /优化建议[：:]\s*([\s\S]*?)(?=问题分析[：:]|执行计划说明[：:]|行动计划[：:]|健康状态[：:]|$)/ },
    { key: '执行计划说明', regex: /执行计划说明[：:]\s*([\s\S]*?)(?=问题分析[：:]|优化建议[：:]|行动计划[：:]|健康状态[：:]|$)/ },
    { key: '健康状态', regex: /健康状态[：:]\s*([\s\S]*?)(?=问题分析[：:]|优化建议[：:]|执行计划说明[：:]|行动计划[：:]|$)/ },
    { key: '行动计划', regex: /行动计划[：:]\s*([\s\S]*?)(?=问题分析[：:]|优化建议[：:]|执行计划说明[：:]|健康状态[：:]|$)/ },
  ];

  const sections = [];
  for (const p of patterns) {
    const m3 = t.match(p.regex);
    if (m3 && m3[1]) {
      const raw = m3[1].trim();
      const items = toBullets(raw);
      if (items.length) {
        sections.push({ title: p.key, items });
      }
    }
  }

  // 4) 若都未匹配，则整体当做一个"分析与建议"
  if (!sections.length) {
    const items = toBullets(t);
    sections.push({ title: '分析与建议', items: items.length ? items : [t] });
  }
  return sections;
}

export function formatAnalysis(text) {
  return { sections: extractSections(text) };
}

export function getHighlightKeywords() {
  return DEFAULT_HIGHLIGHT_KEYWORDS.slice();
}