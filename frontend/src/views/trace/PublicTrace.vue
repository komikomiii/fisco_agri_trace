<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElDialog } from 'element-plus'
import {
  Connection,
  CircleClose,
  CircleCheck,
  ArrowLeft,
  ArrowDown,
  InfoFilled,
  Document,
  CopyDocument
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

// 链上数据弹窗状态
const chainDataDialogVisible = ref(false)
const selectedChainRecord = ref(null)

// 打开链上数据详情弹窗
const openChainDataDialog = (record) => {
  selectedChainRecord.value = record
  chainDataDialogVisible.value = true
}

// 关闭弹窗
const closeChainDataDialog = () => {
  chainDataDialogVisible.value = false
  selectedChainRecord.value = null
}

// 复制到剪贴板
const copyToClipboard = async (text) => {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch (e) {
    ElMessage.error('复制失败')
  }
}

// 获取原始链上记录数据
const getRawChainRecord = (record) => {
  if (!traceData.value?.chain_records) return null
  return traceData.value.chain_records.find(r =>
    (r.recordId || r.index) === record.id
  )
}

// 格式化 data JSON 数据
const formatDataJson = (data) => {
  if (!data) return '{}'
  try {
    const parsed = typeof data === 'string' ? JSON.parse(data) : data
    return JSON.stringify(parsed, null, 2)
  } catch (e) {
    return String(data)
  }
}

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

// 根据产品类别/名称获取对应的 emoji 图片
const getProductEmoji = (name, category) => {
  const n = (name + ' ' + (category || '')).toLowerCase()
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

// 产品图片
const productEmoji = computed(() => {
  if (!traceData.value?.product_info) return '📦'
  return getProductEmoji(
    traceData.value.product_info.name || '',
    traceData.value.product_info.category || ''
  )
})

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
              harvest_date: '采收日期',
              received_quantity: '接收数量',
              received_at: '接收时间',
              process_date: '加工时间',
              inspection_type: '检测类型',
              inspector: '检测员',
              seller: '销售方'
            }
            // 格式化值
            let formattedValue = value
            if (typeof value === 'boolean') {
              formattedValue = value ? '是' : '否'
            } else if (key.includes('date') || key.includes('time')) {
              // 尝试格式化日期
              try {
                const d = new Date(value)
                if (!isNaN(d.getTime())) {
                  formattedValue = d.toLocaleString('zh-CN')
                }
              } catch (e) {
                formattedValue = String(value)
              }
            } else if (key === 'quantity' || key === 'result_quantity' || key === 'received_quantity') {
              formattedValue = value + ' kg'
            }

            if (value !== null && value !== '' && value !== undefined) {
              dataDetails.push({
                label: labelMap[key] || key,
                value: String(formattedValue)
              })
            }
          }
        }
      } catch (e) {
        // 解析失败，data 可能是普通字符串
        if (record.data && typeof record.data === 'string') {
          dataDetails.push({ label: '数据', value: record.data })
        }
      }
    }

    // 获取 txHash（如果有）
    const txHash = record.txHash || null

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
      txHash: txHash
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
                  <span class="product-emoji">{{ productEmoji }}</span>
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

                      <!-- 链上信息 - 始终显示 -->
                      <div class="detail-section chain-info-section">
                        <div class="chain-header-row">
                          <h4>
                            <span class="chain-icon">⛓</span>
                            区块链存证信息
                          </h4>
                          <button class="view-raw-btn" @click.stop="openChainDataDialog(record)">
                            <el-icon><Document /></el-icon>
                            <span>查看完整数据</span>
                          </button>
                        </div>
                        <div class="chain-info-grid">
                          <div class="chain-info-item" v-if="record.txHash">
                            <span class="chain-label">交易哈希</span>
                            <span class="chain-value mono">{{ record.txHash }}</span>
                          </div>
                          <div class="chain-info-item">
                            <span class="chain-label">记录ID</span>
                            <span class="chain-value mono">{{ record.id }}</span>
                          </div>
                          <div class="chain-info-item">
                            <span class="chain-label">上链时间</span>
                            <span class="chain-value">{{ record.timestamp }}</span>
                          </div>
                          <div class="chain-info-item">
                            <span class="chain-label">操作者</span>
                            <span class="chain-value">{{ record.operator }}</span>
                          </div>
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

    <!-- 链上数据详情弹窗 -->
    <el-dialog
      v-model="chainDataDialogVisible"
      title="区块链原始数据"
      width="600px"
      :close-on-click-modal="false"
      class="chain-data-dialog"
    >
      <div v-if="selectedChainRecord" class="chain-data-content">
        <!-- 获取原始记录 -->
        <div v-if="getRawChainRecord(selectedChainRecord)">
          <div class="chain-data-header">
            <span class="chain-data-icon">⛓</span>
            <span class="chain-data-title">完整链上记录</span>
          </div>

          <div class="raw-data-sections">
            <!-- 基本信息 -->
            <div class="data-section">
              <div class="data-section-title">基本信息</div>
              <div class="data-row">
                <span class="data-key">索引 (index)</span>
                <span class="data-value">{{ getRawChainRecord(selectedChainRecord).index ?? '-' }}</span>
              </div>
              <div class="data-row">
                <span class="data-key">记录ID (recordId)</span>
                <span class="data-value mono">{{ getRawChainRecord(selectedChainRecord).recordId ?? '-' }}</span>
              </div>
            </div>

            <!-- 阶段与操作 -->
            <div class="data-section">
              <div class="data-section-title">阶段与操作</div>
              <div class="data-row">
                <span class="data-key">阶段 (stage)</span>
                <span class="data-value stage-badge" :style="{ background: selectedChainRecord.stageColor + '20', color: selectedChainRecord.stageColor }">
                  {{ getRawChainRecord(selectedChainRecord).stage ?? '-' }}
                </span>
              </div>
              <div class="data-row">
                <span class="data-key">操作 (action)</span>
                <span class="data-value">{{ getRawChainRecord(selectedChainRecord).action ?? '-' }}</span>
              </div>
            </div>

            <!-- 数据内容 -->
            <div class="data-section">
              <div class="data-section-title">数据内容 (data)</div>
              <div class="json-data-box">
                <pre class="json-content">{{ formatDataJson(getRawChainRecord(selectedChainRecord).data) }}</pre>
                <button class="copy-btn" @click="copyToClipboard(formatDataJson(getRawChainRecord(selectedChainRecord).data))">
                  <el-icon><CopyDocument /></el-icon>
                  复制
                </button>
              </div>
            </div>

            <!-- 操作信息 -->
            <div class="data-section">
              <div class="data-section-title">操作信息</div>
              <div class="data-row">
                <span class="data-key">操作者 (operator)</span>
                <span class="data-value">{{ getRawChainRecord(selectedChainRecord).operator ?? '-' }}</span>
              </div>
              <div class="data-row">
                <span class="data-key">操作者名称 (operatorName)</span>
                <span class="data-value">{{ getRawChainRecord(selectedChainRecord).operatorName ?? '-' }}</span>
              </div>
              <div class="data-row">
                <span class="data-key">时间戳 (timestamp)</span>
                <span class="data-value mono">{{ getRawChainRecord(selectedChainRecord).timestamp ?? '-' }}</span>
              </div>
              <div class="data-row">
                <span class="data-key">格式化时间</span>
                <span class="data-value">{{ selectedChainRecord.timestamp }}</span>
              </div>
            </div>

            <!-- 交易信息 -->
            <div class="data-section" v-if="getRawChainRecord(selectedChainRecord).txHash">
              <div class="data-section-title">交易信息</div>
              <div class="data-row full-width">
                <span class="data-key">交易哈希 (txHash)</span>
                <span class="data-value mono">{{ getRawChainRecord(selectedChainRecord).txHash }}</span>
              </div>
            </div>

            <!-- 备注 -->
            <div class="data-section" v-if="getRawChainRecord(selectedChainRecord).remark">
              <div class="data-section-title">备注 (remark)</div>
              <div class="data-row full-width">
                <span class="data-value remark-text">{{ getRawChainRecord(selectedChainRecord).remark }}</span>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="no-data">
          未找到链上数据
        </div>
      </div>

      <template #footer>
        <span style="display: flex; justify-content: flex-end;">
          <el-button @click="closeChainDataDialog">关闭</el-button>
        </span>
      </template>
    </el-dialog>
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

