<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { blockchainApi } from '../../api/blockchain'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  txHash: {
    type: String,
    default: ''
  },
  traceCode: {
    type: String,
    default: ''
  },
  blockNumber: {
    type: Number,
    default: null
  },
  productData: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:visible'])

const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
})

// 状态
const loading = ref(false)
const activeTab = ref('transaction')

// 数据
const transactionData = ref(null)
const blockData = ref(null)
const chainInfo = ref(null)
const verifyResult = ref(null)

// 复制到剪贴板
const copyToClipboard = async (text, label) => {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success(`${label}已复制`)
  } catch {
    ElMessage.error('复制失败')
  }
}

// 格式化哈希
const formatHash = (hash, length = 20) => {
  if (!hash || hash.length <= length) return hash
  const half = Math.floor(length / 2)
  return `${hash.slice(0, half)}...${hash.slice(-half)}`
}

// 格式化时间戳
const formatTimestamp = (timestamp) => {
  if (!timestamp) return '-'
  // 处理不同格式的时间戳
  const ts = typeof timestamp === 'string' ? parseInt(timestamp, 16) || parseInt(timestamp) : timestamp
  if (ts > 1e12) {
    return new Date(ts).toLocaleString('zh-CN')
  }
  return new Date(ts * 1000).toLocaleString('zh-CN')
}

// 加载交易详情
const loadTransaction = async () => {
  if (!props.txHash) {
    console.log('[ChainVerify] No txHash provided')
    return
  }

  console.log('[ChainVerify] Loading transaction:', props.txHash)
  loading.value = true
  try {
    const data = await blockchainApi.getTransaction(props.txHash)
    console.log('[ChainVerify] Transaction data received:', data)
    transactionData.value = data
  } catch (error) {
    console.error('[ChainVerify] 加载交易失败', error)
    transactionData.value = null
  } finally {
    loading.value = false
  }
}

// 加载区块详情
const loadBlock = async () => {
  if (!props.blockNumber) {
    console.log('[ChainVerify] No blockNumber provided')
    return
  }

  console.log('[ChainVerify] Loading block:', props.blockNumber)
  loading.value = true
  try {
    const data = await blockchainApi.getBlock(props.blockNumber)
    console.log('[ChainVerify] Block data received:', data)
    blockData.value = data
  } catch (error) {
    console.error('[ChainVerify] 加载区块失败', error)
    blockData.value = null
  } finally {
    loading.value = false
  }
}

// 加载链信息
const loadChainInfo = async () => {
  loading.value = true
  try {
    const data = await blockchainApi.getChainInfo()
    chainInfo.value = data
  } catch (error) {
    console.error('加载链信息失败', error)
    chainInfo.value = null
  } finally {
    loading.value = false
  }
}

// 验证溯源码并获取链上详细数据
const verifyOnChain = async () => {
  if (!props.traceCode) return

  loading.value = true
  try {
    // 获取链上完整产品数据
    const data = await blockchainApi.getProductChainData(props.traceCode)
    verifyResult.value = data
  } catch (error) {
    console.error('验证失败', error)
    // 如果获取详细数据失败，尝试只验证是否存在
    try {
      const simpleData = await blockchainApi.verifyTraceCode(props.traceCode)
      verifyResult.value = simpleData
    } catch {
      verifyResult.value = null
    }
  } finally {
    loading.value = false
  }
}

// 解析链上产品数据（RPC直接返回结构化数据）
const parseProductInfo = (productInfo) => {
  if (!productInfo) return null

  try {
    // RPC返回的是结构化数据，直接使用
    if (typeof productInfo === 'object' && productInfo.name !== undefined) {
      return {
        name: productInfo.name || '',
        category: productInfo.category || '',
        origin: productInfo.origin || '',
        quantity: (productInfo.quantity / 1000).toString(), // 转换为小数
        unit: productInfo.unit || '',
        currentStage: productInfo.currentStage,
        status: productInfo.status,
        creator: productInfo.creator,
        createdAt: productInfo.createdAt
      }
    }

    return null
  } catch (e) {
    console.error('解析产品信息失败:', e)
    return null
  }
}

