# app.py
import os
import hmac
import hashlib
import base64
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
from pydantic import BaseModel
from typing import Optional, Dict, Any

# ---------- 配置 ----------
SEEL_API_KEY = os.getenv("SEEL_API_KEY", "测试Key")
SEEL_API_URL = os.getenv("SEEL_API_URL", "https://api-test.seel.com/v1")
SHOPIFY_WEBHOOK_SECRET = os.getenv("SHOPIFY_WEBHOOK_SECRET", "Webhook密钥")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://*.myshopify.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CartItem(BaseModel):
    product_id: str
    variant_id: str
    quantity: int
    price: float

class QuoteRequest(BaseModel):
    cart: Dict
    customer: Optional[Dict] = None
    shop_domain: str

class SeelClient:
    def __init__(self):
        self.headers = {
            "Content-Type": "application/json",
            "X-Seel-API-Key": SEEL_API_KEY,
            "X-Seel-API-Version": "1.3.0"
        }

    async def create_quote(self, cart: Dict, promotion_type: Optional[str] = None):
        payload = {
            "is_default_on": True,
            "cart": cart,
            "extra_info": {}
        }
        if promotion_type:
            payload["extra_info"]["promotion_type"] = promotion_type

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{SEEL_API_URL}/ecommerce/quotes",
                headers=self.headers,
                json=payload,
                timeout=10.0
            )
        resp.raise_for_status()
        return resp.json()

    async def create_order(self, quote_id: str, order_data: Dict):
        payload = {
            "quote_id": quote_id,
            **order_data
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{SEEL_API_URL}/ecommerce/orders",
                headers=self.headers,
                json=payload,
                timeout=10.0
            )
        resp.raise_for_status()
        return resp.json()

seel_client = SeelClient()

# ---------- 代理接口：用于前端获取报价 ----------
@app.post("/api/proxy/quote")
async def proxy_quote(request: QuoteRequest):
    # 判断会员首单（简化）
    is_member_first_order = False
    if request.customer:
        tags = request.customer.get("tags", [])
        order_count = request.customer.get("order_count", 1)
        if "member" in tags and order_count == 0:
            is_member_first_order = True

    promotion_type = "membership_free" if is_member_first_order else None

    try:
        quote = await seel_client.create_quote(request.cart, promotion_type)
        return {"quote": quote, "promotion_type": promotion_type}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Webhook：订单创建 ----------
@app.post("/webhooks/orders/create")
async def orders_create(request: Request):
    # 1. 验证 HMAC
    body = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256")
    if not verify_hmac(body, hmac_header):
        raise HTTPException(status_code=401, detail="Invalid HMAC")

    order = await request.json()

    # 2. 提取 quote_id
    quote_id = None
    for attr in order.get("note_attributes", []):
        if attr.get("name") == "seel_quote_id":
            quote_id = attr.get("value")
            break

    if not quote_id:
        return {"status": "skipped"}

    # 3. 构建 Seel 订单数据
    seel_order = {
        "order_id": str(order["id"]),
        "order_number": order["order_number"],
        "created_at": order["created_at"],
        "currency": order["currency"],
        "subtotal": float(order.get("subtotal_price", 0)),
        "total": float(order.get("total_price", 0)),
        "line_items": [
            {
                "product_id": str(item.get("product_id")),
                "variant_id": str(item.get("variant_id")),
                "quantity": item["quantity"],
                "price": float(item["price"])
            }
            for item in order.get("line_items", [])
        ],
        "shipping_address": {
            "country_code": order.get("shipping_address", {}).get("country_code"),
            "province_code": order.get("shipping_address", {}).get("province_code"),
            "city": order.get("shipping_address", {}).get("city"),
            "zip": order.get("shipping_address", {}).get("zip")
        }
    }

    # 4. 同步到 Seel
    try:
        result = await seel_client.create_order(quote_id, seel_order)
        return {"status": "success", "seel_response": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def verify_hmac(body: bytes, header_hmac: str) -> bool:
    if not header_hmac:
        return False
    digest = hmac.new(
        SHOPIFY_WEBHOOK_SECRET.encode('utf-8'),
        body,
        hashlib.sha256
    ).digest()
    computed = base64.b64encode(digest).decode()
    return hmac.compare_digest(computed, header_hmac)

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
