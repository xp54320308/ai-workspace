/**
 * Error Classifier
 * 
 * 细粒度 API 错误分类，借鉴 Hermes Agent 的 FailoverReason 枚举。
 * 为每个错误提供明确的恢复策略建议。
 */

// ── Error Types ──────────────────────────────────────────────────────────────

export enum FailoverReason {
  // Authentication
  AUTH = "auth",
  AUTH_PERMANENT = "auth_permanent",
  
  // Billing / Quota
  BILLING = "billing",
  RATE_LIMIT = "rate_limit",
  
  // Server-side
  OVERLOADED = "overloaded",
  SERVER_ERROR = "server_error",
  
  // Transport
  TIMEOUT = "timeout",
  
  // Context / Payload
  CONTEXT_OVERFLOW = "context_overflow",
  PAYLOAD_TOO_LARGE = "payload_too_large",
  
  // Model
  MODEL_NOT_FOUND = "model_not_found",
  
  // Request format
  FORMAT_ERROR = "format_error",
  
  // Provider-specific
  THINKING_SIGNATURE = "thinking_signature",
  LONG_CONTEXT_TIER = "long_context_tier",
  
  // Catch-all
  UNKNOWN = "unknown",
}

// ── Classification Result ─────────────────────────────────────────────────────

export interface ClassifiedError {
  reason: FailoverReason;
  status_code: number | null;
  message: string;
  
  // Recovery hints
  retryable: boolean;
  should_compress: boolean;
  should_rotate_credential: boolean;
  should_fallback: boolean;
  
  // Human-readable recovery recommendation
  recovery: string;
}

// ── Pattern Definitions ──────────────────────────────────────────────────────

const BILLING_PATTERNS = [
  "insufficient credits", "insufficient_quota", "credit balance",
  "credits have been exhausted", "top up your credits", "payment required",
  "billing hard limit", "exceeded your current quota",
  "account is deactivated", "plan does not include",
];

const RATE_LIMIT_PATTERNS = [
  "rate limit", "rate_limit", "too many requests", "throttled",
  "requests per minute", "tokens per minute", "requests per day",
  "try again in", "please retry after", "resource_exhausted",
  "rate increased too quickly",
];

const AUTH_PATTERNS = [
  "invalid api key", "invalid_api_key", "authentication",
  "unauthorized", "forbidden", "invalid token", "token expired",
  "token revoked", "access denied",
];

const CONTEXT_OVERFLOW_PATTERNS = [
  "context length", "context size", "maximum context", "token limit",
  "too many tokens", "reduce the length", "exceeds the limit",
  "context window", "prompt is too long", "prompt exceeds max length",
  "max_tokens", "maximum number of tokens",
  // Chinese
  "超过最大长度", "上下文长度",
];

const MODEL_NOT_FOUND_PATTERNS = [
  "is not a valid model", "invalid model", "model not found",
  "model_not_found", "does not exist", "no such model",
  "unknown model", "unsupported model",
];

const TRANSPORT_ERROR_TYPES = new Set([
  "ReadTimeout", "ConnectTimeout", "PoolTimeout",
  "ConnectError", "RemoteProtocolError",
  "ConnectionError", "ConnectionResetError",
  "ConnectionAbortedError", "BrokenPipeError",
]);

// ── Classifier ────────────────────────────────────────────────────────────────

export function classifyError(error: unknown): ClassifiedError {
  // Handle string errors
  if (typeof error === "string") {
    return classifyErrorMessage(error, null);
  }
  
  // Handle Error objects
  if (error instanceof Error) {
    const statusCode = extractStatusCode(error.message);
    const result = classifyErrorMessage(error.message, statusCode);
    
    // Check for transport errors by type name
    if (result.reason === FailoverReason.UNKNOWN) {
      const errName = error.constructor?.name || "";
      if (TRANSPORT_ERROR_TYPES.has(errName)) {
        return {
          ...result,
          reason: FailoverReason.TIMEOUT,
          recovery: "连接超时，建议重建客户端后重试",
        };
      }
    }
    
    return result;
  }
  
  // Handle objects with message field
  if (typeof error === "object" && error !== null && "message" in error) {
    const msg = String((error as any).message);
    const statusCode = extractStatusCode(msg);
    return classifyErrorMessage(msg, statusCode);
  }
  
  // Unknown shape
  return {
    reason: FailoverReason.UNKNOWN,
    status_code: null,
    message: String(error),
    retryable: true,
    should_compress: false,
    should_rotate_credential: false,
    should_fallback: false,
    recovery: "未知错误，建议重试",
  };
}

