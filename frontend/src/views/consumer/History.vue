<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Clock,
  Delete,
  CircleCheck,
  CircleClose,
  MagicStick,
  Document,
  Loading,
  Refresh
} from '@element-plus/icons-vue'
import { blockchainApi, aiApi } from '../../api'

const router = useRouter()
const route = useRoute()

// 查询记录（从 localStorage 读取）
const history = ref([])
const generating = ref({}) // 正在生成简报的溯源码

// 从 localStorage 加载历史记录
const loadHistory = () => {
  try {
    const saved = localStorage.getItem('trace_history')
    if (saved) {
      history.value = JSON.parse(saved)
    }
  } catch (e) {
    console.error('加载历史记录失败:', e)
  }
}

// 保存历史记录到 localStorage
const saveHistory = () => {
  try {
    localStorage.setItem('trace_history', JSON.stringify(history.value))
  } catch (e) {
    console.error('保存历史记录失败:', e)
  }
}

// 添加历史记录
const addHistory = (traceCode, productInfo, verified) => {
  const existingIndex = history.value.findIndex(h => h.code === traceCode)
  const record = {
    id: Date.now(),
    code: traceCode,
    name: productInfo?.name || '未知产品',
    origin: productInfo?.origin || '-',
    scanDate: new Date().toLocaleString('zh-CN'),
    result: verified ? 'verified' : 'failed',
    summary: null,
    summaryStatus: 'none' // none, generating, done, error
  }

  if (existingIndex >= 0) {
    // 更新现有记录
    history.value[existingIndex] = { ...history.value[existingIndex], ...record }
  } else {
    // 添加新记录到开头
    history.value.unshift(record)
  }

  saveHistory()
}

// 删除记录
const deleteRecord = (id) => {
  history.value = history.value.filter(h => h.id !== id)
  saveHistory()
}

// 清空记录
const clearHistory = () => {
  history.value = []
  saveHistory()
}

// 查看详情 - 跳转到公共溯源页面
const viewDetail = (code) => {
  router.push(`/trace/${code}`)
}

// 生成 AI 简报
const generateSummary = async (record) => {
  if (record.summaryStatus === 'generating') return

  // 更新状态为生成中
  record.summaryStatus = 'generating'
  saveHistory()

  try {
    // 先获取产品的链上数据
    let chainData = null
    try {
      const response = await blockchainApi.getProductChainData(record.code)
      if (response && response.exists) {
        chainData = response
      }
    } catch (e) {
      console.warn('获取链上数据失败，将只使用基本信息', e)
    }

    // 调用真实 AI API 生成简报
    const aiResponse = await aiApi.generateSummary(record.code, chainData)

    if (aiResponse && aiResponse.success) {
      record.summary = aiResponse.summary
      record.summaryStatus = 'done'
      ElMessage.success('AI 简报生成成功')
    } else {
      throw new Error('AI 生成返回失败')
    }
  } catch (error) {
    console.error('AI 简报生成失败:', error)
    record.summaryStatus = 'error'
    ElMessage.error('AI 简报生成失败，请稍后重试')
  }

  saveHistory()
}

// 重新生成
const regenerateSummary = (record) => {
  record.summaryStatus = 'none'
  record.summary = null
  saveHistory()
  generateSummary(record)
}

// 查看简报
const viewSummary = (record) => {
  // 显示简报详情弹窗
  selectedSummary.value = record
  summaryVisible.value = true
}

// 简报弹窗
const summaryVisible = ref(false)
const selectedSummary = ref(null)

// 检查是否需要生成新的简报
onMounted(() => {
  loadHistory()

  // 检查 URL 参数是否有 generate 标记
  const generateCode = route.query.generate
  if (generateCode) {
    // 查找或添加记录并开始生成
    const existing = history.value.find(h => h.code === generateCode)
    if (existing) {
      if (existing.summaryStatus === 'none' || existing.summaryStatus === 'error') {
        generateSummary(existing)
      }
    } else {
      // 先获取产品信息，然后添加记录
      fetchProductAndAdd(generateCode)
    }

    // 清除 URL 参数
    router.replace({ path: route.path, query: {} })
  }
})

