"use client";

import { useCallback, useEffect, useReducer, useRef } from "react";

import { apiClient } from "@/lib/api/client";
import { fallbackSamples } from "@/lib/samples/sampleBugs";
import type {
  AssistantResponse,
  CorrectionSession,
  Language,
  LoopStatus,
  MultiAgentAnalyzeResponse,
  SampleBug,
} from "@/lib/types/loop";
import type { EditorMode } from "@/components/editor/EditorTabs";

// --------------- State ---------------

export type CorrectionState = {
  samples: SampleBug[];
  originalCode: string;
  selectedLanguage: Language;
  errorMessage: string;
  userContext: string;
  session: CorrectionSession | undefined;
  feedback: string;
  mode: EditorMode;
  loading: boolean;
  error: string | undefined;
  logs: string[];
  useMultiAgent: boolean;
  multiAgentResult: MultiAgentAnalyzeResponse | undefined;
};

const initialState: CorrectionState = {
  samples: fallbackSamples,
  originalCode: fallbackSamples[0].code,
  selectedLanguage: fallbackSamples[0].language,
  errorMessage: fallbackSamples[0].error_message,
  userContext: fallbackSamples[0].user_context,
  session: undefined,
  feedback: "",
  mode: "original",
  loading: false,
  error: undefined,
  logs: ["Workspace initialized. Waiting for input loop."],
  useMultiAgent: false,
  multiAgentResult: undefined,
};

// --------------- Actions ---------------

type Action =
  | { type: "SELECT_SAMPLE"; sample: SampleBug }
  | { type: "SET_CODE"; code: string }
  | { type: "SET_LANGUAGE"; language: Language }
  | { type: "SET_ERROR_MESSAGE"; message: string }
  | { type: "SET_USER_CONTEXT"; context: string }
  | { type: "SET_FEEDBACK"; feedback: string }
  | { type: "SET_MODE"; mode: EditorMode }
  | { type: "SET_ATTEMPT"; attemptNumber: number }
  | { type: "START_LOADING"; log?: string }
  | { type: "SET_ERROR"; error: string; log?: string }
  | { type: "ANALYSIS_SUCCESS"; session: CorrectionSession }
  | { type: "SELF_CORRECT_SUCCESS"; session: CorrectionSession }
  | { type: "UPLOAD_SUCCESS"; code: string; language: Language; log: string }
  | { type: "ADD_LOG"; log: string }
  | { type: "RESET" }
  | { type: "BRANCH_SUCCESS"; newSessionId: string; log: string }
  | { type: "TOGGLE_MULTI_AGENT" }
  | { type: "MULTI_AGENT_SUCCESS"; result: MultiAgentAnalyzeResponse; session: CorrectionSession };

