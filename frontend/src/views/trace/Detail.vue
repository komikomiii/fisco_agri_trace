<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProductStore } from '../../store/product'
import TraceCode from '../../components/common/TraceCode.vue'

const route = useRoute()
const router = useRouter()
const productStore = useProductStore()
const loading = ref(true)
const chain = ref(null)

// 获取溯源码
const traceCode = computed(() => route.params.code)

// 加载产品链数据
onMounted(async () => {
  // 模拟加载延迟
  await new Promise(resolve => setTimeout(resolve, 500))
  chain.value = productStore.productChains.find(c => c.traceCode === traceCode.value)
  loading.value = false
})

// 阶段颜色
const stageColors = {
  producer: '#52c41a',
  processor: '#1890ff',
  inspector: '#722ed1',
  seller: '#fa8c16'
}

// 阶段名称
const stageNames = {
  producer: '原料商',
  processor: '加工商',
  inspector: '质检员',
  seller: '销售商'
}

// 操作描述
const getActionLabel = (action) => {
  const map = {
    create: '原料登记',
    harvest: '采收出库',
    amend: '信息修正',
    receive: '接收确认',
    process: '加工处理',
    send_inspect: '送检',
    start_inspect: '开始检测',
    inspect: '检测完成',
    reject: '退回处理',
    terminate: '终止链条',
    stock: '入库登记',
    sell: '销售出库'
  }
  return map[action] || action
}

// 获取产品名称
const productName = computed(() => {
  if (!chain.value) return ''
  const processRecord = chain.value.records.find(r => r.action === 'process')
  return processRecord?.data?.outputProduct || chain.value.productName
})

// 获取产地
const origin = computed(() => {
  return productStore.getMergedData(chain.value)?.origin || '-'
})

// 获取生产日期
const productionDate = computed(() => {
  const processRecord = chain.value?.records.find(r => r.action === 'process')
  if (processRecord?.timestamp) {
    return new Date(processRecord.timestamp).toLocaleDateString('zh-CN')
  }
  return '-'
})

// 获取加工商
const processor = computed(() => {
  const processRecord = chain.value?.records.find(r => r.action === 'process')
  return processRecord?.operator?.name || '-'
})

// 获取检测结果
const inspectionResult = computed(() => {
  const inspectRecord = chain.value?.records.find(r => r.action === 'inspect')
  return inspectRecord?.data?.result === 'pass'
})

// 区块链验证信息
const blockchainInfo = computed(() => {
  if (!chain.value) return null
  const recordsWithTx = chain.value.records.filter(r => r.txHash)
  if (recordsWithTx.length === 0) return null
  const latestRecord = recordsWithTx[recordsWithTx.length - 1]
  return {
    txHash: latestRecord.txHash,
    blockNumber: latestRecord.blockNumber,
    verified: true
  }
})

