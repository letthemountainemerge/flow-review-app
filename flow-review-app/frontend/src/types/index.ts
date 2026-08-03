export interface Section {
  title: string;
  level: number;
  content: string;
  anchor?: string;
}

export interface Role {
  name: string;
  duty?: string;
}

export interface FlowNode {
  id: string;
  name: string;
  node_type: string;
  lane_id?: string;
  outgoing: string[];
  incoming: string[];
  is_kcp: boolean;
  documentation: string;
}

export interface FlowEdge {
  id: string;
  source: string;
  target: string;
  name?: string;
}

export interface Swimlane {
  id: string;
  name: string;
  node_ids: string[];
}

export interface FindingLocation {
  document_type: string;
  section?: string;
  page?: number;
  node_id?: string;
  field_name?: string;
  line_number?: number;
  quote: string;
}

export interface Finding {
  finding_id: string;
  severity: '严重' | '一般' | '建议';
  description: string;
  location: FindingLocation;
  evidence: string;
  suggestion: string;
  confidence: number;
}

export interface DimensionResult {
  dimension_id: number;
  dimension_name: string;
  conclusion: '通过' | '不通过' | '需关注';
  score: number;
  findings: Finding[];
}

export interface ReviewReport {
  task_id: string;
  overall_conclusion: string;
  overall_score: number;
  dimension_results: DimensionResult[];
  summary: string;
}

export interface TaskInfo {
  id: string;
  name: string;
  status: string;
  created_at?: string;
  completed_at?: string;
  manual_file: string;
  diagram_file?: string;
  form_file?: string;
  requirement_file?: string;
}

export interface TaskListResponse {
  tasks: TaskInfo[];
  total: number;
}

export const DIMENSION_NAMES: Record<number, string> = {
  1: '流程是否充分实现了方案设计意图',
  2: '流程活动和角色职责是否匹配',
  3: '风险是否有效识别，KCP得到标识',
  4: '业务场景识别是否充分',
  5: '流程图设计是否规范',
  6: '流程绩效指标定义明确清晰',
  7: '表单、模板完整反映数据和信息要求',
  8: '复杂流程活动是否提供了标准附件',
};
