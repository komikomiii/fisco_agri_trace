# 项目结构说明

## 联盟链架构说明

### 节点与端口

本项目部署了 FISCO BCOS 3.0 本地 4 节点联盟链，每个节点占用两个端口：

| 节点 | RPC 端口 | P2P 端口 | 模拟角色 |
|------|----------|----------|----------|
| node0 | 20200 | 30300 | 农业监管部门 |
| node1 | 20201 | 30301 | 生产/加工企业 |
| node2 | 20202 | 30302 | 质检机构 |
| node3 | 20203 | 30303 | 销售/流通平台 |

- **RPC 端口**：应用程序通过 JSON-RPC 协议连接节点，发送交易、查询链上数据
- **P2P 端口**：节点之间的内部通信，用于 PBFT 共识投票、区块同步、交易广播，对应用层不可见

### 为什么是 4 个节点而不是 1 个

1 个节点也能运行 FISCO BCOS，但那本质上就是一个普通数据库，没有"共识"可言——数据是否被篡改完全取决于这一个节点的管理者，没有任何人能验证。联盟链的核心价值是**多方参与、互相验证、互不信任**。

FISCO BCOS 采用 PBFT（实用拜占庭容错）共识算法，要求节点数满足 `n >= 3f + 1`（f 为可容忍的拜占庭故障节点数）：

| 节点总数 | 可容忍故障节点 | 最少投票节点 | 说明 |
|----------|---------------|-------------|------|
| 1 | 0 | 1 | 无共识，等于单机数据库 |
| 4 | 1 | 3 | 最小推荐配置，本项目采用 |
| 7 | 2 | 5 | 更高容错，适用于大规模生产 |

4 个节点是最小推荐配置，可容忍 1 个节点故障或作恶。每次上链操作，4 个节点都要对交易达成共识（至少 3 个节点同意），数据才会写入区块。

在本项目的农业溯源场景中，4 个节点模拟了溯源链条中的 4 个不同参与机构：

| 节点 | 模拟角色 | 职责 |
|------|----------|------|
| node0 | 农业局（监管方） | 监管整条溯源链，拥有最高可信度 |
| node1 | 加工企业 | 记录原料接收、加工过程 |
| node2 | 质检机构 | 记录检测结果、出具合格/不合格报告 |
| node3 | 销售平台 | 记录入库、销售信息 |

每个机构各自维护一个节点，共同维护同一条链。当原料商提交一笔"产品上链"交易时，这笔交易会经过以下过程：

1. 交易提交到其中一个节点（本项目是 node0）
2. node0 将交易广播给 node1、node2、node3（通过 P2P 端口）
3. 4 个节点执行 PBFT 三阶段共识（Pre-prepare → Prepare → Commit）
4. 至少 3 个节点确认交易有效后，交易被打包进区块
5. 区块同步到所有 4 个节点，每个节点都持有完整且一致的账本副本

这保证了任何一方都无法单独篡改数据——如果质检机构（node2）试图修改某个产品的检测结果，其他 3 个节点的数据与它不一致，篡改会被立即发现。这就是论文里"不可篡改"和"多方可信"的技术支撑。

> **答辩参考话术**：系统部署 4 节点 PBFT 联盟链，模拟农业溯源场景中监管方、生产方、质检方、销售方各自维护一个节点，通过共识机制保证溯源数据的不可篡改和多方可信。

### 群组（Group）机制

FISCO BCOS 3.0 使用字符串命名群组（如 `group0`），支持在同一条链上划分多个群组，每个群组维护独立的账本和共识。

群组的设计目的是**数据隔离**——不同业务域的数据可以在不同群组中流转，只有加入该群组的节点才能看到和参与共识。举例：

| 群组 | 参与节点 | 用途 | 说明 |
|------|----------|------|------|
| group0 | node0, node1, node2, node3 | 农产品溯源主链 | 本项目使用 |
| group1（未启用） | node0, node2 | 质检专用数据 | 只有监管方和质检机构可见 |
| group2（未启用） | node0, node1, node3 | 供应链金融 | 不含质检机构的敏感数据 |

本项目只使用了默认群组 `group0`，4 个节点全部参与同一条溯源链。WeBASE-Front 浏览器中看到的 `group0` 就是这个默认群组。

### 本项目的简化

