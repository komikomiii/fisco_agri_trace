<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Connection,
  CircleClose,
  CircleCheck,
  ArrowLeft,
  ArrowDown,
  InfoFilled
} from '@element-plus/icons-vue'
import { blockchainApi } from '../../api/blockchain'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const traceCode = ref(route.params.code)
const traceData = ref(null)
const verified = ref(false)

// 详情展开状态
const expandedRecordId = ref(null)

// 获取产品链上数据
const fetchTraceData = async () => {
  loading.value = true
  try {
    const response = await blockchainApi.getProductChainData(traceCode.value)
    if (response && response.exists) {
      traceData.value = response
      verified.value = true
    } else {
      verified.value = false
    }
  } catch (error) {
    console.error('获取溯源数据失败:', error)
    verified.value = false
  } finally {
    loading.value = false
  }
}

// 格式化时间
const formatTime = (timestamp) => {
  if (!timestamp) return '-'
  const ts = typeof timestamp === 'string' ? parseInt(timestamp) : timestamp
  if (ts > 1e12) {
    return new Date(ts).toLocaleString('zh-CN')
  }
  return new Date(ts * 1000).toLocaleString('zh-CN')
}

// 解析产品信息
const productInfo = computed(() => {
  if (!traceData.value?.product_info) return null

  const info = traceData.value.product_info
  return {
    name: info.name || info.productName || '未知产品',
    category: info.category || info.productCategory || '-',
    origin: info.origin || info.productOrigin || '-',
    quantity: info.quantity ? (Number(info.quantity) / 1000).toFixed(2) : '-',
    unit: info.unit || 'kg',
    creator: info.creator || '-',
    currentStage: info.currentStage || info.status || '-',
    recordCount: info.recordCountNum || info.record_count || 0
  }
})

// 阶段信息映射
const stageConfig = {
  'producer': { name: '原料种植', icon: '🌱', color: '#52c41a' },
  'processor': { name: '加工生产', icon: '🏭', color: '#1890ff' },
  'inspector': { name: '质量检测', icon: '🔬', color: '#722ed1' },
  'seller': { name: '入库销售', icon: '🏪', color: '#fa8c16' },
  'sold': { name: '已售出', icon: '✅', color: '#52c41a' },
  0: { name: '原料种植', icon: '🌱', color: '#52c41a' },
  1: { name: '加工生产', icon: '🏭', color: '#1890ff' },
  2: { name: '质量检测', icon: '🔬', color: '#722ed1' },
  3: { name: '入库销售', icon: '🏪', color: '#fa8c16' },
  4: { name: '已售出', icon: '✅', color: '#52c41a' }
}

// 操作类型映射
const actionConfig = {
  'create': { name: '创建产品', desc: '首次创建产品信息' },
  'harvest': { name: '采收', desc: '原料采收完成' },
  'receive': { name: '接收原料', desc: '加工厂接收原料' },
  'process': { name: '加工处理', desc: '进行产品加工' },
  'start_inspect': { name: '开始检测', desc: '启动质量检测流程' },
  'inspect': { name: '质量检测', desc: '完成质量检测' },
  'send_inspect': { name: '送检', desc: '送交质量检测' },
  'stock_in': { name: '入库', desc: '产品入库存储' },
  'shelf_listing': { name: '上架', desc: '产品上架销售' },
  'sell': { name: '销售', desc: '产品已售出' },
  'amend': { name: '信息修正', desc: '修正链上信息' },
  0: { name: '创建产品', desc: '首次创建产品信息' },
  1: { name: '采收', desc: '原料采收完成' },
  2: { name: '加工处理', desc: '进行产品加工' },
  3: { name: '入库/上架', desc: '产品入库或上架' },
  4: { name: '销售', desc: '产品已售出' },
  5: { name: '信息修正', desc: '修正链上信息' }
}