// 获取产品信息并添加到历史
const fetchProductAndAdd = async (traceCode) => {
  try {
    const response = await blockchainApi.getProductChainData(traceCode)
    if (response && response.exists) {
      addHistory(traceCode, response.product_info, true)
      // 找到刚添加的记录并生成简报
      const newRecord = history.value.find(h => h.code === traceCode)
      if (newRecord) {
        generateSummary(newRecord)
      }
    }
  } catch (e) {
    // 忽略错误
  }
}

// 获取简报状态配置
const getSummaryStatus = (record) => {
  switch (record.summaryStatus) {
    case 'generating':
      return { icon: Loading, text: '生成中...', class: 'generating', spinning: true }
    case 'done':
      return { icon: Document, text: '已完成', class: 'done', spinning: false }
    case 'error':
      return { icon: CircleClose, text: '生成失败', class: 'error', spinning: false }
    default:
      return { icon: MagicStick, text: '生成简报', class: 'none', spinning: false }
  }
}

// 获取产品图片（根据品类）
const getProductEmoji = (name) => {
  const n = name?.toLowerCase() || ''
  if (n.includes('苹果') || n.includes('果')) return '🍎'
  if (n.includes('石榴')) return '🌰'
  if (n.includes('橙') || n.includes('橘')) return '🍊'
  if (n.includes('香蕉')) return '🍌'
  if (n.includes('葡萄')) return '🍇'
  if (n.includes('西瓜')) return '🍉'
  if (n.includes('番茄') || n.includes('茄')) return '🍅'
  if (n.includes('胡萝卜')) return '🥕'
  if (n.includes('玉米')) return '🌽'
  if (n.includes('菜') || n.includes('芹')) return '🥬'
  if (n.includes('蛋')) return '🥚'
  if (n.includes('奶') || n.includes('牛')) return '🥛'
  if (n.includes('麦') || n.includes('米') || n.includes('粮')) return '🌾'
  if (n.includes('鱼')) return '🐟'
  if (n.includes('肉')) return '🥩'
  return '📦'
}
</script>