function reducer(state: CorrectionState, action: Action): CorrectionState {
  switch (action.type) {
    case "SELECT_SAMPLE":
      return {
        ...state,
        originalCode: action.sample.code,
        selectedLanguage: action.sample.language,
        errorMessage: action.sample.error_message,
        userContext: action.sample.user_context,
        mode: "original",
        error: undefined,
      };
    case "SET_CODE":
      return { ...state, originalCode: action.code };
    case "SET_LANGUAGE":
      return { ...state, selectedLanguage: action.language };
    case "SET_ERROR_MESSAGE":
      return { ...state, errorMessage: action.message };
    case "SET_USER_CONTEXT":
      return { ...state, userContext: action.context };
    case "SET_FEEDBACK":
      return { ...state, feedback: action.feedback };
    case "SET_MODE":
      return { ...state, mode: action.mode };
    case "SET_ATTEMPT":
      return state.session
        ? { ...state, session: { ...state.session, current_attempt_number: action.attemptNumber } }
        : state;
    case "START_LOADING":
      return {
        ...state,
        loading: true,
        error: undefined,
        logs: action.log ? [action.log, ...state.logs] : state.logs,
      };
    case "SET_ERROR":
      return {
        ...state,
        loading: false,
        error: action.error,
        logs: action.log ? [action.log, ...state.logs] : state.logs,
      };
    case "ANALYSIS_SUCCESS":
      return {
        ...state,
        loading: false,
        mode: "diff",
        session: action.session,
        logs: ["Correction generated. Awaiting validation feedback.", ...state.logs],
      };
    case "SELF_CORRECT_SUCCESS":
      return {
        ...state,
        loading: false,
        feedback: "",
        mode: "diff",
        session: action.session,
        logs: [
          `Attempt ${action.session.current_attempt_number} added to correction history.`,
          ...state.logs,
        ],
      };
    case "UPLOAD_SUCCESS":
      return {
        ...state,
        loading: false,
        originalCode: action.code,
        selectedLanguage: action.language,
        mode: "original",
        logs: [action.log, ...state.logs],
      };
    case "BRANCH_SUCCESS":
      return {
        ...state,
        logs: [action.log, ...state.logs],
      };
    case "TOGGLE_MULTI_AGENT":
      return { ...state, useMultiAgent: !state.useMultiAgent };
    case "MULTI_AGENT_SUCCESS":
      return {
        ...state,
        loading: false,
        mode: "diff",
        multiAgentResult: action.result,
        session: action.session,
        logs: ["Multi-agent analysis complete.", ...state.logs],
      };
    case "ADD_LOG":
      return { ...state, logs: [action.log, ...state.logs] };
    case "RESET":
      return {
        ...initialState,
        samples: state.samples,
      };
    default:
      return state;
  }
}

// --------------- Helpers ---------------

const languageFromString = (lang: string): Language => {
  const map: Record<string, Language> = {
    python: "Python",
    javascript: "JavaScript",
    typescript: "TypeScript",
    java: "Java",
    "c++": "C++",
  };
  return map[lang.toLowerCase()] ?? "Python";
};

// --------------- Hook ---------------

