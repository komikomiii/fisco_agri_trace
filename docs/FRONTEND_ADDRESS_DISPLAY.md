# 前端区块链地址显示功能说明

## 功能概述

现在前端可以在多个位置查看用户的区块链地址。

## 显示位置

### 1. 侧边栏用户卡片 ⭐
**位置**: 左下角
**显示内容**: 缩略地址
**格式**: `0x3d6Cc4...35Edc` (前8位 + ... + 后6位)

```
┌────────────────────┐
│  🌾 农链溯源       │
├────────────────────┤
│  🏠 工作台         │
│  📦 原料管理       │
│  📅 采收登记       │
│                    │
│  ┌──────────────┐  │
│  │ 张三农场      │  │ ← 用户名
│  │ 原料商        │  │ ← 角色
│  │ 0x3d6Cc4...  │  │ ← 区块链地址 (缩略)
│  └──────────────┘  │
└────────────────────┘
```

**文件**: [frontend/src/views/dashboard/Layout.vue:129-131](../frontend/src/views/dashboard/Layout.vue#L129-L131)

### 2. 顶部用户下拉菜单 ⭐⭐
**位置**: 右上角用户头像
**操作**: 点击用户头像
**显示内容**: 完整用户信息 + 完整地址

```
点击右上角头像 →
┌────────────────────────┐
│ 👤 张三农场            │
│         ▼              │
├────────────────────────┤
│ 用户名                 │
│ 张三农场               │
│                        │
│ 角色                   │
│ 原料商                 │
│                        │
│ 💼 区块链地址          │
│ 0x3d6Cc42a2Af2f...     │ ← 完整地址 (等宽字体)
│                        │
│ ─────────────────────  │
│ 🔄 退出登录            │
└────────────────────────┘
```

**文件**: [frontend/src/views/dashboard/Layout.vue:174-198](../frontend/src/views/dashboard/Layout.vue#L174-L198)

### 3. 工作台首页 ⭐⭐⭐ (最明显)
**位置**: 工作台顶部欢迎区域
**显示内容**: 完整地址 + 复制按钮

```
┌──────────────────────────────────────────────┐
│ 早上好，张三农场 !                            │
│ 欢迎使用农产品溯源平台，这是您今天的工作概览  │
│                                              │
│ ┌────────────────────────────────────────┐  │
│ │ 💼 区块链地址：                         │  │
│ │ 0x3d6Cc42a2Af2f5aE13d6fB1423bC09F387d35Edc │ │
│ │                             [复制按钮] 📋  │  │
│ └────────────────────────────────────────┘  │
│                                              │
│ 2025年12月28日 星期六                        │
└──────────────────────────────────────────────┘
```

**功能**:
- 显示完整42位地址
- 等宽字体 (Courier New)
- 绿色主题边框
- 复制按钮 (点击复制到剪贴板)

**文件**: [frontend/src/views/dashboard/Home.vue:248-260](../frontend/src/views/dashboard/Home.vue#L248-L260)

## 如何查看

### 方法1: 侧边栏 (快速查看)
1. 登录系统
2. 看左下角用户卡片
3. 地址显示在用户名下方

### 方法2: 下拉菜单 (查看完整地址)
1. 登录系统
2. 点击右上角用户头像
3. 在下拉菜单中查看完整地址

### 方法3: 工作台 (推荐) ⭐
1. 登录系统
2. 进入"工作台" (首页)
3. 欢迎文字下方即可看到地址
4. 点击复制按钮可复制地址

## 技术实现

### 1. 用户状态管理
**文件**: [frontend/src/store/user.js:42](../frontend/src/store/user.js#L42)

```javascript
blockchainAddress: response.user.blockchain_address || null
```

### 2. 侧边栏缩略地址
**文件**: [frontend/src/views/dashboard/Layout.vue:129](../frontend/src/views/dashboard/Layout.vue#L129)

```vue
<span v-if="userStore.user?.blockchainAddress" class="user-address">
  {{ userStore.user?.blockchainAddress?.slice(0, 8) }}...{{ userStore.user?.blockchainAddress?.slice(-6) }}
</span>
```

### 3. 下拉菜单完整地址
**文件**: [frontend/src/views/dashboard/Layout.vue:188-193](../frontend/src/views/dashboard/Layout.vue#L188-L193)

```vue
<el-dropdown-item v-if="userStore.user?.blockchainAddress" :icon="Wallet" disabled>
  <div class="user-dropdown-info">
    <span class="user-dropdown-label">区块链地址</span>
    <span class="user-dropdown-address">{{ userStore.user?.blockchainAddress }}</span>
  </div>
</el-dropdown-item>
```

### 4. 工作台地址显示
**文件**: [frontend/src/views/dashboard/Home.vue:248-260](../frontend/src/views/dashboard/Home.vue#L248-L260)

```vue
<div v-if="userStore.user?.blockchainAddress" class="blockchain-address-display">
  <el-icon><Wallet /></el-icon>
  <span class="address-label">区块链地址：</span>
  <span class="address-value">{{ userStore.user?.blockchainAddress }}</span>
  <el-button text size="small" @click="copyAddress" class="copy-btn">
    <el-icon><DocumentCopy /></el-icon>
  </el-button>
</div>
```

### 5. 复制功能
**文件**: [frontend/src/views/dashboard/Home.vue:12-20](../frontend/src/views/dashboard/Home.vue#L12-L20)

```javascript
const copyAddress = () => {
  if (userStore.user?.blockchainAddress) {
    navigator.clipboard.writeText(userStore.user.blockchainAddress).then(() => {
      ElMessage.success('地址已复制到剪贴板')
    }).catch(() => {
      ElMessage.error('复制失败，请手动复制')
    })
  }
}
```

## 样式特点

### 地址缩略
- **位置**: 侧边栏
- **格式**: 前8位 + ... + 后6位
- **字体**: 11px Courier New
- **颜色**: 主题绿色 (#2db84d)

### 完整地址
- **位置**: 下拉菜单、工作台
- **格式**: 完整42位地址
- **字体**: 12px Courier New (等宽)
- **颜色**: 主题绿色
- **换行**: word-break: break-all

### 工作台特殊样式
- **背景**: 绿色渐变 + 边框
- **图标**: 钱包图标
- **交互**: 复制按钮悬停效果

## 测试验证

### 后端API测试
```bash
# 登录并获取地址
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"producer","password":"123456"}' | jq .

# 响应应包含:
{
  "user": {
    "blockchain_address": "0x3d6Cc42a2Af2f5aE13d6fB1423bC09F387d35Edc"
  }
}
```

### 前端查看步骤
1. 访问 http://localhost:5173
2. 使用任意账号登录 (如: producer / 123456)
3. **查看工作台首页** (最明显)
4. 或者查看侧边栏左下角
5. 或者点击右上角头像查看下拉菜单

## 各个用户的地址

| 用户名 | 角色 | 区块链地址 |
|--------|------|-----------|
| producer | 原料商 | `0x3d6Cc42a2Af2f5aE13d6fB1423bC09F387d35Edc` |
| processor | 加工商 | `0x47F466adbC9167735eD36B7c5D38dc8993E40F85` |
| inspector | 质检员 | `0xd6ea116dc83890e38B162e574d455e47BC92f510` |
| seller | 销售商 | `0x02f57d90a01560912837109F126ECAA5B0FFC3b2` |
| consumer | 消费者 | `0x4196259f89FaAeC319445C3376B1244D5639d4c6` |
| 果农1 | 原料商 | `0xc0373125f10Eb89FABef6066c5dD13d83C0B5270` |
| 加工1 | 加工商 | `0xe39897Cb0606d012F6101623829E547F8EB022FE` |

## 故障排查

### 如果看不到地址

1. **检查后端API**
   ```bash
   curl "http://localhost:8000/api/auth/me" \
     -H "Authorization: Bearer <YOUR_TOKEN>"
   ```
   确认返回的 `blockchain_address` 字段不为空

2. **清除浏览器缓存**
   - F12 打开开发者工具
   - Application → Clear storage → Clear site data

3. **检查前端代码**
   - 确认文件已保存
   - Vite 应该自动热重载
   - 或者刷新页面 (Ctrl+F5)

4. **检查用户Store**
   ```javascript
   // 在浏览器控制台执行
   console.log(JSON.parse(localStorage.getItem('user')))
   ```
   确认 `blockchainAddress` 字段存在

## 截图示例

### 侧边栏显示
```
左下角:
┌────────────┐
│  👤 张     │
│  张三农场   │
│  原料商     │
│ 0x3d6C...  │ ← 这里
└────────────┘
```

### 下拉菜单显示
```
点击右上角头像后:
┌──────────────────┐
│ 用户名           │
│ 张三农场         │
│                  │
│ 角色             │
│ 原料商           │
│                  │
│ 区块链地址       │
│ 0x3d6Cc42a2Af2.. │ ← 这里
│                  │
│ 退出登录         │
└──────────────────┘
```

### 工作台显示 (最明显)
```
欢迎区域:
早上好，张三农场 !
欢迎使用农产品溯源平台...

┌────────────────────────────┐
│ 💼 区块链地址：             │
│ 0x3d6Cc42a2Af2f5aE13d6f... │ ← 这里 (最明显)
│                      [复制] │
└────────────────────────────┘
```

## 总结

✅ **3个位置**显示区块链地址:
1. 侧边栏 (缩略)
2. 下拉菜单 (完整)
3. 工作台 (完整 + 复制)

✅ **推荐使用**: 工作台首页 (最明显、最完整)

✅ **已测试**: 后端API正确返回地址

✅ **样式完善**: 等宽字体、主题色、复制功能
