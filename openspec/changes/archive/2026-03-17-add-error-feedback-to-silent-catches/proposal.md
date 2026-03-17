## Why

前端多处异步数据加载函数在请求失败时使用了空 catch 块或无用户通知的 catch 块，导致用户看到的是空数据而非错误提示，无法区分"数据本来为空"和"加载失败"两种情况，影响问题排查和用户体验。

## What Changes

- `Home.vue` 的三个仪表盘数据加载函数（`fetchStats`、`fetchRecentProducts`、`fetchActivities`）在失败时增加 `ElMessage.warning` 提示
- `ChainVerify.vue` 的 `verifyOnChain` 内层 fallback catch 在两次 API 均失败时增加 `ElMessage.error` 提示

## Capabilities

### New Capabilities

- `error-feedback`: 网络请求失败时向用户展示明确的错误/警告消息，区分"数据为空"与"加载失败"两种状态

### Modified Capabilities

<!-- 无现有 spec 需要修改 -->

## Impact

- `frontend/src/views/dashboard/Home.vue`: 3 处 catch 块增加用户提示（第 65、76、125 行）
- `frontend/src/components/common/ChainVerify.vue`: 1 处内层 catch 增加提示（第 145 行）