在真实生产环境中，每个机构应该部署独立的后端服务，连接本机构的节点：

```
真实生产环境：
  农业局后端   → node0 (20200)  ← 部署在农业局服务器
  加工企业后端 → node1 (20201)  ← 部署在加工企业服务器
  质检机构后端 → node2 (20202)  ← 部署在质检机构服务器
  销售平台后端 → node3 (20203)  ← 部署在销售平台服务器

本项目简化：
  唯一的 FastAPI 后端 → node0 (20200)  ← 全部在一台机器上
  通过 RBAC 角色权限区分不同机构的操作
```

具体简化了以下三点：

1. **单后端连单节点**：只部署一个 FastAPI 后端，连接 node0 的 RPC 端口 20200。通过角色权限（RBAC）在应用层区分不同机构的操作（原料商/加工商/质检员/销售商各自只能调用自己角色的 API），而非通过多后端多节点物理隔离
2. **所有节点同机部署**：4 个节点全部运行在同一台机器（127.0.0.1）上，用不同端口区分。生产环境中应部署在不同服务器甚至不同机房，由各机构独立运维
3. **单群组**：只使用 group0，未演示跨群组数据隔离。生产环境可按业务域划分多个群组

这些简化不影响核心逻辑的正确性——虽然 4 个节点跑在同一台机器上，但链上的共识过程是完整的：每笔交易仍然经过 4 节点 PBFT 共识投票，数据存证和溯源验证流程与生产环境完全一致。区别仅在于部署拓扑，而非共识机制本身。

### 外部工具

项目额外部署了 **WeBASE-Front v3.1.1**（FISCO BCOS 官方区块链浏览器）：

- 独立运行在 `http://localhost:5002/WeBASE-Front`
- 连接 node0 RPC 端口，可视化浏览区块、交易、合约数据
- 与本项目业务逻辑无关，纯粹用于链上数据验证和展示
- 部署位置：`~/webase-front/`（项目目录外）

---

## 项目文件结构

