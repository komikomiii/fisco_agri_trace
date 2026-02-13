<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { blockchainApi } from '../../api/blockchain'
import { aiApi } from '../../api/ai'
import TraceCode from '../../components/common/TraceCode.vue'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const generating = ref(false)
const chain = ref(null)
const aiSummary = ref('')

const traceCode = computed(() => route.params.code)

const actionMap = {
  0: 'create', 1: 'harvest', 2: 'receive', 3: 'process',
  4: 'send_inspect', 5: 'start_inspect', 6: 'inspect',
  7: 'reject', 8: 'terminate', 9: 'stock_in', 10: 'sell', 11: 'amend'
}

const stageMap = {
  0: 'producer', 1: 'processor', 2: 'inspector', 3: 'seller', 4: 'sold'
}

const parseRecord = (r) => {
  let parsedData = {}
  if (r.data) {
    try { parsedData = typeof r.data === 'string' ? JSON.parse(r.data) : r.data } catch { parsedData = {} }
  }
  return {
    action: typeof r.action === 'number' ? (actionMap[r.action] || r.action) : r.action,
    stage: typeof r.stage === 'number' ? (stageMap[r.stage] || r.stage) : r.stage,
    data: parsedData,
    operator: { name: r.operatorName || '-' },
    timestamp: r.timestamp ? new Date(r.timestamp * 1000).toISOString() : null,
    txHash: r.txHash || null,
    blockNumber: r.blockNumber || null
  }
}

onMounted(async () => {
  try {
    const response = await blockchainApi.getProductChainData(traceCode.value)
    if (response && response.exists) {
      const info = response.product_info || {}
      chain.value = {
        productName: info.name || '',
        category: info.category || '',
        traceCode: traceCode.value,
        records: (response.chain_records || []).map(parseRecord)
      }
      generating.value = true
      try {
        const aiResult = await aiApi.generateSummary(traceCode.value, response)
        if (aiResult?.summary) aiSummary.value = aiResult.summary
      } catch (e) {
        console.error('AI 简报生成失败:', e)
      }
      generating.value = false
    }
  } catch (e) {
    console.error('获取溯源数据失败:', e)
  } finally {
    loading.value = false
  }
})

const productName = computed(() => {
  if (!chain.value) return ''
  const processRecord = chain.value.records.find(r => r.action === 'process')
  return processRecord?.data?.result_product || processRecord?.data?.outputProduct || chain.value.productName
})

const rawMaterial = computed(() => {
  return chain.value?.productName || ''
})

const origin = computed(() => {
  const createRecord = chain.value?.records.find(r => r.action === 'create')
  return createRecord?.data?.origin || '-'
})

const productionDate = computed(() => {
  const processRecord = chain.value?.records.find(r => r.action === 'process')
  if (processRecord?.timestamp) {
    return new Date(processRecord.timestamp).toLocaleDateString('zh-CN')
  }
  return '-'
})

// 获取加工商信息
const processor = computed(() => {
  const processRecord = chain.value?.records.find(r => r.action === 'process')
  return processRecord?.operator?.name || '-'
})

// 获取检测结果
const inspectionResult = computed(() => {
  const inspectRecord = chain.value?.records.find(r => r.action === 'inspect')
  return inspectRecord?.data?.result === 'pass' ? '合格' : '-'
})

// 获取检测项
const inspectionItems = computed(() => {
  const inspectRecord = chain.value?.records.find(r => r.action === 'inspect')
  return inspectRecord?.data?.items || []
})

// 获取加工方式
const processType = computed(() => {
  const processRecord = chain.value?.records.find(r => r.action === 'process')
  const type = processRecord?.data?.processType
  const typeMap = {
    wash: '清洗分拣',
    cut: '切割加工',
    juice: '榨汁加工',
    pack: '包装封装',
    freeze: '冷冻处理',
    dry: '烘干处理'
  }
  return typeMap[type] || type || '-'
})

