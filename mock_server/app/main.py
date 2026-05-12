"""Mock API 服务入口 —— 模拟美团本地生活 API"""

from fastapi import FastAPI

app = FastAPI(
    title="SnapTrip Mock API",
    description="模拟美团本地生活 API：POI 搜索 / 排队查询 / 订座订票 / 下单",
    version="0.1.0",
)


@app.get("/health")
async def health():
    return {"status": "ok"}
