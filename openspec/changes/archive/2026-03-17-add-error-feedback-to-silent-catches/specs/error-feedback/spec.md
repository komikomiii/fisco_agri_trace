## ADDED Requirements

### Requirement: 仪表盘数据加载失败时展示用户提示

当 Home.vue 中的仪表盘数据加载函数（fetchStats、fetchRecentProducts、fetchActivities）发生网络或 API 错误时，系统 SHALL 向用户展示 warning 级别的消息提示，使用户能够区分"数据为空"与"加载失败"两种状态。

#### Scenario: fetchStats 请求失败

- **WHEN** 用户打开工作台页面，fetchStats 发生异常
- **THEN** 系统显示 ElMessage.warning 提示"数据加载失败，请稍后刷新"
- **AND** currentStats 保持空数组，页面其余部分正常渲染

#### Scenario: fetchRecentProducts 请求失败

- **WHEN** 用户打开工作台页面，fetchRecentProducts 发生异常
- **THEN** 系统显示 ElMessage.warning 提示"产品列表加载失败，请稍后刷新"
- **AND** recentOnChainProducts 保持空数组

#### Scenario: fetchActivities 请求失败

- **WHEN** 用户打开工作台页面，fetchActivities 发生异常
- **THEN** 系统显示 ElMessage.warning 提示"动态加载失败，请稍后刷新"
- **AND** activities 保持空数组

### Requirement: 链上验证双重失败时展示错误提示

当 ChainVerify.vue 的 verifyOnChain 中主调用与 fallback 调用均失败时，系统 SHALL 向用户展示 error 级别的消息提示，而非静默显示空内容。

#### Scenario: 主调用与 fallback 均失败

- **WHEN** blockchainApi.getProductChainData 抛出异常
- **AND** 内层 blockchainApi.verifyTraceCode 也抛出异常
- **THEN** 系统显示 ElMessage.error 提示"链上数据获取失败，请检查网络"
- **AND** verifyResult 设为 null，页面展示"获取链上数据失败"空状态
