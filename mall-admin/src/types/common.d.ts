/** 通用分页参数 */
export interface PageParam {
  keyword?: string
  pageNum: number
  pageSize: number
}

/** 通用分页结果 */
export interface CommonPage<T> {
  list: T[]
  total: number
  pageNum: number
  pageSize: number
  totalPage: number
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
  value: number
  children?: ElCascaderDataVo[]
}

/** 下拉选择数据 */
export interface ElSelectDataVo {
  label: string
  value: string
}