// 解析链上记录（RPC直接返回结构化数据）
const parseChainRecord = (record) => {
  if (!record) return null

  try {
    // RPC返回的是结构化数据，直接使用
    if (typeof record === 'object' && record.stage !== undefined) {
      return {
        index: record.index,
        stage: record.stage,
        action: record.action,
        data: record.data || '',
        remark: record.remark || '',
        operator: record.operatorName || record.operator || '',
        timestamp: record.timestamp,
        amendReason: record.amendReason || ''
      }
    }

    return null
  } catch (e) {
    console.error('解析记录失败:', e)
    return null
  }
}

// 获取操作类型标签
const getActionLabel = (action) => {
  const actionNum = parseInt(action)
  const map = {
    0: '创建',
    1: '采收',
    2: '加工',
    3: '入库',
    4: '出库',
    5: '修正'
  }
  return map[actionNum] || action
}

// 获取阶段标签
const getStageLabel = (stage) => {
  const stageNum = parseInt(stage)
  const map = {
    0: '原料商',
    1: '加工商',
    2: '仓储商',
    3: '销售商'
  }
  return map[stageNum] || stage
}

// 切换 Tab 时加载数据
const handleTabChange = (tab) => {
  if (tab === 'transaction' && props.txHash && !transactionData.value) {
    loadTransaction()
  } else if (tab === 'block' && props.blockNumber && !blockData.value) {
    loadBlock()
  } else if (tab === 'chain' && !chainInfo.value) {
    loadChainInfo()
  } else if (tab === 'verify' && props.traceCode && !verifyResult.value) {
    verifyOnChain()
  }
}

// 原始JSON数据
const rawJson = computed(() => {
  if (!verifyResult.value) return ''
  return JSON.stringify(verifyResult.value, null, 2)
})