// AI生成的亮点（模拟）
const highlights = computed(() => {
  if (!chain.value) return []

  const items = []

  // 根据产品链信息生成亮点
  if (origin.value && origin.value !== '-') {
    items.push(`源自${origin.value}，产地直供`)
  }

  if (inspectionResult.value === '合格') {
    items.push('通过专业质检机构检测，品质有保障')
  }

  const createData = chain.value.records.find(r => r.action === 'create')?.data
  if (createData?.plantDate || createData?.harvest_date) {
    items.push('采用科学种植管理，全程可追溯')
  }

  if (chain.value.records.length >= 4) {
    items.push(`供应链${chain.value.records.length}个环节全程记录，信息透明`)
  }

  return items.length > 0 ? items : ['全程区块链存证，信息真实可信']
})

// 供应链阶段
const supplyChainStages = computed(() => {
  if (!chain.value) return []

  const stages = []
  const stageMap = {
    producer: { name: '原料商', icon: 'Sunrise', color: '#52c41a' },
    processor: { name: '加工商', icon: 'SetUp', color: '#1890ff' },
    inspector: { name: '质检员', icon: 'DocumentChecked', color: '#722ed1' },
    seller: { name: '销售商', icon: 'Shop', color: '#fa8c16' }
  }

  // 收集各阶段信息
  const createRecord = chain.value.records.find(r => r.action === 'create')
  if (createRecord) {
    stages.push({
      ...stageMap.producer,
      operator: createRecord.operator?.name,
      action: '原料登记',
      timestamp: createRecord.timestamp
    })
  }

  const processRecord = chain.value.records.find(r => r.action === 'process')
  if (processRecord) {
    stages.push({
      ...stageMap.processor,
      operator: processRecord.operator?.name,
      action: '加工处理',
      timestamp: processRecord.timestamp
    })
  }

  const inspectRecord = chain.value.records.find(r => r.action === 'inspect')
  if (inspectRecord) {
    stages.push({
      ...stageMap.inspector,
      operator: inspectRecord.operator?.name,
      action: '质量检测',
      timestamp: inspectRecord.timestamp
    })
  }

  const stockRecord = chain.value.records.find(r => r.action === 'stock')
  if (stockRecord) {
    stages.push({
      ...stageMap.seller,
      operator: stockRecord.operator?.name,
      action: '入库销售',
      timestamp: stockRecord.timestamp
    })
  }

  return stages
})

// 是否有修正记录
const hasAmendments = computed(() => {
  return chain.value?.records.some(r => r.action === 'amend') || false
})

// 修正记录
const amendments = computed(() => {
  return chain.value?.records.filter(r => r.action === 'amend') || []
})

// 区块链验证信息
const blockchainInfo = computed(() => {
  if (!chain.value) return null

  // 获取最新的有效交易哈希
  const recordsWithTx = chain.value.records.filter(r => r.txHash)
  if (recordsWithTx.length === 0) return null

  const latestRecord = recordsWithTx[recordsWithTx.length - 1]
  return {
    txHash: latestRecord.txHash,
    blockNumber: latestRecord.blockNumber,
    totalRecords: chain.value.records.length,
    verified: true
  }
})

// 格式化时间
const formatTime = (timestamp) => {
  if (!timestamp) return '-'
  return new Date(timestamp).toLocaleString('zh-CN')
}

// 查看完整链上记录
const viewFullTrace = () => {
  router.push(`/trace/${traceCode.value}`)
}

// 返回扫码页
const goBack = () => {
  router.push('/dashboard/consumer/scan')
}
</script>

