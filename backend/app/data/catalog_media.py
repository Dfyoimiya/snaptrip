"""商品与品牌媒体资源映射。

资源准备脚本会将远程图片下载到前端公共目录，数据库仅保存稳定的站内路径。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ProductImageAsset(BaseModel):
    """一类商品图片的来源与站内路径。"""

    model_config = ConfigDict(frozen=True)

    source_url: HttpUrl
    file_name: str = Field(pattern=r"^[a-z0-9-]+\.jpg$")

    @property
    def public_path(self) -> str:
        return f"/images/catalog/products/{self.file_name}"


class BrandLogoAsset(BaseModel):
    """品牌 Logo 的站内路径与可选 Simple Icons 标识。"""

    model_config = ConfigDict(frozen=True)

    file_name: str = Field(pattern=r"^[a-z0-9-]+\.svg$")
    icon_slug: str | None = Field(default=None, pattern=r"^[a-z0-9]+$")

    @property
    def public_path(self) -> str:
        return f"/images/catalog/brands/{self.file_name}"


PRODUCT_IMAGE_ASSETS: dict[str, ProductImageAsset] = {
    "phone-apple": ProductImageAsset(
        source_url=(
            "https://images.unsplash.com/photo-1592750475338-74b7b21085ab"
            "?auto=format&fit=crop&w=900&h=900&q=88"
        ),
        file_name="phone-apple.jpg",
    ),
    "phone-android": ProductImageAsset(
        source_url=(
            "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9"
            "?auto=format&fit=crop&w=900&h=900&q=88"
        ),
        file_name="phone-android.jpg",
    ),
    "headphones": ProductImageAsset(
        source_url=(
            "https://images.unsplash.com/photo-1505740420928-5e560c06d30e"
            "?auto=format&fit=crop&w=900&h=900&q=88"
        ),
        file_name="headphones.jpg",
    ),
    "laptop": ProductImageAsset(
        source_url=(
            "https://images.unsplash.com/photo-1517336714731-489689fd1ca8"
            "?auto=format&fit=crop&w=900&h=900&q=88"
        ),
        file_name="laptop.jpg",
    ),
    "tablet": ProductImageAsset(
        source_url=(
            "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0"
            "?auto=format&fit=crop&w=900&h=900&q=88"
        ),
        file_name="tablet.jpg",
    ),
    "monitor": ProductImageAsset(
        source_url=(
            "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf"
            "?auto=format&fit=crop&w=900&h=900&q=88"
        ),
        file_name="monitor.jpg",
    ),
    "kitchen-appliance": ProductImageAsset(
        source_url=(
            "https://images.unsplash.com/photo-1556911220-bff31c812dba"
            "?auto=format&fit=crop&w=900&h=900&q=88"
        ),
        file_name="kitchen-appliance.jpg",
    ),
    "refrigerator": ProductImageAsset(
        source_url=(
            "https://images.unsplash.com/photo-1571175443880-49e1d25b2bc5"
            "?auto=format&fit=crop&w=900&h=900&q=88"
        ),
        file_name="refrigerator.jpg",
    ),
    "vacuum": ProductImageAsset(
        source_url=(
            "https://images.unsplash.com/photo-1558317374-067fb5f30001"
            "?auto=format&fit=crop&w=900&h=900&q=88"
        ),
        file_name="vacuum.jpg",
    ),
    "hair-dryer": ProductImageAsset(
        source_url=(
            "https://images.unsplash.com/photo-1522338140262-f46f5913618a"
            "?auto=format&fit=crop&w=900&h=900&q=88"
        ),
        file_name="hair-dryer.jpg",
    ),
    "shirt": ProductImageAsset(
        source_url=(
            "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab"
            "?auto=format&fit=crop&w=900&h=900&q=88"
        ),
        file_name="shirt.jpg",
    ),
    "jacket": ProductImageAsset(
        source_url=(
            "https://images.unsplash.com/photo-1551028719-00167b16eac5"
            "?auto=format&fit=crop&w=900&h=900&q=88"
        ),
        file_name="jacket.jpg",
    ),
    "dress": ProductImageAsset(
        source_url=(
            "https://images.unsplash.com/photo-1595777457583-95e059d581b8"
            "?auto=format&fit=crop&w=900&h=900&q=88"
        ),
        file_name="dress.jpg",
    ),
    "cap": ProductImageAsset(
        source_url=(
            "https://images.unsplash.com/photo-1588850561407-ed78c282e89b"
            "?auto=format&fit=crop&w=900&h=900&q=88"
        ),
        file_name="cap.jpg",
    ),
    "shoes": ProductImageAsset(
        source_url=(
            "https://images.unsplash.com/photo-1542291026-7eec264c27ff"
            "?auto=format&fit=crop&w=900&h=900&q=88"
        ),
        file_name="shoes.jpg",
    ),
    "shoes-adidas": ProductImageAsset(
        source_url=(
            "https://images.unsplash.com/flagged/photo-1556637640-2c80d3201be8"
            "?auto=format&fit=crop&w=900&h=900&q=88"
        ),
        file_name="shoes-adidas.jpg",
    ),
    "dumbbell": ProductImageAsset(
        source_url=(
            "https://images.unsplash.com/photo-1517836357463-d25dfeac3438"
            "?auto=format&fit=crop&w=900&h=900&q=88"
        ),
        file_name="dumbbell.jpg",
    ),
    "tent": ProductImageAsset(
        source_url=(
            "https://images.unsplash.com/photo-1504280390367-361c6d9f38f4"
            "?auto=format&fit=crop&w=900&h=900&q=88"
        ),
        file_name="tent.jpg",
    ),
    "nuts": ProductImageAsset(
        source_url=(
            "https://images.unsplash.com/photo-1626697556426-8a55a8af4999"
            "?auto=format&fit=crop&w=900&h=900&q=88"
        ),
        file_name="nuts.jpg",
    ),
    "snacks": ProductImageAsset(
        source_url=(
            "https://images.unsplash.com/photo-1632687380457-05a1271e873b"
            "?auto=format&fit=crop&w=900&h=900&q=88"
        ),
        file_name="snacks.jpg",
    ),
    "orange": ProductImageAsset(
        source_url=(
            "https://images.unsplash.com/photo-1547514701-42782101795e"
            "?auto=format&fit=crop&w=900&h=900&q=88"
        ),
        file_name="orange.jpg",
    ),
    "cherry": ProductImageAsset(
        source_url=(
            "https://images.unsplash.com/photo-1528821128474-27f963b062bf"
            "?auto=format&fit=crop&w=900&h=900&q=88"
        ),
        file_name="cherry.jpg",
    ),
    "skincare": ProductImageAsset(
        source_url=(
            "https://images.unsplash.com/photo-1556228578-0d85b1a4d571"
            "?auto=format&fit=crop&w=900&h=900&q=88"
        ),
        file_name="skincare.jpg",
    ),
    "makeup": ProductImageAsset(
        source_url=(
            "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9"
            "?auto=format&fit=crop&w=900&h=900&q=88"
        ),
        file_name="makeup.jpg",
    ),
    "lipstick": ProductImageAsset(
        source_url=(
            "https://images.unsplash.com/photo-1586495777744-4413f21062fa"
            "?auto=format&fit=crop&w=900&h=900&q=88"
        ),
        file_name="lipstick.jpg",
    ),
    "book": ProductImageAsset(
        source_url=(
            "https://images.unsplash.com/photo-1544947950-fa07a98d237f"
            "?auto=format&fit=crop&w=900&h=900&q=88"
        ),
        file_name="book.jpg",
    ),
    "magnetic-blocks": ProductImageAsset(
        source_url=(
            "https://images.unsplash.com/photo-1587654780291-39c9404d746b"
            "?auto=format&fit=crop&w=900&h=900&q=88"
        ),
        file_name="magnetic-blocks.jpg",
    ),
    "lego": ProductImageAsset(
        source_url=(
            "https://images.unsplash.com/photo-1587654780291-39c9404d746b"
            "?auto=format&fit=crop&w=900&h=900&q=88"
        ),
        file_name="lego.jpg",
    ),
}


PRODUCT_IMAGE_KEYS: dict[str, str] = {
    "Adidas Ultraboost Light": "shoes-adidas",
    "Air Jordan 1": "shoes",
    "Air Jordan 1 Retro High": "shoes",
    "Galaxy S24 Ultra": "phone-android",
    "iPad Air 11 英寸": "tablet",
    'iPad Pro M4 12.9"': "tablet",
    "iPhone 15 Pro Max": "phone-apple",
    "iPhone 16 Pro 256GB": "phone-apple",
    "Keep 可调节哑铃 20kg": "dumbbell",
    "MacBook Air 13 M3": "laptop",
    "MacBook Pro 14": "laptop",
    "MacBook Pro 14 (M3 Pro)": "laptop",
    "Mate 60 Pro": "phone-android",
    "New Era 经典棒球帽": "cap",
    "Nike Air Zoom Pegasus 跑鞋": "shoes",
    "Nike Dri-FIT 运动T恤": "shirt",
    "Nike Dri-FIT 速干运动T恤": "shirt",
    "SK-II 护肤精华露 230ml": "skincare",
    "SK-II 神仙水 230ml": "skincare",
    "Sony WH-1000XM5 头戴式降噪耳机": "headphones",
    "Sony WH-1000XM5 降噪耳机": "headphones",
    "Ultraboost 23": "shoes-adidas",
    "Xiaomi 14 Pro": "phone-android",
    "YSL 小金条口红": "lipstick",
    "《三体》刘慈欣科幻典藏版": "book",
    "三只松鼠零食大礼包": "snacks",
    "乐高经典创意积木盒": "lego",
    "优衣库轻型羽绒服": "jacket",
    "儿童磁力片积木 100 件套": "magnetic-blocks",
    "兰蔻小黑瓶精华 100ml": "skincare",
    "华为 Mate 70 Pro": "phone-android",
    "四川爱媛果冻橙 5kg": "orange",
    "小米 15 徕卡影像手机": "phone-android",
    "戴尔 27 英寸 4K 显示器": "monitor",
    "戴森 HD15 吹风机": "hair-dryer",
    "戴森 Supersonic 吹风机": "hair-dryer",
    "智利进口车厘子 2.5kg": "cherry",
    "法式碎花收腰连衣裙": "dress",
    "海尔 501L 十字门冰箱": "refrigerator",
    "海尔 三门冰箱 218L": "refrigerator",
    "牧高笛三人自动帐篷": "tent",
    "石头智能扫地机器人": "vacuum",
    "《置身事内》中国政府与经济发展": "book",
    "美的 5L 可视空气炸锅": "kitchen-appliance",
    "美的 空气炸锅 4.7L": "kitchen-appliance",
    "联想拯救者 Y9000P 游戏本": "laptop",
    "良品铺子 坚果大礼包 1.5kg": "nuts",
    "良品铺子每日坚果 30 袋": "nuts",
    "雅诗兰黛沁水粉底液": "makeup",
}


BRAND_LOGO_ASSETS: dict[str, BrandLogoAsset] = {
    "Adidas": BrandLogoAsset(file_name="adidas.svg", icon_slug="adidas"),
    "Apple": BrandLogoAsset(file_name="apple.svg", icon_slug="apple"),
    "Dell": BrandLogoAsset(file_name="dell.svg", icon_slug="dell"),
    "Dyson": BrandLogoAsset(file_name="dyson.svg", icon_slug="dyson"),
    "Estée Lauder": BrandLogoAsset(file_name="estee-lauder.svg"),
    "Hape": BrandLogoAsset(file_name="hape.svg"),
    "Huawei": BrandLogoAsset(file_name="huawei.svg", icon_slug="huawei"),
    "Keep": BrandLogoAsset(file_name="keep.svg"),
    "Lancôme": BrandLogoAsset(file_name="lancome.svg"),
    "LEGO": BrandLogoAsset(file_name="lego.svg", icon_slug="lego"),
    "Lenovo": BrandLogoAsset(file_name="lenovo.svg", icon_slug="lenovo"),
    "Mobi Garden": BrandLogoAsset(file_name="mobi-garden.svg"),
    "MO&Co.": BrandLogoAsset(file_name="moco.svg"),
    "New Era": BrandLogoAsset(file_name="new-era.svg", icon_slug="newera"),
    "Nike": BrandLogoAsset(file_name="nike.svg", icon_slug="nike"),
    "Roborock": BrandLogoAsset(file_name="roborock.svg", icon_slug="roborock"),
    "Samsung": BrandLogoAsset(file_name="samsung.svg", icon_slug="samsung"),
    "SK-II": BrandLogoAsset(file_name="sk-ii.svg"),
    "Sony": BrandLogoAsset(file_name="sony.svg", icon_slug="sony"),
    "UNIQLO": BrandLogoAsset(file_name="uniqlo.svg", icon_slug="uniqlo"),
    "Xiaomi": BrandLogoAsset(file_name="xiaomi.svg", icon_slug="xiaomi"),
    "YSL": BrandLogoAsset(file_name="ysl.svg"),
    "三只松鼠": BrandLogoAsset(file_name="three-squirrels.svg"),
    "上海人民出版社": BrandLogoAsset(file_name="shanghai-peoples-press.svg"),
    "戴森": BrandLogoAsset(file_name="dyson-cn.svg", icon_slug="dyson"),
    "海尔": BrandLogoAsset(file_name="haier.svg", icon_slug="haier"),
    "索尼": BrandLogoAsset(file_name="sony-cn.svg", icon_slug="sony"),
    "美的": BrandLogoAsset(file_name="midea.svg"),
    "良品铺子": BrandLogoAsset(file_name="bestore.svg"),
    "重庆出版社": BrandLogoAsset(file_name="chongqing-publishing.svg"),
    "鲜果优选": BrandLogoAsset(file_name="fresh-fruit.svg"),
}


def get_product_image_path(product_name: str) -> str:
    """按商品名返回稳定的站内图片路径。"""

    image_key = PRODUCT_IMAGE_KEYS.get(product_name)
    if image_key is None:
        raise KeyError(f"未配置商品图片: {product_name}")
    return PRODUCT_IMAGE_ASSETS[image_key].public_path


def get_brand_logo_path(brand_name: str) -> str:
    """按品牌名返回稳定的站内 Logo 路径。"""

    asset = BRAND_LOGO_ASSETS.get(brand_name)
    if asset is None:
        raise KeyError(f"未配置品牌 Logo: {brand_name}")
    return asset.public_path
