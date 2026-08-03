import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getReport, submitFeedback } from '../../services/api';
import type { ReviewReport, Finding } from '../../types';
import { DIMENSION_NAMES } from '../../types';

const CORRECTION_TYPES: Record<string, string> = {
  false_positive: 'AI误报（实际已满足）',
  false_negative: 'AI漏报（应标记问题）',
  severity_wrong: '严重程度有误',
};

export default function ExpertReviewPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [report, setReport] = useState<ReviewReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [reviewedFindings, setReviewedFindings] = useState<Set<string>>(new Set());
  const [feedbackForm, setFeedbackForm] = useState<{
    finding_id: string;
    dimension_id: number;
    correction_type: string;
    expert_comment: string;
    ai_conclusion: string;
  } | null>(null);

  useEffect(() => {
    if (id) loadReport(id);
  }, [id]);

  async function loadReport(taskId: string) {
    setLoading(true);
    try {
      const data = await getReport(taskId);
      setReport(data);
    } catch (err) {
      console.error('加载报告失败:', err);
    } finally {
      setLoading(false);
    }
  }

  function getAllFindings(): Array<{ finding: Finding; dimId: number }> {
    if (!report) return [];
    const result: Array<{ finding: Finding; dimId: number }> = [];
    for (const dim of report.dimension_results) {
      for (const finding of dim.findings) {
        result.push({ finding, dimId: dim.dimension_id });
      }
    }
    return result;
  }

  async function handleConfirmCorrect(findingId: string, dimId: number) {
    try {
      await submitFeedback(id!, {
        finding_id: findingId,
        dimension_id: dimId,
        correction_type: 'confirmed',
        expert_comment: '专家确认AI评审正确',
        ai_conclusion: 'confirmed',
      });
      setReviewedFindings((prev) => new Set(prev).add(findingId));
    } catch (err) {
      console.error('提交反馈失败:', err);
    }
  }

  function openFeedbackDialog(findingId: string, dimId: number, aiConclusion: string) {
    setFeedbackForm({
      finding_id: findingId,
      dimension_id: dimId,
      correction_type: '',
      expert_comment: '',
      ai_conclusion: aiConclusion,
    });
  }

  async function handleSubmitCorrection() {
    if (!feedbackForm || !feedbackForm.correction_type) return;
    try {
      await submitFeedback(id!, feedbackForm);
      setReviewedFindings((prev) => new Set(prev).add(feedbackForm.finding_id));
      setFeedbackForm(null);
    } catch (err) {
      console.error('提交纠正失败:', err);
      alert('提交失败，请重试');
    }
  }

  if (loading) {
    return (
      <div className="text-center py-16">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-500">加载评审结果...</p>
      </div>
    );
  }

  if (!report) {
    return <div className="text-center py-16 text-gray-500">未找到评审报告</div>;
  }

  const allFindings = getAllFindings();
  const reviewedCount = reviewedFindings.size;
  const totalCount = allFindings.length;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">专家复核</h1>
          <p className="text-sm text-gray-500 mt-1">
            已复核 {reviewedCount}/{totalCount} 条意见
          </p>
          {/* 进度条 */}
          <div className="w-48 h-1.5 bg-gray-200 rounded-full mt-2">
            <div
              className="h-full bg-blue-600 rounded-full transition-all"
              style={{ width: `${totalCount > 0 ? (reviewedCount / totalCount) * 100 : 0}%` }}
            />
          </div>
        </div>
        <button
          onClick={() => navigate(`/tasks/${id}/report`)}
          className="text-blue-600 hover:text-blue-800 text-sm"
        >
          ← 返回报告
        </button>
      </div>

      {/* AI意见列表 */}
      <div className="space-y-4">
        {allFindings.map(({ finding, dimId }) => {
          const isReviewed = reviewedFindings.has(finding.finding_id);
          return (
            <div
              key={finding.finding_id}
              className={`bg-white rounded-lg shadow-sm border p-5 ${
                isReviewed ? 'border-green-300 bg-green-50' : 'border-gray-200'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-1">
                    <span className="text-xs text-gray-500">
                      维度{dimId}: {DIMENSION_NAMES[dimId]}
                    </span>
                    <span className={`text-xs px-1.5 py-0.5 rounded ${
                      finding.severity === '严重' ? 'bg-red-100 text-red-700' :
                      finding.severity === '一般' ? 'bg-yellow-100 text-yellow-700' :
                      'bg-blue-100 text-blue-700'
                    }`}>
                      {finding.severity}
                    </span>
                    {isReviewed && <span className="text-xs text-green-600">✓ 已复核</span>}
                  </div>
                  <p className="text-sm text-gray-900 mt-1">{finding.description}</p>
                  {finding.suggestion && (
                    <p className="text-xs text-blue-600 mt-1">💡 {finding.suggestion}</p>
                  )}
                </div>
                <div className="flex space-x-2 ml-4">
                  {!isReviewed && (
                    <>
                      <button
                        onClick={() => handleConfirmCorrect(finding.finding_id, dimId)}
                        className="px-3 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200"
                      >
                        ✓ 确认正确
                      </button>
                      <button
                        onClick={() => openFeedbackDialog(finding.finding_id, dimId, finding.severity)}
                        className="px-3 py-1 text-xs bg-yellow-100 text-yellow-700 rounded hover:bg-yellow-200"
                      >
                        ✎ 纠正
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {allFindings.length === 0 && (
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
          <div className="text-4xl mb-3">🎉</div>
          <p className="text-gray-500">该报告无发现项，无需复核</p>
        </div>
      )}

      {/* 纠正弹窗 */}
      {feedbackForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold mb-4">纠正AI评审意见</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">纠正类型</label>
                <select
                  value={feedbackForm.correction_type}
                  onChange={(e) => setFeedbackForm({ ...feedbackForm, correction_type: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                >
                  <option value="">请选择...</option>
                  {Object.entries(CORRECTION_TYPES).map(([key, label]) => (
                    <option key={key} value={key}>{label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">专家意见</label>
                <textarea
                  value={feedbackForm.expert_comment}
                  onChange={(e) => setFeedbackForm({ ...feedbackForm, expert_comment: e.target.value })}
                  rows={3}
                  placeholder="请输入您的评审意见..."
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => setFeedbackForm(null)}
                  className="px-4 py-2 text-sm text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200"
                >
                  取消
                </button>
                <button
                  onClick={handleSubmitCorrection}
                  disabled={!feedbackForm.correction_type}
                  className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  提交纠正
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
