# Image Asset Design — Linglong Composer 配图系统

## 背景

当前 `linglong` monorepo 的 `composer/assets/` 下只有 `text.py`，缺少图片处理能力。
`linglong-pipeline` 遗留项目中有完整的图虫下载/处理脚本，需要泛化后迁移到 monorepo，支持多网站、多规格（背景图/文章配图）、随机选择。

## 目标

为 Composer 流水线增加配图能力：
1. 从用户维护的 URL 列表文件下载图片
2. 按两种规格处理：博客背景图、文章配图
3. 随机选取，支持去重
4. 集成到 `composer.py` 和 `BlogTemplate`

## 非目标（v2.0）

- AI 封面图生成
- Playwright 爬虫自动抓 URL
- 多模板输出（早报/周报/PPT）
- 发布队列与重试
- WebSearchAdapter 实际搜索

## 架构

```
composer.py run()
    │
    ▼
image_selector.py        image_fetcher.py
  - 解析 URL 文件           - 下载图片
  - 按用途分类              - 尺寸/比例过滤
  - 随机选择                - 压缩/清除 EXIF
  - 去重记录                - 保存到规格目录
    │                           │
    └──────────┬────────────────┘
               ▼
        BlogTemplate.apply()
            - frontmatter 插背景图
            - 正文插配图
```

## 组件

### 1. `ImageAssetSelector`

职责：读取 URL 列表 → 解析标签和用途标记 → 随机选择 → 去重

```python
class ImageAssetSelector:
    def __init__(self, config: dict)
    def select(self, usage: str, count: int = 1) -> list[str]  # 返回 URL 列表
    def record_used(self, urls: list[str])
```

**URL 文件格式：**
```text
# URL # 标签 [background|article_image|both]
https://photo.tuchong.com/123/f/456.jpg # 风景 [background]
https://images.unsplash.com/photo-xxx # tech [article_image]
```

**去重策略：** 记录最近 N 天已用 URL，选择时排除。

### 2. `ImageAssetFetcher`

职责：下载 → 尺寸过滤 → 压缩 → 清除 EXIF → 保存

基于 `linglong-pipeline` 的 `TuchongImageFetcher` 泛化：
- 去掉图虫特化逻辑（referer 等保留为可配置）
- 支持多来源配置（不同来源可配不同 headers）
- 输出到规格子目录

```python
class ImageAssetFetcher:
    def __init__(self, spec_config: dict, source_config: dict)
    def fetch(self, url: str) -> Path | None
    def process(self, url: str) -> Path | None  # download + filter + compress
```

**规格配置：**
```yaml
specs:
  background:
    min_width: 1920
    min_height: 1080
    quality: 90
    output_dir: "~/linglong/images/backgrounds"
  article_image:
    min_width: 800
    min_height: 600
    quality: 85
    output_dir: "~/linglong/images/articles"
```

### 3. Composer 集成

在 `composer.py` 的 `_process_day()` 中：

```python
if self.config.image_assets.enabled:
    selector = ImageAssetSelector(self.config.image_assets)
    fetcher_bg = ImageAssetFetcher(spec=background_spec, source=...)
    fetcher_img = ImageAssetFetcher(spec=article_image_spec, source=...)

    bg_url = selector.select("background", count=1)[0]
    img_url = selector.select("article_image", count=1)[0]

    bg_path = fetcher_bg.process(bg_url)
    img_path = fetcher_img.process(img_url)

    metadata["background_image"] = str(bg_path)
    metadata["article_image"] = str(img_path)
```

### 4. BlogTemplate 集成

`BlogTemplate.apply()` 读取 metadata：
- `background_image` → 写入 frontmatter `cover` 字段
- `article_image` → 在正文顶部插入 `![配图](path)`

## 配置模型

```yaml
composer:
  image_assets:
    enabled: true
    specs:
      background:
        min_width: 1920
        min_height: 1080
        quality: 90
        output_dir: "~/linglong/images/backgrounds"
      article_image:
        min_width: 800
        min_height: 600
        quality: 85
        output_dir: "~/linglong/images/articles"
    sources:
      - name: tuchong
        type: url_list
        url_file: "~/.linglong/images/tuchong_urls.txt"
        headers:
          Referer: "https://tuchong.com/"
        default_usage: both
      - name: unsplash
        type: url_list
        url_file: "~/.linglong/images/unsplash_urls.txt"
        default_usage: both
    selection:
      strategy: random
      dedup_days: 30
```

## 错误处理

- 下载失败 → 跳过该 URL，不阻塞文章生成
- 尺寸不符 → 过滤掉，记录 warning
- 无可用图片 → 不插入图片，文章正常生成
- 去重耗尽 → 重置去重窗口，允许复用旧图

## 测试策略

- `test_image_selector.py`：解析、分类、随机选择、去重
- `test_image_fetcher.py`：下载 mock、尺寸过滤、压缩
- `test_composer_image_integration.py`：Composer 集成（mock fetcher）

## 验收标准

- [ ] `ImageAssetSelector` 能正确解析 URL 文件并按用途分类
- [ ] `ImageAssetFetcher` 能下载图片并按规格处理
- [ ] `composer.run()` 生成文章时自动附上图
- [ ] `BlogTemplate` 在 frontmatter 和正文中正确引用图片路径
- [ ] 现有 75 个测试全部通过