<template>
  <div class="history-page">
    <div class="page-header">
      <div class="header-content">
        <h1>
          <el-icon :size="28"><Clock /></el-icon>
          查询记录
        </h1>
        <p class="subtitle">查看您的溯源查询历史和 AI 生成的简报</p>
      </div>
      <el-button v-if="history.length > 0" type="danger" plain :icon="Delete" @click="clearHistory">
        清空记录
      </el-button>
    </div>

    <!-- 空状态 -->
    <div v-if="history.length === 0" class="empty-state">
      <div class="empty-icon">
        <el-icon :size="80" color="#d9d9d9"><Clock /></el-icon>
      </div>
      <h3>暂无查询记录</h3>
      <p>扫码或输入溯源码查询后，记录将显示在这里</p>
      <el-button type="primary" @click="router.push('/dashboard/consumer/scan')">
        开始扫码溯源
      </el-button>
    </div>

    <!-- 历史记录列表 -->
    <div v-else class="history-list">
      <div
        v-for="record in history"
        :key="record.id"
        class="history-card"
        :class="{ 'failed': record.result === 'failed' }"
      >
        <!-- 左侧：产品信息 -->
        <div class="product-section">
          <div class="product-icon">
            <span class="emoji">{{ getProductEmoji(record.name) }}</span>
          </div>
          <div class="product-info">
            <h3>{{ record.name }}</h3>
            <div class="meta-tags">
              <el-tag size="small" effect="plain" type="info">{{ record.code }}</el-tag>
              <span class="origin">{{ record.origin }}</span>
            </div>
          </div>
        </div>

        <!-- 右侧：操作区 -->
        <div class="action-section">
          <!-- 验证状态 -->
          <div class="status-badge" :class="record.result">
            <el-icon v-if="record.result === 'verified'"><CircleCheck /></el-icon>
            <el-icon v-else><CircleClose /></el-icon>
            <span>{{ record.result === 'verified' ? '验证通过' : '验证失败' }}</span>
          </div>

          <!-- AI 简报操作 -->
          <div class="summary-section">
            <template v-if="record.result === 'verified'">
              <template v-if="record.summaryStatus === 'done'">
                <el-button type="success" plain size="small" @click="viewSummary(record)">
                  <el-icon><Document /></el-icon>
                  查看简报
                </el-button>
                <el-button text size="small" @click="regenerateSummary(record)">
                  <el-icon><Refresh /></el-icon>
                </el-button>
              </template>

              <template v-else-if="record.summaryStatus === 'generating'">
                <div class="generating-btn">
                  <el-icon class="rotating"><Loading /></el-icon>
                  <span>AI 生成中...</span>
                </div>
              </template>

              <template v-else-if="record.summaryStatus === 'error'">
                <el-button type="warning" plain size="small" @click="generateSummary(record)">
                  <el-icon><MagicStick /></el-icon>
                  重试生成
                </el-button>
              </template>

              <template v-else>
                <el-button type="primary" plain size="small" @click="generateSummary(record)">
                  <el-icon><MagicStick /></el-icon>
                  生成 AI 简报
                </el-button>
              </template>
            </template>
          </div>

          <!-- 操作按钮 -->
          <div class="card-actions">
            <el-button
              v-if="record.result === 'verified'"
              type="primary"
              text
              @click="viewDetail(record.code)"
            >
              查看详情
            </el-button>
            <el-button
              type="danger"
              text
              size="small"
              @click="deleteRecord(record.id)"
            >
              删除
            </el-button>
          </div>

          <div class="scan-time">{{ record.scanDate }}</div>
        </div>
      </div>
    </div>

    <!-- 简报详情弹窗 -->
    <el-dialog
      v-model="summaryVisible"
      title="AI 溯源简报"
      width="500px"
      center
    >
      <div v-if="selectedSummary" class="summary-content">
        <div class="summary-header">
          <span class="summary-emoji">{{ getProductEmoji(selectedSummary.name) }}</span>
          <div class="summary-title">
            <h3>{{ selectedSummary.name }}</h3>
            <el-tag size="small" type="info">{{ selectedSummary.code }}</el-tag>
          </div>
        </div>
        <div class="summary-text">
          <pre>{{ selectedSummary.summary }}</pre>
        </div>
        <div class="summary-footer">
          <el-tag type="success" effect="plain">
            <el-icon><CircleCheck /></el-icon>
            AI 分析完成
          </el-tag>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.history-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
}

.header-content h1 {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 28px;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0 0 8px 0;
}

.subtitle {
  font-size: 14px;
  color: #999;
  margin: 0;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 80px 24px;
}

.empty-icon {
  margin-bottom: 24px;
}

.empty-state h3 {
  font-size: 20px;
  color: #666;
  margin: 0 0 12px 0;
}

.empty-state p {
  font-size: 14px;
  color: #999;
  margin: 0 0 24px 0;
}

/* 历史记录列表 */
.history-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.history-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  transition: all 0.2s;
}

.history-card:hover {
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.history-card.failed {
  border-left: 4px solid #ff4d4f;
}

/* 产品区域 */
.product-section {
  display: flex;
  align-items: center;
  gap: 16px;
}

.product-icon {
  width: 56px;
  height: 56px;
  background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.emoji {
  font-size: 28px;
}

.product-info h3 {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 8px 0;
}

.meta-tags {
  display: flex;
  align-items: center;
  gap: 12px;
}

.origin {
  font-size: 13px;
  color: #999;
}

/* 操作区域 */
.action-section {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
}

.status-badge.verified {
  background: #f6ffed;
  color: #52c41a;
}

.status-badge.failed {
  background: #fff2f0;
  color: #ff4d4f;
}

.summary-section {
  display: flex;
  align-items: center;
  gap: 8px;
}

.generating-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
}

.rotating {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.scan-time {
  font-size: 12px;
  color: #bbb;
}

/* 简报弹窗 */
.summary-content {
  padding: 12px 0;
}

.summary-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.summary-emoji {
  font-size: 48px;
}

.summary-title h3 {
  font-size: 20px;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0 0 8px 0;
}

.summary-text {
  background: #fafafa;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 16px;
}

.summary-text pre {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
  font-size: 14px;
  line-height: 1.8;
  color: #333;
}

.summary-footer {
  display: flex;
  justify-content: center;
}
</style>
