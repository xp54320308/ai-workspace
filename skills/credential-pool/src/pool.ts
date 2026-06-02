/**
 * Credential Pool
 * 
 * API Key 轮换池，借鉴 Hermes Agent 的 CredentialPool。
 * 支持多 Key 权重分配、故障隔离、自动恢复检测。
 */

export interface ApiKey {
  id: string;
  key: string;
  weight: number;
}

export interface KeyHealth {
  id: string;
  state: "healthy" | "rate_limited" | "exhausted" | "error";
  failures: number;
  lastFailure: number | null;
  lastSuccess: number | null;
  requestCount: number;
  disabledUntil: number | null; // timestamp
}

export interface ProviderPool {
  provider: string;
  keys: ApiKey[];
  health: Map<string, KeyHealth>;
}

export class CredentialPool {
  private pools: Map<string, ProviderPool> = new Map();
  
  // Track global jitter counter for decorrelation
  private jitterCounter = 0;
  
  addProvider(provider: string, keys: ApiKey[]): void {
    const health = new Map<string, KeyHealth>();
    
    for (const key of keys) {
      health.set(key.id, {
        id: key.id,
        state: "healthy",
        failures: 0,
        lastFailure: null,
        lastSuccess: null,
        requestCount: 0,
        disabledUntil: null,
      });
    }
    
    this.pools.set(provider, { provider, keys, health });
  }
  
  /**
   * 获取当前可用 Key（权重随机 + 健康检查）
   */
  getKey(provider: string): ApiKey | null {
    const pool = this.pools.get(provider);
    if (!pool || pool.keys.length === 0) {
      return null;
    }
    
    // Filter to available keys (not rate limited or exhausted)
    const now = Date.now();
    const available = pool.keys.filter(k => {
      const h = pool.health.get(k.id);
      if (!h) return true;
      if (h.disabledUntil && h.disabledUntil > now) return false;
      if (h.state === "exhausted") return false;
      return true;
    });
    
    if (available.length === 0) {
      // All keys are down, return the least-bad one
      const sorted = [...pool.keys].sort((a, b) => {
        const ha = pool.health.get(a.id);
        const hb = pool.health.get(b.id);
        return (ha?.failures || 0) - (hb?.failures || 0);
      });
      return sorted[0] || null;
    }
    
    // Weight-based random selection
    const totalWeight = available.reduce((sum, k) => sum + k.weight, 0);
    let rand = Math.random() * totalWeight;
    
    for (const key of available) {
      rand -= key.weight;
      if (rand <= 0) {
        return key;
      }
    }
    
    return available[available.length - 1];
  }
  
  /**
   * 报告 Key 使用成功
   */
  reportSuccess(provider: string, keyId: string): void {
    const pool = this.pools.get(provider);
    if (!pool) return;
    
    const h = pool.health.get(keyId);
    if (!h) return;
    
    h.state = "healthy";
    h.failures = Math.max(0, h.failures - 1); // Decay
    h.lastSuccess = Date.now();
    h.requestCount++;
    
    // Clear any temporary disable
    if (h.state !== "rate_limited") {
      h.disabledUntil = null;
    }
  }
  
  /**
   * 报告 Key 使用失败（可分类）
   */
  reportFailure(
    provider: string,
    keyId: string,
    failureType: "rate_limit" | "error" | "exhausted"
  ): void {
    const pool = this.pools.get(provider);
    if (!pool) return;
    
    const h = pool.health.get(keyId);
    if (!h) return;
    
    h.failures++;
    h.lastFailure = Date.now();
    h.requestCount++;
    
    switch (failureType) {
      case "rate_limit":
        h.state = "rate_limited";
        // Temporarily disable for 30-60 seconds (jitter)
        this.jitterCounter++;
        const jitter = 30000 + (this.jitterCounter % 30000);
        h.disabledUntil = Date.now() + jitter;
        break;
      
      case "exhausted":
        h.state = "exhausted";
        // Long-term disable (5 minutes)
        h.disabledUntil = Date.now() + 5 * 60 * 1000;
        break;
      
      case "error":
        h.state = "error";
        if (h.failures >= 5) {
          // Too many errors, disable temporarily
          h.disabledUntil = Date.now() + 60000;
        }
        break;
    }
  }
  
  /**
   * 检查被禁用的 Key 是否已恢复
   */
  checkRecovery(provider: string): void {
    const pool = this.pools.get(provider);
    if (!pool) return;
    
    const now = Date.now();
    
    for (const [keyId, h] of pool.health.entries()) {
      if (h.disabledUntil && h.disabledUntil <= now) {
        // Try to re-enable
        if (h.state === "rate_limited") {
          h.state = "healthy";
          h.disabledUntil = null;
        } else if (h.state === "exhausted" && h.failures < 3) {
          h.state = "healthy";
          h.disabledUntil = null;
        }
      }
    }
  }
  
  /**
   * 获取池状态摘要
   */
  getStatus(provider?: string): Record<string, KeyHealth[]> {
    const result: Record<string, KeyHealth[]> = {};
    
    const providers = provider ? [provider] : [...this.pools.keys()];
    
    for (const p of providers) {
      const pool = this.pools.get(p);
      if (!pool) continue;
      
      result[p] = [...pool.health.values()];
    }
    
    return result;
  }
  
  /**
   * 重置池状态
   */
  reset(provider?: string): void {
    if (provider) {
      const pool = this.pools.get(provider);
      if (pool) {
        for (const h of pool.health.values()) {
          h.state = "healthy";
          h.failures = 0;
          h.disabledUntil = null;
        }
      }
    } else {
      for (const pool of this.pools.values()) {
        for (const h of pool.health.values()) {
          h.state = "healthy";
          h.failures = 0;
          h.disabledUntil = null;
        }
      }
    }
  }
}

// ── Singleton for global use ─────────────────────────────────────────────────

let globalPool: CredentialPool | null = null;

export function getGlobalPool(): CredentialPool {
  if (!globalPool) {
    globalPool = new CredentialPool();
  }
  return globalPool;
}
