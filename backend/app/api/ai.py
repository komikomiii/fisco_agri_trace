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
    if not chain_data:
        return f"请为溯源码为 {trace_code} 的农产品生成一份溯源简报。"

    product_info = chain_data.get("product_info", {})
    records = chain_data.get("chain_records", [])

    # 基本信息
    name = product_info.get("name", "未知产品")
    origin = product_info.get("origin", "未知产地")
    category = product_info.get("category", "")

    # 阶段映射
    stage_names = {
        0: "原料种植",
        1: "加工生产",
        2: "质量检测",
        3: "仓储物流",
        4: "销售",
        5: "已售出"
    }

    # 构建流程描述
    process_summary = []
    for record in records:
        stage = record.get("stage", 0)
        action = record.get("action", 0)
        operator_name = record.get("operatorName", "")
        remark = record.get("remark", "")
        data = record.get("data", {})

        stage_name = stage_names.get(stage, f"阶段{stage}")

        # 构建记录描述
        record_desc = f"- {stage_name}"
        if operator_name:
            record_desc += f"（操作者：{operator_name}）"
        if remark:
            record_desc += f"：{remark}"

        # 特殊处理质检结果
        if stage == 2 and data:
            if isinstance(data, str):
                try:
                    import json
                    data = json.loads(data)
                except:
                    data = {}
            if data.get("result"):
                record_desc += f"，检测结果：{data['result']}"

        process_summary.append(record_desc)

    process_text = "\n".join(process_summary) if process_summary else "暂无流转记录"

    # 构建完整提示词
    prompt = f"""你是一个农产品溯源专家。请根据以下产品的区块链溯源数据，生成一份简洁易懂的溯源简报。

【产品信息】
- 产品名称：{name}
- 产品类别：{category}
- 产地：{origin}
- 溯源码：{trace_code}

【流转记录】
{process_text}

【要求】
1. 生成3-5句话的简报
2. 突出产品的安全性和可追溯性
3. 语言简洁明了，让消费者容易理解
4. 重点关注质检结果和流转环节的完整性
5. 以自然流畅的段落形式输出，不要使用列表或项目符号

请直接输出简报内容："""

    return prompt


@router.post("/summary", response_model=AISummaryResponse)
async def generate_summary(request: AISummaryRequest):
    """
    生成 AI 溯源简报

    调用智谱 GLM-4.7 模型，根据区块链溯源数据生成易读的中文简报
    """
    try:
        client = get_glm_client()

        # 构建提示词
        prompt = build_summary_prompt(request.trace_code, request.chain_data)

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
