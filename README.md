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
| AI 集成 | 硅基流动 GLM-4.5-Air |

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
| 原料商 | producer | 农产品生产者 | 产品登记、确认上链、生成溯源码 |
| 加工商 | processor | 农产品加工企业 | 原料接收、加工记录、送检 |
| 质检员 | inspector | 质量检测机构 | 质量检测、出具报告、合格/退回 |
| 销售商 | seller | 零售/批发商 | 入库管理、商品上架、销售 |
| 消费者 | consumer | 终端消费者 | 扫码溯源、查看 AI 简报 |

## 产品链生命周期

```
原料商登记 → 确认上链 → 生成唯一溯源码
                ↓
加工商接收 → 加工记录 → 送检
                ↓
质检员检测 → 检测报告上链 → 合格/退回
                ↓
销售商入库 → 上架销售
                ↓
消费者扫码 → AI生成简报 → 查看完整溯源
```

## 项目结构

```
komi-project/
├── README.md                    # 项目文档
├── frontend/                    # Vue 3 前端
│   ├── src/
│   │   ├── views/               # 页面组件
│   │   │   ├── producer/        # 原料商模块
│   │   │   ├── processor/       # 加工商模块
│   │   │   ├── inspector/       # 质检员模块
│   │   │   ├── seller/          # 销售商模块
│   │   │   ├── consumer/        # 消费者模块
│   │   │   └── trace/           # 公共溯源页
│   │   ├── components/          # 通用组件
│   │   ├── store/               # Pinia 状态管理
│   │   ├── api/                 # API 客户端
│   │   └── router/              # 路由配置
│   └── package.json
├── backend/                     # Python FastAPI 后端
│   ├── app/
│   │   ├── api/                 # API 路由
│   │   ├── models/              # SQLAlchemy 模型
│   │   ├── schemas/             # Pydantic 模式
│   │   ├── services/            # 业务逻辑层
│   │   ├── blockchain/          # 区块链交互层
│   │   └── config.py            # 应用配置
│   ├── main.py                  # 应用入口
│   └── requirements.txt         # Python 依赖
├── blockchain/                  # FISCO BCOS 智能合约
│   └── contracts/
│       └── AgriTrace.sol        # 溯源智能合约
└── scripts/                     # 工具脚本
    ├── chain_explorer.py        # 区块链数据查询工具
    ├── query_chain_data.sh      # Bash 查询脚本
    └── start.sh                 # 一键启动脚本
```

## 环境要求

| 组件 | 版本要求 |
|------|----------|
| Node.js | 16.x 或以上 |
| Python | 3.8 或以上 |
| MySQL | 5.7 或以上 |
| FISCO BCOS | 3.0+ |

## 快速开始

### 方式一：一键启动 (推荐)

```bash
# 启动区块链 + 后端 + 前端
bash scripts/start.sh
```

### 方式二：分步启动

#### 1. 启动 FISCO BCOS 区块链

```bash
# 启动所有节点
bash ~/fisco/nodes/127.0.0.1/start_all.sh

# 检查节点状态
ps aux | grep fisco-bcos
```

#### 2. 启动后端服务

```bash
cd backend

# 创建虚拟环境 (首次)
python3 -m venv venv
source venv/bin/activate

# 安装依赖 (首次)
pip install -r requirements.txt

# 配置环境变量 (首次)
cp .env.example .env
# 编辑 .env 文件配置 AI API Key

# 启动服务
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

访问 API 文档：http://localhost:8000/docs

#### 3. 启动前端服务

```bash
cd frontend

# 安装依赖 (首次)
npm install

# 启动开发服务器
npm run dev
```

访问前端：http://localhost:5173

## 区块链配置

### 智能合约部署信息

| 项目 | 值 |
|------|------|
| 合约名称 | AgriTrace |
| 合约地址 | `0x6849f21d1e455e9f0712b1e99fa4fcd23758e8f1` |
| 部署网络 | FISCO BCOS 3.0 (本地4节点) |
| RPC 端口 | 20200 |
| 群组 ID | group0 |

### 智能合约功能

| 功能 | 方法 | 状态 |
|------|------|------|
| 创建产品 | `createProduct()` | 已集成 |
| 添加记录 | `addRecord()` | 已集成 |
| 修正记录 | `addAmendRecord()` | 已集成 |
| 产品转移 | `transferProduct()` | 已集成 |
| 质检通过 | `inspectPass()` | 已集成 |
| 查询产品 | `getProduct()` | 已集成 |
| 验证溯源码 | `verifyTraceCode()` | 已集成 |

### 使用 Console 查询链上数据

```bash
cd /home/pdm/fisco/console

# 查询区块高度
./console.sh getBlockNumber

# 查询链上产品总数
./console.sh call AgriTrace 0x6849f21d1e455e9f0712b1e99fa4fcd23758e8f1 getProductCount

