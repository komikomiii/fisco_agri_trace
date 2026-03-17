## Context

项目前端已引入 Element Plus 的 `ElMessage` 用于用户通知，但部分仪表盘数据加载函数和链上验证的 fallback 路径在失败时未调用 `ElMessage`，仅静默重置数据为空。

## Goals / Non-Goals

**Goals:**
- 在 4 处 catch 块中加入最小必要的用户反馈
- 使用已有的 `ElMessage` API，与项目现有风格保持一致

**Non-Goals:**
- 不重构错误处理架构
- 不为所有 catch 块统一添加提示（仅针对用户无感知的静默失败）
- 不改动 `Scan.vue:stopScanner` 等有意为空的 catch

## Decisions

### Decision 1: 使用 warning 级别（仪表盘）vs error 级别（链上验证）

仪表盘数据（统计、产品列表、动态）加载失败属于非阻塞性问题，用户仍可正常使用其他功能，使用 `ElMessage.warning` 传达"有问题但不严重"的语气。

`verifyOnChain` 的双重失败属于用户主动操作的核心功能失败，使用 `ElMessage.error` 以明确告知。

### Decision 2: 不绑定 catch 的错误变量

现有代码风格中 `catch {}` 和 `catch (error) { console.error(...) }` 混用。
新增的 4 处只需 `ElMessage` 提示，无需再次 `console.error`（已有日志或无需重复），保持最小改动原则。

## Risks / Trade-offs

- [风险] 仪表盘加载时若网络抖动，页面初始化时会连续弹出多条 warning → `ElMessage` 默认会合并相同内容，可接受
- [权衡] 不做全局统一处理（如 axios 拦截器），保持改动范围极小