/* 链上信息区域 */
.chain-info-section {
  background: linear-gradient(135deg, #f6ffed, #fffbe6);
  border: 1px solid #b7eb8f;
  border-radius: 12px;
  padding: 16px;
}

.chain-info-section h4 {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #52c41a;
  margin-bottom: 12px;
}

.chain-icon {
  font-size: 16px;
}

.chain-info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.chain-info-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.6);
  border-radius: 8px;
}

.chain-label {
  font-size: 11px;
  color: #52c41a;
  font-weight: 600;
}

.chain-value {
  font-size: 13px;
  color: #333;
  word-break: break-all;
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

/* 链上信息头部行 */
.chain-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.chain-header-row h4 {
  margin: 0;
}

/* 查看完整数据按钮 */
.view-raw-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  background: white;
  border: 1px solid #b7eb8f;
  border-radius: 8px;
  font-size: 12px;
  color: #52c41a;
  cursor: pointer;
  transition: all 0.2s;
}

.view-raw-btn:hover {
  background: #f6ffed;
  border-color: #95de64;
}

/* 弹窗样式 */
.chain-data-dialog .chain-data-content {
  padding: 0;
}

.chain-data-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-bottom: 16px;
  margin-bottom: 20px;
  border-bottom: 2px solid #f0f0f0;
}

.chain-data-icon {
  font-size: 24px;
}

.chain-data-title {
  font-size: 16px;
  font-weight: 700;
  color: #1a1a1a;
}

.raw-data-sections {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.data-section {
  background: #fafafa;
  border-radius: 12px;
  padding: 16px;
}

.data-section-title {
  font-size: 12px;
  font-weight: 700;
  color: #52c41a;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}

.data-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.data-row:last-child {
  border-bottom: none;
}

.data-row.full-width {
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
}

.data-key {
  font-size: 13px;
  color: #666;
  font-weight: 500;
}

.data-value {
  font-size: 13px;
  color: #333;
  font-weight: 600;
  max-width: 60%;
  text-align: right;
  word-break: break-all;
}

.data-row.full-width .data-value {
  max-width: 100%;
  text-align: left;
}

.data-value.mono {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 12px;
}

.data-value.remark-text {
  background: white;
  padding: 10px 14px;
  border-radius: 8px;
  width: 100%;
}

.stage-badge {
  padding: 4px 12px;
  border-radius: 6px;
  font-weight: 600;
  font-size: 12px;
}

/* JSON 数据框 */
.json-data-box {
  position: relative;
  background: #1a1a1a;
  border-radius: 10px;
  padding: 16px;
  margin-top: 8px;
}

.json-content {
  margin: 0;
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
  font-size: 12px;
  color: #a9b7c6;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 200px;
  overflow-y: auto;
}

.copy-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 6px;
  font-size: 11px;
  color: white;
  cursor: pointer;
  transition: all 0.2s;
}

.copy-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.3);
}

.no-data {
  text-align: center;
  padding: 40px;
  color: #999;
  font-size: 14px;
}
</style>
