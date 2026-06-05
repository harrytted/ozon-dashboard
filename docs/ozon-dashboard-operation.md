# Ozon 店铺订单管家操作文档

## 1. 项目结构

```text
frontend/
  index.html          # 前端页面入口
  styles.css          # 页面样式
  app.js              # 前端交互和本地状态

backend/
  main.py             # FastAPI 应用入口
  ozon_client.py      # Ozon API 调用和店铺绑定逻辑
  db.py               # SQLite 初始化、连接和记录转换
  alibaba1688_client.py # 1688 URL 解析和页面采集
  pricing.py          # 动态利润率定价公式
  sku.py              # 系统 SKU / Ozon offer_id 生成
  ai_normalizer.py    # OpenAI 兼容接口俄语文案和属性补全
  models.py           # API 请求/响应模型
  requirements.txt    # 后端依赖说明

tests/
  app.test.js                 # 前端业务逻辑测试
  backend/test_main.py        # FastAPI 路由测试
  backend/test_ozon_client.py # Ozon 客户端逻辑测试
```

## 2. Conda 环境

项目使用专用 conda 环境：

```bash
ozon-dashboard
```

如果环境已经创建，直接使用即可。

如需重新创建：

```bash
/opt/anaconda3/bin/conda create -n ozon-dashboard python=3.11 fastapi uvicorn httpx -y
```

检查依赖：

```bash
/opt/anaconda3/bin/conda run -n ozon-dashboard python -c "import fastapi, uvicorn, httpx; print('ok')"
```

## 3. 启动后端

在项目根目录运行：

```bash
cd /Users/harry/Documents/code/self/ozon-dashboard
/opt/anaconda3/bin/conda run -n ozon-dashboard uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

后端地址：

```text
http://127.0.0.1:8000
```

健康检查：

```bash
curl http://127.0.0.1:8000/api/health
```

正常返回：

```json
{"status":"ok"}
```

## 4. 启动前端

另开一个终端窗口，运行：

```bash
cd /Users/harry/Documents/code/self/ozon-dashboard/frontend
python3 -m http.server 8088 --bind 127.0.0.1
```

浏览器访问：

```text
http://localhost:8088/index.html
```

前端会调用：

```text
http://127.0.0.1:8000/api/ozon/bind
```

## 5. 绑定真实 Ozon 店铺

1. 打开前端页面。
2. 点击 `绑定 Ozon`。
3. 输入：
   - Ozon 店铺名称
   - Client ID
   - API Key
4. 点击 `验证并绑定 Ozon 店铺`。

后端会用 `Client ID` 和 `API Key` 请求 Ozon Seller API：

```text
POST https://api-seller.ozon.ru/v1/warehouse/list
```

验证成功后，前端只保存安全展示信息，例如：

```text
Client ID: 1234...7890 · 2 个仓库
```

不会把 API Key 保存到浏览器状态里。

## 6. 1688 采集与批量上架

第一版是本地 MVP：

- 1688：输入商品 URL，系统尝试抓取页面；失败时按 URL 生成待复核商品源。
- SKU：按店铺/商品/规格生成唯一 offer_id，避免多店铺冲突。
- 定价：默认目标净利率 30%，公式为 `售价 = 固定成本 / (1 - 综合扣点 - 目标净利率)`。
- Ozon：通过校验的商品提交发布；缺字段、类目或价格异常的商品不发布。
- 订单：可按店铺查询订单接口；没有真实同步记录时返回本地 demo 订单。

新增接口：

```text
POST /api/1688/import-url
GET  /api/1688/sources
POST /api/products/normalize
POST /api/products/publish
GET  /api/products/publish-jobs
GET  /api/stores/{store_id}/products
GET  /api/stores/{store_id}/orders
POST /api/ozon/bind-bulk
```

批量绑定 Ozon 店铺格式：

```text
店铺名称,Client ID,API Key
莫斯科家居店,1001001,ozon-api-key-1
圣彼得堡数码店,1001002,ozon-api-key-2
```

## 7. 运行测试

前端测试：

```bash
cd /Users/harry/Documents/code/self/ozon-dashboard
node --test tests/app.test.js
```

后端测试：

```bash
cd /Users/harry/Documents/code/self/ozon-dashboard
/opt/anaconda3/bin/conda run -n ozon-dashboard python -m unittest discover -s tests/backend
```

## 8. 常见问题

### 前端打开后绑定失败

确认后端已启动：

```bash
curl http://127.0.0.1:8000/api/health
```

如果没有返回 `{"status":"ok"}`，先启动后端。

### 端口被占用

查看占用：

```bash
pgrep -fl "uvicorn backend.main:app|http.server 8088"
```

停止对应进程：

```bash
kill <PID>
```

### Ozon 返回认证失败

检查：

- Client ID 是否来自 Ozon Seller 后台。
- API Key 是否复制完整。
- API Key 是否仍有效。
- 当前 Ozon 账号是否有访问 Seller API 的权限。

## 9. 安全注意事项

- 不要把 API Key 写入前端代码。
- 不要把 API Key 发到聊天、文档或截图里。
- 真实 Ozon 凭证只应输入到本机页面表单。
- 当前 MVP 会把 Ozon 凭证保存在本机 SQLite 文件中；只适合本地使用。
- 如果以后需要团队部署，应接入加密存储、用户权限和审计日志。