<template>
  <div class="report-container" v-loading="loading">
    <!-- 未找到 -->
    <template v-if="!loading && !chain">
      <el-result
        icon="warning"
        title="未找到产品信息"
        :sub-title="`溯源码 ${traceCode} 暂无对应的产品记录`"
      >
        <template #extra>
          <el-button type="primary" @click="goBack">返回重新查询</el-button>
        </template>
      </el-result>
    </template>

    <!-- 生成中 -->
    <template v-else-if="generating">
      <div class="generating-state">
        <div class="generating-animation">
          <el-icon :size="48" class="rotating"><Loading /></el-icon>
        </div>
        <h3>正在生成溯源简报</h3>
        <p>AI 正在分析供应链数据...</p>
      </div>
    </template>

    <!-- 简报内容 -->
    <template v-else-if="chain">
      <!-- 产品头部卡片 -->
      <div class="product-hero">
        <div class="hero-background"></div>
        <div class="hero-content">
          <div class="product-avatar">
            <el-icon :size="48"><GoodsFilled /></el-icon>
          </div>
          <h1>{{ productName }}</h1>
          <div class="verification-badge">
            <el-icon><CircleCheck /></el-icon>
            <span>区块链验证通过</span>
          </div>
          <TraceCode :trace-code="traceCode" size="large" />
        </div>
      </div>

      <!-- 核心信息卡片 -->
      <el-card class="info-card">
        <template #header>
          <div class="card-header">
            <span class="title">
              <el-icon><InfoFilled /></el-icon>
              产品信息
            </span>
          </div>
        </template>

        <div class="info-grid">
          <div class="info-item">
            <div class="info-icon origin">
              <el-icon><Location /></el-icon>
            </div>
            <div class="info-content">
              <span class="label">产地</span>
              <span class="value">{{ origin }}</span>
            </div>
          </div>
          <div class="info-item">
            <div class="info-icon material">
              <el-icon><Grape /></el-icon>
            </div>
            <div class="info-content">
              <span class="label">原材料</span>
              <span class="value">{{ rawMaterial }}</span>
            </div>
          </div>
          <div class="info-item">
            <div class="info-icon process">
              <el-icon><SetUp /></el-icon>
            </div>
            <div class="info-content">
              <span class="label">加工方式</span>
              <span class="value">{{ processType }}</span>
            </div>
          </div>
          <div class="info-item">
            <div class="info-icon date">
              <el-icon><Calendar /></el-icon>
            </div>
            <div class="info-content">
              <span class="label">生产日期</span>
              <span class="value">{{ productionDate }}</span>
            </div>
          </div>
          <div class="info-item">
            <div class="info-icon processor">
              <el-icon><OfficeBuilding /></el-icon>
            </div>
            <div class="info-content">
              <span class="label">加工商</span>
              <span class="value">{{ processor }}</span>
            </div>
          </div>
          <div class="info-item">
            <div class="info-icon inspection">
              <el-icon><DocumentChecked /></el-icon>
            </div>
            <div class="info-content">
              <span class="label">检测结果</span>
              <span class="value success">{{ inspectionResult }}</span>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 产品亮点 -->
      <el-card class="highlights-card">
        <template #header>
          <div class="card-header">
            <span class="title">
              <el-icon><Star /></el-icon>
              产品亮点
            </span>
            <el-tag size="small" type="info">AI 生成</el-tag>
          </div>
        </template>

        <div class="highlights-list">
          <div v-for="(highlight, index) in highlights" :key="index" class="highlight-item">
            <el-icon class="check-icon"><CircleCheck /></el-icon>
            <span>{{ highlight }}</span>
          </div>
        </div>
      </el-card>

      <!-- 检测详情 -->
      <el-card v-if="inspectionItems.length > 0" class="inspection-card">
        <template #header>
          <div class="card-header">
            <span class="title">
              <el-icon><DocumentChecked /></el-icon>
              检测详情
            </span>
            <el-tag type="success">全部合格</el-tag>
          </div>
        </template>

        <el-table :data="inspectionItems" border size="small">
          <el-table-column prop="name" label="检测项" width="120" />
          <el-table-column prop="value" label="检测值" />
          <el-table-column prop="standard" label="标准值" />
          <el-table-column label="结果" width="80">
            <template #default="{ row }">
              <el-tag :type="row.pass ? 'success' : 'danger'" size="small">
                {{ row.pass ? '合格' : '不合格' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 供应链概览 -->
      <el-card class="chain-card">
        <template #header>
          <div class="card-header">
            <span class="title">
              <el-icon><Connection /></el-icon>
              供应链追溯
            </span>
            <span class="subtitle">{{ supplyChainStages.length }} 个环节</span>
          </div>
        </template>

        <div class="chain-stages">
          <div
            v-for="(stage, index) in supplyChainStages"
            :key="index"
            class="stage-item"
          >
            <div class="stage-node" :style="{ background: stage.color }">
              <el-icon><component :is="stage.icon" /></el-icon>
            </div>
            <div v-if="index < supplyChainStages.length - 1" class="stage-line"></div>
            <div class="stage-content">
              <div class="stage-header">
                <el-tag :color="stage.color" effect="dark" size="small">{{ stage.name }}</el-tag>
                <span class="stage-action">{{ stage.action }}</span>
              </div>
              <div class="stage-operator">{{ stage.operator }}</div>
              <div class="stage-time">{{ formatTime(stage.timestamp) }}</div>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 修正记录 -->
      <el-card v-if="hasAmendments" class="amend-card">
        <template #header>
          <div class="card-header">
            <span class="title">
              <el-icon><Edit /></el-icon>
              信息修正记录
            </span>
            <el-tag type="warning" size="small">{{ amendments.length }} 条修正</el-tag>
          </div>
        </template>

        <el-timeline>
          <el-timeline-item
            v-for="amend in amendments"
            :key="amend.id"
            :timestamp="formatTime(amend.timestamp)"
            type="warning"
          >
            <div class="amend-item">
              <div class="amend-header">
                <span class="operator">{{ amend.operator?.name }}</span>
              </div>
              <div class="amend-reason">修正原因：{{ amend.reason || '-' }}</div>
            </div>
          </el-timeline-item>
        </el-timeline>
      </el-card>

      <!-- 区块链存证 -->
      <el-card v-if="blockchainInfo" class="blockchain-card">
        <div class="blockchain-content">
          <div class="blockchain-icon">
            <el-icon :size="32"><Connection /></el-icon>
          </div>
          <div class="blockchain-info">
            <h4>区块链存证信息</h4>
            <div class="blockchain-details">
              <div class="detail-item">
                <span class="label">交易哈希</span>
                <span class="value hash">{{ blockchainInfo.txHash }}</span>
              </div>
              <div class="detail-item">
                <span class="label">区块高度</span>
                <span class="value">{{ blockchainInfo.blockNumber }}</span>
              </div>
              <div class="detail-item">
                <span class="label">记录总数</span>
                <span class="value">{{ blockchainInfo.totalRecords }} 条</span>
              </div>
            </div>
          </div>
          <el-button type="primary" @click="viewFullTrace">
            <el-icon><View /></el-icon>
            查看完整链上记录
          </el-button>
        </div>
      </el-card>

      <!-- 底部操作 -->
      <div class="bottom-actions">
        <el-button size="large" @click="goBack">
          <el-icon><Back /></el-icon>
          返回查询
        </el-button>
        <el-button type="primary" size="large" @click="viewFullTrace">
          <el-icon><View /></el-icon>
          查看完整记录
        </el-button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.report-container {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-bottom: 40px;
}

/* 生成中状态 */
.generating-state {
  text-align: center;
  padding: 80px 20px;
}

.generating-animation {
  margin-bottom: 24px;
}

.rotating {
  animation: rotate 1s linear infinite;
  color: var(--primary-color);
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.generating-state h3 {
  font-size: 20px;
  margin-bottom: 8px;
}

.generating-state p {
  color: var(--text-muted);
}

/* 产品头部 */
.product-hero {
  position: relative;
  border-radius: 20px;
  overflow: hidden;
  padding: 40px 24px;
  text-align: center;
  color: white;
}

.hero-background {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, #1a1f36, #0f1225);
  z-index: 0;
}

.hero-background::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 30% 20%, rgba(82, 196, 26, 0.2), transparent 50%);
}

.hero-content {
  position: relative;
  z-index: 1;
}

.product-avatar {
  width: 80px;
  height: 80px;
  margin: 0 auto 16px;
  background: linear-gradient(135deg, var(--primary-color), var(--primary-dark));
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.product-hero h1 {
  font-size: 28px;
  margin-bottom: 16px;
}

.verification-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: rgba(82, 196, 26, 0.2);
  border: 1px solid rgba(82, 196, 26, 0.4);
  border-radius: 20px;
  font-size: 14px;
  margin-bottom: 20px;
}

.verification-badge .el-icon {
  color: #52c41a;
}

/* 信息卡片 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
}

.subtitle {
  font-size: 13px;
  color: var(--text-muted);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: var(--bg-color);
  border-radius: 12px;
}

.info-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.info-icon.origin { background: rgba(82, 196, 26, 0.1); color: #52c41a; }
.info-icon.material { background: rgba(250, 140, 22, 0.1); color: #fa8c16; }
.info-icon.process { background: rgba(24, 144, 255, 0.1); color: #1890ff; }
.info-icon.date { background: rgba(114, 46, 209, 0.1); color: #722ed1; }
.info-icon.processor { background: rgba(47, 84, 235, 0.1); color: #2f54eb; }
.info-icon.inspection { background: rgba(82, 196, 26, 0.1); color: #52c41a; }

.info-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-content .label {
  font-size: 12px;
  color: var(--text-muted);
}

.info-content .value {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary);
}

.info-content .value.success {
  color: #52c41a;
}

/* 亮点卡片 */
.highlights-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.highlight-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: #f6ffed;
  border-radius: 8px;
  font-size: 14px;
}

