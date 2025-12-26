# 基于 FISCO BCOS 的可视化农产品生产溯源平台

基于区块链技术的农产品全流程溯源系统，实现从原料生产到消费者手中的完整追溯链条。

## 项目信息

- **项目名称**: 基于 FISCO BCOS（飞梭链）的可视化农产品生产溯源平台
- **技术栈**: Vue 3 + Element Plus + Pinia + Python + FISCO BCOS

## 系统角色

| 角色 | 说明 |
|------|------|
| 原料商 (producer) | 登记原料信息、采收出库、生成溯源码 |
| 加工商 (processor) | 接收原料、加工处理、送检 |
| 质检员 (inspector) | 质量检测、出具检测报告、退回/终止处理 |
| 销售商 (seller) | 入库管理、销售登记、生成二维码 |
| 消费者 (consumer) | 扫码查询、查看AI简报、查看完整链上记录 |

## 项目结构

```
komi-project/
├── README.md              # 本文档
├── 开发计划.md            # 开发进度追踪
├── frontend/              # Vue 3 前端
│   ├── src/
│   │   ├── views/         # 页面组件
│   │   │   ├── producer/  # 原料商模块
│   │   │   ├── processor/ # 加工商模块
│   │   │   ├── inspector/ # 质检员模块
│   │   │   ├── seller/    # 销售商模块
│   │   │   ├── consumer/  # 消费者模块
│   │   │   └── trace/     # 溯源详情
│   │   ├── store/         # Pinia 状态管理
│   │   │   ├── product.js # 产品链状态
│   │   │   ├── notification.js # 通知状态
│   │   │   └── user.js    # 用户状态
│   │   ├── components/    # 通用组件
│   │   │   └── common/    # 公共组件
│   │   └── router/        # 路由配置
│   └── package.json
├── backend/               # Python 后端（待开发）
├── blockchain/            # FISCO BCOS 智能合约
├── ai-service/            # Python AI 服务
├── docs/                  # 其他文档
└── 毕设文件/              # 毕设相关文档
```

---

## 核心功能（已完成）

### 产品链生命周期

```
原料商登记(草稿) → 确认上链 → 生成唯一溯源码 → 待加工池/指定发送
                                    ↓
加工商接收 → 加工记录上链 → 送检
                                    ↓
质检员检测 → 检测报告上链 → 合格/退回/终止
                                    ↓
销售商入库 → 入库记录上链 → 销售登记 → 生成二维码
                                    ↓
消费者扫码 → AI生成简报 → 查看详情/链上记录
```

### 关键特性

| 特性 | 说明 |
|------|------|
| 唯一溯源码 | 首次上链时生成，永不改变 |
| 修正记录 | 上链后不可修改原记录，只能追加修正记录（版本链） |
| 分配方式 | 支持"公共池自选"和"指定发送"两种模式 |
| 退回/终止 | 质检不合格可退回指定环节或终止链条，操作上链 |
| 消息通知 | 跨角色实时通知，包含待处理和链变动通知 |
| AI简报 | 消费者扫码后展示AI生成的产品简报 |

### 前端模块完成情况

| 模块 | 状态 | 说明 |
|------|------|------|
| 基础设施 | ✅ 完成 | store/product.js, store/notification.js, 通用组件 |
| 原料商 | ✅ 完成 | Products.vue, Harvest.vue |
| 加工商 | ✅ 完成 | Receive.vue, Process.vue |
| 质检员 | ✅ 完成 | Pending.vue, Reports.vue + 退回/终止功能 |
| 销售商 | ✅ 完成 | Inventory.vue, Sales.vue |
| 消费者 | ✅ 完成 | Scan.vue, Report.vue, Detail.vue |

---

## 环境要求

| 组件 | 版本要求 |
|------|----------|
| Node.js | 16.x 或以上 |
| Python | 3.8 或以上（后端） |

---

## 快速开始

### 前端运行

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问：http://localhost:3000

### 测试账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| producer | 123456 | 原料商 |
| processor | 123456 | 加工商 |
| inspector | 123456 | 质检员 |
| seller | 123456 | 销售商 |
| consumer | 123456 | 消费者 |

---

## 前端通用组件

| 组件 | 路径 | 功能 |
|------|------|------|
| ChainConfirm | components/common/ChainConfirm.vue | 上链确认对话框 |
| TraceCode | components/common/TraceCode.vue | 溯源码展示 |
| AmendRecord | components/common/AmendRecord.vue | 修正记录 |
| RejectDialog | components/common/RejectDialog.vue | 退回/终止对话框 |
| NotificationCenter | components/common/NotificationCenter.vue | 通知中心 |

---

## 开发进度

- [x] 前端框架搭建（Vue 3 + Element Plus + Pinia）
- [x] 原料商模块（草稿/上链、采收出库）
- [x] 加工商模块（接收、加工、送检）
- [x] 质检员模块（检测、退回/终止）
- [x] 销售商模块（入库、销售、二维码）
- [x] 消费者模块（扫码、AI简报、溯源详情）
- [x] 通知系统
- [ ] Python 后端开发
- [ ] 区块链集成（FISCO BCOS）
- [ ] AI 模块（OCR识别、简报生成）
- [ ] 联调测试

详细进度请查看 [开发计划.md](开发计划.md)

---

## 常见问题

### 1. 前端启动失败

```bash
# 清除缓存重新安装
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### 2. 端口被占用

```bash
# 查找占用端口的进程
lsof -i :3000

# 杀死进程
kill -9 <PID>
```

### 3. Mock 模式说明

前端默认开启 Mock 模式，使用 `store/product.js` 中的模拟数据，无需后端即可测试完整流程。

---

## License

MIT License
