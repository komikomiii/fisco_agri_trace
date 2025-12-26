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
  if (!props.txHash) return

  loading.value = true
  try {
    const data = await blockchainApi.getTransaction(props.txHash)
    transactionData.value = data
  } catch (error) {
    console.error('加载交易失败', error)
    transactionData.value = null
  } finally {
    loading.value = false
  }
}

// 加载区块详情
const loadBlock = async () => {
  if (!props.blockNumber) return

  loading.value = true
  try {
    const data = await blockchainApi.getBlock(props.blockNumber)
    blockData.value = data
  } catch (error) {
    console.error('加载区块失败', error)
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

// 验证溯源码
const verifyOnChain = async () => {
  if (!props.traceCode) return

  loading.value = true
  try {
    const data = await blockchainApi.verifyTraceCode(props.traceCode)
    verifyResult.value = data
  } catch (error) {
    console.error('验证失败', error)
    verifyResult.value = null
  } finally {
    loading.value = false
  }
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

      <!-- 溯源验证 -->
      <el-tab-pane label="溯源验证" name="verify" v-if="traceCode">
        <div v-if="loading" class="loading-state">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>正在验证溯源码...</span>
        </div>
        <div v-else-if="verifyResult" class="data-section">
          <div class="verify-result">
            <div class="verify-icon" :class="{ success: verifyResult.exists }">
              <el-icon :size="48">
                <CircleCheckFilled v-if="verifyResult.exists" />
                <CircleCloseFilled v-else />
              </el-icon>
            </div>
            <h3>{{ verifyResult.exists ? '验证通过' : '验证失败' }}</h3>
            <p>{{ verifyResult.exists ? '该溯源码在区块链上真实存在' : '未在区块链上找到该溯源码' }}</p>
          </div>
          <div class="data-item">
            <span class="label">溯源码</span>
            <span class="value code">{{ verifyResult.trace_code }}</span>
          </div>
          <div class="data-item">
            <span class="label">链上状态</span>
            <el-tag :type="verifyResult.on_chain ? 'success' : 'info'" size="small">
              {{ verifyResult.on_chain ? '已上链' : '未上链' }}
            </el-tag>
          </div>
        </div>
        <div v-else class="empty-state">
          <el-icon><Warning /></el-icon>
          <span>验证失败</span>
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
  text-align: center;
  padding: 20px;
  margin-bottom: 20px;
  background: var(--bg-color);
  border-radius: 12px;
}

.verify-icon {
  margin-bottom: 12px;
  color: #f5222d;
}

.verify-icon.success {
  color: #52c41a;
}

.verify-result h3 {
  font-size: 18px;
  margin-bottom: 8px;
}

.verify-result p {
  color: var(--text-muted);
  font-size: 14px;
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
