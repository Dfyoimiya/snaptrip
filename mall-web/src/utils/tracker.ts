/**
 * ============================================
 * 行为追踪埋点 SDK
 *
 * 前端无侵入埋点工具:
 *   - trackView(productId)       — 商品浏览
 *   - trackSearch(keyword)        — 搜索
 *   - trackAddCart(productId)     — 加购
 *   - trackPurchase(orderId, ids) — 购买
 *
 * 批量上报 (debounce 2s), 失败静默。
 * ============================================
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
const BEHAVIOR_ENDPOINT = `${API_BASE}/api/v1/portal/behaviors`
const BATCH_INTERVAL = 2000  // 2s 批量上报间隔
const MAX_BATCH_SIZE = 50

interface BehaviorEvent {
  behavior_type: string
  item_id?: string | null
  item_type?: string | null
  metadata?: Record<string, unknown> | null
}

function generateSessionId(): string {
  let sid = sessionStorage.getItem('_snaptrip_sid')
  if (!sid) {
    sid = crypto.randomUUID?.() || Date.now().toString(36) + Math.random().toString(36).slice(2)
    sessionStorage.setItem('_snaptrip_sid', sid)
  }
  return sid
}

class BehaviorTracker {
  private queue: BehaviorEvent[] = []
  private timer: ReturnType<typeof setTimeout> | null = null
  private sessionId: string

  constructor() {
    this.sessionId = generateSessionId()
    // 页面卸载时立即 flush
    if (typeof window !== 'undefined') {
      window.addEventListener('beforeunload', () => this.flush())
      window.addEventListener('pagehide', () => this.flush())
    }
  }

  track(behaviorType: string, itemId?: string, itemType?: string, metadata?: Record<string, unknown>) {
    this.queue.push({
      behavior_type: behaviorType,
      item_id: itemId || null,
      item_type: itemType || null,
      metadata: metadata || null,
    })
    if (this.queue.length >= MAX_BATCH_SIZE) {
      this.flush()
    } else {
      this.scheduleFlush()
    }
  }

  private scheduleFlush() {
    if (this.timer) return
    this.timer = setTimeout(() => {
      this.timer = null
      this.flush()
    }, BATCH_INTERVAL)
  }

  private async flush() {
    if (this.timer) {
      clearTimeout(this.timer)
      this.timer = null
    }
    if (this.queue.length === 0) return

    const batch = this.queue.splice(0, MAX_BATCH_SIZE)
    try {
      await fetch(BEHAVIOR_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: this.sessionId,
          events: batch,
        }),
        // fire-and-forget: 不阻塞主线程
        keepalive: true,
      })
    } catch {
      // 静默失败 — 埋点不影响业务
    }
  }
}

// ── 全局单例 ──
const tracker = new BehaviorTracker()

// ── 公共 API ──

/** 商品浏览 */
export function trackView(productId: string) {
  tracker.track('view', productId, 'product')
}

/** 搜索 */
export function trackSearch(keyword: string, filters?: Record<string, unknown>, resultCount?: number) {
  tracker.track('search', undefined, undefined, { keyword, filters, result_count: resultCount })
}

/** 加入购物车 */
export function trackAddCart(productId: string, skuId?: string) {
  tracker.track('add_cart', productId, 'product', { sku_id: skuId })
}

/** 完成购买 */
export function trackPurchase(orderId: string, productIds: string[]) {
  tracker.track('purchase', orderId, 'order', { product_ids: productIds })
}

/** 收藏商品 */
export function trackFavorite(productId: string) {
  tracker.track('favorite', productId, 'product')
}

export default tracker
