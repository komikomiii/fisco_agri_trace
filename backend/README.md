# 农链溯源 - 后端服务

基于 FastAPI + FISCO BCOS 的农产品溯源后端 API 服务。

## 技术栈

- **框架**: FastAPI
- **数据库**: SQLite (开发) / MySQL (生产)
- **ORM**: SQLAlchemy
- **认证**: JWT (python-jose)
- **密码**: passlib + bcrypt
- **区块链**: FISCO BCOS 3.0

---

## 快速开始

### 1. 创建虚拟环境

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
```

### 2. 安装依赖

```bash
# 使用阿里云镜像加速
pip install -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com \
    fastapi uvicorn sqlalchemy python-jose passlib bcrypt==4.0.1 python-multipart
```

> **注意**: bcrypt 版本必须为 4.0.1，与 passlib 1.7.4 兼容

### 3. 启动服务

```bash
# 开发模式（热重载）
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 生产模式
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4. 访问 API 文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 项目结构

```
backend/
├── main.py                 # FastAPI 应用入口
├── app/
│   ├── config.py          # 配置文件
│   ├── database.py        # 数据库连接
│   ├── models/            # SQLAlchemy 模型
│   │   ├── user.py        # 用户模型
│   │   └── product.py     # 产品模型
│   ├── api/               # API 路由
│   │   ├── auth.py        # 认证接口
│   │   └── producer.py    # 原料商接口
│   ├── services/          # 业务逻辑层
│   └── blockchain/        # 区块链交互层
├── venv/                  # Python 虚拟环境
├── agri_trace.db          # SQLite 数据库文件
└── README.md
```

---

## API 接口

### 认证接口 `/api/auth`

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/auth/login` | 用户登录，返回 JWT token |
| POST | `/auth/register` | 用户注册 |
| GET | `/auth/me` | 获取当前用户信息 |

### 原料商接口 `/api/producer`

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/producer/products` | 获取产品列表（支持 status 过滤）|
| POST | `/producer/products` | 创建产品（草稿）|
| GET | `/producer/products/{id}` | 获取产品详情 |
| PUT | `/producer/products/{id}` | 更新产品（仅草稿）|
| DELETE | `/producer/products/{id}` | 删除产品（仅草稿）|
| POST | `/producer/products/{id}/submit` | 提交上链，生成唯一溯源码 |
| GET | `/producer/products/{id}/records` | 获取产品流转记录 |
| POST | `/producer/products/{id}/amend` | 提交修正记录（仅已上链）|
| GET | `/producer/statistics` | 获取原料商统计数据 |

---

## 测试账号

已预置的测试用户（密码均为 `123456`）：

| 用户名 | 角色 | 名称 |
|--------|------|------|
| producer | 原料商 | 张三农场 |
| processor | 加工商 | 绿源加工厂 |
| inspector | 质检员 | 李质检 |
| seller | 销售商 | 优鲜超市 |
| consumer | 消费者 | 王小明 |

### API 测试示例

```bash
# 登录获取 token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"producer","password":"123456"}'

# 使用 token 创建产品
TOKEN="your_jwt_token_here"
curl -X POST http://localhost:8000/api/producer/products \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"有机番茄","category":"蔬菜","origin":"山东省寿光市","quantity":500,"unit":"kg"}'

# 提交上链
curl -X POST http://localhost:8000/api/producer/products/1/submit \
  -H "Authorization: Bearer $TOKEN"

# 提交修正记录（已上链产品）
curl -X POST http://localhost:8000/api/producer/products/1/amend \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"field":"origin","old_value":"山东省寿光市","new_value":"山东省寿光市蔬菜基地","reason":"补充详细地址"}'

# 获取流转记录
curl http://localhost:8000/api/producer/products/1/records \
  -H "Authorization: Bearer $TOKEN"

# 获取统计数据
curl http://localhost:8000/api/producer/statistics \
  -H "Authorization: Bearer $TOKEN"
```

---

