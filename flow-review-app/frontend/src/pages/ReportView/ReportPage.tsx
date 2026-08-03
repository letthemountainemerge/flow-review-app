import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getReport } from '../../services/api';
import type { ReviewReport, DimensionResult } from '../../types';
import { DIMENSION_NAMES } from '../../types';

const CONCLUSION_COLORS: Record<string, string> = {
  '通过': 'text-green-600 bg-green-50',
  '不通过': 'text-red-600 bg-red-50',
  '需关注': 'text-yellow-600 bg-yellow-50',
};

const SEVERITY_ICONS: Record<string, string> = {
  '严重': '❌',
  '一般': '⚠️',
  '建议': '💡',
};

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [report, setReport] = useState<ReviewReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedDims, setExpandedDims] = useState<Set<number>>(new Set());
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    if (id) loadReport(id);
  }, [id]);

  async function loadReport(taskId: string) {
    setLoading(true);
    setError('');
    try {
      const data = await getReport(taskId);
      setReport(data);
      // 默认展开所有维度
      setExpandedDims(new Set(data.dimension_results.map((d) => d.dimension_id)));
    } catch (err: any) {
      setError(err?.response?.data?.detail || '加载报告失败');
    } finally {
      setLoading(false);
    }
  }

  function toggleDim(dimId: number) {
    setExpandedDims((prev) => {
      const next = new Set(prev);
      if (next.has(dimId)) next.delete(dimId);
      else next.add(dimId);
      return next;
    });
  }

  function getFilteredResults(): DimensionResult[] {
    if (!report) return [];
    if (filter === 'all') return report.dimension_results;
    return report.dimension_results.filter((d) => d.conclusion === filter);
  }

  if (loading) {
    return (
      <div className="text-center py-16">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-500">加载报告...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-16">
        <div className="text-4xl mb-3">⚠️</div>
        <p className="text-red-500 mb-4">{error}</p>
        <button onClick={() => navigate('/')} className="text-blue-600 hover:underline">
          返回任务列表
        </button>
      </div>
    );
  }

  if (!report) return null;

  return (
    <div>
      {/* 报告头部 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold text-gray-900">评审报告</h1>
            <p className="text-sm text-gray-500 mt-1">任务ID: {report.task_id}</p>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold text-gray-900">{report.overall_score}<span className="text-lg text-gray-400">/100</span></div>
            <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${CONCLUSION_COLORS[report.overall_conclusion] || 'text-gray-600 bg-gray-50'}`}>
              {report.overall_conclusion || '未评定'}
            </span>
          </div>
        </div>
        {report.summary && (
          <p className="mt-4 text-sm text-gray-600 bg-gray-50 p-3 rounded-lg">{report.summary}</p>
        )}
      </div>

      {/* 维度筛选 */}
      <div className="flex space-x-2 mb-4">
        {[
          { key: 'all', label: '全部' },
          { key: '通过', label: '✅ 通过' },
          { key: '不通过', label: '❌ 不通过' },
          { key: '需关注', label: '⚠️ 需关注' },
        ].map((item) => (
          <button
            key={item.key}
            onClick={() => setFilter(item.key)}
            className={`px-3 py-1.5 rounded-md text-sm ${
              filter === item.key
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-600 border border-gray-300 hover:bg-gray-50'
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {/* 维度评审结果 */}
      <div className="space-y-4">
        {getFilteredResults().map((dim) => (
          <div key={dim.dimension_id} className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            {/* 维度头部 */}
            <button
              onClick={() => toggleDim(dim.dimension_id)}
              className="w-full flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors text-left"
            >
              <div className="flex items-center space-x-3">
                <span className="text-gray-400">{expandedDims.has(dim.dimension_id) ? '▼' : '▶'}</span>
                <div>
                  <span className="text-sm text-gray-500">维度{dim.dimension_id}</span>
                  <span className="ml-2 font-medium text-gray-900">
                    {DIMENSION_NAMES[dim.dimension_id] || dim.dimension_name}
                  </span>
                </div>
              </div>
              <div className="flex items-center space-x-3">
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${CONCLUSION_COLORS[dim.conclusion] || 'text-gray-600 bg-gray-50'}`}>
                  {dim.conclusion}
                </span>
                <span className="text-sm font-medium text-gray-600">{dim.score}分</span>
              </div>
            </button>

            {/* 发现项列表 */}
            {expandedDims.has(dim.dimension_id) && (
              <div className="border-t border-gray-100">
                {dim.findings.length === 0 ? (
                  <div className="px-6 py-4 text-sm text-green-600">✅ 无发现项，评审通过</div>
                ) : (
                  <div className="divide-y divide-gray-50">
                    {dim.findings
                      .sort((a, b) => {
                        const order = { '严重': 0, '一般': 1, '建议': 2 };
                        return (order[a.severity] || 3) - (order[b.severity] || 3);
                      })
                      .map((finding) => (
                        <div key={finding.finding_id} className="px-6 py-4">
                          <div className="flex items-start space-x-2">
                            <span className="text-lg mt-0.5">{SEVERITY_ICONS[finding.severity] || '•'}</span>
                            <div className="flex-1">
                              <div className="flex items-center space-x-2">
                                <span className={`text-xs px-1.5 py-0.5 rounded ${
                                  finding.severity === '严重' ? 'bg-red-100 text-red-700' :
                                  finding.severity === '一般' ? 'bg-yellow-100 text-yellow-700' :
                                  'bg-blue-100 text-blue-700'
                                }`}>
                                  {finding.severity}
                                </span>
                                <span className="text-sm text-gray-400">
                                  置信度: {(finding.confidence * 100).toFixed(0)}%
                                </span>
                              </div>
                              <p className="mt-1 text-sm text-gray-900">{finding.description}</p>

                              {/* 定位信息 */}
                              {finding.location && (
                                <div className="mt-1 text-xs text-gray-500">
                                  📍 位置: {finding.location.document_type}
                                  {finding.location.section ? ` / ${finding.location.section}` : ''}
                                  {finding.location.node_id ? ` / 节点: ${finding.location.node_id}` : ''}
                                  {finding.location.quote && (
                                    <blockquote className="mt-1 pl-2 border-l-2 border-gray-200 italic text-gray-400">
                                      "{finding.location.quote}"
                                    </blockquote>
                                  )}
                                </div>
                              )}

                              {/* 证据和建议 */}
                              {finding.evidence && (
                                <p className="mt-1 text-xs text-gray-500">📖 依据: {finding.evidence}</p>
                              )}
                              {finding.suggestion && (
                                <p className="mt-1 text-xs text-blue-600">💡 建议: {finding.suggestion}</p>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* 底部操作 */}
      <div className="mt-6 flex justify-end space-x-3">
        <button
          onClick={() => navigate(`/tasks/${id}/review`)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          进入专家复核
        </button>
      </div>
    </div>
  );
}
