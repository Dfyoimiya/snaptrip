import type { CommonResult, CommonPage } from '@/types/common'
import type { PageParam } from '@/types/common'
import type { CmsSubject, CmsSubjectCategory } from '@/types/subject'
import request from '@/utils/request'

export function getSubjectListAllAPI() {
  return request<CommonResult<CmsSubject[]>>({
    url: '/subject/listAll',
    method: 'get',
  })
}

export function getSubjectListAPI(params: PageParam) {
  return request<CommonResult<CommonPage<CmsSubject>>>({
    url: '/subject/list',
    method: 'get',
    params,
  })
}

// 向后兼容别名（视图层使用）
export const fetchSubjectList = getSubjectListAPI

// 以下为 mock 函数（TODO: 后端对接后替换为真实接口）
import { ElMessage } from 'element-plus'

export function fetchSubjectCategoryList() {
  return Promise.resolve({ code: 200, data: [] as CmsSubjectCategory[], message: 'success' })
}

export function saveSubject() {
  ElMessage.success('保存成功（演示模式）')
  return Promise.resolve({ code: 200, data: null, message: 'success' })
}

export function deleteSubject() {
  ElMessage.success('删除成功（演示模式）')
  return Promise.resolve({ code: 200, data: null, message: 'success' })
}

export function updateSubjectRecommendStatus() {
  ElMessage.success('更新成功（演示模式）')
  return Promise.resolve({ code: 200, data: null, message: 'success' })
}

export function updateSubjectShowStatus() {
  ElMessage.success('更新成功（演示模式）')
  return Promise.resolve({ code: 200, data: null, message: 'success' })
}
