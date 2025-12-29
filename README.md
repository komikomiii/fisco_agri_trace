# 基于 FISCO BCOS 的农产品溯源平台

基于区块链技术的农产品全流程溯源系统，实现从原料生产到消费者手中的完整追溯链条。

## 项目信息

- **项目名称**: 基于 FISCO BCOS 的农产品溯源平台
- **技术栈**: Vue 3 + Element Plus + FastAPI + MySQL + FISCO BCOS 3.0
- **AI 集成**: 智谱 GLM-4 API

## 系统角色

| 角色 | 说明 | 功能模块 |
|------|------|----------|
| 原料商 (producer) | 原料管理、产品上链 | 原料管理 |
| 加工商 (processor) | 接收原料、加工处理 | 原料接收、加工记录 |
| 质检员 (inspector) | 质量检测、结果上链 | 待检产品 |
| 销售商 (seller) | 入库管理、商品上架 | 库存管理 |
| 消费者 (consumer) | 扫码查询、查看简报 | 扫码溯源、查询记录 |

## 项目结构

```
komi-project/
├── README.md              # 本文档
├── frontend/              # Vue 3 前端
│   ├── src/
│   │   ├── views/         # 页面组件
│   │   │   ├── producer/  # 原料商模块
│   │   │   │   └── Products.vue    # 原料管理
│   │   │   ├── processor/ # 加工商模块
│   │   │   │   ├── Receive.vue      # 原料接收
│   │   │   │   └── Process.vue      # 加工记录
│   │   │   ├── inspector/ # 质检员模块
│   │   │   │   └── Pending.vue      # 待检产品
│   │   │   ├── seller/    # 销售商模块
│   │   │   │   └── Products.vue     # 库存管理
│   │   │   ├── consumer/  # 消费者模块
│   │   │   │   ├── Scan.vue         # 扫码溯源
│   │   │   │   ├── History.vue      # 查询记录
│   │   │   │   └── Report.vue       # 溯源简报
│   │   │   └── trace/     # 公共溯源
│   │   │       └── PublicTrace.vue  # 公共溯源页
│   │   ├── components/    # 通用组件
│   │   ├── store/         # Pinia 状态管理
│   │   ├── api/           # API 客户端
│   │   └── router/        # 路由配置
│   └── package.json
├── backend/               # Python FastAPI 后端
│   ├── app/
│   │   ├── api/          # API 路由
│   │   ├── models/       # 数据模型
│   │   ├── schemas/      # Pydantic 模式
│   │   ├── core/         # 核心配置
│   │   └── config.py     # 应用配置
│   ├── .env              # 环境变量 (本地)
│   ├── .env.example      # 环境变量示例
│   └── main.py           # 应用入口
└── blockchain/           # FISCO BCOS 智能合约
```

## 核心功能

### 产品链生命周期

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

### 关键特性

| 特性 | 说明 |
|------|------|
| 唯一溯源码 | 首次上链时生成，永不改变 |
| 区块链存证 | 所有操作记录上 FISCO BCOS 链 |
| AI 智能简报 | 消费者扫码后可查看 AI 生成的产品简报 |
| 公共溯源页 | 无需登录即可通过溯源码查询 |
| 二维码下载 | 支持下载和打印产品溯源二维码 |

## 环境要求

| 组件 | 版本要求 |
|------|----------|
| Node.js | 16.x 或以上 |
| Python | 3.8 或以上 |
| MySQL | 5.7 或以上 |
| FISCO BCOS | 3.0+ |

## 快速开始

### 1. 前端运行

```bash
cd frontend
npm install
npm run dev
```

访问：http://localhost:5173

### 2. 后端运行

```bash
cd backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置 GLM_API_KEY 等

# 启动服务
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

访问：
- API 文档：http://localhost:8000/docs
- ReDoc：http://localhost:8000/redoc

### 3. 数据库初始化

```bash
cd backend
mysql -u root -p < init.sql
```

### 4. FISCO BCOS 节点启动

```bash
# 启动所有节点
bash ~/nodes/127.0.0.1/start_all.sh

# 检查节点状态
ps aux | grep fisco-bcos
```

## 测试账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| producer | 123456 | 原料商 |
| processor | 123456 | 加工商 |
| inspector | 123456 | 质检员 |
| seller | 123456 | 销售商 |
| consumer | 123456 | 消费者 |

## 已完成 API

| 模块 | 接口 | 说明 |
|------|------|------|
| 认证 | POST `/api/auth/login` | 用户登录 |
| 认证 | POST `/api/auth/register` | 用户注册 |
| 认证 | GET `/api/auth/me` | 获取当前用户 |
| 原料商 | GET `/api/producer/products` | 获取产品列表 |
| 原料商 | POST `/api/producer/products` | 创建产品 |
| 原料商 | PUT `/api/producer/products/{id}` | 更新产品 |
| 原料商 | POST `/api/producer/products/{id}/submit` | 提交上链 |
| 区块链 | GET `/api/blockchain/product/{trace_code}` | 获取产品溯源信息 |
| 区块链 | GET `/api/blockchain/products` | 获取已上架产品 |
| AI | POST `/api/ai/summary` | 生成 AI 简报 |

## 环境变量

后端 `.env` 配置示例：

```bash
# AI API 配置
GLM_API_KEY=your_glm_api_key_here
```

## 常见问题

### 1. 前端启动失败

```bash
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### 2. 后端 dotenv 模块缺失

```bash
source venv/bin/activate
pip install python-dotenv
```

### 3. 端口被占用

```bash
lsof -i :8000  # 查找后端端口
lsof -i :5173  # 查找前端端口
kill -9 <PID>  # 杀死进程
```

### 4. FISCO BCOS 节点无法启动

```bash
# 检查端口占用
netstat -an | grep 20200

# 重新启动节点
bash ~/nodes/127.0.0.1/stop_all.sh
bash ~/nodes/127.0.0.1/start_all.sh
```

## 开发进度

- [x] 前端框架搭建（Vue 3 + Element Plus + Pinia）
- [x] 原料商模块（产品管理、上链）
- [x] 加工商模块（原料接收、加工记录）
- [x] 质检员模块（待检产品、检测报告）
- [x] 销售商模块（库存管理、产品上架）
- [x] 消费者模块（扫码溯源、查询记录、AI 简报）
- [x] 公共溯源页面（二维码展示、下载、打印）
- [x] Python 后端框架（FastAPI + SQLAlchemy + JWT）
- [x] 用户认证 API
- [x] 原料商 API
- [x] 区块链查询 API
- [x] AI 简报生成（智谱 GLM-4）
- [x] FISCO BCOS 3.0 区块链部署
- [x] 环境变量配置（GitHub 友好）

## License

MIT License
