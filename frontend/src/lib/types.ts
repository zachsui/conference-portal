export type TimeOfDay = "morning" | "afternoon" | "evening";
export type Level = "beginner" | "intermediate" | "advanced";
export type CapacityStatus = "available" | "almost_full" | "full";

export interface Session {
  session_id: string;
  title: string;
  description: string;
  track: string;
  topic: string;
  date: string;
  start_time: string;
  end_time: string;
  time_of_day: TimeOfDay;
  room: string;
  speaker: string;
  company: string;
  level: Level;
  capacity: number;
  registered_count: number;
}

export interface CapacityInfo {
  session_id: string;
  capacity: number;
  registered_count: number;
  seats_remaining: number;
  status: CapacityStatus;
}

export interface Registration {
  registration_id: string;
  attendee_id: string;
  session_id: string;
  created_at: string;
}

export interface AgendaItem {
  registration_id: string;
  session: Session;
}

export interface ApiErrorDetail {
  error: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface ApiError {
  status: number;
  detail: ApiErrorDetail | string;
}

export interface Attendee {
  attendee_id: string;
  email: string;
  name: string;
  company?: string | null;
  role?: string | null;
  created_at: string;
}

export interface ToolCallTrace {
  step_number: number;
  tool_name: string;
  arguments: Record<string, unknown>;
  result: unknown;
  success: boolean;
  latency_ms: number;
  error?: string | null;
}

export interface PolicyViolation {
  rule: string;
  detail: string;
  tool_name?: string | null;
}

export type ChatStatus = "completed" | "clarification_needed" | "failed";

export interface PendingAction {
  attendee_id: string;
  action: "register_session";
  session_id: string;
  session_title?: string | null;
  created_at: string;
  expires_after_minutes: number;
}

export interface ChatResponse {
  trace_id: string;
  user_message: string;
  tool_calls: ToolCallTrace[];
  final_answer: string;
  status: ChatStatus;
  policy_violations: PolicyViolation[];
  pending_action_before?: PendingAction | null;
  pending_action_after?: PendingAction | null;
  confirmation_detected?: boolean;
}
