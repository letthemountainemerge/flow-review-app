import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { listTasks, getReport } from '../../services/api';
import type { TaskInfo, ReviewReport } from '../../types';
import { DIMENSION_NAMES } from '../../types';

interface TaskReport {
  task: TaskInfo;
  report: ReviewReport | null;
  loading: boolean;
  error: string | null;
}

const CONCLUSION_COLORS: Record<string, string> = {
  '通过': 'text-green-600 bg-green-50',
  '不通过': 'text-red-600 bg-red-50',
  '需关注': 'text-yellow-600 bg-yellow-50',
};

function ScoreBar({ score, maxScore = 100 }: { score: number; maxScore?: number }) {
  const pct = Math.min((score / maxScore) * 100, 100);
  const color = score >= 80 ? 'bg-green-500' : score >= 60 ? 'bg-yellow-500' : 'bg-red-500';
  return (
    <div className="w-full bg-gray-100 rounded-full h-2">
      <div
        className={`${color} h-2 rounded-full transition-all duration-500`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export default function ResultsOverview() {
  const navigate = useNavigate();
  const [taskReports, setTaskReports] = useState<TaskReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadResults();
  }, []);

  async function loadResults() {
    setLoading(true);
    setError(null);
    try {
      const result = await listTasks({ status: 'completed', page_size: 100 });
      if (result.tasks.length === 0) {
        setTaskReports([]);
        setLoading(false);
        return;
      }

      const initial: TaskReport[] = result.tasks.map((task) => ({
        task,
        report: null,
        loading: true,
        error: null,
      }));
      setTaskReports(initial);

      // 逐个加载报告
      for (let i = 0; i < initial.length; i++) {
        try {
          const report = await getReport(initial[i].task.id);
          setTaskReports((prev) => {
            const next = [...prev];
            next[i] = { ...next[i], report, loading: false, error: null };
            return next;
          });
        } catch (err: any) {
          setTaskReports((prev) => {
            const next = [...prev];
            next[i] = {
              ...next[i],
              report: null,
              loading: false,
              error: err?.response?.data?.detail || '加载报告失败',
            };
            return next;
          });
        }
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '加载失败');
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="text-center py-16">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-500">正在加载评审结果...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-16 bg-white rounded-lg shadow-sm border border-red-200">
        <div className="text-4xl mb-3">⚠️</div>
        <p className="text-red-600 mb-2">加载失败</p>
        <p className="text-gray-500 text-sm mb-4">{error}</p>
        <button
          onClick={loadResults}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
        >
          重试
        </button>
      </div>
    );
  }

  if (taskReports.length === 0) {
    return (
      <div className="text-center py-16 bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="text-4xl mb-3">📭</div>
        <p className="text-gray-500">暂未完成任何评审，请先提交评审任务</p>
      </div>
    );
  }

  const totalTasks = taskReports.length;
  const passed = taskReports.filter((t) => t.report?.overall_conclusion === '通过').length;
  const failed = taskReports.filter((t) => t.report?.overall_conclusion === '不通过').length;
  const warning = taskReports.filter((t) => t.report?.overall_conclusion === '需关注').length;
  const avgScore =
    taskReports.reduce((sum, t) => sum + (t.report?.overall_score || 0), 0) / Math.max(totalTasks, 1);

  return (
    <div>
      {/* 统计概览 */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <p className="text-sm text-gray-500">评审任务数</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{totalTasks}</p>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <p className="text-sm text-gray-500">平均得分</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{avgScore.toFixed(1)}</p>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <p className="text-sm text-gray-500">结论分布</p>
          <div className="flex items-center space-x-3 mt-1">
            <span className="text-green-600 text-sm">✅ {passed}</span>
            <span className="text-red-600 text-sm">❌ {failed}</span>
            <span className="text-yellow-600 text-sm">⚠️ {warning}</span>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <p className="text-sm text-gray-500">最高分 / 最低分</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">
            {Math.max(...taskReports.map((t) => t.report?.overall_score || 0))}
            <span className="text-gray-300 mx-1">/</span>
            {Math.min(...taskReports.map((t) => t.report?.overall_score || 0))}
          </p>
        </div>
      </div>

      {/* 任务评审结果卡片 */}
      <div className="space-y-4">
        {taskReports.map((tr) => (
          <div
            key={tr.task.id}
            className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden"
          >
            <div
              className="px-6 py-4 cursor-pointer hover:bg-gray-50 transition-colors"
              onClick={() => navigate(`/tasks/${tr.task.id}/report`)}
            >
              <div className="flex items-center justify-between">
                {/* 左侧：任务信息 */}
                <div className="flex-1 min-w-0">
                  <h3 className="text-base font-semibold text-gray-900 truncate">
                    {tr.task.name}
                  </h3>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {tr.task.created_at
                      ? new Date(tr.task.created_at).toLocaleString('zh-CN')
                      : '-'}
                  </p>
                </div>

                {/* 右侧：评分与结论 */}
                {tr.loading ? (
                  <div className="flex items-center space-x-2 text-gray-400">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
                    <span className="text-sm">加载报告...</span>
                  </div>
                ) : tr.error ? (
                  <span className="text-sm text-red-500">{tr.error}</span>
                ) : tr.report ? (
                  <div className="flex items-center space-x-4">
                    <div className="text-right">
                      <span className="text-2xl font-bold text-gray-900">
                        {tr.report.overall_score}
                      </span>
                      <span className="text-sm text-gray-400">/100</span>
                    </div>
                    <span
                      className={`px-3 py-1 rounded-full text-sm font-medium ${
                        CONCLUSION_COLORS[tr.report.overall_conclusion] ||
                        'text-gray-600 bg-gray-50'
                      }`}
                    >
                      {tr.report.overall_conclusion || '未评定'}
                    </span>
                    <span className="text-gray-300">→</span>
                  </div>
                ) : null}
              </div>

              {/* 维度得分条 */}
              {tr.report && !tr.loading && (
                <div className="mt-3 grid grid-cols-4 gap-x-6 gap-y-2">
                  {tr.report.dimension_results.map((dim) => (
                    <div key={dim.dimension_id} className="flex items-center space-x-2">
                      <span
                        className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                          dim.conclusion === '通过'
                            ? 'bg-green-400'
                            : dim.conclusion === '不通过'
                            ? 'bg-red-400'
                            : 'bg-yellow-400'
                        }`}
                      />
                      <span className="text-xs text-gray-500 truncate flex-1" title={DIMENSION_NAMES[dim.dimension_id] || dim.dimension_name}>
                        {DIMENSION_NAMES[dim.dimension_id] || dim.dimension_name}
                      </span>
                      <span className="text-xs font-medium text-gray-700">
                        {dim.score}分
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {/* 总结摘要 */}
              {tr.report?.summary && !tr.loading && (
                <p className="mt-3 text-xs text-gray-500 line-clamp-1">
                  {tr.report.summary}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