function classifyErrorMessage(
  message: string,
  statusCode: number | null
): ClassifiedError {
  const lower = message.toLowerCase();
  
  // Status code based classification
  if (statusCode !== null) {
    switch (statusCode) {
      case 401:
      case 403:
        return {
          reason: FailoverReason.AUTH,
          status_code: statusCode,
          message,
          retryable: true,
          should_compress: false,
          should_rotate_credential: true,
          should_fallback: false,
          recovery: "认证失败，建议刷新/轮换凭证后重试",
        };
      
      case 402:
      case 402: // Payment required
        return {
          reason: FailoverReason.BILLING,
          status_code: statusCode,
          message,
          retryable: false,
          should_compress: false,
          should_rotate_credential: true,
          should_fallback: true,
          recovery: "配额/计费问题，立即切换 API Key 或 Provider",
        };
      
      case 429:
        return {
          reason: FailoverReason.RATE_LIMIT,
          status_code: statusCode,
          message,
          retryable: true,
          should_compress: false,
          should_rotate_credential: false,
          should_fallback: true,
          recovery: "限流，建议退避后重试或切换模型",
        };
      
      case 500:
      case 502:
        return {
          reason: FailoverReason.SERVER_ERROR,
          status_code: statusCode,
          message,
          retryable: true,
          should_compress: false,
          should_rotate_credential: false,
          should_fallback: false,
          recovery: "服务器内部错误，等待后重试",
        };
      
      case 503:
      case 529:
        return {
          reason: FailoverReason.OVERLOADED,
          status_code: statusCode,
          message,
          retryable: true,
          should_compress: false,
          should_rotate_credential: false,
          should_fallback: true,
          recovery: "服务过载，建议退避后重试或切换 Provider",
        };
      
      case 413:
        return {
          reason: FailoverReason.PAYLOAD_TOO_LARGE,
          status_code: statusCode,
          message,
          retryable: true,
          should_compress: true,
          should_rotate_credential: false,
          should_fallback: false,
          recovery: "请求体太大，建议压缩上下文后重试",
        };
      
      case 404:
        // Could be model not found
        if (MODEL_NOT_FOUND_PATTERNS.some(p => lower.includes(p))) {
          return {
            reason: FailoverReason.MODEL_NOT_FOUND,
            status_code: statusCode,
            message,
            retryable: false,
            should_compress: false,
            should_rotate_credential: false,
            should_fallback: true,
            recovery: "模型不存在，切换到 fallback 模型",
          };
        }
        break;
      
      case 400:
        if (lower.includes("thinking") && lower.includes("signature")) {
          return {
            reason: FailoverReason.THINKING_SIGNATURE,
            status_code: statusCode,
            message,
            retryable: false,
            should_compress: false,
            should_rotate_credential: false,
            should_fallback: true,
            recovery: "Thinking 块签名无效，切换模型",
          };
        }
        return {
          reason: FailoverReason.FORMAT_ERROR,
          status_code: statusCode,
          message,
          retryable: false,
          should_compress: false,
          should_rotate_credential: false,
          should_fallback: true,
          recovery: "请求格式错误，尝试移除问题部分后重试",
        };
    }
  }
  
  // Pattern-based classification (no status code)
  
  // Billing patterns
  if (BILLING_PATTERNS.some(p => lower.includes(p))) {
    return {
      reason: FailoverReason.BILLING,
      status_code: null,
      message,
      retryable: false,
      should_compress: false,
      should_rotate_credential: true,
      should_fallback: true,
      recovery: "配额耗尽，立即切换 API Key 或 Provider",
    };
  }
  
  // Rate limit patterns
  if (RATE_LIMIT_PATTERNS.some(p => lower.includes(p))) {
    return {
      reason: FailoverReason.RATE_LIMIT,
      status_code: null,
      message,
      retryable: true,
      should_compress: false,
      should_rotate_credential: false,
      should_fallback: true,
      recovery: "限流，抖动退避后重试或切换模型",
    };
  }
  
  // Auth patterns
  if (AUTH_PATTERNS.some(p => lower.includes(p))) {
    return {
      reason: FailoverReason.AUTH,
      status_code: null,
      message,
      retryable: true,
      should_compress: false,
      should_rotate_credential: true,
      should_fallback: false,
      recovery: "认证失败，轮换凭证后重试",
    };
  }
  
  // Context overflow patterns
  if (CONTEXT_OVERFLOW_PATTERNS.some(p => lower.includes(p))) {
    return {
      reason: FailoverReason.CONTEXT_OVERFLOW,
      status_code: null,
      message,
      retryable: true,
      should_compress: true,
      should_rotate_credential: false,
      should_fallback: false,
      recovery: "上下文太长，建议启用上下文压缩后重试",
    };
  }
  
  // Model not found patterns
  if (MODEL_NOT_FOUND_PATTERNS.some(p => lower.includes(p))) {
    return {
      reason: FailoverReason.MODEL_NOT_FOUND,
      status_code: null,
      message,
      retryable: false,
      should_compress: false,
      should_rotate_credential: false,
      should_fallback: true,
      recovery: "模型不存在，切换到 fallback 模型",
    };
  }
  
  // Default
  return {
    reason: FailoverReason.UNKNOWN,
    status_code: statusCode,
    message,
    retryable: true,
    should_compress: false,
    should_rotate_credential: false,
    should_fallback: false,
    recovery: "未知错误，可尝试重试",
  };
}

function extractStatusCode(message: string): number | null {
  // Try to extract HTTP status code from error message
  const match = message.match(/\b([4-5]\d{2})\b/);
  if (match) {
    const code = parseInt(match[1], 10);
    if (code >= 400 && code < 600) {
      return code;
    }
  }
  return null;
}

// ── Recovery Action Helpers ───────────────────────────────────────────────────

export function getRecoveryActions(result: ClassifiedError): string[] {
  const actions: string[] = [];
  
  if (result.should_compress) {
    actions.push("compress_context");
  }
  
  if (result.should_rotate_credential) {
    actions.push("rotate_api_key");
  }
  
  if (result.should_fallback) {
    actions.push("fallback_model");
  }
  
  if (result.retryable) {
    actions.push("retry_with_backoff");
  }
  
  if (actions.length === 0) {
    actions.push("abort_and_report");
  }
  
  return actions;
}
