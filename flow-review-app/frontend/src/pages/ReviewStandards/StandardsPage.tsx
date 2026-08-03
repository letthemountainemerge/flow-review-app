import { useEffect, useState } from 'react';
import axios from 'axios';

interface RuleItem {
  index: string;
  content: string;
}

interface SectionItem {
  title: string;
  rules: RuleItem[];
}

interface CategoryItem {
  title: string;
  sections: SectionItem[];
}

interface StandardsContent {
  title: string;
  source_count: number;
  categories: CategoryItem[];
}

const categoryIcons: Record<string, string> = {
  '流程完整性规范': '🔗',
  '判断节点规范': '🔀',
};

const categoryColors: Record<string, string> = {
  '流程完整性规范': 'border-l-blue-500',
  '判断节点规范': 'border-l-amber-500',
};

const docTypeLabels: Record<string, { label: string; color: string }> = {
  standard: { label: '规范文档', color: 'bg-blue-100 text-blue-700' },
  example: { label: '范例说明书', color: 'bg-green-100 text-green-700' },
  checklist: { label: '评审清单', color: 'bg-purple-100 text-purple-700' },
};

export default function StandardsPage() {
  const [content, setContent] = useState<StandardsContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [title, setTitle] = useState('');
  const [docType, setDocType] = useState('standard');
  const [showUpload, setShowUpload] = useState(false);

  useEffect(() => {
    loadContent();
  }, []);

  async function loadContent() {
    setLoading(true);
    try {
      const { data } = await axios.get('/api/standards/content');
      setContent(data);
    } catch (err) {
      console.error('加载评审标准失败:', err);
    } finally {
      setLoading(false);
    }
  }

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    const fileInput = document.getElementById('standard-file-upload') as HTMLInputElement;
    const file = fileInput?.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('title', title || file.name);
      formData.append('doc_type', docType);
      await axios.post('/api/standards/upload', formData);
      setTitle('');
      fileInput.value = '';
      setShowUpload(false);
      loadContent();
    } catch (err) {
      console.error('上传失败:', err);
      alert('上传失败');
    } finally {
      setUploading(false);
    }
  }

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto flex items-center justify-center py-20">
        <div className="text-center">
          <div className="inline-block w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <p className="mt-3 text-sm text-gray-500">加载评审标准...</p>
        </div>
      </div>
    );
  }

  if (!content || content.categories.length === 0) {
    return (
      <div className="max-w-3xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">评审标准</h1>
        <div className="bg-white rounded-lg border border-gray-200 text-center py-16">
          <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
            <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          <p className="text-gray-400 mb-4">暂无评审标准</p>
          <button
            onClick={() => setShowUpload(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium transition-colors"
          >
            录入第一条评审标准
          </button>

          {showUpload && (
            <div className="mt-6 mx-10">
              <UploadForm
                title={title} setTitle={setTitle}
                docType={docType} setDocType={setDocType}
                uploading={uploading}
                onUpload={handleUpload}
                onCancel={() => setShowUpload(false)}
              />
            </div>
          )}
        </div>
      </div>
    );
  }

  const totalRules = content.categories.reduce(
    (sum, c) => sum + c.sections.reduce((s, sec) => s + sec.rules.length, 0),
    0
  );

  return (
    <div className="max-w-4xl mx-auto pb-10">
      {/* 页头 */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">评审标准</h1>
          <p className="text-sm text-gray-500 mt-1">
            {content.source_count > 0
              ? `已整合 ${content.source_count} 份标准文档，共 ${content.categories.length} 项分类 ${totalRules} 条规则`
              : '尚未录入评审标准'}
          </p>
        </div>
        <button
          onClick={() => setShowUpload(!showUpload)}
          className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M12 4v16m8-8H4" />
          </svg>
          录入标准
        </button>
      </div>

      {/* 录入表单（可折叠） */}
      {showUpload && (
        <div className="bg-white rounded-lg border border-gray-200 mb-8 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-medium text-gray-800">录入新的评审标准文档</h3>
            <span className="text-xs text-gray-400">支持 .md / .docx / .txt / .json</span>
          </div>
          <UploadForm
            title={title} setTitle={setTitle}
            docType={docType} setDocType={setDocType}
            uploading={uploading}
            onUpload={handleUpload}
            onCancel={() => setShowUpload(false)}
          />
        </div>
      )}

      {/* 分类卡片 */}
      <div className="space-y-6">
        {content.categories.map((cat, ci) => (
          <div
            key={ci}
            className={`bg-white rounded-lg border border-gray-200 border-l-4 ${
              categoryColors[cat.title] || 'border-l-gray-300'
            } overflow-hidden shadow-sm`}
          >
            {/* 分类标题 */}
            <div className="px-6 py-4 bg-gray-50/80 border-b border-gray-100">
              <div className="flex items-center gap-2.5">
                <span className="text-xl">{categoryIcons[cat.title] || '📋'}</span>
                <div>
                  <h2 className="font-semibold text-gray-900">{cat.title}</h2>
                  <span className="text-xs text-gray-400">
                    {cat.sections.length} 个章节 · {cat.sections.reduce((s, sec) => s + sec.rules.length, 0)} 条规则
                  </span>
                </div>
              </div>
            </div>

            {/* 章节列表 */}
            <div className="px-6 py-2 divide-y divide-gray-50">
              {cat.sections.map((sec, si) => (
                <div key={si} className="py-4">
                  <h3 className="text-sm font-medium text-gray-700 mb-3 flex items-center">
                    <span className="w-1.5 h-1.5 rounded-full bg-gray-300 mr-2.5" />
                    {sec.title}
                  </h3>
                  <ul className="space-y-2.5 ml-6">
                    {sec.rules.map((rule, ri) => (
                      <li key={ri} className="flex items-start gap-3 text-sm text-gray-600">
                        <span className="flex-shrink-0 inline-flex items-center justify-center w-5 h-5 rounded-full bg-gray-100 text-gray-500 text-[10px] font-mono font-medium mt-0.5">
                          {ci + 1}
                        </span>
                        <span className="leading-relaxed">{rule.content}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---- 上传表单子组件 ---- */
function UploadForm({
  title, setTitle, docType, setDocType,
  uploading, onUpload, onCancel,
}: {
  title: string; setTitle: (v: string) => void;
  docType: string; setDocType: (v: string) => void;
  uploading: boolean;
  onUpload: (e: React.FormEvent) => void;
  onCancel: () => void;
}) {
  return (
    <form onSubmit={onUpload}>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            规则名称 <span className="text-gray-400 font-normal">（可选）</span>
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="如：采购流程审批规范"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">规则类型</label>
          <select
            value={docType}
            onChange={(e) => setDocType(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          >
            {Object.entries(docTypeLabels).map(([key, { label }]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <label className="flex-1 flex items-center justify-center px-4 py-2 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors">
          <svg className="w-5 h-5 mr-2 text-gray-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          <span className="text-sm text-gray-500" id="file-name-hint">点击选择文件或拖拽到此处</span>
          <input
            id="standard-file-upload"
            type="file"
            accept=".md,.docx,.txt,.json"
            className="hidden"
            onChange={(e) => {
              const name = e.target.files?.[0]?.name || '点击选择文件或拖拽到此处';
              const hint = document.getElementById('file-name-hint');
              if (hint) hint.textContent = name;
            }}
          />
        </label>
        <button
          type="submit"
          disabled={uploading}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium transition-colors"
        >
          {uploading ? '上传中...' : '确认录入'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-sm text-gray-500 hover:text-gray-700 transition-colors"
        >
          取消
        </button>
      </div>
    </form>
  );
}