// 解析链上记录
const timelineData = computed(() => {
  if (!traceData.value?.chain_records) return []

  return traceData.value.chain_records.map((record, index) => {
    const stageKey = record.stage
    const actionKey = record.action
    const stageInfo = stageConfig[stageKey] || { name: '未知阶段', icon: '❓', color: '#d9d9d9' }
    const actionInfo = actionConfig[actionKey] || { name: '其他操作', desc: '' }

    // 解析 data JSON
    let dataDetails = []
    if (record.data) {
      try {
        const data = typeof record.data === 'string' ? JSON.parse(record.data) : record.data
        for (const [key, value] of Object.entries(data)) {
          if (key !== 'trace_code' && key !== 'action' && key !== 'timestamp' && key !== 'seller') {
            const labelMap = {
              name: '产品名称',
              category: '品类',
              origin: '产地',
              quantity: '数量',
              unit: '单位',
              quality: '质量等级',
              result_product: '加工结果',
              result_quantity: '结果数量',
              process_type: '加工方式',
              warehouse: '仓库',
              buyer_name: '买家',
              buyer_phone: '买家电话',
              qualified: '检测结果',
              quality_grade: '质量等级',
              inspect_result: '检测结论',
              notes: '备注',
              batch_no: '批次号',
              harvest_date: '采收日期'
            }
            if (value !== null && value !== '' && value !== undefined) {
              dataDetails.push({
                label: labelMap[key] || key,
                value: String(value)
              })
            }
          }
        }
      } catch (e) {
        // 解析失败
      }
    }

    return {
      id: record.recordId || record.index || index,
      index: index + 1,
      stage: stageInfo.name,
      stageIcon: stageInfo.icon,
      stageColor: stageInfo.color,
      action: actionInfo.name,
      actionDesc: actionInfo.desc,
      operator: record.operatorName || record.operator || '-',
      timestamp: record.timestamp ? formatTime(record.timestamp) : '-',
      rawTimestamp: record.timestamp,
      remark: record.remark || '',
      dataDetails: dataDetails,
      isAmend: actionKey === 'amend' || actionKey === 5,
      txHash: record.txHash || null
    }
  })
})

// 当前展开的记录
const currentRecord = computed(() => {
  if (expandedRecordId.value === null) return null
  return timelineData.value.find(r => r.id === expandedRecordId.value)
})

// 切换展开状态
const toggleRecord = (recordId) => {
  if (expandedRecordId.value === recordId) {
    expandedRecordId.value = null
  } else {
    expandedRecordId.value = recordId
  }
}

// 返回上一页
const goBack = () => {
  router.back()
}

// 生成 AI 简报
const generateAISummary = async () => {
  // 跳转到消费者查询记录页面，标记为生成中
  router.push('/dashboard/consumer/history?generate=' + traceCode.value)
}

onMounted(() => {
  if (traceCode.value) {
    fetchTraceData()
  }
})

// 监听路由变化
const unwatch = router.afterEach((to) => {
  if (to.name === 'PublicTrace' && to.params.code !== traceCode.value) {
    traceCode.value = to.params.code
    fetchTraceData()
  }
})
</script>

