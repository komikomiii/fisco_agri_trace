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

## 智能合约详解（AgriTrace.sol）

### 合约功能总览

合约部署在 FISCO BCOS 链上，地址为 `0x6849f21d1e455e9f0712b1e99fa4fcd23758e8f1`（与 `backend/app/blockchain/config.py` 中 `CONTRACT_ADDRESS` 一致；重新部署后须同步修改该配置及本文档）。提供以下功能：

| 方法 | 类型 | 功能 |
|------|------|------|
| `createProduct()` | 写入 | 创建产品并上链，同时生成第一条采收记录 |
| `addRecord()` | 写入 | 添加流转记录（加工、送检、质检、入库、销售等） |
| `addAmendRecord()` | 写入 | 追加修正记录，关联被修正的前一条记录 |
| `transferProduct()` | 写入 | 转移产品持有者和阶段（原料→加工→质检→销售→已售） |
| `inspectPass()` | 写入 | 质检通过，添加质检记录 |
| `rejectProduct()` | 写入 | 质检退回，转移回加工商或原料商 |
| `terminateProduct()` | 写入 | 终止产品链，标记为 TERMINATED |
| `getProduct()` | 只读 | 查询产品主信息（名称、产地、阶段、持有者等） |
| `getRecord()` | 只读 | 查询指定索引的流转记录 |
| `getRecordCount()` | 只读 | 查询某产品的记录总数 |
| `verifyTraceCode()` | 只读 | 验证溯源码是否存在 |
| `getProductCount()` | 只读 | 查询链上产品总数 |
| `getTotalRecordCount()` | 只读 | 查询链上记录总数 |

### 合约存储的数据结构

**Product（产品主信息）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| traceCode | string | 溯源码（唯一标识） |
| name | string | 产品名称 |
| category | string | 品类 |
| origin | string | 产地 |
| quantity | uint256 | 数量（×1000 存储，支持 3 位小数） |
| unit | string | 单位 |
| currentStage | enum | 当前阶段（0=原料 1=加工 2=质检 3=销售 4=已售） |
| status | enum | 状态（0=已上链 1=已终止） |
| creator | address | 创建者区块链地址 |
| currentHolder | address | 当前持有者区块链地址 |
| createdAt | uint256 | 创建时间（Unix 时间戳） |
| recordCount | uint256 | 该产品的记录数量 |

**Record（流转记录）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| recordId | uint256 | 全局递增记录 ID |
| traceCode | string | 溯源码 |
| stage | enum | 操作阶段 |
| action | enum | 操作类型（0=创建 1=采收 2=接收 3=加工 4=送检 5=质检 6=退回 7=终止 8=入库 9=销售 10=修正） |
| data | string | 操作数据（JSON 字符串，如加工参数、质检结果等） |
| remark | string | 备注 |
| operator | address | 操作人区块链地址 |
| operatorName | string | 操作人名称 |
| timestamp | uint256 | 操作时间（Unix 时间戳） |
| previousRecordId | uint256 | 前一条记录 ID（修正时使用） |
| amendReason | string | 修正原因 |

### 合约事件（Event）

链上操作会触发事件，记录在交易日志（logEntries）中，WeBASE-Front 交易回执里可以看到：

| 事件 | 触发时机 |
|------|----------|
| ProductCreated | 产品首次上链 |
| RecordAdded | 每次添加流转记录 |
| ProductTransferred | 产品持有者转移 |
| ProductTerminated | 产品链终止 |

---

## 链上数据 vs 数据库数据对比

### 设计原则

- **区块链**：存证层，存溯源核心数据，不可篡改，用于验证
- **数据库（MySQL）**：业务层，存业务管理数据，支持增删改查，用于日常操作

### Product 数据对比

