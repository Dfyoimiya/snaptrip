/** 首页专题推荐 */
export interface SmsHomeRecommendSubject {
  id?: number
  subjectId?: number
  subjectName?: string
  recommendStatus?: number
  sort?: number
  createTime?: string
}

/** 专题推荐查询参数 */
export interface HomeSubjectQueryParam {
  subjectName?: string
  recommendStatus?: number
  pageNum: number
  pageSize: number
}