// 时间线数据
const timelineItems = computed(() => {
  if (!chain.value) return []

  return chain.value.records.map(record => {
    const stageColor = stageColors[record.stage] || '#666'
    const stageName = stageNames[record.stage] || record.stage

    // 构建详情数据
    let details = []
    if (record.data) {
      switch (record.action) {
        case 'create':
          if (record.data.origin) details.push({ label: '产地', value: record.data.origin })
          if (record.data.quantity) details.push({ label: '数量', value: `${record.data.quantity} ${record.data.unit || 'kg'}` })
          if (record.data.plantDate) details.push({ label: '种植日期', value: record.data.plantDate })
          break
        case 'harvest':
          if (record.data.batchNo) details.push({ label: '批次号', value: record.data.batchNo })
          if (record.data.quantity) details.push({ label: '采收量', value: `${record.data.quantity} kg` })
          if (record.data.harvestDate) details.push({ label: '采收日期', value: record.data.harvestDate })
          break
        case 'receive':
          if (record.data.quality) details.push({ label: '质量评级', value: record.data.quality })
          break
        case 'process':
          if (record.data.outputProduct) details.push({ label: '成品名称', value: record.data.outputProduct })
          if (record.data.processType) details.push({ label: '加工类型', value: record.data.processType })
          if (record.data.outputQuantity) details.push({ label: '产出数量', value: `${record.data.outputQuantity} 件` })
          break
        case 'inspect':
          if (record.data.result) details.push({ label: '检测结果', value: record.data.result === 'pass' ? '合格' : '不合格' })
          if (record.data.reportNo) details.push({ label: '报告编号', value: record.data.reportNo })
          break
        case 'stock':
          if (record.data.stockQuantity) details.push({ label: '入库数量', value: `${record.data.stockQuantity} 件` })
          if (record.data.price) details.push({ label: '销售单价', value: `¥${record.data.price.toFixed(2)}` })
          if (record.data.location) details.push({ label: '存放位置', value: record.data.location })
          break
        case 'sell':
          if (record.data.quantity) details.push({ label: '销售数量', value: `${record.data.quantity} 件` })
          if (record.data.totalAmount) details.push({ label: '销售金额', value: `¥${record.data.totalAmount.toFixed(2)}` })
          if (record.data.customer) details.push({ label: '客户', value: record.data.customer })
          break
        case 'reject':
          if (record.data.reason) details.push({ label: '退回原因', value: record.data.reason })
          if (record.data.rejectTo) details.push({ label: '退回至', value: stageNames[record.data.rejectTo] || record.data.rejectTo })
          break
        case 'terminate':
          if (record.data.reason) details.push({ label: '终止原因', value: record.data.reason })
          if (record.data.disposal) details.push({ label: '处理方式', value: record.data.disposal })
          break
      }
    }

    return {
      id: record.id,
      stage: record.stage,
      stageName,
      stageColor,
      action: record.action,
      actionLabel: getActionLabel(record.action),
      operator: record.operator?.name || '-',
      timestamp: record.timestamp,
      txHash: record.txHash,
      blockNumber: record.blockNumber,
      reason: record.reason,
      details,
      isAmend: record.action === 'amend',
      isReject: record.action === 'reject',
      isTerminate: record.action === 'terminate'
    }
  })
})

// 是否有修正记录
const hasAmendments = computed(() => {
  return chain.value?.records.some(r => r.action === 'amend') || false
})

// 格式化时间
const formatTime = (timestamp) => {
  if (!timestamp) return '-'
  return new Date(timestamp).toLocaleString('zh-CN')
}

// 返回
const goBack = () => {
  router.back()
}

// 返回扫码页
const goToScan = () => {
  router.push('/dashboard/consumer/scan')
}
</script>