| 数据项 | 链上（AgriTrace.Product） | 数据库（products 表） | 说明 |
|--------|--------------------------|----------------------|------|
| 溯源码 | ✓ traceCode | ✓ trace_code | 两边一致 |
| 产品名称 | ✓ name | ✓ name | 两边一致 |
| 品类 | ✓ category | ✓ category | 两边一致 |
| 产地 | ✓ origin | ✓ origin | 两边一致 |
| 数量 | ✓ quantity（×1000 整数） | ✓ quantity（浮点数） | 链上不支持浮点，乘 1000 转整数 |
| 单位 | ✓ unit | ✓ unit | 两边一致 |
| 当前阶段 | ✓ currentStage（枚举值 0-4） | ✓ current_stage（字符串枚举） | 链上用数字，DB 用字符串 |
| 状态 | ✓ status（0=上链/1=终止） | ✓ status（6 种状态） | **DB 比链上多**：DRAFT、PENDING_CHAIN、CHAIN_FAILED、INVALIDATED 是业务状态 |
| 创建者 | ✓ creator（区块链地址） | ✓ creator_id（用户 ID） | 链上存地址，DB 存用户 ID 关联 |
| 当前持有者 | ✓ currentHolder（区块链地址） | ✓ current_holder_id（用户 ID） | 同上 |
| 创建时间 | ✓ createdAt（Unix 时间戳） | ✓ created_at（DateTime） | 格式不同 |
| 批次号 | ✗ | ✓ batch_no | **仅 DB** |
| 采收日期 | ✗ | ✓ harvest_date | **仅 DB** |
| 分配方式 | ✗ | ✓ distribution_type | **仅 DB**（公共池/指定发送） |
| 指定加工商 | ✗ | ✓ assigned_processor_id | **仅 DB** |
| 交易哈希 | ✗（链自身的元数据） | ✓ tx_hash | 链上不需要存自己的 tx_hash |
| 区块高度 | ✗（链自身的元数据） | ✓ block_number | 同上 |
| 作废信息 | ✗ | ✓ invalidated_at/by/reason | **仅 DB**（链上通过 TERMINATED 状态体现） |

### Record 数据对比

| 数据项 | 链上（AgriTrace.Record） | 数据库（product_records 表） | 说明 |
|--------|--------------------------|----------------------------|------|
| 记录 ID | ✓ recordId（全局递增） | ✓ id（自增主键） | 两边独立递增 |
| 溯源码 | ✓ traceCode | ✗（通过 product_id 关联） | 链上直接存，DB 通过外键 |
| 阶段 | ✓ stage（枚举值 0-4） | ✓ stage（字符串枚举） | 格式不同 |
| 操作类型 | ✓ action（枚举值 0-10） | ✓ action（字符串枚举） | 格式不同，DB 多一个 START_INSPECT |
| 操作数据 | ✓ data（JSON 字符串） | ✓ data（JSON 字符串） | 两边一致 |
| 备注 | ✓ remark | ✓ remark | 两边一致 |
| 操作人 | ✓ operator（区块链地址） | ✓ operator_id（用户 ID） | 链上存地址，DB 存用户 ID |
| 操作人名称 | ✓ operatorName | ✓ operator_name | 两边一致 |
| 时间 | ✓ timestamp（Unix 时间戳） | ✓ created_at（DateTime） | 格式不同 |
| 修正关联 | ✓ previousRecordId | ✓ previous_record_id | 两边一致 |
| 修正原因 | ✓ amendReason | ✓ amend_reason | 两边一致 |
| 交易哈希 | ✗ | ✓ tx_hash | **仅 DB**（链上交易哈希是区块链底层元数据） |
| 区块高度 | ✗ | ✓ block_number | **仅 DB** |

### User 数据（仅数据库）

用户信息**不上链**，全部存在 MySQL 的 `users` 表中：

| 字段 | 说明 |
|------|------|
| id | 主键 |
| username | 用户名（唯一） |
| password_hash | 密码哈希（bcrypt） |
| role | 角色（producer/processor/inspector/seller/consumer） |
| real_name | 真实姓名 |
| phone | 手机号 |
| company | 企业名称 |
| blockchain_address | 区块链地址（注册时自动生成） |
| created_at / updated_at | 创建/更新时间 |

