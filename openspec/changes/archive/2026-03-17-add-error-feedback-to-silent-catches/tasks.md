## 1. Home.vue — 仪表盘数据加载失败提示

- [x] 1.1 在 `fetchStats` 的 catch 块中加入 `ElMessage.warning('数据加载失败，请稍后刷新')`
- [x] 1.2 在 `fetchRecentProducts` 的 catch 块中加入 `ElMessage.warning('产品列表加载失败，请稍后刷新')`
- [x] 1.3 在 `fetchActivities` 的 catch 块中加入 `ElMessage.warning('动态加载失败，请稍后刷新')`

## 2. ChainVerify.vue — 链上验证双重失败提示

- [x] 2.1 在 `verifyOnChain` 内层 catch 块中加入 `ElMessage.error('链上数据获取失败，请检查网络')`

## 3. 验证

- [x] 3.1 确认 Home.vue 已导入 `ElMessage`（已有，确认即可）
- [x] 3.2 确认 ChainVerify.vue 已导入 `ElMessage`（已有，确认即可）
