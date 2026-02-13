# 农链溯源 - 基于 FISCO BCOS 的农产品溯源平台

基于区块链技术的农产品全流程溯源系统，实现从原料生产到消费者手中的完整追溯链条。

## 项目概述

| 项目 | 说明 |
|------|------|
| 项目名称 | 农链溯源 (Komi Project) |
| 前端技术 | Vue 3 + Vite + Element Plus + Pinia |
| 后端技术 | Python FastAPI + SQLAlchemy + JWT |
| 数据库 | MySQL 5.7+ |
| 区块链 | FISCO BCOS 3.0 (4节点联盟链) |
| AI 集成 | SiliconFlow GLM-4.5-Air |

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户端 (浏览器)                          │
├─────────────────────────────────────────────────────────────────┤
│                    Vue 3 + Element Plus 前端                     │
│              (原料商/加工商/质检员/销售商/消费者)                   │
├─────────────────────────────────────────────────────────────────┤
│                    FastAPI 后端 (RESTful API)                    │
├──────────────────────┬──────────────────────────────────────────┤
│    MySQL 数据库       │          FISCO BCOS 区块链               │
│   (用户/产品/记录)     │     (溯源数据上链/智能合约)               │
└──────────────────────┴──────────────────────────────────────────┘
```

## 系统角色

| 角色 | 标识 | 说明 | 核心功能 |
|------|------|------|----------|
| 原料商 | producer | 农产品生产者 | 产品登记、确认上链、生成溯源码、修正记录 |
| 加工商 | processor | 农产品加工企业 | 原料接收、加工记录、送检 |
| 质检员 | inspector | 质量检测机构 | 质量检测、出具报告、合格/退回/终止 |
| 销售商 | seller | 零售/批发商 | 入库管理、销售出库 |
| 消费者 | consumer | 终端消费者 | 扫码溯源、图片识别、查看 AI 简报 |

## 产品链生命周期

```
原料商登记 → 确认上链 → 生成唯一溯源码
                ↓
加工商接收 → 加工记录 → 送检
                ↓
质检员检测 → 检测报告上链 → 合格/退回
                ↓
销售商入库 → 销售出库
                ↓
消费者扫码 → AI生成简报 → 查看完整溯源
```

## 环境要求

| 组件 | 版本要求 |
|------|----------|
| Node.js | 16.x 或以上 |
| Python | 3.8 或以上 |
| MySQL | 5.7 或以上 |
| FISCO BCOS | 3.0+ |

## 快速开始

### 方式一：一键启动（推荐）

```bash
bash start.sh
```

该脚本依次启动 MySQL → FISCO BCOS 4节点 → FastAPI 后端 → Vue 前端，并检测各服务状态。

### 方式二：分步启动

#### 1. 启动 FISCO BCOS 区块链

```bash
bash ~/fisco/nodes/127.0.0.1/start_all.sh
```

#### 2. 启动后端服务

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt  # 首次
cp .env.example .env             # 首次，配置 AI API Key
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

API 文档：http://localhost:8000/docs

#### 3. 启动前端服务

```bash
cd frontend
npm install  # 首次
npm run dev
```

前端地址：http://localhost:5173

## 区块链配置

### 智能合约

| 项目 | 值 |
|------|------|
| 合约名称 | AgriTrace |
| 合约地址 | `0x6849f21d1e455e9f0712b1e99fa4fcd23758e8f1` |
| 部署网络 | FISCO BCOS 3.0 (本地4节点) |
| RPC 端口 | 20200 |
| 群组 ID | group0 |

### 合约方法

| 方法 | 说明 |
|------|------|
| `createProduct()` | 创建产品并上链 |
| `addRecord()` | 添加操作记录 |
| `addAmendRecord()` | 追加修正记录 |
| `transferProduct()` | 产品转移至下一阶段 |
| `inspectPass()` | 质检通过 |
| `getProduct()` | 查询产品信息 |
| `verifyTraceCode()` | 验证溯源码真伪 |

## API 接口

### 认证 `/api/auth`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/register` | 用户注册 |
| POST | `/auth/login` | 用户登录 |
| GET | `/auth/me` | 获取当前用户信息 |

### 原料商 `/api/producer`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/producer/products` | 获取产品列表 |
| POST | `/producer/products` | 创建产品 |
| GET | `/producer/products/{id}` | 获取产品详情 |
| PUT | `/producer/products/{id}` | 更新产品 |
| DELETE | `/producer/products/{id}` | 删除产品 |
| POST | `/producer/products/{id}/submit` | 提交上链 |
| POST | `/producer/products/{id}/amend` | 提交修正记录 |
| POST | `/producer/products/{id}/invalidate` | 作废产品 |
| POST | `/producer/products/{id}/resubmit` | 重新提交被退回产品 |
| GET | `/producer/products/{id}/records` | 获取产品记录 |
| GET | `/producer/processors` | 获取加工商列表 |
| GET | `/producer/rejected` | 获取被退回产品 |
| GET | `/producer/invalidated` | 获取已作废产品 |
| GET | `/producer/statistics` | 获取统计数据 |

