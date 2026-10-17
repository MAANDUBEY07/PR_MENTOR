export type AnalysisMode = 'demo' | 'live';
export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'informational';
export type VerificationStatus = 'verified' | 'needs_review' | 'unsupported';
export type FindingSource = 'static_analysis' | 'ai_candidate' | 'test_evidence' | 'combined' | 'demo';

export interface PullRequestMetadata {
  repository_owner: string;
  repository_name: string;
  repository_url: string;
  pull_request_number: number;
  pull_request_url: string;
  title: string;
  description: string | null;
  author: string | null;
  base_branch: string | null;
  head_branch: string | null;
  head_sha: string | null;
  state: string;
  changed_files: number;
  additions: number;
  deletions: number;
  repository?: string;
  pull_request_title?: string;
  url?: string;
}

export interface ReviewFinding {
  id: string;
  title: string;
  description: string;
  file_path: string;
  line_start: number | null;
  line_end: number | null;
  severity: Severity;
  category: 'bug' | 'security' | 'performance' | 'maintainability' | 'code_quality' | 'testing' | 'documentation' | 'learning';
  confidence: number;
  source: FindingSource;
  verification_status: VerificationStatus;
  evidence: string[];
  why_it_matters: string;
  suggested_fix: string;
  learning_explanation: string;
  limitations: string[];
  file?: string;
  line?: number | string;
  text?: string;
  proof?: string;
  status?: string;
  severity_label?: string;
}

export interface ReviewResponse {
  review_id: string;
  status: string;
  analysis_mode: AnalysisMode;
  is_demo: boolean;
  pull_request: PullRequestMetadata;
  summary: string;
  findings: ReviewFinding[];
  verification_summary: Record<string, number>;
  tool_results: ToolResult[];
  warnings: string[];
  created_at: string;
  duration_ms: number;
  diff_files?: DiffFile[];
  repository?: string;
  pull_request_title?: string;
  pull_request_number?: number;
  url?: string;
}

export interface ToolResult {
  tool: string;
  status: string;
  reason?: string;
  message?: string;
  executed?: boolean;
  exit_code?: number;
  files_received?: number;
  analyzable_patch_files?: number;
  findings?: Array<Record<string, unknown>>;
}

export interface DiffLine {
  kind: 'added' | 'removed' | 'context';
  line: number;
  text: string;
}

export interface DiffHunk {
  header: string;
  lines: DiffLine[];
}

export interface DiffFile {
  path: string;
  previous_path?: string | null;
  status: string;
  added: number;
  removed: number;
  hunks: DiffHunk[];
  truncated: boolean;
}

export interface DiffResponse {
  review_id: string;
  files: DiffFile[];
  warnings: string[];
}

export interface SavedPullRequest {
  saved_id: string;
  url: string;
  temporary: boolean;
}

export interface LearningExercise {
  id: string;
  title: string;
  description: string;
  language: string;
  difficulty: string;
  category: string;
  instructions: string;
  code_snippet: string;
  hints: string[];
  options: string[];
  learning_objectives: string[];
}

export interface LearningResult {
  correct: boolean;
  explanation: string;
  feedback: string;
  points: number;
  progress: LearningProgress;
}

export interface LearningProgress {
  temporary: boolean;
  exercises_completed: number;
  correct_answers: number;
  attempt_count: number;
  accuracy: number;
  topics_practiced: Record<string, number>;
}

export interface LearningHistory {
  temporary: boolean;
  attempts: Array<{ exercise_id: string; category: string; correct: boolean }>;
}

export interface ApiErrorBody {
  detail?: string | Array<{ msg?: string }>;
  error?: { message?: string };
}
