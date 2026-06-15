/** 菜单 */
export interface UmsMenu {
  id?: string
  parentId?: string
  title?: string
  name?: string
  icon?: string
  level?: number
  sort?: number
  hidden?: number
  createdAt?: string
  children?: UmsMenu[]
}

/** 菜单节点 */
export interface MenuNode {
  id: string
  title: string
  level: number
  name: string
  icon: string
  children?: MenuNode[]
}

/** 菜单树节点（后端返回） */
export interface UmsMenuNode extends UmsMenu {
  children?: UmsMenuNode[]
}
