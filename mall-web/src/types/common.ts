/**
 * ============================================
 * 通用类型定义
 * 对应后端 CommonResult<T> 和 CommonPage<T>
 * ============================================
 */

/** 通用返回结果封装类 */
export interface CommonResult<T = unknown> {
  /** 状态码 */
  code: number
  /** 提示信息 */
  message: string
  /** 封装数据 */
  data: T
}

/** 通用分页结果封装类 */
export interface CommonPage<T> {
  /** 当前页码 */
  pageNum: number
  /** 每页数量 */
  pageSize: number
  /** 总页数 */
  totalPage: number
  /** 总条数 */
  total: number
  /** 分页数据 */
  list: T[]
}

/** 通用分页请求参数 */
export interface PageParam {
  /** 当前页码，从1开始 */
  pageNum: number
  /** 每页数量，默认10 */
  pageSize: number
  /** 查询关键字 */
  keyword?: string
}

/** API 响应类型别名 */
export type ApiResult<T> = Promise<CommonResult<T>>
