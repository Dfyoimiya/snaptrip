import { useEffect, useState } from 'react';
import { Card, Form, Input, InputNumber, Select, Button, Space, message, Divider, Tabs } from 'antd';
import { useNavigate, useParams } from '@umijs/max';
import { createProductAPI, getProductDetailAPI, updateProductAPI } from '@/services/product';
import { getAllBrandsAPI } from '@/services/brand';
import { getCategoryTreeAPI } from '@/services/category';

export default function ProductForm() {
  const [form] = Form.useForm();
  const { id } = useParams<{ id: string }>();
  const isEdit = id && id !== 'create';
  const navigate = useNavigate();
  const [brands, setBrands] = useState<API.Brand[]>([]);
  const [categories, setCategories] = useState<API.CategoryTree[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    Promise.all([getAllBrandsAPI(), getCategoryTreeAPI()]).then(([bRes, cRes]) => {
      setBrands(bRes.data);
      setCategories(cRes.data);
    });
  }, []);

  useEffect(() => {
    if (isEdit) {
      getProductDetailAPI(id!).then((res) => form.setFieldsValue(res.data));
    }
  }, [id]);

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const values = form.getFieldsValue();
      if (isEdit) {
        await updateProductAPI(id!, values);
        message.success('Updated');
      } else {
        await createProductAPI(values);
        message.success('Created');
      }
      navigate('/product/list');
    } finally {
      setLoading(false);
    }
  };

  const buildCategoryOptions = (nodes: API.CategoryTree[], depth = 0): { value: string; label: string }[] =>
    nodes.flatMap((n) => [
      { value: n.id, label: `${'　'.repeat(depth)}${n.name}` },
      ...buildCategoryOptions(n.children, depth + 1),
    ]);

  return (
    <Card title={isEdit ? '编辑商品' : '新建商品'}>
      <Form form={form} layout="vertical" style={{ maxWidth: 800 }}>
        <Form.Item name="name" label="商品名称" rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <Form.Item name="subTitle" label="副标题">
          <Input />
        </Form.Item>
        <Space size="large">
          <Form.Item name="brandId" label="品牌">
            <Select allowClear style={{ width: 200 }} options={brands.map((b) => ({ value: b.id, label: b.name }))} />
          </Form.Item>
          <Form.Item name="categoryId" label="分类">
            <Select allowClear style={{ width: 300 }} options={buildCategoryOptions(categories)} />
          </Form.Item>
        </Space>
        <Space size="large">
          <Form.Item name="price" label="价格" rules={[{ required: true }]}>
            <InputNumber min={0} precision={2} />
          </Form.Item>
          <Form.Item name="originalPrice" label="原价">
            <InputNumber min={0} precision={2} />
          </Form.Item>
          <Form.Item name="promotionPrice" label="促销价">
            <InputNumber min={0} precision={2} />
          </Form.Item>
        </Space>
        <Form.Item name="description" label="商品描述">
          <Input.TextArea rows={4} />
        </Form.Item>
        <Form.Item name="keywords" label="SEO关键词">
          <Input />
        </Form.Item>
        <Form.Item name="unit" label="单位">
          <Input style={{ width: 120 }} />
        </Form.Item>
        <Form.Item name="weight" label="重量(g)">
          <InputNumber min={0} />
        </Form.Item>
        <Form.Item name="pics" label="商品图片 (逗号分隔)">
          <Input />
        </Form.Item>
        <Form.Item name="defaultPic" label="主图URL">
          <Input />
        </Form.Item>
        <Space size="large">
          <Form.Item name="publishStatus" label="上架" initialValue={0}>
            <Select style={{ width: 100 }} options={[{ value: 0, label: '下架' }, { value: 1, label: '上架' }]} />
          </Form.Item>
          <Form.Item name="newStatus" label="新品" initialValue={0}>
            <Select style={{ width: 100 }} options={[{ value: 0, label: '否' }, { value: 1, label: '是' }]} />
          </Form.Item>
          <Form.Item name="recommendStatus" label="推荐" initialValue={0}>
            <Select style={{ width: 100 }} options={[{ value: 0, label: '否' }, { value: 1, label: '是' }]} />
          </Form.Item>
        </Space>
        <Divider />
        <Button type="primary" onClick={handleSubmit} loading={loading}>
          {isEdit ? '更新' : '创建'}
        </Button>
      </Form>
    </Card>
  );
}