## 数据库配置

### SQLite（开发环境，默认）

无需额外配置，自动创建 `agri_trace.db` 文件。

### MySQL（生产环境）

1. 修改 `app/config.py`:

```python
USE_SQLITE: bool = False  # 改为 False
MYSQL_HOST: str = "localhost"
MYSQL_PORT: int = 3306
MYSQL_USER: str = "root"
MYSQL_PASSWORD: str = "your_password"
MYSQL_DATABASE: str = "agri_trace"
```

2. 安装 MySQL 驱动:

```bash
pip install pymysql
```

3. 创建数据库:

```sql
CREATE DATABASE agri_trace CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

---

## FISCO BCOS 区块链配置

### 1. 下载部署脚本

```bash
cd ~
curl -#LO https://osp-1257653870.cos.ap-guangzhou.myqcloud.com/FISCO-BCOS/FISCO-BCOS/releases/v3.6.0/build_chain.sh
chmod +x build_chain.sh
```

### 2. 构建 4 节点链

```bash
bash build_chain.sh -l 127.0.0.1:4 -p 30300,20200
```

参数说明：
- `-l 127.0.0.1:4`: 在本地部署 4 个节点
- `-p 30300,20200`: P2P 端口起始 30300，RPC 端口起始 20200

### 3. 启动所有节点

```bash
bash nodes/127.0.0.1/start_all.sh
```

### 4. 检查节点状态

```bash
# 查看进程
ps aux | grep -v grep | grep fisco-bcos

# 预期输出：4 个 fisco-bcos 进程
# 端口分配：
# - P2P: 30300, 30301, 30302, 30303
# - RPC: 20200, 20201, 20202, 20203
```

### 5. 停止所有节点

```bash
bash nodes/127.0.0.1/stop_all.sh
```

### 6. 节点目录结构

```
~/nodes/127.0.0.1/
├── node0/          # 节点0
├── node1/          # 节点1
├── node2/          # 节点2
├── node3/          # 节点3
├── start_all.sh    # 启动所有节点
└── stop_all.sh     # 停止所有节点
```

---

## 区块链集成 (已完成)

### 智能合约部署信息

| 项目 | 值 |
|------|------|
| 合约名称 | AgriTrace |
| 合约地址 | `0x6849f21d1e455e9f0712b1e99fa4fcd23758e8f1` |
| 部署网络 | FISCO BCOS 3.0 (本地4节点) |
| RPC 端口 | 20200 |
| 群组 ID | group0 |

### 区块链服务层

位于 `app/blockchain/` 目录：

```
app/blockchain/
├── __init__.py      # 模块导出
├── config.py        # 区块链配置（RPC地址、合约地址等）
└── client.py        # 区块链客户端（调用智能合约）
```

### 智能合约功能

溯源智能合约已部署至链上，位于 `blockchain/contracts/AgriTrace.sol`，实现以下功能：

| 功能 | 合约方法 | 描述 | 状态 |
|------|----------|------|------|
| 创建产品 | `createProduct()` | 原料商上链 | ✅ 已集成 |
| 添加记录 | `addRecord()` | 添加流转记录 | ✅ 已集成 |
| 修正记录 | `addAmendRecord()` | 提交修正记录 | ✅ 已集成 |
| 产品转移 | `transferProduct()` | 转移到下一阶段 | 待集成 |
| 质检通过 | `inspectPass()` | 质检员确认通过 | 待集成 |
| 退回产品 | `rejectProduct()` | 质检不合格退回 | 待集成 |
| 终止产品 | `terminateProduct()` | 终止产品链 | 待集成 |
| 查询产品 | `getProduct()` | 获取产品信息 | ✅ 已集成 |
| 验证溯源码 | `verifyTraceCode()` | 验证溯源码是否存在 | ✅ 已集成 |

### 使用 Console 管理合约

```bash
# 进入 Console
cd /home/pdm/fisco/console
./console.sh

