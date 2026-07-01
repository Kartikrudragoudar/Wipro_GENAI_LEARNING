export type Language = "Python" | "JavaScript" | "TypeScript" | "Java" | "C++";

export type AttemptStatus = "generated" | "validated" | "failed" | "improved" | "needs_review";

export type LoopStatus =
  | "waiting_for_input"
  | "analyzing"
  | "fix_generated"
  | "awaiting_validation_feedback"
  | "self_correcting"
  | "correction_complete"
  | "needs_another_loop";

export type AnalyzeRequest = {
  code: string;
  language: Language;
  error_message: string;
  user_context?: string;
};

export type CorrectionAttempt = {
  attempt_number: number;
  timestamp: string;
  status: AttemptStatus;
  bug_summary: string;
  root_cause: string;
  fixed_code: string;
  explanation: string;
  confidence_score: number;
  change_summary: string;
};

export type LoopTrace = {
  input_received: boolean;
  analysis_completed: boolean;
  correction_generated: boolean;
  validation_feedback_received: boolean;
  self_correction_completed: boolean;
  final_status: LoopStatus;
  cache_warmed?: number;
  high_confidence_exit?: boolean;
  auto_reanalyzed?: boolean;
  branched_from?: { original_session_id: string; attempt_number: number };
};

export type AnalyzeResponse = {
  session_id: string;
  bug_summary: string;
  root_cause: string;
  fixed_code: string;
  explanation: string;
  confidence_score: number;
  suggested_tests: string[];
  risks: string[];
  attempts: CorrectionAttempt[];
  loop_trace: LoopTrace;
};

export type SelfCorrectRequest = {
  session_id: string;
  original_code: string;
  previous_fixed_code: string;
  language: Language;
  test_output?: string;
  user_feedback?: string;
  attempt_number: number;
  previous_attempts: CorrectionAttempt[];
};

export type SelfCorrectResponse = {
  session_id: string;
  attempt: CorrectionAttempt;
  attempts: CorrectionAttempt[];
  loop_trace: LoopTrace;
  suggested_tests: string[];
  risks: string[];
};

export type SampleBug = {
  id: string;
  title: string;
  language: Language;
  code: string;
  error_message: string;
  user_context: string;
};

export type AssistantResponse = Pick<AnalyzeResponse, "bug_summary" | "root_cause" | "explanation" | "confidence_score" | "suggested_tests" | "risks">;

export type UploadedFile = {
  filename: string;
  content: string;
  size: number;
};

export type UploadResponse = {
  files: UploadedFile[];
  total_files: number;
  combined_code: string;
  primary_language: string;
};

export type CorrectionSession = {
  session_id: string;
  original_code: string;
  language: Language;
  error_message: string;
  user_context?: string;
  attempts: CorrectionAttempt[];
  current_attempt_number: number;
  loop_trace: LoopTrace;
  status: LoopStatus;
  assistant_response?: AssistantResponse;
};

// --- Agent workflow types ---

export type AgentAnalyzeRequest = {
  code: string;
  language: string;
  error_message: string;
  user_context?: string;
};

export type AgentAnalyzeResponse = {
  session_id: string;
  analysis: Record<string, unknown> | null;
  fixed_code: string | null;
  explanation: string | null;
  confidence_score: number;
  suggested_tests: string[];
  risks: string[];
  attempts: CorrectionAttempt[];
  loop_trace: LoopTrace;
  status: string;
  step: string;
};

export type AgentSelfCorrectRequest = {
  session_id: string;
  feedback: string;
};

export type AgentSelfCorrectResponse = AgentAnalyzeResponse;

export type CheckpointEntry = {
  attempt_number: number;
  created_at: number;
};

export type CheckpointListResponse = {
  session_id: string;
  checkpoints: CheckpointEntry[];
};

export type BranchRequest = {
  session_id: string;
  attempt_number: number;
};

// --- Multi-agent types ---

export type ReviewVerdict = {
  passed: boolean;
  issues: string[];
  reviewer_confidence: number;
  recommendation: "accept" | "revise" | "reject";
  lint_output?: string | null;
};

export type TestSuiteOutput = {
  tests: string[];
  test_strategy: string;
  coverage_notes: string;
};

export type MultiAgentAnalyzeResponse = AgentAnalyzeResponse & {
  reviewer_verdict: ReviewVerdict | null;
  test_suite: TestSuiteOutput | null;
  lint_output: string | null;
  tool_calls_trace: string[];
};

export type BranchResponse = {
  new_session_id: string;
  branched_from: string;
  attempt: number;
};

export type CacheStats = {
  active_sessions: number;
  total_checkpoints: number;
  max_size: number;
  ttl_seconds: number;
  db_size_kb: number;
};

export type SidebarView = "explorer" | "search" | "loop" | "problems";

export type Theme = "dark" | "light";
