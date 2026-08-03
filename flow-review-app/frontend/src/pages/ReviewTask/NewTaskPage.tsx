import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createTask, startReview, getTaskStatus } from '../../services/api';

const FILE_TYPES: Record<string, string> = {
  manual: '.md,.docx',
  diagram: '.bpmn,.vsdx,.png,.jpg,.jpeg',
  form: '.xlsx,.csv',
  requirement: '.md,.docx',
};

const FILE_LABELS: Record<string, string> = {
  manual: '流程说明书',
  diagram: '流程图',
  form: '表单模板（可选）',
  requirement: '需求文档（可选）',
};

const FILE_HINTS: Record<string, string> = {
  manual: '支持 Markdown (.md) 或 Word (.docx)',
  diagram: '优先 BPMN (.bpmn)，兼容 Visio (.vsdx) 或图片',
  form: '支持 Excel (.xlsx) 或 CSV (.csv)',
  requirement: '支持 Markdown (.md) 或 Word (.docx)',
};

export default function NewTaskPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState<'upload' | 'submitting' | 'reviewing' | 'done'>('upload');
  const [taskId, setTaskId] = useState<string>('');
  const [taskName, setTaskName] = useState('');
  const [files, setFiles] = useState<Record<string, File | null>>({
    manual: null,
    diagram: null,
    form: null,
    requirement: null,
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  function handleFileChange(key: string, file: File | null) {
    setFiles((prev) => ({ ...prev, [key]: file }));
    setErrors((prev) => ({ ...prev, [key]: '' }));
  }

  function validate(): boolean {
    const newErrors: Record<string, string> = {};

    if (!taskName.trim()) {
      newErrors.name = '请输入任务名称';
    }
    // 测试阶段不强制要求任何文件上传

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  function pollReviewStatus(id: string) {
    const interval = setInterval(async () => {
      try {
        const task = await getTaskStatus(id);
        if (task.status === 'completed') {
          clearInterval(interval);
          setStep('done');
        } else if (task.status === 'failed') {
          clearInterval(interval);
          alert('评审失败，请稍后重试');
          setStep('upload');
        }
        // reviewing / parsing 状态继续轮询
      } catch {
        clearInterval(interval);
        alert('获取评审状态失败');
        setStep('upload');
      }
    }, 3000); // 每 3 秒轮询一次

    // 60 秒后自动停止轮询（防止无限挂起）
    setTimeout(() => clearInterval(interval), 120000);
  }

  async function handleSubmit() {
    if (!validate()) return;
    setStep('submitting');

    try {
      const formData = new FormData();
      formData.append('name', taskName.trim());
      for (const [key, file] of Object.entries(files)) {
        if (file) formData.append(`${key}_file`, file);
      }

      const task = await createTask(formData);
      setTaskId(task.id);
      setStep('reviewing');

      // 启动后台评审（立即返回，不阻塞）
      await startReview(task.id);

      // 轮询等待评审完成
      pollReviewStatus(task.id);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err.message || '创建失败';
      alert('评审任务失败: ' + msg);
      setStep('upload');
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">新建评审任务</h1>

      {/* 步骤指示器 */}
      <div className="flex items-center mb-8">
        {['上传文件', '创建任务', '评审分析', '完成'].map((label, i) => {
          const isActive =
            (i === 0 && step === 'upload') ||
            (i === 1 && step === 'submitting') ||
            (i === 2 && step === 'reviewing') ||
            (i === 3 && step === 'done');
          const isDone =
            (i === 0 && step !== 'upload') ||
            (i === 1 && ['reviewing', 'done'].includes(step)) ||
            (i === 2 && step === 'done');
          return (
            <div key={i} className="flex items-center">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                isActive
                  ? 'bg-blue-600 text-white'
                  : isDone
                  ? 'bg-green-500 text-white'
                  : 'bg-gray-200 text-gray-500'
              }`}>
                {isDone ? '✓' : i + 1}
              </div>
              <span className="ml-2 text-sm text-gray-600">{label}</span>
              {i < 3 && <div className="w-8 h-px bg-gray-300 mx-2" />}
            </div>
          );
        })}
      </div>

      {step === 'upload' && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          {/* 任务名称 */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              任务名称 <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={taskName}
              onChange={(e) => { setTaskName(e.target.value); setErrors(prev => ({...prev, name: ''})); }}
              placeholder="例如：采购审批流程评审"
              className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                errors.name ? 'border-red-300' : 'border-gray-300'
              }`}
            />
            {errors.name && <p className="mt-1 text-sm text-red-500">{errors.name}</p>}
          </div>

          {/* 文件上传区 */}
          <div className="grid grid-cols-2 gap-4">
            {Object.entries(FILE_LABELS).map(([key, label]) => (
              <div key={key} className="col-span-2 sm:col-span-1">
                <label className="block text-sm font-medium mb-2 text-gray-500">
                  {label}
                </label>
                <label className={`flex flex-col items-center justify-center h-32 border-2 border-dashed rounded-lg cursor-pointer transition-colors ${
                  errors[key]
                    ? 'border-red-300 bg-red-50'
                    : files[key]
                    ? 'border-green-300 bg-green-50'
                    : 'border-gray-300 hover:border-blue-400 bg-gray-50 hover:bg-gray-100'
                }`}>
                  {files[key] ? (
                    <div className="text-center">
                      <div className="text-sm font-medium text-green-700">{files[key]!.name}</div>
                      <div className="text-xs text-gray-500 mt-1">{(files[key]!.size / 1024).toFixed(1)} KB</div>
                    </div>
                  ) : (
                    <div className="text-center">
                      <div className="text-2xl mb-1">📎</div>
                      <div className="text-sm text-gray-500">点击或拖拽上传</div>
                      <div className="text-xs text-gray-400 mt-1">{FILE_HINTS[key]}</div>
                    </div>
                  )}
                  <input
                    type="file"
                    accept={FILE_TYPES[key]}
                    onChange={(e) => handleFileChange(key, e.target.files?.[0] || null)}
                    className="hidden"
                  />
                </label>
                {errors[key] && <p className="mt-1 text-sm text-red-500">{errors[key]}</p>}
              </div>
            ))}
          </div>

          <div className="mt-6 flex justify-end space-x-3">
            <button
              onClick={() => navigate('/')}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
            >
              取消
            </button>
            <button
              onClick={handleSubmit}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              开始解析并评审
            </button>
          </div>
        </div>
      )}

      {step === 'submitting' && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600 text-lg">正在创建任务并解析文件...</p>
          <p className="text-gray-400 text-sm mt-2">请稍候，创建完成后自动开始评审</p>
        </div>
      )}

      {step === 'reviewing' && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600 text-lg">正在分析评审...</p>
          <p className="text-gray-400 text-sm mt-2">AI 正在对流程文件进行多维度分析，请稍候</p>
        </div>
      )}

      {step === 'done' && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
          <div className="text-5xl mb-4">✅</div>
          <p className="text-gray-900 text-lg font-medium">评审完成</p>
          <p className="text-gray-500 text-sm mt-2">任务已创建并评审完毕</p>
          <div className="mt-6 space-x-3">
            <button
              onClick={() => navigate('/tasks/' + taskId + '/report')}
              className="px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              查看评审报告
            </button>
            <button
              onClick={() => navigate('/')}
              className="px-5 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
            >
              返回任务列表
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