// 打开时加载数据
watch(dialogVisible, (val) => {
  if (val) {
    // 重置数据
    transactionData.value = null
    blockData.value = null
    chainInfo.value = null
    verifyResult.value = null

    // 加载当前 Tab 数据
    handleTabChange(activeTab.value)
  }
})
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    title="链上数据验证"
    width="700px"
    :close-on-click-modal="false"
  >
    <el-tabs v-model="activeTab" @tab-change="handleTabChange">
      <!-- 交易详情 -->
      <el-tab-pane label="交易详情" name="transaction">
        <div v-if="loading" class="loading-state">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>正在查询链上数据...</span>
        </div>
        <div v-else-if="transactionData" class="data-section">
          <!-- 状态标识 -->
          <div class="tx-status-banner success">
            <el-icon><CircleCheckFilled /></el-icon>
            <span>交易已确认</span>
          </div>

          <div class="data-item">
            <span class="label">交易哈希</span>
            <div class="value-wrapper">
              <el-tooltip :content="transactionData.tx_hash" placement="top">
                <span class="value hash">{{ formatHash(transactionData.tx_hash, 24) }}</span>
              </el-tooltip>
              <el-button type="primary" link size="small" @click="copyToClipboard(transactionData.tx_hash, '交易哈希')">
                <el-icon><CopyDocument /></el-icon>
              </el-button>
            </div>
          </div>
          <div class="data-item">
            <span class="label">状态</span>
            <el-tag :type="transactionData.status === '0x0' ? 'success' : 'danger'" size="small">
              {{ transactionData.status === '0x0' ? '成功' : '失败' }}
            </el-tag>
          </div>
          <div class="data-item">
            <span class="label">发送方</span>
            <div class="value-wrapper">
              <span class="value mono">{{ formatHash(transactionData.from_address, 20) }}</span>
              <el-button type="primary" link size="small" @click="copyToClipboard(transactionData.from_address, '发送方地址')">
                <el-icon><CopyDocument /></el-icon>
              </el-button>
            </div>
          </div>
          <div class="data-item">
            <span class="label">合约地址</span>
            <div class="value-wrapper">
              <span class="value mono">{{ formatHash(transactionData.contract_address, 20) }}</span>
              <el-button type="primary" link size="small" @click="copyToClipboard(transactionData.contract_address, '合约地址')">
                <el-icon><CopyDocument /></el-icon>
              </el-button>
            </div>
          </div>
          <div v-if="transactionData.chain_id" class="data-item">
            <span class="label">链 ID</span>
            <span class="value">{{ transactionData.chain_id }}</span>
          </div>
          <div v-if="transactionData.group_id" class="data-item">
            <span class="label">群组 ID</span>
            <span class="value">{{ transactionData.group_id }}</span>
          </div>
          <div v-if="transactionData.import_time" class="data-item">
            <span class="label">上链时间</span>
            <span class="value">{{ formatTimestamp(transactionData.import_time) }}</span>
          </div>

          <el-collapse class="raw-data-collapse">
            <el-collapse-item title="原始交易数据" name="raw">
              <pre class="raw-json">{{ JSON.stringify(transactionData.raw_transaction, null, 2) }}</pre>
            </el-collapse-item>
          </el-collapse>
        </div>
        <div v-else class="empty-state">
          <el-icon><Warning /></el-icon>
          <span>未找到交易数据</span>
        </div>
      </el-tab-pane>

      <!-- 区块详情 -->
      <el-tab-pane label="区块详情" name="block">
        <div v-if="loading" class="loading-state">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>正在查询链上数据...</span>
        </div>
        <div v-else-if="blockData" class="data-section">
          <div class="data-item">
            <span class="label">区块高度</span>
            <span class="value">{{ blockData.block_number }}</span>
          </div>
          <div class="data-item">
            <span class="label">区块哈希</span>
            <div class="value-wrapper">
              <el-tooltip :content="blockData.block_hash" placement="top">
                <span class="value hash">{{ formatHash(blockData.block_hash, 24) }}</span>
              </el-tooltip>
              <el-button type="primary" link size="small" @click="copyToClipboard(blockData.block_hash, '区块哈希')">
                <el-icon><CopyDocument /></el-icon>
              </el-button>
            </div>
          </div>
          <div class="data-item">
            <span class="label">时间戳</span>
            <span class="value">{{ formatTimestamp(blockData.timestamp) }}</span>
          </div>
          <div class="data-item">
            <span class="label">交易数量</span>
            <span class="value">{{ blockData.transaction_count }}</span>
          </div>
          <div class="data-item">
            <span class="label">出块节点</span>
            <span class="value">{{ blockData.sealer || '-' }}</span>
          </div>

          <el-collapse class="raw-data-collapse">
            <el-collapse-item title="原始数据" name="raw">
              <pre class="raw-json">{{ JSON.stringify(blockData.raw_block, null, 2) }}</pre>
            </el-collapse-item>
          </el-collapse>
        </div>
        <div v-else class="empty-state">
          <el-icon><Warning /></el-icon>
          <span>未找到区块数据</span>
        </div>
      </el-tab-pane>

      <!-- 链信息 -->
      <el-tab-pane label="链信息" name="chain">
        <div v-if="loading" class="loading-state">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>正在查询链信息...</span>
        </div>
        <div v-else-if="chainInfo" class="data-section">
          <div class="chain-status">
            <el-tag :type="chainInfo.connected ? 'success' : 'danger'" size="large">
              {{ chainInfo.connected ? '已连接' : '未连接' }}
            </el-tag>
          </div>
          <div class="data-item">
            <span class="label">当前区块高度</span>
            <span class="value highlight">{{ chainInfo.block_number }}</span>
          </div>
          <div class="data-item">
            <span class="label">链上产品总数</span>
            <span class="value highlight">{{ chainInfo.product_count }}</span>
          </div>
          <div class="data-item">
            <span class="label">合约地址</span>
            <div class="value-wrapper">
              <span class="value mono">{{ formatHash(chainInfo.contract_address, 24) }}</span>
              <el-button type="primary" link size="small" @click="copyToClipboard(chainInfo.contract_address, '合约地址')">
                <el-icon><CopyDocument /></el-icon>
              </el-button>
            </div>
          </div>
          <div class="data-item">
            <span class="label">RPC 地址</span>
            <span class="value mono">{{ chainInfo.rpc_url }}</span>
          </div>
        </div>
        <div v-else class="empty-state">
          <el-icon><Warning /></el-icon>
          <span>获取链信息失败</span>
        </div>
      </el-tab-pane>

      <!-- 溯源验证 - 链上数据详情 -->
      <el-tab-pane label="链上数据" name="verify" v-if="props.traceCode">
        <div v-if="loading" class="loading-state">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>正在获取链上数据...</span>
        </div>
        <div v-else-if="verifyResult" class="data-section">
          <!-- 验证状态 -->
          <div class="verify-result" :class="{ success: verifyResult.exists }">
            <div class="verify-icon" :class="{ success: verifyResult.exists }">
              <el-icon :size="40">
                <CircleCheckFilled v-if="verifyResult.exists" />
                <CircleCloseFilled v-else />
              </el-icon>
            </div>
            <div class="verify-text">
              <h3>{{ verifyResult.exists ? '链上数据验证通过' : '验证失败' }}</h3>
              <p>{{ verifyResult.exists ? '以下数据来自区块链，不可篡改' : '未在区块链上找到该溯源码' }}</p>
            </div>
          </div>

          <div class="data-item">
            <span class="label">溯源码</span>
            <span class="value code">{{ verifyResult.trace_code }}</span>
          </div>

          <!-- 链上产品信息 -->
          <template v-if="verifyResult.product_info">
            <div class="chain-data-section">
              <h4>
                <el-icon><Document /></el-icon>
                链上产品信息
              </h4>
              <div class="chain-data-card">
                <template v-if="parseProductInfo(verifyResult.product_info)">
                  <div class="chain-data-row" v-if="parseProductInfo(verifyResult.product_info).name">
                    <span class="data-label">产品名称</span>
                    <span class="data-value">{{ parseProductInfo(verifyResult.product_info).name }}</span>
                  </div>
                  <div class="chain-data-row" v-if="parseProductInfo(verifyResult.product_info).category">
                    <span class="data-label">产品类别</span>
                    <span class="data-value">{{ parseProductInfo(verifyResult.product_info).category }}</span>
                  </div>
                  <div class="chain-data-row" v-if="parseProductInfo(verifyResult.product_info).origin">
                    <span class="data-label">产地</span>
                    <span class="data-value">{{ parseProductInfo(verifyResult.product_info).origin }}</span>
                  </div>
                  <div class="chain-data-row" v-if="parseProductInfo(verifyResult.product_info).quantity">
                    <span class="data-label">数量</span>
                    <span class="data-value">
                      {{ parseProductInfo(verifyResult.product_info).quantity }}
                      {{ parseProductInfo(verifyResult.product_info).unit }}
                    </span>
                  </div>
                  <div class="chain-data-row" v-if="parseProductInfo(verifyResult.product_info).operator">
                    <span class="data-label">操作人</span>
                    <span class="data-value">{{ parseProductInfo(verifyResult.product_info).operator }}</span>
                  </div>
                </template>
                <template v-else>
                  <pre class="raw-data">{{ JSON.stringify(verifyResult.product_info, null, 2) }}</pre>
                </template>
              </div>
            </div>
          </template>

          <!-- 链上记录列表 -->
          <template v-if="verifyResult.chain_records && verifyResult.chain_records.length > 0">
            <div class="chain-data-section">
              <h4>
                <el-icon><List /></el-icon>
                链上操作记录 ({{ verifyResult.record_count }} 条)
              </h4>
              <div class="chain-records-list">
                <div
                  v-for="record in verifyResult.chain_records"
                  :key="record.index"
                  class="chain-record-item"
                >
                  <div class="record-index">#{{ record.index + 1 }}</div>
                  <div class="record-content">
                    <template v-if="parseChainRecord(record)">
                      <div class="record-tags">
                        <el-tag size="small" type="info">{{ getStageLabel(parseChainRecord(record).stage) }}</el-tag>
                        <el-tag size="small" :type="parseChainRecord(record).action === '5' ? 'warning' : 'primary'">
                          {{ getActionLabel(parseChainRecord(record).action) }}
                        </el-tag>
                      </div>
                      <div v-if="parseChainRecord(record).data" class="record-data">
                        数据: {{ parseChainRecord(record).data }}
                      </div>
                      <div v-if="parseChainRecord(record).operator" class="record-operator">
                        操作人: {{ parseChainRecord(record).operator }}
                      </div>
                      <div v-if="parseChainRecord(record).amendReason" class="record-amend-reason">
                        修正原因: {{ parseChainRecord(record).amendReason }}
                      </div>
                    </template>
                    <template v-else>
                      <pre class="raw-data-small">{{ JSON.stringify(record, null, 2) }}</pre>
                    </template>
                  </div>
                </div>
              </div>
            </div>
          </template>

          <!-- 原始数据展开 -->
          <el-collapse class="raw-data-collapse">
            <el-collapse-item title="查看原始链上数据" name="raw">
              <pre class="raw-json">{{ rawJson }}</pre>
            </el-collapse-item>
          </el-collapse>
        </div>
        <div v-else class="empty-state">
          <el-icon><Warning /></el-icon>
          <span>获取链上数据失败</span>
        </div>
      </el-tab-pane>
    </el-tabs>

    <template #footer>
      <el-button @click="dialogVisible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px;
  color: var(--text-muted);
}