### keystore 目录的作用及与 users 表的联动

**keystore 是做什么的**：项目根目录下的 `keystore/` 用来在**服务器本地**保存每个用户的**区块链账户私钥**（经以太坊兼容格式加密后写入 JSON 文件），并配合 `accounts.json` 维护「数据库用户 id → 链上地址 → 密钥文件路径」的索引。链上合约里的 `creator`、`currentHolder`、`operator` 等字段存的是**地址**；真正要能代表该用户发交易，后端必须在写链时取出对应私钥完成签名（本项目通过 FISCO Console 等路径间接使用该身份，密钥仍由 `WalletManager` 管理）。

**和 users 表如何对应**：

1. **一对一按主键对齐**：用户注册并 `commit` 得到 `users.id` 后，`backend/app/api/auth.py` 调用 `wallet_manager.ensure_user_account(user.id, username)`。`WalletManager`（`backend/app/blockchain/wallet.py`）生成密钥对，写入 `keystore/user_{id}.json`，并在 `accounts.json` 里增加一条记录，其键为字符串形式的 **`users.id`**，值为 `username`、`address`、`keystore` 文件绝对路径。
2. **地址写回数据库**：同一流程里把生成的 `address` 写入 **`users.blockchain_address`**。因此：**链上可见的地址**与**业务库里的 blockchain_address**一致，便于接口返回、权限业务与链上数据对照；**私钥从不进数据库**，只存在于 keystore 文件中（加密存储，解密口令在实现上为用户 id 的字符串形式，属服务端保管方案）。
3. **分工小结**：`users` 表负责登录态、角色、展示信息与**链上地址的可查副本**；`keystore` 负责**可签名身份的密钥材料**。二者通过 **`users.id` ↔ `user_{id}.json` ↔ accounts.json 中的 id 键** 联动，缺一不可：缺库则无法认证与关联业务；缺 keystore 则无法用该用户地址完成需要其私钥的链上写入（需重新生成或恢复密钥并与库中地址一致）。

### 为什么这样设计