<template>
  <div class="public-trace-page" v-loading="loading">
    <!-- 顶部导航栏 -->
    <header class="trace-header">
      <div class="header-content">
        <button class="back-btn" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          <span>返回</span>
        </button>
        <div class="header-logo">
          <el-icon :size="28" color="#52c41a"><Connection /></el-icon>
          <span>农链溯源</span>
        </div>
        <div class="header-spacer"></div>
      </div>
    </header>

    <div class="trace-content" v-if="!loading">
      <!-- 未找到溯源信息 -->
      <div v-if="!verified" class="not-found">
        <div class="not-found-icon">
          <el-icon :size="80" color="#ff4d4f"><CircleClose /></el-icon>
        </div>
        <h2>未找到溯源信息</h2>
        <p>该溯源码不存在或未上链，请检查后重试</p>
        <div class="trace-code-box">{{ traceCode }}</div>
      </div>

      <!-- 溯源信息主内容 -->
      <template v-else-if="traceData && productInfo">
        <div class="main-container">
          <!-- 左侧：产品信息卡片 -->
          <div class="left-panel">
            <!-- 产品卡片 -->
            <div class="product-card">
              <div class="verify-status">
                <el-icon :size="20" color="#52c41a"><CircleCheck /></el-icon>
                <span>区块链验证通过</span>
              </div>

              <div class="product-image">
                <div class="image-placeholder">
                  <span class="product-emoji">🍎</span>
                </div>
              </div>

              <h1 class="product-name">{{ productInfo.name }}</h1>
              <p class="product-code">{{ traceCode }}</p>

              <div class="product-meta">
                <div class="meta-item">
                  <span class="meta-label">品类</span>
                  <span class="meta-value">{{ productInfo.category }}</span>
                </div>
                <div class="meta-item">
                  <span class="meta-label">产地</span>
                  <span class="meta-value">{{ productInfo.origin }}</span>
                </div>
                <div class="meta-item">
                  <span class="meta-label">数量</span>
                  <span class="meta-value">{{ productInfo.quantity }} {{ productInfo.unit }}</span>
                </div>
                <div class="meta-item">
                  <span class="meta-label">流转记录</span>
                  <span class="meta-value">{{ productInfo.recordCount }} 条</span>
                </div>
              </div>

              <div class="chain-info">
                <div class="info-row">
                  <span class="info-label">
                    <el-icon><InfoFilled /></el-icon>
                    数据上链
                  </span>
                  <span class="info-value">已存证</span>
                </div>
                <div class="info-row">
                  <span class="info-label">创建者地址</span>
                  <span class="info-value mono">{{ productInfo.creator.slice(0, 8) }}...{{ productInfo.creator.slice(-6) }}</span>
                </div>
              </div>
            </div>

            <!-- AI 简报按钮 -->
            <div class="ai-summary-card">
              <div class="ai-header">
                <span class="ai-icon">✨</span>
                <span class="ai-title">AI 智能简报</span>
              </div>
              <p class="ai-desc">让 AI 为您生成产品溯源总结报告</p>
              <button class="ai-btn" @click="generateAISummary">
                <span>生成 AI 简报</span>
                <el-icon><ArrowDown /></el-icon>
              </button>
            </div>
          </div>

          <!-- 右侧：流转时间线 -->
          <div class="right-panel">
            <div class="timeline-card">
              <div class="timeline-header">
                <h2>产品流转记录</h2>
                <span class="record-count">共 {{ timelineData.length }} 条记录</span>
              </div>

              <div class="timeline-list">
                <div
                  v-for="(record, idx) in timelineData"
                  :key="record.id"
                  class="timeline-item"
                  :class="{
                    'expanded': expandedRecordId === record.id,
                    'amend': record.isAmend
                  }"
                >
                  <!-- 时间线节点 -->
                  <div class="timeline-node" :style="{ '--stage-color': record.stageColor }">
                    <span class="stage-icon">{{ record.stageIcon }}</span>
                  </div>

                  <!-- 记录内容 -->
                  <div class="record-content">
                    <div class="record-header" @click="toggleRecord(record.id)">
                      <div class="record-title">
                        <span class="step-num">{{ String(idx + 1).padStart(2, '0') }}</span>
                        <div class="title-text">
                          <h3>{{ record.stage }} · {{ record.action }}</h3>
                          <p>{{ record.remark || record.actionDesc }}</p>
                        </div>
                      </div>
                      <div class="record-meta">
                        <span class="operator">{{ record.operator }}</span>
                        <span class="time">{{ record.timestamp }}</span>
                        <el-icon class="expand-icon" :class="{ 'rotated': expandedRecordId === record.id }">
                          <ArrowDown />
                        </el-icon>
                      </div>
                    </div>

                    <!-- 展开详情 -->
                    <div v-if="expandedRecordId === record.id" class="record-details">
                      <div class="detail-section">
                        <h4>详细信息</h4>
                        <div class="detail-grid">
                          <div class="detail-item" v-for="detail in record.dataDetails" :key="detail.label">
                            <span class="detail-label">{{ detail.label }}</span>
                            <span class="detail-value">{{ detail.value }}</span>
                          </div>
                        </div>
                        <div v-if="record.dataDetails.length === 0" class="no-details">
                          暂无详细信息
                        </div>
                      </div>

                      <div class="detail-section" v-if="record.txHash">
                        <h4>链上信息</h4>
                        <div class="chain-hash">
                          <span class="hash-label">交易哈希</span>
                          <span class="hash-value mono">{{ record.txHash }}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- 连接线 -->
                  <div v-if="idx < timelineData.length - 1" class="timeline-line"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
* {
  box-sizing: border-box;
}

.public-trace-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #f0f9f4 0%, #e8f5e9 50%, #f1f8e9 100%);
}

/* 顶部导航 */
.trace-header {
  background: white;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 16px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: #f5f5f5;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  color: #333;
  transition: all 0.2s;
}

.back-btn:hover {
  background: #e8e8e8;
}

.header-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 20px;
  font-weight: 700;
  color: #52c41a;
}

.header-spacer {
  width: 80px;
}

/* 主内容 */
.trace-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.main-container {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 24px;
  align-items: start;
}

@media (max-width: 900px) {
  .main-container {
    grid-template-columns: 1fr;
  }
}

/* 左侧面板 */
.left-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
  position: sticky;
  top: 80px;
}

/* 产品卡片 */
.product-card {
  background: white;
  border-radius: 20px;
  padding: 24px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
}

