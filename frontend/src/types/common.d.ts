/** 通用分页参数（匹配后端 snake_case） */
export interface PageParam {
  keyword?: string
  page: number
  page_size: number
}

/** 通用分页结果（匹配后端 PaginatedResponse，经 camelCase 转换后） */
export interface CommonPage<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

/** 通用接口响应 */
export interface CommonResult<T> {
  code: number
  data: T
  message: string
}

/** 级联选择数据 */
export interface ElCascaderDataVo {
  label: string
  value: string
  children?: ElCascaderDataVo[]
}

/** 下拉选择数据 */
export interface ElSelectDataVo {
  label: string
  value: string
}