# 查询链上产品数量
call AgriTrace 0x6849f21d1e455e9f0712b1e99fa4fcd23758e8f1 getProductCount

# 验证溯源码
call AgriTrace 0x6849f21d1e455e9f0712b1e99fa4fcd23758e8f1 verifyTraceCode "TRACE-20251226-XXXXXXXX"

# 查询产品信息
call AgriTrace 0x6849f21d1e455e9f0712b1e99fa4fcd23758e8f1 getProduct "TRACE-20251226-XXXXXXXX"
```

---

## 环境变量

可通过环境变量覆盖默认配置：

```bash
export APP_NAME="农链溯源 API"
export SECRET_KEY="your-production-secret-key"
export USE_SQLITE="false"
export MYSQL_HOST="your-mysql-host"
export MYSQL_PASSWORD="your-mysql-password"
```

---

## 常见问题

### 1. bcrypt 版本错误

```
AttributeError: module 'bcrypt' has no attribute '__about__'
```

**解决方案**: 安装兼容版本

```bash
pip install bcrypt==4.0.1
```

### 2. 端口被占用

```bash
# 查找占用端口的进程
lsof -i :8000

# 杀死进程
kill -9 <PID>
```

### 3. 数据库迁移

目前使用 SQLAlchemy 自动创建表。如需迁移工具，可安装 Alembic：

```bash
pip install alembic
alembic init alembic
```

---

## 开发计划

### 已完成

- [x] 用户认证 (JWT)
- [x] 原料商完整 API（CRUD + 上链 + 修正 + 统计）
- [x] 溯源智能合约 (Solidity)
- [x] FISCO BCOS 区块链部署 (4节点)
- [x] **原料商前后端联调**（前端已适配 API 数据格式）
- [x] **真实区块链交互**（通过 Console 调用智能合约，数据真实上链）

### 待开发

- [ ] 加工商 API + 区块链集成
- [ ] 质检员 API + 区块链集成
- [ ] 销售商 API + 区块链集成
- [ ] 消费者溯源 API
- [ ] AI 简报生成

---

## 原料商功能说明

原料商模块已完成前后端完整联调，支持以下功能：

### 产品管理

| 功能 | 状态 | 说明 |
|------|------|------|
| 创建产品 | ✅ 完成 | 创建草稿状态的产品 |
| 编辑产品 | ✅ 完成 | 仅草稿状态可编辑 |
| 删除产品 | ✅ 完成 | 仅草稿状态可删除 |
| 产品列表 | ✅ 完成 | 支持状态过滤（草稿/已上链/全部）|
| 上链提交 | ✅ 完成 | 生成唯一溯源码，**真实上链**到 FISCO BCOS |
| 修正记录 | ✅ 完成 | 已上链产品可追加修正记录，**真实上链** |
| 流转记录 | ✅ 完成 | 查看产品完整操作历史 |
| 统计数据 | ✅ 完成 | 产品总数、各状态数量统计 |

### 前端适配

前端 `Products.vue` 已完成以下适配：

1. **双格式兼容**：同时支持 API 返回格式和本地 store 格式
2. **详情抽屉**：自动加载产品流转记录
3. **修正记录组件**：正确传递 API 格式数据
4. **状态映射**：`draft` → 草稿, `on_chain` → 已上链, `terminated` → 已终止

### API 测试示例

```bash
# 登录获取 token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"producer","password":"123456"}' | jq -r '.access_token')

# 获取产品列表
curl http://localhost:8000/api/producer/products -H "Authorization: Bearer $TOKEN"

# 获取流转记录
curl http://localhost:8000/api/producer/products/1/records -H "Authorization: Bearer $TOKEN"

# 提交修正记录
curl -X POST http://localhost:8000/api/producer/products/1/amend \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"field":"origin","old_value":"山东省","new_value":"山东省寿光市","reason":"补充详细地址"}'

# 获取统计数据
curl http://localhost:8000/api/producer/statistics -H "Authorization: Bearer $TOKEN"
```
