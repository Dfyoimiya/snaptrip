"""开发商城商品目录种子数据。"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CatalogProduct(BaseModel):
    """可重复导入的商品 SPU/SKU 定义。"""

    model_config = ConfigDict(frozen=True)

    product_sn: str = Field(min_length=3, max_length=64)
    name: str = Field(min_length=2, max_length=200)
    category: str = Field(min_length=2, max_length=64)
    brand: str = Field(min_length=1, max_length=64)
    price: Decimal = Field(gt=0)
    original_price: Decimal = Field(gt=0)
    image_url: str
    sub_title: str = Field(max_length=255)
    keywords: str = Field(max_length=255)
    stock: int = Field(ge=0)
    sale_count: int = Field(ge=0)
    unit: str = Field(default="件", max_length=16)


PHONE_IMAGE = (
    "https://images.unsplash.com/photo-1592750475338-74b7b21085ab"
    "?auto=format&fit=crop&w=800&q=85"
)
ANDROID_IMAGE = (
    "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9"
    "?auto=format&fit=crop&w=800&q=85"
)
LAPTOP_IMAGE = (
    "https://images.unsplash.com/photo-1517336714731-489689fd1ca8"
    "?auto=format&fit=crop&w=800&q=85"
)
TABLET_IMAGE = (
    "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0"
    "?auto=format&fit=crop&w=800&q=85"
)
APPLIANCE_IMAGE = (
    "https://images.unsplash.com/photo-1556911220-bff31c812dba"
    "?auto=format&fit=crop&w=800&q=85"
)
VACUUM_IMAGE = (
    "https://images.unsplash.com/photo-1558317374-067fb5f30001"
    "?auto=format&fit=crop&w=800&q=85"
)
CLOTHING_IMAGE = (
    "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab"
    "?auto=format&fit=crop&w=800&q=85"
)
DRESS_IMAGE = (
    "https://images.unsplash.com/photo-1595777457583-95e059d581b8"
    "?auto=format&fit=crop&w=800&q=85"
)
SHOES_IMAGE = (
    "https://images.unsplash.com/photo-1542291026-7eec264c27ff"
    "?auto=format&fit=crop&w=800&q=85"
)
FITNESS_IMAGE = (
    "https://images.unsplash.com/photo-1517836357463-d25dfeac3438"
    "?auto=format&fit=crop&w=800&q=85"
)
SNACK_IMAGE = (
    "https://images.unsplash.com/photo-1599599810694-b5b37304c041"
    "?auto=format&fit=crop&w=800&q=85"
)
FRUIT_IMAGE = (
    "https://images.unsplash.com/photo-1610832958506-aa56368176cf"
    "?auto=format&fit=crop&w=800&q=85"
)
SKINCARE_IMAGE = (
    "https://images.unsplash.com/photo-1556228578-0d85b1a4d571"
    "?auto=format&fit=crop&w=800&q=85"
)
MAKEUP_IMAGE = (
    "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9"
    "?auto=format&fit=crop&w=800&q=85"
)
BOOK_IMAGE = (
    "https://images.unsplash.com/photo-1544947950-fa07a98d237f"
    "?auto=format&fit=crop&w=800&q=85"
)
TOY_IMAGE = (
    "https://images.unsplash.com/photo-1594787318286-3d835c1d207f"
    "?auto=format&fit=crop&w=800&q=85"
)


def product(
    product_sn: str,
    name: str,
    category: str,
    brand: str,
    price: str,
    original_price: str,
    image_url: str,
    sub_title: str,
    keywords: str,
    stock: int,
    sale_count: int,
) -> CatalogProduct:
    return CatalogProduct(
        product_sn=product_sn,
        name=name,
        category=category,
        brand=brand,
        price=Decimal(price),
        original_price=Decimal(original_price),
        image_url=image_url,
        sub_title=sub_title,
        keywords=keywords,
        stock=stock,
        sale_count=sale_count,
    )


CATALOG_PRODUCTS: tuple[CatalogProduct, ...] = (
    product("DEMO-PHONE-001", "iPhone 16 Pro 256GB", "手机通讯", "Apple", "7999", "8999", PHONE_IMAGE, "A18 Pro 芯片｜钛金属设计｜专业影像", "手机 iPhone 苹果 5G", 320, 2680),
    product("DEMO-PHONE-002", "华为 Mate 70 Pro", "手机通讯", "Huawei", "6999", "7499", ANDROID_IMAGE, "鸿蒙智能｜超可靠玄武架构｜红枫原色影像", "手机 华为 Mate 鸿蒙", 260, 2130),
    product("DEMO-PHONE-003", "小米 15 徕卡影像手机", "手机通讯", "Xiaomi", "4499", "4999", ANDROID_IMAGE, "骁龙旗舰平台｜徕卡光学｜高亮直屏", "手机 小米 徕卡 安卓", 500, 3420),
    product("DEMO-PHONE-004", "Sony WH-1000XM5 降噪耳机", "手机通讯", "Sony", "2399", "2999", PHONE_IMAGE, "旗舰降噪｜30 小时续航｜Hi-Res 音质", "耳机 蓝牙 降噪 索尼", 420, 1890),

    product("DEMO-PC-001", "MacBook Air 13 M3", "电脑办公", "Apple", "7999", "8999", LAPTOP_IMAGE, "M3 芯片｜轻薄便携｜全天候续航", "电脑 笔记本 MacBook 办公", 240, 1760),
    product("DEMO-PC-002", "联想拯救者 Y9000P 游戏本", "电脑办公", "Lenovo", "9999", "10999", LAPTOP_IMAGE, "高性能独显｜高刷电竞屏｜霜刃散热", "电脑 游戏本 联想 电竞", 180, 1320),
    product("DEMO-PC-003", "iPad Air 11 英寸", "电脑办公", "Apple", "4799", "5199", TABLET_IMAGE, "M2 芯片｜Liquid Retina｜支持手写笔", "平板电脑 iPad 学习 办公", 300, 1540),
    product("DEMO-PC-004", "戴尔 27 英寸 4K 显示器", "电脑办公", "Dell", "2299", "2699", LAPTOP_IMAGE, "4K IPS｜广色域｜USB-C 一线连接", "显示器 电脑配件 4K 办公", 210, 980),

    product("DEMO-HOME-001", "美的 5L 可视空气炸锅", "家用电器", "美的", "399", "599", APPLIANCE_IMAGE, "可视大容量｜少油烹饪｜智能菜单", "家电 厨房 空气炸锅 美的", 680, 5260),
    product("DEMO-HOME-002", "海尔 501L 十字门冰箱", "家用电器", "海尔", "4599", "5299", APPLIANCE_IMAGE, "风冷无霜｜双系统保鲜｜一级能效", "家电 冰箱 海尔 保鲜", 130, 860),
    product("DEMO-HOME-003", "石头智能扫地机器人", "家用电器", "Roborock", "3299", "3999", VACUUM_IMAGE, "扫拖一体｜自动集尘｜智能避障", "家电 扫地机器人 清洁", 240, 1450),
    product("DEMO-HOME-004", "戴森 Supersonic 吹风机", "家用电器", "Dyson", "2999", "3490", VACUUM_IMAGE, "快速干发｜智能温控｜负离子护发", "家电 吹风机 戴森 个护", 280, 1680),

    product("DEMO-CLOTH-001", "Nike Dri-FIT 速干运动T恤", "服装鞋帽", "Nike", "259", "329", CLOTHING_IMAGE, "吸湿速干｜轻盈透气｜日常运动", "男装 T恤 运动 速干", 900, 6210),
    product("DEMO-CLOTH-002", "优衣库轻型羽绒服", "服装鞋帽", "UNIQLO", "599", "699", CLOTHING_IMAGE, "轻盈保暖｜便携收纳｜简约百搭", "服装 羽绒服 男女 保暖", 650, 4380),
    product("DEMO-CLOTH-003", "法式碎花收腰连衣裙", "服装鞋帽", "MO&Co.", "699", "899", DRESS_IMAGE, "收腰显瘦｜轻盈雪纺｜通勤约会", "女装 连衣裙 法式 夏季", 430, 2870),
    product("DEMO-CLOTH-004", "New Era 经典棒球帽", "服装鞋帽", "New Era", "229", "299", CLOTHING_IMAGE, "经典帽型｜可调节帽围｜街头百搭", "帽子 棒球帽 配饰 潮流", 720, 3650),

    product("DEMO-SPORT-001", "Nike Air Zoom Pegasus 跑鞋", "运动户外", "Nike", "799", "999", SHOES_IMAGE, "轻量缓震｜透气鞋面｜公路跑步", "运动鞋 跑步鞋 Nike", 580, 4820),
    product("DEMO-SPORT-002", "Adidas Ultraboost Light", "运动户外", "Adidas", "1099", "1399", SHOES_IMAGE, "BOOST 回弹｜舒适包裹｜日常慢跑", "运动鞋 Adidas 跑步", 460, 3190),
    product("DEMO-SPORT-003", "Keep 可调节哑铃 20kg", "运动户外", "Keep", "499", "699", FITNESS_IMAGE, "快速调重｜家用健身｜安全防滑", "健身 哑铃 力量训练 Keep", 350, 2460),
    product("DEMO-SPORT-004", "牧高笛三人自动帐篷", "运动户外", "Mobi Garden", "429", "599", FITNESS_IMAGE, "快速搭建｜防风防雨｜露营便携", "户外 帐篷 露营 野营", 310, 1970),

    product("DEMO-FOOD-001", "良品铺子每日坚果 30 袋", "食品生鲜", "良品铺子", "139", "169", SNACK_IMAGE, "科学配比｜独立包装｜每日营养", "零食 坚果 健康 礼盒", 1600, 12600),
    product("DEMO-FOOD-002", "三只松鼠零食大礼包", "食品生鲜", "三只松鼠", "119", "159", SNACK_IMAGE, "人气零食组合｜多种口味｜聚会分享", "零食 礼包 休闲食品", 1800, 15800),
    product("DEMO-FOOD-003", "四川爱媛果冻橙 5kg", "食品生鲜", "鲜果优选", "79", "99", FRUIT_IMAGE, "当季鲜果｜皮薄多汁｜现摘现发", "水果 橙子 生鲜 当季", 900, 7350),
    product("DEMO-FOOD-004", "智利进口车厘子 2.5kg", "食品生鲜", "鲜果优选", "259", "329", FRUIT_IMAGE, "大果脆甜｜冷链直达｜礼盒装", "水果 车厘子 生鲜 进口", 420, 2860),

    product("DEMO-BEAUTY-001", "SK-II 护肤精华露 230ml", "美妆个护", "SK-II", "1699", "2150", SKINCARE_IMAGE, "PITERA 精华｜晶莹透亮｜改善肤质", "护肤 精华 神仙水 SK-II", 360, 2740),
    product("DEMO-BEAUTY-002", "兰蔻小黑瓶精华 100ml", "美妆个护", "Lancôme", "1299", "1590", SKINCARE_IMAGE, "强韧屏障｜细腻焕亮｜保湿修护", "护肤 精华 兰蔻 修护", 420, 3210),
    product("DEMO-BEAUTY-003", "雅诗兰黛沁水粉底液", "美妆个护", "Estée Lauder", "480", "590", MAKEUP_IMAGE, "水润服帖｜自然遮瑕｜持久妆效", "彩妆 粉底液 底妆", 530, 4160),
    product("DEMO-BEAUTY-004", "YSL 小金条口红", "美妆个护", "YSL", "350", "395", MAKEUP_IMAGE, "高显色｜丝绒质感｜经典色号", "彩妆 口红 唇膏 YSL", 760, 6890),

    product("DEMO-BOOK-001", "《三体》刘慈欣科幻典藏版", "图书文娱", "重庆出版社", "68", "93", BOOK_IMAGE, "中国科幻经典｜雨果奖作品｜全三册", "图书 小说 科幻 三体", 1200, 9820),
    product("DEMO-BOOK-002", "《置身事内》中国政府与经济发展", "图书文娱", "上海人民出版社", "45", "68", BOOK_IMAGE, "理解中国经济｜通俗经济学｜年度好书", "图书 经济 管理 置身事内", 850, 6470),
    product("DEMO-BOOK-003", "儿童磁力片积木 100 件套", "图书文娱", "Hape", "199", "269", TOY_IMAGE, "磁力搭建｜空间启蒙｜安全大颗粒", "玩具 积木 儿童 益智", 620, 5130),
    product("DEMO-BOOK-004", "乐高经典创意积木盒", "图书文娱", "LEGO", "359", "449", TOY_IMAGE, "多彩颗粒｜自由创作｜亲子互动", "玩具 乐高 积木 创意", 480, 3860),
)
