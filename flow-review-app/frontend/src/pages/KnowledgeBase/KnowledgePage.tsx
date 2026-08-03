import { useEffect, useState } from 'react';
import axios from 'axios';

interface KnowledgeDoc {
  id: string;
  title: string;
  doc_type: string;
  file_path: string;
  chunk_count: number;
  uploaded_at?: string;
}

export default function KnowledgePage() {
  const [docs, setDocs] = useState<KnowledgeDoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [title, setTitle] = useState('');
  const [docType, setDocType] = useState('standard');

  useEffect(() => {
    loadDocs();
  }, []);

  async function loadDocs() {
    setLoading(true);
    try {
      const { data } = await axios.get('/api/knowledge');
      setDocs(data.documents);
    } catch (err) {
      console.error('加载知识库失败:', err);
    } finally {
      setLoading(false);
    }
  }

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    const fileInput = document.getElementById('file-upload') as HTMLInputElement;
    const file = fileInput?.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('title', title || file.name);
      formData.append('doc_type', docType);
      await axios.post('/api/knowledge/upload', formData);
      setTitle('');
      fileInput.value = '';
      loadDocs();
    } catch (err) {
      console.error('上传失败:', err);
      alert('上传失败');
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(docId: string) {
    if (!confirm('确定删除该文档？')) return;
    try {
      await axios.delete(`/api/knowledge/${docId}`);
      loadDocs();
    } catch (err) {
      console.error('删除失败:', err);
    }
  }

  async function handleRebuild() {
    if (!confirm('确定重建索引？')) return;
    try {
      await axios.post('/api/knowledge/rebuild');
      alert('索引重建成功');
      loadDocs();
    } catch (err) {
      console.error('重建失败:', err);
    }
  }

  const docTypeLabels: Record<string, string> = {
    standard: '规范文档',
    example: '范例说明书',
    checklist: '评审清单',
  };

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">知识库管理</h1>

      {/* 上传区 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">上传评审标准文档</h2>
        <form onSubmit={handleUpload} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">文档标题</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="可选，默认使用文件名"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">文档类型</label>
              <select
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              >
                {Object.entries(docTypeLabels).map(([key, label]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <input
              id="file-upload"
              type="file"
              accept=".md,.docx,.txt,.json"
              className="flex-1 text-sm"
            />
            <button
              type="submit"
              disabled={uploading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm"
            >
              {uploading ? '上传中...' : '上传'}
            </button>
          </div>
        </form>
      </div>

      {/* 文档列表 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="flex justify-between items-center px-6 py-4 border-b border-gray-200">
          <h2 className="font-semibold">已上传文档 ({docs.length})</h2>
          <button
            onClick={handleRebuild}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            重建索引
          </button>
        </div>
        {loading ? (
          <div className="text-center py-8 text-gray-500">加载中...</div>
        ) : docs.length === 0 ? (
          <div className="text-center py-8 text-gray-400">暂无文档，请上传评审标准文档</div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">标题</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">类型</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">分片数</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {docs.map((doc) => (
                <tr key={doc.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">{doc.title}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">{docTypeLabels[doc.doc_type] || doc.doc_type}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">{doc.chunk_count}</td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={() => handleDelete(doc.id)}
                      className="text-red-500 hover:text-red-700 text-sm"
                    >
                      删除
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
