/**
 * ============================================
 * 搜索建议 API
 * 自动补全、热门搜索、AI 建议
 * ============================================
 */

import { get, post } from '@/utils/request'

export interface SuggestQuery {
  query: string
  type: 'autocomplete' | 'trending' | 'ai' | 'history'
  frequency: number
  detail: string
}

export interface SuggestSection {
  section_type: 'autocomplete' | 'trending' | 'ai_suggestions' | 'history'
  title: string
  queries: SuggestQuery[]
}

export interface SuggestResponse {
  prefix: string
  sections: SuggestSection[]
  total_ms: number
}

/** 搜索框智能建议 — GET /portal/search/suggest */
export const getSearchSuggestAPI = (params: {
  prefix?: string
  limit?: number
}) => {
  return get<SuggestResponse>('/api/v1/portal/search/suggest', {
    prefix: params.prefix || '',
    limit: params.limit || 8,
  })
}

/** 记录搜索 — POST /portal/behaviors (通过 tracker 自动处理) */
export const recordSearchAPI = (keyword: string, filters?: Record<string, unknown>, resultCount?: number) => {
  // 搜索记录通过 BehaviorTracker 上报
  // 此处保留显式调用入口, 供特殊场景使用
  return post('/api/v1/portal/behaviors', {
    session_id: sessionStorage.getItem('_snaptrip_sid') || 'unknown',
    events: [{
      behavior_type: 'search',
      metadata: { keyword, filters, result_count: resultCount },
    }],
  })
}
