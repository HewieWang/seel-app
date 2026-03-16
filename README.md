app.py

FastAPI 服务器

代理 Seel Quote 的接口

接收 Shopify Webhook 的接口

调用 Seel Create Order

HMAC 验证

```
pip install fastapi uvicorn httpx pydantic python-dotenv
uvicorn app:app --reload
```

Functions 必须通过 Shopify CLI 打包,需要配套的 shopify.function.extension.toml 和 GraphQL 输入定义
	
app.py	Python 后端（代理、Webhook）	
extension.jsx	前端 UI 扩展	
function.js	Shopify Functions（可选）