<template>
  <div class="trace-detail" v-loading="loading">
    <!-- 未找到 -->
    <template v-if="!loading && !chain">
      <el-result
        icon="warning"
        title="未找到产品信息"
        :sub-title="`溯源码 ${traceCode} 暂无对应的产品记录`"
      >
        <template #extra>
          <el-button type="primary" @click="goToScan">返回查询</el-button>
        </template>
      </el-result>
    </template>

    <template v-else-if="chain">
      <!-- 产品信息头部 -->
      <div class="product-header">
        <div class="product-image">
          <el-icon :size="64" color="#fff"><GoodsFilled /></el-icon>
        </div>
        <div class="product-info">
          <h1>{{ productName }}</h1>
          <div class="product-meta">
            <el-tag v-if="blockchainInfo?.verified" type="success" effect="dark">
              <el-icon><CircleCheck /></el-icon>
              区块链验证通过
            </el-tag>
            <el-tag v-if="hasAmendments" type="warning" effect="dark">
              <el-icon><Edit /></el-icon>
              含修正记录
            </el-tag>
            <el-tag v-if="chain.status === 'terminated'" type="danger" effect="dark">
              <el-icon><CircleClose /></el-icon>
              已终止
            </el-tag>
          </div>
          <TraceCode :trace-code="traceCode" />
          <div class="product-details">
            <div class="detail-item">
              <span class="label">产地</span>
              <span class="value">{{ origin }}</span>
            </div>
            <div class="detail-item">
              <span class="label">加工商</span>
              <span class="value">{{ processor }}</span>
            </div>
            <div class="detail-item">
              <span class="label">生产日期</span>
              <span class="value">{{ productionDate }}</span>
            </div>
            <div class="detail-item">
              <span class="label">检测结果</span>
              <span class="value" :class="{ success: inspectionResult }">
                {{ inspectionResult ? '合格' : (inspectionResult === false ? '不合格' : '-') }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 区块链信息 -->
      <el-card v-if="blockchainInfo" class="blockchain-card">
        <div class="blockchain-info">
          <div class="chain-icon">
            <el-icon :size="32"><Connection /></el-icon>
          </div>
          <div class="chain-details">
            <h3>区块链存证信息</h3>
            <div class="chain-items">
              <div class="chain-item">
                <span class="label">交易哈希</span>
                <span class="value hash">{{ blockchainInfo.txHash }}</span>
              </div>
              <div class="chain-item">
                <span class="label">区块高度</span>
                <span class="value">{{ blockchainInfo.blockNumber }}</span>
              </div>
              <div class="chain-item">
                <span class="label">记录总数</span>
                <span class="value">{{ chain.records.length }} 条</span>
              </div>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 溯源时间线 -->
      <el-card class="timeline-card">
        <template #header>
          <div class="card-header">
            <span class="title">
              <el-icon><Clock /></el-icon>
              全程溯源信息
            </span>
            <span class="subtitle">共 {{ timelineItems.length }} 条记录</span>
          </div>
        </template>

        <div class="trace-timeline">
          <div
            v-for="(item, index) in timelineItems"
            :key="item.id"
            class="timeline-item"
            :class="{
              'is-amend': item.isAmend,
              'is-reject': item.isReject,
              'is-terminate': item.isTerminate
            }"
          >
            <div
              class="timeline-node"
              :style="{ background: item.isAmend ? '#faad14' : item.isReject ? '#ff7875' : item.isTerminate ? '#ff4d4f' : item.stageColor }"
            >
              <el-icon v-if="item.isAmend"><Edit /></el-icon>
              <el-icon v-else-if="item.isReject"><RefreshLeft /></el-icon>
              <el-icon v-else-if="item.isTerminate"><CircleClose /></el-icon>
              <el-icon v-else-if="item.stage === 'producer'"><Sunrise /></el-icon>
              <el-icon v-else-if="item.stage === 'processor'"><SetUp /></el-icon>
              <el-icon v-else-if="item.stage === 'inspector'"><DocumentChecked /></el-icon>
              <el-icon v-else-if="item.stage === 'seller'"><Shop /></el-icon>
              <el-icon v-else><Document /></el-icon>
            </div>
            <div class="timeline-line" v-if="index < timelineItems.length - 1"></div>

            <div class="timeline-content">
              <div class="content-header">
                <div class="header-left">
                  <el-tag
                    :color="item.isAmend ? '#faad14' : item.isReject ? '#ff7875' : item.isTerminate ? '#ff4d4f' : item.stageColor"
                    effect="dark"
                    size="small"
                  >
                    {{ item.isAmend ? '修正' : item.isReject ? '退回' : item.isTerminate ? '终止' : item.stageName }}
                  </el-tag>
                  <h4>{{ item.actionLabel }}</h4>
                </div>
                <span class="date">{{ formatTime(item.timestamp) }}</span>
              </div>

              <div class="content-body">
                <div class="operator">
                  <el-icon><User /></el-icon>
                  {{ item.operator }}
                </div>

                <!-- 修正原因 -->
                <div v-if="item.reason" class="reason-box">
                  <el-icon><InfoFilled /></el-icon>
                  <span>{{ item.isAmend ? '修正原因' : item.isReject ? '退回原因' : '终止原因' }}：{{ item.reason }}</span>
                </div>

                <!-- 详情数据 -->
                <div v-if="item.details.length > 0" class="detail-grid">
                  <div
                    v-for="detail in item.details"
                    :key="detail.label"
                    class="detail-box"
                  >
                    <span class="detail-label">{{ detail.label }}</span>
                    <span class="detail-value">{{ detail.value }}</span>
                  </div>
                </div>

                <!-- 区块链信息 -->
                <div v-if="item.txHash" class="tx-info">
                  <el-icon><Link /></el-icon>
                  <span class="tx-hash">{{ item.txHash }}</span>
                  <span class="block-number">区块 #{{ item.blockNumber }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 底部操作 -->
      <div class="bottom-actions">
        <el-button size="large" @click="goBack">
          <el-icon><Back /></el-icon>
          返回
        </el-button>
        <el-button type="primary" size="large" @click="goToScan">
          <el-icon><Search /></el-icon>
          继续查询
        </el-button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.trace-detail {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding-bottom: 40px;
}