.loading-state .el-icon {
  font-size: 32px;
  color: var(--primary-color);
}

.empty-state .el-icon {
  font-size: 32px;
  color: var(--text-muted);
}

.data-section {
  padding: 16px 0;
}

/* 交易状态横幅 */
.tx-status-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 16px;
  border-radius: 10px;
  margin-bottom: 16px;
  font-weight: 600;
  font-size: 14px;
}

.tx-status-banner.success {
  background: linear-gradient(135deg, rgba(82, 196, 26, 0.1), rgba(82, 196, 26, 0.05));
  border: 1px solid rgba(82, 196, 26, 0.3);
  color: #52c41a;
}

.tx-status-banner.success .el-icon {
  font-size: 18px;
}

.data-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-color);
}

.data-item:last-child {
  border-bottom: none;
}

.data-item .label {
  color: var(--text-muted);
  font-size: 13px;
  flex-shrink: 0;
}

.data-item .value {
  font-size: 14px;
  font-weight: 500;
}

.data-item .value.mono,
.data-item .value.hash {
  font-family: monospace;
  font-size: 13px;
}

.data-item .value.hash {
  color: #667eea;
  cursor: pointer;
}

.data-item .value.hash:hover {
  text-decoration: underline;
}

.data-item .value.code {
  color: var(--primary-color);
  font-family: monospace;
}