1. **链上只存溯源必需数据**：产品信息 + 流转记录。这些是需要"不可篡改"保证的核心证据
2. **业务管理数据放数据库**：用户账号、密码、草稿状态、分配方式等是业务逻辑，不需要上链，也不适合上链（链上存储成本高、不支持删改）
3. **tx_hash 和 block_number 存在 DB 不存在链上**：这两个是区块链底层的交易元数据，合约内部无法获取自身的交易哈希，所以由后端在链操作成功后保存到数据库，用于前端展示和 WeBASE 交叉验证

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
│   ├── requirements.txt               # Python 依赖：fastapi, uvicorn, sqlalchemy, pymysql, alembic, python-jose, passlib, httpx等
│   ├── .env                           # 环境变量（GLM_API_KEY，即 SiliconFlow AI API 密钥）
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
│   │   │   ├── ai.py                # /api/ai：调用 SiliconFlow GLM-4.5-Air 生成溯源简报
│   │   │   └── blockchain_address_fix.py  # 辅助工具：将链上零地址/Console 地址替换为数据库中用户真实地址
│   │   │
│   │   ├── blockchain/               # 区块链交互层
│   │   │   ├── __init__.py           # 导出 blockchain_client, FiscoBcosClient, config
│   │   │   ├── config.py            # FISCO 配置：RPC_URL、GROUP_ID、合约地址、Console/Keystore 绝对路径（换机需改）
│   │   │   ├── client.py            # FiscoBcosClient：混合模式（Console 子进程写链 + JSON-RPC 读链）
│   │   │   │                         #   get_block_number, get_product, add_record, create_product 等
│   │   │   ├── account_manager.py   # AccountManager：检查/修复 Console 账户 PEM 文件
│   │   │   └── wallet.py            # WalletManager：为用户创建区块链账户、管理 Keystore 文件
│   │   │
│   │   │
│   │   │ 
│   │   │
│   └── scripts/                       # 后端辅助脚本
│       ├── generate_wallets.py       # 为无区块链地址的用户批量生成钱包
│       └── setup_console_accounts.py # 为所有用户创建 Console 兼容的 PEM 账户文件
│
├── blockchain/                        # ===== 智能合约 =====
│   └── contracts/
│       └── AgriTrace.sol             # Solidity 智能合约：
│                                      #   枚举：Stage（5阶段）、Status（上链/终止）、Action（11种操作，下标 0–10）
│                                      #   结构体：Product（产品信息）、Record（操作记录）
│                                      #   写入方法（7个）：createProduct, addRecord, addAmendRecord,
│                                      #     transferProduct, inspectPass, rejectProduct, terminateProduct
│                                      #   查询方法（6个）：getProduct, getRecord, getRecordCount,
│                                      #     verifyTraceCode, getProductCount, getTotalRecordCount
│
├── keystore/                          # ===== 用户区块链密钥（与 users 表联动说明见上文「keystore 目录的作用及与 users 表的联动」）=====
│   ├── accounts.json                 # users.id（字符串键）→ 用户名、区块链地址、user_{id}.json 路径
│   ├── user_0.json                   # 用户密钥文件（加密存储）
│   ├── user_1.json
│   ├── user_2.json
│   ├── user_3.json
│   ├── user_4.json
│   ├── user_5.json
│   └── user_6.json
│
├── scripts/                           # ===== 工具脚本 =====
│   ├── README.md                     # 脚本使用说明
│   ├── chain_explorer.py             # Python 链上数据查询工具：product/height/count/block/tx 子命令
│   ├── query_chain_data.sh           # Bash 链上数据查询：product/block/tx/height/list
│   ├── verify_chain.py               # Python 溯源码链上验证
│   ├── verify_chain.sh               # Bash 溯源码链上验证
│   ├── verify_chain_encoding.py      # 检查链上中文字段编码是否正确
│   └── compare_db_chain.py           # 对比数据库与链上数据一致性
│
└── （毕业设计 Word/PPT 等文档未纳入本仓库，由本地另行保管）
```

---

# 中期答辩准备指南

## 核心数据流（必须能讲清楚）

一个农产品从诞生到消费者扫码溯源的完整路径：

```
[原料商] 填写产品信息 → 前端 POST /api/producer/products 创建草稿（存数据库）
    │
    ▼
[原料商] 点击"提交上链" → POST /api/producer/products/{id}/submit
    │   后端调用 blockchain/client.py → Console 子进程 → FISCO BCOS
    │   4 节点 PBFT 共识 → 交易打包进区块
    │   后端把 tx_hash / block_number 写回数据库
    │   产品状态: DRAFT → PENDING_CHAIN → ON_CHAIN
    │
    ▼
[加工商] 登录 → 看到公共池 → 接收原料 POST /api/processor/receive
    │   调用合约 transferProduct()，持有者变更为加工商地址
    │
    ▼
[加工商] 添加加工记录 → addRecord() 写链 → 送检 transferProduct() → 质检阶段
    │
    ▼
[质检员] 开始检测 → 完成检测（合格）→ inspectPass() 写链 → 转移给销售商
    │   （如不合格: rejectProduct() 退回，或 terminateProduct() 终止）
    │
    ▼
[销售商] 入库登记 → addRecord() → 销售出库 → addRecord()
    │
    ▼
[消费者] 扫二维码 → /trace/{traceCode}（无需登录）
    │   前端调用 GET /api/blockchain/verify/{traceCode}
    │   后端调用合约 verifyTraceCode() + getProduct() + getRecord() × N
    │   展示完整溯源时间线 + 区块链验证徽章