.verify-status {
  display: flex;
  align-items: center;
  gap: 6px;
  justify-content: center;
  padding: 8px 16px;
  background: linear-gradient(135deg, #f6ffed, #d9f7be);
  border: 1px solid #b7eb8f;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  color: #52c41a;
  margin-bottom: 20px;
}

.product-image {
  margin-bottom: 20px;
}

.image-placeholder {
  width: 120px;
  height: 120px;
  margin: 0 auto;
  background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
  border-radius: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.product-emoji {
  font-size: 56px;
}

.product-name {
  font-size: 26px;
  font-weight: 700;
  text-align: center;
  color: #1a1a1a;
  margin: 0 0 8px 0;
}

.product-code {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 13px;
  color: #52c41a;
  text-align: center;
  background: rgba(82, 196, 26, 0.08);
  padding: 6px 12px;
  border-radius: 8px;
  margin: 0 auto 20px;
  display: inline-block;
  width: 100%;
}

.product-meta {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 20px;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-label {
  font-size: 12px;
  color: #999;
}

.meta-value {
  font-size: 15px;
  font-weight: 600;
  color: #333;
}

.chain-info {
  border-top: 1px solid #f0f0f0;
  padding-top: 16px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.info-row:last-child {
  margin-bottom: 0;
}

.info-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #666;
}

.info-value {
  font-size: 13px;
  font-weight: 600;
  color: #52c41a;
}

.mono {
  font-family: 'Monaco', 'Menlo', monospace;
}

/* AI 简报卡片 */
.ai-summary-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 20px;
  padding: 24px;
  color: white;
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.3);
}

.ai-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.ai-icon {
  font-size: 20px;
}

.ai-title {
  font-size: 16px;
  font-weight: 700;
}

.ai-desc {
  font-size: 13px;
  opacity: 0.9;
  margin: 0 0 16px 0;
}

.ai-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 20px;
  background: white;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  color: #667eea;
  cursor: pointer;
  transition: all 0.2s;
}

.ai-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

/* 右侧面板 - 时间线 */
.right-panel {
  position: relative;
}

.timeline-card {
  background: white;
  border-radius: 20px;
  padding: 28px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
}

.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.timeline-header h2 {
  font-size: 20px;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0;
}

.record-count {
  font-size: 13px;
  color: #999;
  background: #f5f5f5;
  padding: 4px 12px;
  border-radius: 12px;
}

/* 时间线列表 */
.timeline-list {
  position: relative;
}

.timeline-item {
  display: flex;
  gap: 20px;
  position: relative;
  margin-bottom: 16px;
}

.timeline-item:last-child {
  margin-bottom: 0;
}

.timeline-line {
  position: absolute;
  left: 19px;
  top: 48px;
  width: 2px;
  height: calc(100% + 8px);
  background: linear-gradient(180deg, #e8e8e8 0%, transparent 100%);
}

/* 时间线节点 */
.timeline-node {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--stage-color, #52c41a);
  flex-shrink: 0;
  position: relative;
  z-index: 1;
  box-shadow: 0 4px 12px var(--stage-color);
}

.stage-icon {
  font-size: 20px;
}

/* 记录内容 */
.record-content {
  flex: 1;
  background: #fafafa;
  border-radius: 16px;
  overflow: hidden;
  transition: all 0.3s;
}

.timeline-item.expanded .record-content {
  background: white;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}

.timeline-item.amend .record-content {
  border: 1px solid #faad14;
  background: #fffbe6;
}

.record-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  cursor: pointer;
  transition: background 0.2s;
}

.record-header:hover {
  background: rgba(0, 0, 0, 0.02);
}

.record-title {
  display: flex;
  align-items: center;
  gap: 14px;
  flex: 1;
}

.step-num {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #52c41a, #73d13d);
  color: white;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
}

.title-text h3 {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 4px 0;
}

.title-text p {
  font-size: 13px;
  color: #999;
  margin: 0;
}

.record-meta {
  display: flex;
  align-items: center;
  gap: 16px;
}

.operator {
  font-size: 13px;
  color: #666;
}

.time {
  font-size: 12px;
  color: #999;
}

.expand-icon {
  transition: transform 0.3s;
  color: #999;
}

.expand-icon.rotated {
  transform: rotate(180deg);
}

/* 展开详情 */
.record-details {
  border-top: 1px solid #f0f0f0;
  padding: 20px;
}

.detail-section {
  margin-bottom: 16px;
}

.detail-section:last-child {
  margin-bottom: 0;
}

.detail-section h4 {
  font-size: 13px;
  font-weight: 600;
  color: #666;
  margin: 0 0 12px 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 14px;
  background: #fafafa;
  border-radius: 10px;
}

.detail-label {
  font-size: 12px;
  color: #999;
}

.detail-value {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.no-details {
  text-align: center;
  padding: 20px;
  color: #999;
  font-size: 13px;
}

.chain-hash {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 16px;
  background: #f6ffed;
  border-radius: 10px;
}

.hash-label {
  font-size: 12px;
  color: #52c41a;
}

.hash-value {
  font-size: 13px;
  color: #333;
  word-break: break-all;
}

/* 未找到页面 */
.not-found {
  text-align: center;
  padding: 80px 24px;
}

.not-found-icon {
  margin-bottom: 24px;
}

.not-found h2 {
  font-size: 24px;
  color: #333;
  margin: 0 0 12px 0;
}

.not-found p {
  font-size: 15px;
  color: #999;
  margin: 0 0 24px 0;
}

.trace-code-box {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 14px;
  color: #52c41a;
  background: rgba(82, 196, 26, 0.08);
  padding: 12px 24px;
  border-radius: 12px;
  display: inline-block;
}
</style>
