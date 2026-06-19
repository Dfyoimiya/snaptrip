/**
 * ============================================
 * 省市区数据 —— CDN 动态加载 china-area-data
 * 首次加载后缓存在内存，后续组件复用
 *
 * v5 数据格式 (已嵌套为树):
 *   "86":     { "110000": "北京市", "130000": "河北省", ... }  省代码→省名
 *   "110000": { "110100": "市辖区" }                          市代码→市名
 *   "110100": { "110101": "东城区", "110102": "西城区", ... }  区代码→区名
 * ============================================
 */

export interface RegionItem {
  value: string
  label: string
  children?: RegionItem[]
}

const CDN_URL = 'https://cdn.jsdelivr.net/npm/china-area-data@5.0.0/v5/data.json'

type CodeMap = Record<string, string>
type TreeData = Record<string, CodeMap>

let cachedTree: RegionItem[] | null = null
let pendingPromise: Promise<RegionItem[]> | null = null

/** 获取省市区树 —— 首次调用从 CDN 拉取，之后走缓存 */
export async function fetchRegionTree(): Promise<RegionItem[]> {
  if (cachedTree) return cachedTree
  if (pendingPromise) return pendingPromise

  pendingPromise = (async () => {
    const resp = await fetch(CDN_URL)
    if (!resp.ok) throw new Error(`加载地区数据失败: HTTP ${resp.status}`)
    const raw: TreeData = await resp.json()
    cachedTree = buildTree(raw)
    return cachedTree
  })()

  return pendingPromise
}

/** 将 v5 嵌套数据转为 RegionItem 树 */
function buildTree(data: TreeData): RegionItem[] {
  const provinceMap = data['86']
  if (!provinceMap) throw new Error('地区数据格式无效')

  const directMunicipality = new Set(['北京市', '天津市', '上海市', '重庆市'])

  const result: RegionItem[] = []
  for (const [provCode, provName] of Object.entries(provinceMap)) {
    const cityMap = data[provCode]
    if (!cityMap) {
      result.push({ value: provName, label: provName })
      continue
    }

    const buildDistricts = (cityCode: string): RegionItem[] | undefined => {
      const dm = data[cityCode]
      if (!dm) return undefined
      const filtered = Object.entries(dm).filter(([_, n]) => n !== '市辖区')
      if (filtered.length === 0) return undefined
      return filtered.map(([_, n]) => ({ value: n, label: n }))
    }

    if (directMunicipality.has(provName)) {
      // 直辖市: 保留省→市→区三层结构，city 自动填充为省名
      const cityCode = Object.keys(cityMap)[0] // 只有一个 "市辖区"
      const districts = buildDistricts(cityCode)
      result.push({
        value: provName,
        label: provName,
        children: [{
          value: provName,
          label: provName,
          children: districts,
        }],
      })
    } else {
      // 普通省份: province → city → district
      const cityNodes: RegionItem[] = []
      for (const [cityCode, cityName] of Object.entries(cityMap)) {
        if (cityName === '市辖区') continue // 跳过占位伪城市
        cityNodes.push({
          value: cityName,
          label: cityName,
          children: buildDistricts(cityCode),
        })
      }
      result.push({
        value: provName,
        label: provName,
        children: cityNodes.length > 0 ? cityNodes : undefined,
      })
    }
  }

  return result
}
