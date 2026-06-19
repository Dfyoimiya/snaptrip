/** 管理员 */
export interface UmsAdmin {
  id?: string
  email?: string
  password?: string
  isActive?: boolean
  createdAt?: string
  roles?: Array<{ id: string; name: string }>
  roleIds?: string[]
}