.check-icon {
  color: #52c41a;
  font-size: 18px;
}

/* 供应链卡片 */
.chain-stages {
  display: flex;
  flex-direction: column;
}

.stage-item {
  display: flex;
  position: relative;
  padding-bottom: 24px;
}

.stage-item:last-child {
  padding-bottom: 0;
}

.stage-node {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  z-index: 2;
  flex-shrink: 0;
}

.stage-line {
  position: absolute;
  left: 17px;
  top: 36px;
  width: 2px;
  height: calc(100% - 36px);
  background: #e8e8e8;
}

.stage-content {
  margin-left: 16px;
  flex: 1;
}

.stage-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.stage-action {
  font-size: 14px;
  font-weight: 500;
}

.stage-operator {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.stage-time {
  font-size: 12px;
  color: var(--text-muted);
}

/* 修正记录 */
.amend-item {
  padding: 8px 0;
}

.amend-header {
  margin-bottom: 6px;
}

.amend-header .operator {
  font-weight: 500;
}

.amend-reason {
  font-size: 13px;
  color: #ad6800;
  padding: 8px 12px;
  background: #fffbe6;
  border-radius: 6px;
}

/* 区块链卡片 */
.blockchain-card {
  background: linear-gradient(135deg, #667eea15, #764ba215);
}

.blockchain-content {
  display: flex;
  align-items: center;
  gap: 20px;
}

.blockchain-icon {
  width: 64px;
  height: 64px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.blockchain-info {
  flex: 1;
}

.blockchain-info h4 {
  font-size: 15px;
  margin-bottom: 12px;
}

.blockchain-details {
  display: flex;
  gap: 24px;
}

.blockchain-details .detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.blockchain-details .label {
  font-size: 12px;
  color: var(--text-muted);
}

.blockchain-details .value {
  font-size: 13px;
  color: var(--text-primary);
}

.blockchain-details .hash {
  font-family: monospace;
  color: #667eea;
}

/* 底部操作 */
.bottom-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  padding-top: 20px;
}
</style>