```
komi-project/
├── README.md                          # 项目主文档
├── intro-project.md                   # 本文件，项目结构说明
├── start.sh                           # 一键启动脚本（MySQL → FISCO BCOS → 后端 → 前端 → WeBASE-Front），末尾展示端口占用状态
├── .gitignore                         # Git 忽略规则
│
├── frontend/                          # ===== 前端项目（Vue 3 + Vite）=====
│   ├── package.json                   # 项目依赖声明（vue, element-plus, pinia, axios, html5-qrcode 等）
│   ├── package-lock.json              # 依赖锁定文件
│   ├── vite.config.js                 # Vite 构建配置
│   ├── index.html                     # HTML 入口文件，加载 /src/main.js
│   ├── .env                           # 前端环境变量（VITE_API_BASE_URL）
│   ├── README.md                      # Vue 模板默认说明
│   ├── public/                        # 静态资源
│   │   └── vite.svg                   # Vite 默认图标
│   ├── dist/                          # 生产构建输出目录（npm run build 生成）
│   │
│   └── src/                           # ----- 前端源码 -----
│       ├── main.js                    # 应用入口：挂载 Pinia、Router、Element Plus（中文）、全局样式
│       ├── App.vue                    # 根组件：ElConfigProvider 包裹，路由出口，会话恢复
│       │
│       ├── assets/                    # 静态资源
│       │   └── styles/
│       │       └── global.css         # 全局 CSS 变量（颜色、角色色、阴影、圆角）、通用样式
│       │
│       ├── router/                    # 路由
│       │   └── index.js              # 路由配置：/login、/trace/:code（公共溯源页）、/dashboard 及各角色子路由
│       │                              # 包含导航守卫：鉴权（token 检查）和角色权限控制
│       │
│       ├── store/                     # Pinia 状态管理
│       │   ├── user.js               # 用户状态：登录、注册、登出、会话恢复、角色映射
│       │   ├── product.js            # 产品链数据：productChains 集合、草稿/上链/终止筛选、合并数据
│       │   └── notification.js       # 通知中心：通知列表、未读计数、标记已读、抽屉控制
│       │
│       ├── api/                       # API 请求层（Axios）
│       │   ├── index.js              # Axios 实例：baseURL、JWT 拦截器、401 自动跳转登录
│       │   ├── auth.js               # 认证 API：登录、注册、获取当前用户
│       │   ├── producer.js           # 原料商 API：产品 CRUD、提交上链、修正、作废、统计
│       │   ├── processor.js          # 加工商 API：可接收/已接收/加工中/已送检产品、接收、加工、送检
│       │   ├── inspector.js          # 质检员 API：待检/检测中/已完成产品、开始检测、完成检测
│       │   ├── seller.js             # 销售商 API：库存/已售产品、入库、销售、统计
│       │   ├── blockchain.js         # 区块链 API：链信息、交易/区块查询、溯源码验证、产品链上数据
│       │   └── ai.js                 # AI API：生成溯源简报、健康检查
│       │
│       ├── components/                # 通用组件
│       │   ├── HelloWorld.vue        # Vue 默认模板组件（未使用）
│       │   └── common/
│       │       ├── TraceCode.vue     # 溯源码展示：二维码生成（vue-qrcode）、复制、下载、打印
│       │       ├── ChainVerify.vue   # 链上验证弹窗：交易详情、区块信息、溯源码校验
│       │       ├── ChainConfirm.vue  # 上链确认弹窗：确认提交、加载动画、成功/失败提示
│       │       ├── AmendRecord.vue   # 修正记录弹窗：修改产品字段、填写修正原因、提交
│       │       ├── RejectDialog.vue  # 退回/终止弹窗：退回至加工商/原料商、终止链条
│       │       └── NotificationCenter.vue  # 通知中心抽屉：通知列表、标记已读、跳转溯源
│       │
│       └── views/                     # 页面组件
│           ├── auth/
│           │   └── Login.vue         # 登录/注册页：角色选择、平台介绍
│           │
│           ├── dashboard/
│           │   ├── Layout.vue        # 仪表盘布局：侧边栏菜单（按角色动态生成）、通知中心、登出
│           │   └── Home.vue          # 工作台首页：角色统计卡片、数据概览图表、最近活动、快捷操作、链上产品列表
│           │
│           ├── producer/
│           │   └── Products.vue      # 原料商页面：产品列表、创建/编辑产品、提交上链、修正记录、作废、被退回处理
│           │
│           ├── processor/
│           │   ├── Receive.vue       # 接收原料页：待接收产品池、已接收列表、接收操作、查看溯源码
│           │   └── Process.vue       # 加工处理页：待加工/加工中/已送检/被退回列表、添加加工记录、送检
│           │
│           ├── inspector/
│           │   └── Pending.vue       # 质检页面：待检/检测中/已完成产品列表、开始检测、完成检测（合格/不合格）、退回、终止
│           │
│           ├── seller/
│           │   ├── Products.vue      # 销售商页面：库存管理、已售产品、入库登记、销售出库
│           │   └── Inventory.vue     # 库存视图（基于 productStore，备用页面）
│           │
│           ├── consumer/
│           │   ├── Scan.vue          # 扫码溯源页：摄像头实时扫码（html5-qrcode）、图片上传识别、手动输入溯源码
│           │   ├── Report.vue        # AI 溯源报告页：获取链上数据、调用 AI 生成简报、展示溯源时间线
│           │   └── History.vue       # 查询历史页：本地 localStorage 存储的溯源查询记录
│           │
│           └── trace/
│               ├── PublicTrace.vue   # 公共溯源页（/trace/:code）：无需登录、链上数据展示、二维码、区块链验证徽章
│               └── Detail.vue        # 仪表盘内溯源详情页（基于 productStore）
│
├── backend/                           # ===== 后端项目（Python FastAPI）=====
│   ├── main.py                        # 应用入口：FastAPI 实例、CORS 配置、lifespan（自动建表）、注册路由
│   ├── requirements.txt               # Python 依赖：fastapi, uvicorn, sqlalchemy, pymysql, python-jose, passlib, httpx, zhipuai
│   ├── README.md                      # 后端开发文档
│   ├── .env                           # 环境变量（GLM_API_KEY）
│   ├── .env.example                   # 环境变量模板
│   │
│   ├── app/                           # ----- 应用核心 -----
│   │   ├── __init__.py               # 包初始化
│   │   ├── config.py                 # 配置类：数据库连接、JWT 密钥、FISCO 节点、AI API 地址/模型
│   │   ├── database.py               # SQLAlchemy：引擎创建、SessionLocal、Base、get_db 依赖注入
│   │   │
│   │   ├── models/                   # 数据模型（SQLAlchemy ORM）
│   │   │   ├── __init__.py           # 导出 User, Product, ProductRecord
│   │   │   ├── user.py              # User 模型：用户名、密码哈希、角色枚举、区块链地址、注册时间
│   │   │   └── product.py           # Product 模型：产品名/产地/溯源码/状态/阶段枚举
│   │   │                             # ProductRecord 模型：操作记录/阶段/动作枚举/操作人/交易哈希/数据JSON
│   │   │
│   │   ├── api/                      # API 路由（FastAPI Router）
│   │   │   ├── __init__.py           # 包初始化
│   │   │   ├── auth.py              # /api/auth：注册（自动生成区块链地址）、登录（JWT）、获取当前用户
│   │   │   ├── producer.py          # /api/producer：产品 CRUD、提交上链（后台异步写链）、修正、作废、重新提交、统计
│   │   │   ├── processor.py         # /api/processor：产品列表（多状态筛选）、接收原料、加工处理、送检、统计
│   │   │   ├── inspector.py         # /api/inspector：待检/检测中/已完成列表、开始检测、完成检测（合格/不合格/退回/终止）、统计
│   │   │   ├── seller.py            # /api/seller：库存/已售列表、入库登记、销售出库、统计
│   │   │   ├── blockchain.py        # /api/blockchain：链信息、链上产品列表、产品链上数据、交易/区块查询、溯源码验证、健康检查
│   │   │   ├── ai.py                # /api/ai：调用 SiliconFlow GLM-4.5-Air 生成溯源简报、健康检查
│   │   │   └── blockchain_address_fix.py  # 辅助工具：将链上零地址/Console 地址替换为数据库中用户真实地址
│   │   │
│   │   ├── blockchain/               # 区块链交互层
│   │   │   ├── __init__.py           # 导出 blockchain_client, FiscoBcosClient, config
│   │   │   ├── config.py            # FISCO 配置：RPC_URL、GROUP_ID、合约地址、Console 路径、Keystore 路径
│   │   │   ├── client.py            # FiscoBcosClient：混合模式（Console 子进程写链 + JSON-RPC 读链）
│   │   │   │                         #   get_block_number, get_product, add_record, create_product 等
│   │   │   ├── account_manager.py   # AccountManager：检查/修复 Console 账户 PEM 文件
│   │   │   └── wallet.py            # WalletManager：为用户创建区块链账户、管理 Keystore 文件
│   │   │
│   │   └── services/                 # 业务服务层
│   │       └── __init__.py           # 包初始化（预留扩展）
│   │
│   └── scripts/                       # 后端辅助脚本
│       ├── generate_wallets.py       # 为无区块链地址的用户批量生成钱包
│       └── setup_console_accounts.py # 为所有用户创建 Console 兼容的 PEM 账户文件
│
├── blockchain/                        # ===== 智能合约 =====
│   └── contracts/
│       └── AgriTrace.sol             # Solidity 智能合约：
│                                      #   枚举：Stage（5阶段）、Status（上链/终止）、Action（12种操作）
│                                      #   结构体：Product（产品信息）、Record（操作记录）
│                                      #   方法：createProduct, addRecord, addAmendRecord, transferProduct,
│                                      #         inspectPass, getProduct, verifyTraceCode, getProductCount
│
├── keystore/                          # ===== 用户区块链密钥 =====
│   ├── accounts.json                 # 用户名 → 区块链地址映射表
│   ├── user_0.json                   # 用户密钥文件（加密存储）
│   ├── user_1.json
│   ├── user_2.json
│   ├── user_3.json
│   ├── user_4.json
│   ├── user_5.json
│   └── user_6.json
│
└── scripts/                           # ===== 工具脚本 =====
    ├── README.md                     # 脚本使用说明
    ├── chain_explorer.py             # Python 链上数据查询工具：product/height/count/block/tx 子命令
    ├── query_chain_data.sh           # Bash 链上数据查询：product/block/tx/height/list
    ├── verify_chain.py               # Python 溯源码链上验证
    ├── verify_chain.sh               # Bash 溯源码链上验证
    ├── verify_chain_encoding.py      # 检查链上中文字段编码是否正确
    └── compare_db_chain.py           # 对比数据库与链上数据一致性
```
