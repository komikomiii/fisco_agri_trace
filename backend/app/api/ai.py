"""
AI API - AI 溯源简报生成接口
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from zhipuai import ZhipuAI

from app.config import settings

router = APIRouter(prefix="/ai", tags=["AI简报"])


class AISummaryRequest(BaseModel):
    """AI简报生成请求"""
    trace_code: str
    chain_data: Optional[dict] = None


class AISummaryResponse(BaseModel):
    """AI简报生成响应"""
    summary: str
    trace_code: str
    success: bool


def get_glm_client():
    """获取 GLM API 客户端"""
    api_key = settings.GLM_API_KEY
    return ZhipuAI(api_key=api_key)


def build_summary_prompt(trace_code: str, chain_data: dict) -> str:
    """构建 AI 简报生成的提示词"""
    from datetime import datetime

    if not chain_data:
        return f"请为溯源码为 {trace_code} 的农产品生成一份溯源简报。"

    product_info = chain_data.get("product_info", {})
    records = chain_data.get("chain_records", [])

    # 基本信息
    name = product_info.get("name", "未知产品")
    origin = product_info.get("origin", "未知产地")
    category = product_info.get("category", "")
    quantity = product_info.get("quantity", 0)
    unit = product_info.get("unit", "")
    created_at = product_info.get("createdAt")
    record_count = product_info.get("recordCountNum", len(records))

    # 格式化创建时间
    if created_at:
        create_time = datetime.fromtimestamp(created_at).strftime("%Y年%m月%d日")
    else:
        create_time = "未知"

    # 阶段和动作映射
    stage_names = {
        "producer": "原料种植",
        "processor": "加工生产",
        "inspector": "质量检测",
        "seller": "销售"
    }

    action_names = {
        "create": "创建产品",
        "harvest": "收获",
        "receive": "接收原料",
        "process": "加工处理",
        "send_inspect": "送检",
        "start_inspect": "开始检测",
        "inspect": "质量检测",
        "stock_in": "入库",
        "sell": "销售"
    }

    # 构建详细流程描述
    process_details = []
    for record in records:
        stage = record.get("stage", "")
        action = record.get("action", "")
        operator_name = record.get("operatorName", "")
        remark = record.get("remark", "")
        data_str = record.get("data", "")
        timestamp = record.get("timestamp")

        # 格式化时间
        if timestamp:
            time_str = datetime.fromtimestamp(timestamp).strftime("%m月%d日 %H:%M")
        else:
            time_str = ""

        # 解析 data 字段获取更多信息
        extra_info = ""
        if data_str:
            try:
                import json
                data = json.loads(data_str) if isinstance(data_str, str) else data_str
                # 提取关键信息
                if "warehouse" in data:
                    extra_info += f" → {data['warehouse']}"
                if "buyer_name" in data:
                    extra_info += f" → 买家: {data['buyer_name']}"
                if "inspect_result" in data:
                    extra_info += f" → {data['inspect_result']}"
                if "quality_grade" in data:
                    extra_info += f" → 等级: {data['quality_grade']}"
                if "process_type" in data:
                    extra_info += f" → 工艺: {data['process_type']}"
                if "result_product" in data:
                    extra_info += f" → 产出: {data['result_product']}"
            except:
                pass

        stage_name = stage_names.get(stage, stage)
        action_name = action_names.get(action, action)

        # 构建记录描述
        parts = [f"- {time_str}"] if time_str else []
        parts.append(f"{stage_name}")
        if action_name:
            parts.append(action_name)
        if operator_name:
            parts.append(f"({operator_name})")
        if remark:
            parts.append(f": {remark}")
        if extra_info:
            parts.append(extra_info)

        process_details.append(" ".join(parts))

    process_text = "\n".join(process_details) if process_details else "暂无流转记录"

    # 构建完整提示词
    prompt = f"""你是一个农产品溯源专家。请根据以下产品的区块链溯源数据，生成一份简洁易懂的溯源简报。

【产品基本信息】
- 产品名称：{name}
- 产品类别：{category}
- 产地：{origin}
- 数量：{quantity} {unit}
- 溯源码：{trace_code}
- 创建时间：{create_time}
- 流转记录数：{record_count} 条

【完整流转记录】
{process_text}

【要求】
1. 生成3-5句话的简报
2. 突出产品的安全性和可追溯性
3. 语言简洁明了，让消费者容易理解
4. 重点关注质检结果和流转环节的完整性
5. 包含关键时间点和操作者信息
6. 以自然流畅的段落形式输出，不要使用列表或项目符号

请直接输出简报内容："""

    return prompt


@router.post("/summary", response_model=AISummaryResponse)
async def generate_summary(request: AISummaryRequest):
    """
    生成 AI 溯源简报

    调用智谱 GLM-4.5-X 模型，根据区块链溯源数据生成易读的中文简报
    """
    try:
        client = get_glm_client()

        # 打印请求数据用于调试
        print(f"=== AI Summary Request ===")
        print(f"trace_code: {request.trace_code}")
        print(f"chain_data type: {type(request.chain_data)}")
        if request.chain_data:
            print(f"chain_data keys: {request.chain_data.keys() if isinstance(request.chain_data, dict) else 'N/A'}")
            print(f"product_info: {request.chain_data.get('product_info', {})}")
            print(f"records count: {len(request.chain_data.get('chain_records', []))}")
        else:
            print("chain_data is None or empty")

        # 构建提示词
        prompt = build_summary_prompt(request.trace_code, request.chain_data)
        print(f"Generated prompt length: {len(prompt)}")

        # 调用 GLM API
        # 使用 glm-4.5-x 模型，禁用深度思考以直接获取结果
        response = client.chat.completions.create(
            model="glm-4.5-x",
            messages=[
                {
                    "role": "system",
                    "content": "你是一个农产品溯源专家，擅长用简洁易懂的语言生成产品溯源简报。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.8,
            max_tokens=300,
            thinking={
                "type": "disabled"  # 禁用深度思考，直接输出结果
            },
        )

        # 提取生成的简报
        message = response.choices[0].message
        content = message.content if message.content else ""

        if content:
            summary = content.strip()
        else:
            summary = "AI生成失败，请稍后重试"

        return AISummaryResponse(
            summary=summary,
            trace_code=request.trace_code,
            success=True
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"AI简报生成失败: {str(e)}")


@router.get("/health")
async def ai_health():
    """检查 AI API 服务状态"""
    try:
        client = get_glm_client()
        # 简单测试调用
        response = client.chat.completions.create(
            model="glm-4.7",
            messages=[{"role": "user", "content": "你好"}],
            max_tokens=10,
        )
        return {
            "status": "healthy",
            "connected": True,
            "model": "glm-4.7"
        }
    except Exception as e:
        return {
            "status": "error",
            "connected": False,
            "error": str(e)
        }
