# 电商详情图制作 / Ecommerce Detail Image Maker

> 傻瓜式电商图片生成工具。只需提交白底图 + 产品信息，自动生成 5 张主图 + 5 张描述图。

> Foolproof ecommerce image generator. Just upload a white-background product photo + product info, auto-generate 5 main images + 5 detail images.

---

## 功能 / Features

- **5 张淘宝主图** / 5 Taobao Main Images
  - 01 促销首图 / Promo Hero
  - 02 痛点解决图 / Pain Point Solution
  - 03 设计细节图 / Design Details
  - 04 场景穿搭图 / Scene Styling
  - 05 白底图 / White Background

- **5 张详情描述图** / 5 Detail Images
  - 01 首屏焦点 / First Screen Focus
  - 02 对比卖点 / Comparison Selling Points
  - 03 工艺细节 / Craftsmanship Details
  - 04 场景展示 / Scene Display
  - 05 尺码售后 / Size & After-sales

---

## 使用方法 / Usage

```python
from ecommerce_image_plugin import generate, set_api_key

# 设置 API Key
set_api_key("sk-your-api-key")

# 生成一套电商图
result = generate(
    image_path="白底图.png",
    product_name="美式多功能早餐机",
    color="经典黑",
    original_price=399,
    current_price=199,
    category="家居",  # 可选 / optional
    selling_points="带咖啡壶、煎盘、双层烤箱"
)

print(result)
```

---

## 安装 / Installation

将 `ecommerce_image_plugin` 文件夹放入你的 Agent 插件目录即可。

Copy the `ecommerce_image_plugin` folder into your Agent plugins directory.

---

## 配置 / Configuration

- API Key: 设置环境变量 `HENNG_API_KEY` 或调用 `set_api_key()`
- 输出目录: 桌面 `描述图制作/`

---

## 更新 / Updates

插件支持从 GitHub 远程检查更新。

The plugin supports remote update checks from GitHub.

---

## 作者 / Author

- 微信 / WeChat: nulifeiyu001
- 价格 / Price: 5元/套 (5主图+5详情图)