export function useCorrection() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  // --- Derived ---

  const activeAttempt = state.session?.attempts.find(
    (a) => a.attempt_number === state.session?.current_attempt_number,
  );
  const loopStatus: LoopStatus = state.session?.status ?? (state.loading ? "analyzing" : "waiting_for_input");
  const suggestedTests = state.session?.assistant_response?.suggested_tests ?? [];
  const canSelfCorrect = Boolean(state.session && activeAttempt && state.feedback.trim());

  // --- Validation ---

  const validate = useCallback((): string | null => {
    if (!state.originalCode.trim()) return "Code is required.";
    if (!state.errorMessage.trim()) return "Error message is required.";
    return null;
  }, [state.originalCode, state.errorMessage]);

  // --- Actions ---

  const selectSample = useCallback((sample: SampleBug) => {
    dispatch({ type: "SELECT_SAMPLE", sample });
  }, []);

  const setCode = useCallback((code: string) => dispatch({ type: "SET_CODE", code }), []);
  const setLanguage = useCallback((language: Language) => dispatch({ type: "SET_LANGUAGE", language }), []);
  const setErrorMessage = useCallback((message: string) => dispatch({ type: "SET_ERROR_MESSAGE", message }), []);
  const setUserContext = useCallback((context: string) => dispatch({ type: "SET_USER_CONTEXT", context }), []);
  const setFeedback = useCallback((feedback: string) => dispatch({ type: "SET_FEEDBACK", feedback }), []);
  const setMode = useCallback((mode: EditorMode) => dispatch({ type: "SET_MODE", mode }), []);
  const setAttempt = useCallback((n: number) => dispatch({ type: "SET_ATTEMPT", attemptNumber: n }), []);

  const analyze = useCallback(async () => {
    const validationError = validate();
    if (validationError) {
      dispatch({ type: "SET_ERROR", error: validationError });
      return;
    }

    if (state.useMultiAgent) {
      dispatch({ type: "START_LOADING", log: "Multi-agent pipeline started." });
      try {
        const response = await apiClient.agentMultiAnalyze({
          code: state.originalCode,
          language: state.selectedLanguage,
          error_message: state.errorMessage,
          user_context: state.userContext,
        });
        if (!mountedRef.current) return;

        const assistantResponse: AssistantResponse = {
          bug_summary: (response.analysis as Record<string, string> | null)?.bug_summary ?? "",
          root_cause: (response.analysis as Record<string, string> | null)?.root_cause ?? "",
          explanation: response.explanation ?? "",
          confidence_score: response.confidence_score,
          suggested_tests: response.suggested_tests,
          risks: response.risks,
        };

        dispatch({
          type: "MULTI_AGENT_SUCCESS",
          result: response,
          session: {
            session_id: response.session_id,
            original_code: state.originalCode,
            language: state.selectedLanguage as import("@/lib/types/loop").Language,
            error_message: state.errorMessage,
            user_context: state.userContext,
            attempts: response.attempts,
            current_attempt_number: response.attempts.at(-1)?.attempt_number ?? 1,
            loop_trace: response.loop_trace,
            status: response.status as import("@/lib/types/loop").LoopStatus,
            assistant_response: assistantResponse,
          },
        });
      } catch (err) {
        if (!mountedRef.current) return;
        if (err instanceof DOMException && err.name === "AbortError") return;
        dispatch({
          type: "SET_ERROR",
          error: err instanceof Error ? err.message : "Multi-agent request failed.",
          log: "Multi-agent pipeline failed.",
        });
      }
      return;
    }

    dispatch({ type: "START_LOADING", log: "Analysis loop started." });

    try {
      const response = await apiClient.analyze({
        code: state.originalCode,
        language: state.selectedLanguage,
        error_message: state.errorMessage,
        user_context: state.userContext,
      });
      if (!mountedRef.current) return;

      const assistantResponse: AssistantResponse = {
        bug_summary: response.bug_summary,
        root_cause: response.root_cause,
        explanation: response.explanation,
        confidence_score: response.confidence_score,
        suggested_tests: response.suggested_tests,
        risks: response.risks,
      };

      dispatch({
        type: "ANALYSIS_SUCCESS",
        session: {
          session_id: response.session_id,
          original_code: state.originalCode,
          language: state.selectedLanguage,
          error_message: state.errorMessage,
          user_context: state.userContext,
          attempts: response.attempts,
          current_attempt_number: response.attempts[0]?.attempt_number ?? 1,
          loop_trace: response.loop_trace,
          status: "awaiting_validation_feedback",
          assistant_response: assistantResponse,
        },
      });
    } catch (err) {
      if (!mountedRef.current) return;
      if (err instanceof DOMException && err.name === "AbortError") return;
      dispatch({
        type: "SET_ERROR",
        error: err instanceof Error ? err.message : "Analyze request failed.",
        log: "Analysis loop failed.",
      });
    }
  }, [state.originalCode, state.selectedLanguage, state.errorMessage, state.userContext, validate]);

  const selfCorrect = useCallback(async () => {
    if (!state.session || !activeAttempt) return;

    dispatch({ type: "START_LOADING", log: "Self-correction loop started from validation feedback." });

    try {
      const response = await apiClient.selfCorrect({
        session_id: state.session.session_id,
        original_code: state.session.original_code,
        previous_fixed_code: activeAttempt.fixed_code,
        language: state.session.language,
        test_output: state.feedback,
        user_feedback: state.feedback,
        attempt_number: activeAttempt.attempt_number,
        previous_attempts: state.session.attempts,
      });
      if (!mountedRef.current) return;

      const assistantResponse: AssistantResponse = {
        bug_summary: response.attempt.bug_summary,
        root_cause: response.attempt.root_cause,
        explanation: response.attempt.explanation,
        confidence_score: response.attempt.confidence_score,
        suggested_tests: response.suggested_tests,
        risks: response.risks,
      };

      dispatch({
        type: "SELF_CORRECT_SUCCESS",
        session: {
          ...state.session,
          attempts: response.attempts,
          current_attempt_number: response.attempt.attempt_number,
          loop_trace: response.loop_trace,
          status: response.loop_trace.final_status,
          assistant_response: assistantResponse,
        },
      });
    } catch (err) {
      if (!mountedRef.current) return;
      if (err instanceof DOMException && err.name === "AbortError") return;
      dispatch({
        type: "SET_ERROR",
        error: err instanceof Error ? err.message : "Self-correction request failed.",
        log: "Self-correction loop failed.",
      });
    }
  }, [state.session, state.feedback, activeAttempt]);

  const cancelRequest = useCallback(() => {
    apiClient.cancel();
    dispatch({ type: "SET_ERROR", error: "Request cancelled.", log: "Request cancelled by user." });
  }, []);

  const reset = useCallback(() => dispatch({ type: "RESET" }), []);

  const toggleMultiAgent = useCallback(() => dispatch({ type: "TOGGLE_MULTI_AGENT" }), []);

  const handleFileUpload = useCallback(async (file: File) => {
    dispatch({ type: "START_LOADING", log: `Uploading file: ${file.name}` });
    try {
      const result = await apiClient.uploadFile(file);
      if (!mountedRef.current) return;
      dispatch({
        type: "UPLOAD_SUCCESS",
        code: result.combined_code,
        language: languageFromString(result.primary_language),
        log: `File loaded: ${result.total_files} file(s), language: ${result.primary_language}`,
      });
    } catch (err) {
      if (!mountedRef.current) return;
      dispatch({ type: "SET_ERROR", error: err instanceof Error ? err.message : "File upload failed." });
    }
  }, []);

  const handleFolderUpload = useCallback(async (file: File) => {
    dispatch({ type: "START_LOADING", log: `Uploading folder zip: ${file.name}` });
    try {
      const result = await apiClient.uploadFolder(file);
      if (!mountedRef.current) return;
      dispatch({
        type: "UPLOAD_SUCCESS",
        code: result.combined_code,
        language: languageFromString(result.primary_language),
        log: `Folder loaded: ${result.total_files} file(s), language: ${result.primary_language}`,
      });
    } catch (err) {
      if (!mountedRef.current) return;
      dispatch({ type: "SET_ERROR", error: err instanceof Error ? err.message : "Folder upload failed." });
    }
  }, []);

  const handleMultipleFilesUpload = useCallback(async (files: File[]) => {
    dispatch({ type: "START_LOADING", log: `Uploading ${files.length} files...` });
    try {
      const result = await apiClient.uploadFiles(files);
      if (!mountedRef.current) return;
      dispatch({
        type: "UPLOAD_SUCCESS",
        code: result.combined_code,
        language: languageFromString(result.primary_language),
        log: `Files loaded: ${result.total_files} file(s), language: ${result.primary_language}`,
      });
    } catch (err) {
      if (!mountedRef.current) return;
      dispatch({ type: "SET_ERROR", error: err instanceof Error ? err.message : "Multi-file upload failed." });
    }
  }, []);

  const branchFromAttempt = useCallback(async (attemptNumber: number) => {
    if (!state.session) return;
    try {
      const result = await apiClient.branchFromCheckpoint({
        session_id: state.session.session_id,
        attempt_number: attemptNumber,
      });
      if (!mountedRef.current) return;
      dispatch({
        type: "BRANCH_SUCCESS",
        newSessionId: result.new_session_id,
        log: `Branched from attempt ${attemptNumber} → new session ${result.new_session_id.slice(0, 8)}`,
      });
    } catch {
      dispatch({ type: "ADD_LOG", log: `Branch from attempt ${attemptNumber} failed (checkpoint may not exist).` });
    }
  }, [state.session]);

  return {
    state,
    activeAttempt,
    loopStatus,
    suggestedTests,
    canSelfCorrect,
    // Actions
    selectSample,
    setCode,
    setLanguage,
    setErrorMessage,
    setUserContext,
    setFeedback,
    setMode,
    setAttempt,
    analyze,
    selfCorrect,
    cancelRequest,
    reset,
    toggleMultiAgent,
    handleFileUpload,
    handleFolderUpload,
    handleMultipleFilesUpload,
    branchFromAttempt,
  };
}