```

> **关键点**：链上数据（合约）负责"不可篡改的证据"，数据库负责"业务逻辑和状态管理"，两者并行但职责不同。

---

## 高概率被问到的问题

### 架构与设计类（理论）

**Q：为什么选联盟链而不是公有链（以太坊）或中心化数据库？**
> 公有链（以太坊）写入成本高（Gas 费）、延迟高、隐私性差，不适合企业间业务数据；中心化数据库无法解决多方信任问题——任何一方都可以篡改数据。联盟链兼顾了"多方参与、共识不可篡改"和"高效低成本、数据可控"，适合政府监管部门 + 多个企业共同参与的溯源场景。

**Q：数据库和区块链都存了数据，会不会不一致？谁是权威？**
> 设计上链上是"存证权威"，数据库是"业务状态权威"。链上只存溯源必需的不可变数据（产品信息 + 流转记录），数据库存链上没有也不适合存的业务数据（草稿状态、用户账号、分配关系等）。前端的"链上验证"功能就是让用户亲眼对比：数据库展示的信息和链上存的信息是否一致，增加可信度。

**Q：为什么用 PBFT 而不是 PoW（工作量证明）？**
> PBFT 是许可链（联盟链）的主流共识算法，不需要大量算力竞争，出块快（秒级），节点身份已知可控，适合企业联盟场景。PoW 浪费算力、延迟高，适合无需许可的公有链。

**Q：这个项目和真实生产环境有什么差距？**
> 三个简化点（参见本文件"本项目的简化"章节）：单后端连单节点（用 RBAC 替代物理隔离）、4 节点同机部署（生产应在不同服务器）、单群组（未启用数据隔离）。但核心链上共识流程与生产一致。

---

### 代码与实现类（实践）

**Q：智能合约里数量为什么要乘 1000 存储？**
> Solidity 不支持浮点数，`uint256` 只能存整数。把浮点数乘 1000 转成整数存储（保留 3 位小数精度），读取时除以 1000 还原。例如 12.5 kg 存为 12500，显示时 12500 / 1000 = 12.5。

**Q：区块链地址是怎么生成的？用户注册时发生了什么？**
> 用户注册时，后端 `auth.py` 调用 `blockchain/wallet.py` 的 `WalletManager`，自动生成一对 ECDSA 密钥对（私钥/公钥），公钥哈希后得到区块链地址，私钥以加密的 JSON Keystore 文件存在 `keystore/` 目录。用户以后的每笔链上操作都用这个地址签名。

**Q：后端是怎么和 FISCO BCOS 通信的？为什么用 Console 子进程？**
> 后端 `blockchain/client.py` 采用混合模式：**写操作**（需要签名的交易）通过调用 FISCO BCOS 的 Console 工具子进程执行，因为 Console 内置了账户管理和合约 ABI 编码；**读操作**（查询）直接调用 JSON-RPC 接口（HTTP 请求到节点 20200 端口），更高效。

**Q：`ChainVerify.vue` 是做什么的？链上验证的逻辑是什么？**
> 这是一个弹窗组件，让用户验证某笔链上操作的真实性。它做三件事：①查交易哈希（tx_hash）调 `/api/blockchain/transaction/{hash}` 获取交易回执；②查区块高度调 `/api/blockchain/block/{number}` 获取区块信息；③调 `/api/blockchain/verify/{traceCode}` 验证溯源码确实存在于链上。三者都能查到，说明这条记录真实上链了。

**Q：用户权限是怎么控制的？一个角色能不能访问另一个角色的 API？**
> 后端每个 API 都有 `get_current_user` 依赖注入（JWT 鉴权），并检查 `current_user.role`。例如 `processor.py` 里的接收接口会验证 `role == "processor"`，不符合直接返回 403。前端路由守卫也做了角色过滤，但安全边界在后端。

---

## 三个必须读懂的关键文件

这三个文件不需要背，但需要在导师问到时能**当场读懂并解释**：

### 1. `blockchain/contracts/AgriTrace.sol`
重点关注：
- `struct Product` 和 `struct Record` —— 链上存了哪些字段，为什么
- `createProduct()` 函数 —— 产品第一次上链时做了什么
- `mapping(string => Product)` —— 为什么用 string（溯源码）做 key
- `event ProductCreated` 等事件 —— 为什么要发事件（供外部监听和 WeBASE 展示）

### 2. `backend/app/blockchain/client.py`
重点关注：
- 类的整体结构：哪些方法是读（RPC），哪些是写（Console 子进程）
- `create_product()` 方法的流程：如何构造参数、调用 Console、解析返回值
- 错误处理：Console 调用失败时如何返回给上层

### 3. `frontend/src/components/common/ChainVerify.vue`
重点关注：
- `verifyOnChain()` 方法：三个串联的 API 调用
- 数据如何展示：tx_hash、区块高度、溯源码三者如何对应

---

## 现场展示建议

### 推荐演示顺序（约 10 分钟）
1. **登录不同角色**（30 秒）：展示 5 种角色，说明 RBAC 权限设计
2. **原料商上链**（2 分钟）：创建产品 → 提交上链 → 等待确认 → 查看 tx_hash
3. **流转全流程**（3 分钟）：加工商接收 → 加工 → 送检 → 质检通过 → 销售商入库 → 销售
4. **消费者扫码溯源**（2 分钟）：展示完整时间线，点"链上验证"展示区块信息
5. **WeBASE 交叉验证**（1 分钟）：打开 `localhost:5002/WeBASE-Front`，找到同一笔交易，证明链上有记录
6. **AI 溯源简报**（1 分钟）：Report 页面生成 AI 摘要，说明 AI 辅助功能

### 注意事项
- 演示前确认 `start.sh` 已成功启动所有服务（4 节点 + 后端 + 前端 + WeBASE）
- 上链操作有 2-5 秒延迟（PBFT 共识时间），演示时正常，不要以为卡了
- 如果被问到某段代码，直接在 IDE 里找到文件，不要翻来翻去——提前把三个关键文件打开好
- 对于"代码为什么这样写"的问题，可以从**设计意图**回答而不是逐行解释

---

## 如果被问到敏感问题

**Q：你是自己写的代码吗 / AI 帮你写的吗？**
> 诚实回答的同时强调：使用 AI 辅助开发是现代工程实践，重要的是你理解系统设计、能排查问题、能解释每个模块的职责。导师更关心你是否理解这个系统，而不是你每行代码是否手打。

**Q：你遇到了什么技术难点？怎么解决的？**
> 可以选真实遇到的问题，例如：
> - FISCO BCOS Python SDK 不成熟，改用 Console 子进程 + JSON-RPC 混合方案
> - 链上不支持浮点数，设计了 ×1000 整数存储方案
> - 前端需要跨角色演示，设计了 RBAC + 路由守卫的权限体系

## 代码问答

**Q：后端是否采用MVC模式？**
> 没有按经典MVC那种目录命名（没有单独的`controllers/`、服务端模板`views/`），但职责上能对应到M和C。Model对应`app/models/`里的SQLAlchemy ORM；Controller对应`app/api/`下各模块的FastAPI路由，处理HTTP、查库、调链等；后端是REST API主要返回JSON，没有服务端渲染HTML，View通常指响应体或由前端Vue承担展示。整体更接近FastAPI常见的Router加ORM加JSON API，有时也和前端一起看成前后端分离下的变体MVC。另有`app/blockchain/`等属于集成层，不是MVC三件套的标准一层。

**Q：`app/models`里只有两个文件，数据库不是有三张表吗？**
> 三张表与代码仍一一对应：`users`对应`User`（`user.py`），`products`对应`Product`，`product_records`对应`ProductRecord`；后两个模型写在同一个`product.py`里，因为业务上是产品主表加流转记录、且用`relationship`关联，所以用两个Python文件承载三个模型是常见的模块划分方式，不是缺表。`app/models/__init__.py`中导出的也是`User`、`Product`、`ProductRecord`三个类。

