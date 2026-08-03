import { useState, useEffect } from 'react';

interface Settings {
  LLM_PROVIDER: string;
  LLM_API_KEY: string;
  LLM_MODEL: string;
  LLM_BASE_URL: string;
  AI_CONFIDENCE_THRESHOLD: number;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings>({
    LLM_PROVIDER: 'deepseek',
    LLM_API_KEY: '',
    LLM_MODEL: 'deepseek-chat',
    LLM_BASE_URL: 'https://api.deepseek.com',
    AI_CONFIDENCE_THRESHOLD: 0.7,
  });
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    // 从localStorage加载设置
    const saved = localStorage.getItem('review_settings');
    if (saved) {
      try {
        setSettings(JSON.parse(saved));
      } catch {}
    }
  }, []);

  function handleSave() {
    localStorage.setItem('review_settings', JSON.stringify(settings));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">系统设置</h1>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 space-y-5">
        <h2 className="text-lg font-semibold">大模型 API 配置</h2>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">提供商</label>
          <select
            value={settings.LLM_PROVIDER}
            onChange={(e) => setSettings({ ...settings, LLM_PROVIDER: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
          >
            <option value="deepseek">DeepSeek</option>
            <option value="qwen">通义千问</option>
            <option value="openai">OpenAI</option>
            <option value="anthropic">Claude (Anthropic)</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
          <input
            type="password"
            value={settings.LLM_API_KEY}
            onChange={(e) => setSettings({ ...settings, LLM_API_KEY: e.target.value })}
            placeholder="sk-..."
            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">模型名称</label>
          <input
            type="text"
            value={settings.LLM_MODEL}
            onChange={(e) => setSettings({ ...settings, LLM_MODEL: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">API 地址</label>
          <input
            type="text"
            value={settings.LLM_BASE_URL}
            onChange={(e) => setSettings({ ...settings, LLM_BASE_URL: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            AI 置信度阈值: {settings.AI_CONFIDENCE_THRESHOLD}
          </label>
          <input
            type="range"
            min="0.5"
            max="1.0"
            step="0.05"
            value={settings.AI_CONFIDENCE_THRESHOLD}
            onChange={(e) => setSettings({ ...settings, AI_CONFIDENCE_THRESHOLD: parseFloat(e.target.value) })}
            className="w-full"
          />
          <p className="text-xs text-gray-400 mt-1">低于此值的AI结论将标记为"需人工确认"</p>
        </div>

        <div className="flex justify-end pt-2">
          <button
            onClick={handleSave}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            {saved ? '已保存 ✓' : '保存设置'}
          </button>
        </div>
      </div>
    </div>
  );
}