/* 产品头部 */
.product-header {
  display: flex;
  gap: 24px;
  padding: 32px;
  background: linear-gradient(135deg, #1a1f36, #0f1225);
  border-radius: 20px;
  color: white;
}

.product-image {
  width: 120px;
  height: 120px;
  background: linear-gradient(135deg, var(--primary-color), var(--primary-dark));
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.product-info {
  flex: 1;
}

.product-info h1 {
  font-size: 28px;
  margin-bottom: 12px;
}

.product-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.product-details {
  display: flex;
  gap: 32px;
  margin-top: 16px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-item .label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}

.detail-item .value {
  font-size: 15px;
}

.detail-item .value.success {
  color: #52c41a;
}

/* 区块链信息 */
.blockchain-card {
  background: linear-gradient(135deg, #667eea15, #764ba215);
}

.blockchain-info {
  display: flex;
  align-items: center;
  gap: 20px;
}

.chain-icon {
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

.chain-details {
  flex: 1;
}

.chain-details h3 {
  font-size: 16px;
  margin-bottom: 12px;
}

.chain-items {
  display: flex;
  gap: 32px;
}

.chain-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.chain-item .label {
  font-size: 12px;
  color: var(--text-muted);
}

.chain-item .value {
  font-size: 14px;
  color: var(--text-primary);
}

.chain-item .hash {
  font-family: monospace;
  color: #667eea;
}

/* 时间线 */
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

.trace-timeline {
  position: relative;
  padding-left: 44px;
}

.timeline-item {
  position: relative;
  padding-bottom: 28px;
}

.timeline-item:last-child {
  padding-bottom: 0;
}

.timeline-node {
  position: absolute;
  left: -44px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  z-index: 2;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.timeline-line {
  position: absolute;
  left: -29px;
  top: 32px;
  width: 2px;
  height: calc(100% - 32px);
  background: linear-gradient(to bottom, #e8e8e8, #f5f5f5);
}

.timeline-content {
  background: var(--bg-color);
  border-radius: 12px;
  padding: 20px;
  margin-left: 16px;
  border: 1px solid var(--border-color);
}

.timeline-item.is-amend .timeline-content {
  background: #fffbe6;
  border-color: #ffe58f;
}

.timeline-item.is-reject .timeline-content {
  background: #fff1f0;
  border-color: #ffccc7;
}

.timeline-item.is-terminate .timeline-content {
  background: #fff1f0;
  border-color: #ffa39e;
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-left h4 {
  font-size: 16px;
  font-weight: 600;
}

.date {
  font-size: 13px;
  color: var(--text-muted);
}

.operator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.reason-box {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.03);
  border-radius: 8px;
  margin-bottom: 12px;
  font-size: 14px;
  color: var(--text-secondary);
}

.timeline-item.is-amend .reason-box {
  background: #fff7e6;
  color: #ad6800;
}

.timeline-item.is-reject .reason-box,
.timeline-item.is-terminate .reason-box {
  background: #fff1f0;
  color: #cf1322;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.detail-box {
  background: white;
  padding: 12px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  border: 1px solid var(--border-color);
}

.timeline-item.is-amend .detail-box,
.timeline-item.is-reject .detail-box,
.timeline-item.is-terminate .detail-box {
  background: rgba(255, 255, 255, 0.8);
}

.detail-label {
  font-size: 12px;
  color: var(--text-muted);
}

.detail-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.tx-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px dashed var(--border-color);
  font-size: 12px;
  color: var(--text-muted);
}

.tx-hash {
  font-family: monospace;
  color: #667eea;
}

.block-number {
  margin-left: auto;
}

/* 底部操作 */
.bottom-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  padding-top: 20px;
}
</style>
