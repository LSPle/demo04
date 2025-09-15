import React from 'react';
import { Tag } from 'antd';
import { formatAnalysis, getHighlightKeywords } from './analysisFormatter';

/**
 * 渲染分析结果，支持关键词高亮
 * @param {string} text - 要渲染的文本
 * @returns {JSX.Element} 渲染后的JSX元素
 */
export const renderAnalysis = (text) => {
  const { sections } = formatAnalysis(text);
  const keywords = getHighlightKeywords();
  const highlight = (str) => {
    if (!str) return str;
    let out = String(str);
    keywords.forEach(k => {
      const esc = k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      out = out.replace(new RegExp(esc, 'g'), (m) => `$$$HL${m}$$$`);
    });
    const parts = out.split(/\$\$\$HL/);
    const nodes = [];
    parts.forEach((p, idx) => {
      const endIdx = p.indexOf('$$$');
      if (endIdx >= 0) {
        const word = p.slice(0, endIdx);
        const rest = p.slice(endIdx + 3);
        nodes.push(<span key={`hl-${idx}`} style={{ background: 'rgba(250, 173, 20, 0.2)', padding: '0 2px' }}>{word}</span>);
        if (rest) nodes.push(<span key={`t-${idx}`}>{rest}</span>);
      } else {
        nodes.push(<span key={`p-${idx}`}>{p}</span>);
      }
    });
    return <>{nodes}</>;
  };

  return (
    <div className="analysis-text" style={{ lineHeight: 1.7 }}>
      {sections.map((sec, i) => (
        <div key={i} style={{ marginBottom: 12 }}>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>{sec.title}</div>
          <ul style={{ paddingLeft: 20, margin: 0 }}>
            {sec.items.map((it, j) => (
              <li key={j} style={{ marginBottom: 4 }}>{highlight(it)}</li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
};

/**
 * 获取状态标签组件
 * @param {string} status - 状态值
 * @returns {JSX.Element} Tag组件
 */
export const getStatusTag = (status) => {
  const statusMap = {
    running: { color: 'success', text: '运行中' },
    warning: { color: 'warning', text: '警告' },
    error: { color: 'error', text: '异常' },
    closed: { color: 'default', text: '已关闭' }
  };
  const config = statusMap[status] || { color: 'default', text: '未知' };
  return <Tag color={config.color}>{config.text}</Tag>;
};