# 验证溯源码
./console.sh call AgriTrace 0x6849f21d1e455e9f0712b1e99fa4fcd23758e8f1 verifyTraceCode "TRACE-XXXXXXXX"

# 查询产品信息
./console.sh call AgriTrace 0x6849f21d1e455e9f0712b1e99fa4fcd23758e8f1 getProduct "TRACE-XXXXXXXX"
```

## API 接口

### 认证接口 `/api/auth`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/login` | 用户登录 |
| POST | `/auth/register` | 用户注册 |
| GET | `/auth/me` | 获取当前用户 |

### 原料商接口 `/api/producer`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/producer/products` | 获取产品列表 |
| POST | `/producer/products` | 创建产品 |
| PUT | `/producer/products/{id}` | 更新产品 |
| POST | `/producer/products/{id}/submit` | 提交上链 |
| POST | `/producer/products/{id}/amend` | 提交修正记录 |

### 区块链接口 `/api/blockchain`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/blockchain/info` | 获取链信息 |
| GET | `/blockchain/products` | 获取已上架产品 |
| GET | `/blockchain/product/{trace_code}/chain-data` | 获取产品链上数据 |
| GET | `/blockchain/transaction/{tx_hash}` | 查询交易详情 |
| GET | `/blockchain/block/{block_number}` | 查询区块详情 |
| GET | `/blockchain/verify/{trace_code}` | 验证溯源码 |
| GET | `/blockchain/health` | 检查区块链连接状态 |

### AI 接口 `/api/ai`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/ai/summary` | 生成 AI 溯源简报 |

## 测试账号

| 用户名 | 密码 | 角色 | 名称 |
|--------|------|------|------|
| producer | 123456 | 原料商 | 张三农场 |
| processor | 123456 | 加工商 | 绿源加工厂 |
| inspector | 123456 | 质检员 | 李质检 |
| seller | 123456 | 销售商 | 优鲜超市 |
| consumer | 123456 | 消费者 | 王小明 |

## 环境变量配置

后端 `.env` 配置：

```bash
# 数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=123456
MYSQL_DATABASE=agri_trace

# JWT 配置
SECRET_KEY=your-secret-key-here

# AI API 配置 (硅基流动)
SILICONFLOW_API_KEY=your_api_key_here
```

## 常见问题

### 1. FISCO BCOS 节点无法启动

```bash
# 检查端口占用
netstat -an | grep 20200

# 重新启动节点
bash ~/fisco/nodes/127.0.0.1/stop_all.sh
bash ~/fisco/nodes/127.0.0.1/start_all.sh
```

### 2. 后端 bcrypt 版本错误

```bash
pip install bcrypt==4.0.1
```

### 3. 前端启动失败

```bash
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### 4. 端口被占用

```bash
lsof -i :8000  # 后端端口
lsof -i :5173  # 前端端口
kill -9 <PID>
```

## 开发进度

### 已完成

- [x] Vue 3 + Element Plus 前端框架
- [x] FastAPI + SQLAlchemy 后端框架
- [x] JWT 用户认证系统
- [x] FISCO BCOS 3.0 区块链部署 (4节点)
- [x] AgriTrace 智能合约部署
- [x] 原料商模块 (产品管理、上链、修正)
- [x] 加工商模块 (原料接收、加工记录)
- [x] 质检员模块 (待检产品、检测报告)
- [x] 销售商模块 (库存管理、产品上架)
- [x] 消费者模块 (扫码溯源、AI 简报)
- [x] 公共溯源页面 (二维码展示、下载)
- [x] 区块链数据查询 (交易/区块详情)
- [x] AI 简报生成 (硅基流动 GLM-4.5-Air)

### 关键特性

| 特性 | 说明 |
|------|------|
| 唯一溯源码 | 首次上链时生成，格式：TRACE-YYYYMMDD-XXXXXXXX |
| 区块链存证 | 所有操作记录上 FISCO BCOS 链，不可篡改 |
| AI 智能简报 | 消费者扫码后可查看 AI 生成的产品溯源简报 |
| 公共溯源页 | 无需登录即可通过溯源码查询完整溯源信息 |
| 二维码生成 | 支持下载和打印产品溯源二维码 |
| 产品作废 | 支持作废问题产品，链上记录作废原因 |
| 修正记录 | 已上链产品支持追加修正记录 |

## 数据查询工具

项目提供链上数据查询工具：

```bash
# Python 版本 (推荐)
python3 scripts/chain_explorer.py product TRACE-XXXXXXXX
python3 scripts/chain_explorer.py height
python3 scripts/chain_explorer.py count
python3 scripts/chain_explorer.py block 10

# Bash 版本
bash scripts/query_chain_data.sh product TRACE-XXXXXXXX
```

## 技术文档

- [后端开发文档](backend/README.md)
- [脚本工具文档](scripts/README.md)

## License

MIT License
