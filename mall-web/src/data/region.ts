/**
 * ============================================
 * 省市区级联选择器数据
 * ============================================
 */

export interface RegionItem {
  value: string
  label: string
  children?: RegionItem[]
}

export const provinceData: RegionItem[] = [
  {
    value: '北京市', label: '北京市',
    children: [
      { value: '北京市', label: '北京市', children: [
        { value: '朝阳区', label: '朝阳区' },
        { value: '海淀区', label: '海淀区' },
        { value: '东城区', label: '东城区' },
        { value: '西城区', label: '西城区' },
        { value: '丰台区', label: '丰台区' },
        { value: '通州区', label: '通州区' },
        { value: '昌平区', label: '昌平区' },
        { value: '大兴区', label: '大兴区' },
        { value: '石景山区', label: '石景山区' },
        { value: '顺义区', label: '顺义区' },
      ]},
    ],
  },
  {
    value: '上海市', label: '上海市',
    children: [
      { value: '上海市', label: '上海市', children: [
        { value: '浦东新区', label: '浦东新区' },
        { value: '黄浦区', label: '黄浦区' },
        { value: '静安区', label: '静安区' },
        { value: '徐汇区', label: '徐汇区' },
        { value: '长宁区', label: '长宁区' },
        { value: '普陀区', label: '普陀区' },
        { value: '虹口区', label: '虹口区' },
        { value: '杨浦区', label: '杨浦区' },
        { value: '闵行区', label: '闵行区' },
        { value: '宝山区', label: '宝山区' },
        { value: '松江区', label: '松江区' },
      ]},
    ],
  },
  {
    value: '广东省', label: '广东省',
    children: [
      { value: '深圳市', label: '深圳市', children: [
        { value: '南山区', label: '南山区' },
        { value: '福田区', label: '福田区' },
        { value: '罗湖区', label: '罗湖区' },
        { value: '宝安区', label: '宝安区' },
        { value: '龙岗区', label: '龙岗区' },
        { value: '龙华区', label: '龙华区' },
        { value: '盐田区', label: '盐田区' },
        { value: '坪山区', label: '坪山区' },
      ]},
      { value: '广州市', label: '广州市', children: [
        { value: '天河区', label: '天河区' },
        { value: '越秀区', label: '越秀区' },
        { value: '海珠区', label: '海珠区' },
        { value: '荔湾区', label: '荔湾区' },
        { value: '白云区', label: '白云区' },
        { value: '番禺区', label: '番禺区' },
        { value: '黄埔区', label: '黄埔区' },
      ]},
      { value: '东莞市', label: '东莞市', children: [
        { value: '南城区', label: '南城区' },
        { value: '东城区', label: '东城区' },
        { value: '莞城区', label: '莞城区' },
      ]},
    ],
  },
  {
    value: '浙江省', label: '浙江省',
    children: [
      { value: '杭州市', label: '杭州市', children: [
        { value: '西湖区', label: '西湖区' },
        { value: '上城区', label: '上城区' },
        { value: '拱墅区', label: '拱墅区' },
        { value: '滨江区', label: '滨江区' },
        { value: '萧山区', label: '萧山区' },
        { value: '余杭区', label: '余杭区' },
      ]},
      { value: '宁波市', label: '宁波市', children: [
        { value: '海曙区', label: '海曙区' },
        { value: '江北区', label: '江北区' },
        { value: '鄞州区', label: '鄞州区' },
      ]},
    ],
  },
  {
    value: '江苏省', label: '江苏省',
    children: [
      { value: '南京市', label: '南京市', children: [
        { value: '玄武区', label: '玄武区' },
        { value: '秦淮区', label: '秦淮区' },
        { value: '建邺区', label: '建邺区' },
        { value: '鼓楼区', label: '鼓楼区' },
        { value: '雨花台区', label: '雨花台区' },
      ]},
      { value: '苏州市', label: '苏州市', children: [
        { value: '姑苏区', label: '姑苏区' },
        { value: '虎丘区', label: '虎丘区' },
        { value: '工业园区', label: '工业园区' },
      ]},
    ],
  },
  {
    value: '四川省', label: '四川省',
    children: [
      { value: '成都市', label: '成都市', children: [
        { value: '锦江区', label: '锦江区' },
        { value: '青羊区', label: '青羊区' },
        { value: '金牛区', label: '金牛区' },
        { value: '武侯区', label: '武侯区' },
        { value: '成华区', label: '成华区' },
        { value: '高新区', label: '高新区' },
      ]},
    ],
  },
  {
    value: '湖北省', label: '湖北省',
    children: [
      { value: '武汉市', label: '武汉市', children: [
        { value: '江岸区', label: '江岸区' },
        { value: '江汉区', label: '江汉区' },
        { value: '硚口区', label: '硚口区' },
        { value: '武昌区', label: '武昌区' },
        { value: '洪山区', label: '洪山区' },
      ]},
    ],
  },
  {
    value: '陕西省', label: '陕西省',
    children: [
      { value: '西安市', label: '西安市', children: [
        { value: '雁塔区', label: '雁塔区' },
        { value: '碑林区', label: '碑林区' },
        { value: '未央区', label: '未央区' },
        { value: '莲湖区', label: '莲湖区' },
      ]},
    ],
  },
]

/** 根据省市区路径获取文字 */
export const getRegionPath = (province: string, city: string, region: string): string => {
  const p = provinceData.find(p => p.value === province)
  if (!p) return `${province} ${city} ${region}`
  const c = p.children?.find(c => c.value === city)
  if (!c) return `${province} ${city} ${region}`
  const r = c.children?.find(r => r.value === region)
  if (!r) return `${province} ${city} ${region}`
  return `${p.label} ${c.label} ${r.label}`
}