.data-item .value.highlight {
  color: var(--primary-color);
  font-size: 18px;
}

.value-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chain-status {
  text-align: center;
  margin-bottom: 20px;
}

.verify-result {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  margin-bottom: 20px;
  background: linear-gradient(135deg, rgba(245, 34, 45, 0.08), rgba(245, 34, 45, 0.03));
  border: 1px solid rgba(245, 34, 45, 0.2);
  border-radius: 12px;
}

.verify-result.success {
  background: linear-gradient(135deg, rgba(82, 196, 26, 0.08), rgba(82, 196, 26, 0.03));
  border-color: rgba(82, 196, 26, 0.2);
}

.verify-icon {
  color: #f5222d;
  flex-shrink: 0;
}

.verify-icon.success {
  color: #52c41a;
}

.verify-text h3 {
  font-size: 16px;
  margin-bottom: 4px;
}

.verify-text p {
  color: var(--text-muted);
  font-size: 13px;
  margin: 0;
}

/* 链上数据区块样式 */
.chain-data-section {
  margin-top: 20px;
}

.chain-data-section h4 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--text-primary);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-color);
}

.chain-data-card {
  padding: 16px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.05), rgba(118, 75, 162, 0.05));
  border: 1px solid rgba(102, 126, 234, 0.15);
  border-radius: 10px;
}

.chain-data-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px dashed rgba(102, 126, 234, 0.1);
}

.chain-data-row:last-child {
  border-bottom: none;
}

.chain-data-row .data-label {
  color: var(--text-muted);
  font-size: 13px;
}

.chain-data-row .data-value {
  font-size: 14px;
  font-weight: 500;
  color: #667eea;
}

/* 链上记录列表 */
.chain-records-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chain-record-item {
  display: flex;
  gap: 12px;
  padding: 12px;
  background: var(--bg-color);
  border-radius: 8px;
  border-left: 3px solid #667eea;
}

.record-index {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 600;
  flex-shrink: 0;
}

.record-content {
  flex: 1;
}

.record-tags {
  display: flex;
  gap: 6px;
  margin-bottom: 8px;
}

.record-data,
.record-operator,
.record-amend-reason {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.record-amend-reason {
  color: #e6a23c;
}

.raw-data,
.raw-data-small {
  background: #f5f5f5;
  padding: 10px;
  border-radius: 6px;
  font-size: 11px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.raw-data-small {
  font-size: 10px;
  max-height: 80px;
  overflow-y: auto;
}

.raw-data-collapse {
  margin-top: 16px;
}

.raw-json {
  background: #f5f5f5;
  padding: 12px;
  border-radius: 8px;
  font-size: 12px;
  overflow-x: auto;
  max-height: 300px;
  overflow-y: auto;
}
</style>
