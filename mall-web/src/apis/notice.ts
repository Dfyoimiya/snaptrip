import { get } from '@/utils/request'

export interface NoticeItem {
  id: string
  title: string
  content: string
  categoryName: string
  status: number
  createdAt: string
}

export interface NoticePage {
  items: NoticeItem[]
  total: number
  page: number
  pageSize: number
}

/** 公告分页列表 —— GET /api/v1/portal/notices */
export function getNoticeListAPI(params: { page?: number; page_size?: number }) {
  return get<NoticePage>('/api/v1/portal/notices', {
    page: params.page ?? 1,
    page_size: params.page_size ?? 20,
  })
}

/** 公告详情 —— GET /api/v1/portal/notices/{id} */
export function getNoticeDetailAPI(id: string) {
  return get<NoticeItem>('/api/v1/portal/notices/' + id)
}
