import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { listTasks, deleteTask } from '../../services/api';
import type { TaskInfo } from '../../types';
import StatusBadge from '../../components/StatusBadge';
import ResultsOverview from './ResultsOverview';

export default function HomePage() {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState<TaskInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState('');

  useEffect(() => {
    if (filterStatus === 'results') return;
    loadTasks();
  }, [filterStatus]);

  async function loadTasks() {
    setLoading(true);
    setError(null);
    try {
      const result = await listTasks({ status: filterStatus || undefined });
      setTasks(result.tasks);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || '无法连接到评审服务，请确认后端已启动';
      console.error('加载任务列表失败:', msg);
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('确定删除该任务？')) return;
    try {
      await deleteTask(id);
      loadTasks();
    } catch (err) {
      console.error('删除失败:', err);
    }
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">评审任务列表</h1>
        <button
          onClick={() => navigate('/tasks/new')}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          + 新建评审任务
        </button>
      </div>

      {/* 状态筛选 */}
      <div className="flex space-x-2 mb-4">
        {['', 'pending', 'reviewing', 'completed', 'failed', 'results'].map((s) => (
          <button
            key={s}
            onClick={() => setFilterStatus(s)}
            className={`px-3 py-1.5 rounded-md text-sm ${
              filterStatus === s
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-600 border border-gray-300 hover:bg-gray-50'
            }`}
          >
            {s === '' ? '全部' : s === 'pending' ? '待处理' : s === 'reviewing' ? '评审中' : s === 'completed' ? '已完成' : s === 'failed' ? '失败' : '评审结果'}
          </button>
        ))}
      </div>

      {/* 任务列表 */}
      {/* 评审结果视图 */}
      {filterStatus === 'results' ? (
        <ResultsOverview />
      ) : loading ? (
        <div className="text-center py-16 text-gray-500">加载中...</div>
      ) : error ? (
        <div className="text-center py-16 bg-white rounded-lg shadow-sm border border-red-200">
          <div className="text-4xl mb-3">⚠️</div>
          <p className="text-red-600 mb-2">加载失败</p>
          <p className="text-gray-500 text-sm mb-4">{error}</p>
          <button
            onClick={loadTasks}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
          >
            重试
          </button>
        </div>
      ) : tasks.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="text-4xl mb-3">📭</div>
          <p className="text-gray-500 mb-4">暂无评审任务</p>
          <button
            onClick={() => navigate('/tasks/new')}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
          >
            创建第一个评审任务
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">任务名称</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">状态</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">说明书</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">流程图</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">创建时间</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {tasks.map((task) => (
                <tr key={task.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <button
                      onClick={() => task.status === 'completed' ? navigate(`/tasks/${task.id}/report`) : null}
                      className="text-blue-600 hover:text-blue-800 font-medium"
                    >
                      {task.name}
                    </button>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <StatusBadge status={task.status} />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{task.manual_file}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{task.diagram_file || '-'}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {task.created_at ? new Date(task.created_at).toLocaleString('zh-CN') : '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                    {task.status === 'completed' && (
                      <>
                        <button
                          onClick={() => navigate(`/tasks/${task.id}/report`)}
                          className="text-blue-600 hover:text-blue-800 mr-3"
                        >
                          查看报告
                        </button>
                        <button
                          onClick={() => navigate(`/tasks/${task.id}/review`)}
                          className="text-green-600 hover:text-green-800 mr-3"
                        >
                          复核
                        </button>
                      </>
                    )}
                    <button
                      onClick={() => handleDelete(task.id)}
                      className="text-red-500 hover:text-red-700"
                    >
                      删除
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