### 加工商 `/api/processor`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/processor/products` | 获取可接收产品 |
| GET | `/processor/products/received` | 已接收产品 |
| GET | `/processor/products/pending` | 待加工产品 |
| GET | `/processor/products/processing` | 加工中产品 |
| GET | `/processor/products/sent` | 已送检产品 |
| GET | `/processor/products/rejected` | 被退回产品 |
| GET | `/processor/products/invalidated` | 已作废产品 |
| POST | `/processor/products/{id}/receive` | 接收原料 |
| POST | `/processor/products/{id}/process` | 添加加工记录 |
| POST | `/processor/products/{id}/send-inspect` | 送检 |
| GET | `/processor/products/{id}/records` | 获取产品记录 |
| GET | `/processor/statistics` | 获取统计数据 |

### 质检员 `/api/inspector`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/inspector/products/pending` | 待检产品 |
| GET | `/inspector/products/testing` | 检测中产品 |
| GET | `/inspector/products/completed` | 已完成检测 |
| POST | `/inspector/products/{id}/start-inspect` | 开始检测 |
| POST | `/inspector/products/{id}/inspect` | 完成检测 |
| GET | `/inspector/products/{id}/records` | 获取产品记录 |
| GET | `/inspector/statistics` | 获取统计数据 |

### 销售商 `/api/seller`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/seller/products/inventory` | 库存产品 |
| GET | `/seller/products/sold` | 已售产品 |
| POST | `/seller/products/{id}/stock-in` | 入库登记 |
| POST | `/seller/products/{id}/sell` | 销售出库 |
| GET | `/seller/products/{id}/records` | 获取产品记录 |
| GET | `/seller/statistics` | 获取统计数据 |

### 区块链 `/api/blockchain`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/blockchain/info` | 获取链信息 |
| GET | `/blockchain/products` | 获取链上产品列表 |
| GET | `/blockchain/product/{trace_code}/chain-data` | 获取产品链上数据 |
| GET | `/blockchain/transaction/{tx_hash}` | 查询交易详情 |
| GET | `/blockchain/block/{block_number}` | 查询区块详情 |
| GET | `/blockchain/verify/{trace_code}` | 验证溯源码 |
| GET | `/blockchain/products/invalidated` | 获取已作废产品 |
| GET | `/blockchain/health` | 检查区块链连接状态 |

### AI `/api/ai`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/ai/summary` | 生成 AI 溯源简报 |
| GET | `/ai/health` | AI 服务健康检查 |

## 测试账号

| 用户名 | 密码 | 角色 | 名称 |
|--------|------|------|------|
| producer | 123456 | 原料商 | 张三农场 |
| processor | 123456 | 加工商 | 绿源加工厂 |
| inspector | 123456 | 质检员 | 李质检 |
| seller | 123456 | 销售商 | 优鲜超市 |
| consumer | 123456 | 消费者 | 王小明 |

## 环境变量

后端 `.env`：

```bash
GLM_API_KEY=your_glm_api_key_here
```

数据库、JWT、FISCO BCOS 连接配置位于 `backend/app/config.py`。

前端 `.env`：

```bash
VITE_API_BASE_URL=http://localhost:8000/api
```

## 数据查询工具

```bash
python3 scripts/chain_explorer.py product TRACE-XXXXXXXX
python3 scripts/chain_explorer.py height
python3 scripts/chain_explorer.py count
python3 scripts/chain_explorer.py block 10

bash scripts/query_chain_data.sh product TRACE-XXXXXXXX
```

## Console 查询示例

```bash
cd /home/pdm/fisco/console

./console.sh getBlockNumber
./console.sh call AgriTrace 0x6849f21d1e455e9f0712b1e99fa4fcd23758e8f1 getProductCount
./console.sh call AgriTrace 0x6849f21d1e455e9f0712b1e99fa4fcd23758e8f1 verifyTraceCode "TRACE-XXXXXXXX"
./console.sh call AgriTrace 0x6849f21d1e455e9f0712b1e99fa4fcd23758e8f1 getProduct "TRACE-XXXXXXXX"
```

## 关键特性

| 特性 | 说明 |
|------|------|
| 唯一溯源码 | 首次上链时生成，格式：`TRACE-YYYYMMDD-XXXXXXXX` |
| 区块链存证 | 所有操作记录上 FISCO BCOS 链，不可篡改 |
| 双重存储 | MySQL 存业务数据，区块链存溯源证据 |
| AI 智能简报 | 消费者扫码后可查看 AI 生成的产品溯源简报 |
| 公共溯源页 | 无需登录即可通过溯源码查询完整溯源信息 |
| 二维码生成 | 支持下载和打印产品溯源二维码 |
| 扫码识别 | 支持摄像头实时扫码和图片上传识别 |
| 产品作废 | 支持作废问题产品，链上记录作废原因 |
| 修正记录 | 已上链产品支持追加修正记录 |
| 钱包管理 | 自动为用户生成区块链地址和密钥对 |

## License

MIT License
