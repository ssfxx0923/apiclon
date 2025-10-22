"""
AI模型API中继服务
支持转发请求到目标API，兼容OpenAI格式
"""
import os
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import json
import logging

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI API中继服务",
    description="转发AI模型API请求的中继服务",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 目标API地址
TARGET_API_URL = os.getenv("TARGET_API_URL", "https://sdwfger.edu.kg/v1/chat/completions")
TARGET_API_KEY = os.getenv("TARGET_API_KEY", "")
TIMEOUT = int(os.getenv("TIMEOUT", "300"))

# 中继服务自己的密钥（用于验证客户端）
RELAY_API_KEY = os.getenv("RELAY_API_KEY", "")  # 留空表示不验证


def verify_relay_key(request: Request):
    """验证中继服务的API密钥"""
    if not RELAY_API_KEY:
        # 如果没有配置中继密钥，跳过验证
        return True
    
    # 获取客户端提供的密钥
    auth_header = request.headers.get("authorization", "")
    
    if not auth_header:
        raise HTTPException(
            status_code=401,
            detail="未提供API密钥，请在Authorization头中提供Bearer token"
        )
    
    # 提取token
    if auth_header.startswith("Bearer "):
        client_key = auth_header[7:]
    else:
        raise HTTPException(
            status_code=401,
            detail="无效的Authorization格式，请使用 'Bearer YOUR_KEY'"
        )
    
    # 验证密钥
    if client_key != RELAY_API_KEY:
        logger.warning(f"无效的API密钥尝试: {client_key[:10]}...")
        raise HTTPException(
            status_code=403,
            detail="API密钥无效"
        )
    
    return True


async def stream_response(response):
    """处理流式响应"""
    async for chunk in response.aiter_bytes():
        if chunk:
            yield chunk


@app.get("/")
async def root():
    """根路径，返回服务信息"""
    return {
        "service": "AI API中继服务",
        "status": "running",
        "target_api": TARGET_API_URL,
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """健康检查端点"""
    return {"status": "healthy"}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """
    中继聊天完成API请求
    支持流式和非流式响应
    """
    # 验证中继密钥
    verify_relay_key(request)
    
    try:
        # 获取请求体
        body = await request.json()
        
        # 获取请求头
        headers = dict(request.headers)
        
        # 准备转发的请求头
        forward_headers = {
            "Content-Type": "application/json",
        }
        
        # 如果客户端提供了Authorization，使用客户端的；否则使用配置的API密钥
        if "authorization" in headers:
            forward_headers["Authorization"] = headers["authorization"]
        elif TARGET_API_KEY:
            forward_headers["Authorization"] = f"Bearer {TARGET_API_KEY}"
        
        # 记录请求信息
        logger.info(f"收到请求: model={body.get('model', 'unknown')}, stream={body.get('stream', False)}")
        
        # 判断是否为流式请求
        is_stream = body.get("stream", False)
        
        # 创建HTTP客户端
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # 转发请求
            response = await client.post(
                TARGET_API_URL,
                json=body,
                headers=forward_headers,
            )
            
            # 检查响应状态
            if response.status_code != 200:
                logger.error(f"目标API返回错误: {response.status_code} - {response.text}")
                return JSONResponse(
                    status_code=response.status_code,
                    content={"error": f"目标API错误: {response.text}"}
                )
            
            # 如果是流式响应
            if is_stream:
                logger.info("返回流式响应")
                return StreamingResponse(
                    stream_response(response),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                    }
                )
            else:
                # 非流式响应
                logger.info("返回非流式响应")
                return JSONResponse(
                    content=response.json(),
                    status_code=response.status_code
                )
    
    except httpx.TimeoutException:
        logger.error("请求超时")
        raise HTTPException(status_code=504, detail="请求超时")
    except httpx.RequestError as e:
        logger.error(f"请求错误: {str(e)}")
        raise HTTPException(status_code=502, detail=f"请求目标API失败: {str(e)}")
    except json.JSONDecodeError:
        logger.error("无效的JSON格式")
        raise HTTPException(status_code=400, detail="无效的JSON格式")
    except Exception as e:
        logger.error(f"未知错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")


@app.post("/chat/completions")
async def chat_completions_no_prefix(request: Request):
    """
    兼容不带/v1前缀的请求
    """
    return await chat_completions(request)


@app.get("/v1/models")
async def list_models(request: Request):
    """
    获取可用模型列表
    """
    # 验证中继密钥
    verify_relay_key(request)
    
    try:
        # 构建目标URL - 从chat/completions URL推导出models端点
        base_url = TARGET_API_URL.rsplit("/v1/chat/completions", 1)[0]
        models_url = f"{base_url}/v1/models"
        
        # 获取请求头
        headers = dict(request.headers)
        
        # 准备转发的请求头
        forward_headers = {}
        
        # 如果客户端提供了Authorization，使用客户端的；否则使用配置的API密钥
        if "authorization" in headers:
            forward_headers["Authorization"] = headers["authorization"]
        elif TARGET_API_KEY:
            forward_headers["Authorization"] = f"Bearer {TARGET_API_KEY}"
        
        logger.info(f"获取模型列表: {models_url}")
        
        # 创建HTTP客户端
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # 转发请求
            response = await client.get(
                models_url,
                headers=forward_headers,
            )
            
            # 检查响应状态
            if response.status_code != 200:
                logger.error(f"获取模型列表失败: {response.status_code} - {response.text}")
                return JSONResponse(
                    status_code=response.status_code,
                    content={"error": f"获取模型列表失败: {response.text}"}
                )
            
            logger.info(f"成功获取模型列表")
            return JSONResponse(
                content=response.json(),
                status_code=response.status_code
            )
    
    except httpx.TimeoutException:
        logger.error("请求超时")
        raise HTTPException(status_code=504, detail="请求超时")
    except httpx.RequestError as e:
        logger.error(f"请求错误: {str(e)}")
        raise HTTPException(status_code=502, detail=f"请求目标API失败: {str(e)}")
    except Exception as e:
        logger.error(f"未知错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")


@app.get("/models")
async def list_models_no_prefix(request: Request):
    """
    兼容不带/v1前缀的模型列表请求
    """
    return await list_models(request)


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def catch_all(request: Request, path: str):
    """
    捕获所有其他路径的请求，尝试转发
    """
    try:
        # 构建目标URL
        target_url = TARGET_API_URL.rsplit("/v1/chat/completions", 1)[0] + "/" + path
        
        # 获取请求体
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
        else:
            body = None
        
        # 获取请求头
        headers = dict(request.headers)
        forward_headers = {
            "Content-Type": headers.get("content-type", "application/json"),
        }
        
        if "authorization" in headers:
            forward_headers["Authorization"] = headers["authorization"]
        elif TARGET_API_KEY:
            forward_headers["Authorization"] = f"Bearer {TARGET_API_KEY}"
        
        logger.info(f"转发请求: {request.method} {path}")
        
        # 转发请求
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                content=body,
                headers=forward_headers,
                params=dict(request.query_params)
            )
            
            return JSONResponse(
                content=response.json() if response.headers.get("content-type", "").startswith("application/json") else {"data": response.text},
                status_code=response.status_code
            )
    
    except Exception as e:
        logger.error(f"转发请求失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"转发请求失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"启动服务: {host}:{port}")
    logger.info(f"目标API: {TARGET_API_URL}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )

