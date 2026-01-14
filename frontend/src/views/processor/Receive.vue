<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../../store/user'
import { useNotificationStore } from '../../store/notification'
import ChainConfirm from '../../components/common/ChainConfirm.vue'
import TraceCode from '../../components/common/TraceCode.vue'
import * as processorApi from '../../api/processor'

const userStore = useUserStore()
const notificationStore = useNotificationStore()

// Tab 切换
const activeTab = ref('pool')

// 产品数据
const availableProducts = ref([])
const receivedProductsData = ref([])
const loading = ref(false)

// 公共池中的产品（distribution_type 为 pool 或 null）
const poolProducts = computed(() => {
  return availableProducts.value.filter(p =>
    p.distribution_type === 'pool' || !p.distribution_type
  )
})

// 指定给当前加工商的产品（distribution_type 为 assigned 且 is_assigned_to_me 为 true）
const assignedProducts = computed(() => {
  return availableProducts.value.filter(p =>
    p.distribution_type === 'assigned' && p.is_assigned_to_me
  )
})

// 已接收的产品（在加工商阶段）
const receivedProducts = computed(() => {
  return receivedProductsData.value
})

// 当前显示的列表
const currentList = computed(() => {
  if (activeTab.value === 'pool') return poolProducts.value
  if (activeTab.value === 'assigned') return assignedProducts.value
  if (activeTab.value === 'received') return receivedProducts.value
  return []
})

// 状态映射
const statusMap = {
  pending: { label: '待接收', type: 'warning' },
  received: { label: '已接收', type: 'success' },
  ON_CHAIN: { label: '已上链', type: 'success' },
  PENDING_CHAIN: { label: '正在接收...', type: 'info', icon: 'Loading' },
  CHAIN_FAILED: { label: '接收失败', type: 'danger' }
}

// ==================== 接收确认（上链） ====================
const chainConfirmVisible = ref(false)
const pendingReceive = ref(null)
const chainConfirmRef = ref(null)
const receiveForm = ref({
  receivedQuantity: 0,
  quality: 'A',
  notes: ''
})

const openReceiveDialog = (product) => {
  receiveForm.value = {
    receivedQuantity: product.quantity || 0,
    quality: 'A',
    notes: ''
  }
  pendingReceive.value = {
    product,
    data: {
      productName: product.name,
      traceCode: product.trace_code,
      origin: product.origin,
      quantity: `${product.quantity} ${product.unit}`,
      supplier: product.creator_name || '-'
    },
    labels: {
      productName: '产品名称',
      traceCode: '溯源码',
      origin: '产地',
      quantity: '发货数量',
      supplier: '供应商'
    }
  }
  chainConfirmVisible.value = true
}

// 轮询定时器
const pollTimer = ref(null)
const pollingForId = ref(null)

// 开启轮询
const startPolling = (productId = null) => {
  if (productId) pollingForId.value = productId
  if (pollTimer.value) return
  pollTimer.value = setInterval(async () => {
    await fetchAvailableProducts(false)
    await fetchReceivedProducts(false)

    if (pollingForId.value) {
      // 在已接收列表中找
      const product = receivedProductsData.value.find(p => p.id === pollingForId.value)
      if (product && product.status === 'ON_CHAIN') {
        if (chainConfirmVisible.value && pendingReceive.value?.product?.id === product.id) {
          chainConfirmRef.value?.setSuccess(product.trace_code, product.block_number, product.tx_hash)
        }
        pollingForId.value = null
      }
    }

    const hasPending = [...availableProducts.value, ...receivedProductsData.value].some(p => p.status === 'PENDING_CHAIN')
    if (!hasPending && !pollingForId.value) {
      stopPolling()
    }
  }, 3000)
}

// 停止轮询
const stopPolling = () => {
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }
}

const onReceiveConfirm = async () => {
  if (!pendingReceive.value) return

  chainConfirmRef.value?.setLoading()

  try {
    const result = await processorApi.receiveProduct(
      pendingReceive.value.product.id,
      {
        product_id: pendingReceive.value.product.id,
        received_quantity: receiveForm.value.receivedQuantity,
        quality: receiveForm.value.quality,
        notes: receiveForm.value.notes
      }
    )

    ElMessage.success('接收请求已提交，请等待区块确认...')
    
    fetchAvailableProducts()
    fetchReceivedProducts()
    startPolling(pendingReceive.value.product.id)
  } catch (error) {
    chainConfirmRef.value?.setError(error.response?.data?.detail || '接收失败')
  }
}

// 获取可接收的产品列表
const fetchAvailableProducts = async (showLoading = true) => {
  try {
    if (showLoading) loading.value = true
    const data = await processorApi.getAvailableProducts()
    availableProducts.value = data
  } catch (error) {
    ElMessage.error('获取可接收产品列表失败')
  } finally {
    if (showLoading) loading.value = false
  }
}

// 获取已接收的产品列表
const fetchReceivedProducts = async (showLoading = true) => {
  try {
    if (showLoading) loading.value = true
    const data = await processorApi.getReceivedProducts()
    receivedProductsData.value = data
  } catch (error) {
    ElMessage.error('获取已接收产品列表失败')
  } finally {
    if (showLoading) loading.value = false
  }
}

// 页面加载时获取数据
onMounted(() => {
  fetchAvailableProducts()
  fetchReceivedProducts()
})

// ==================== 辅助函数 ====================
// 获取操作描述
const getActionLabel = (action) => {
  const map = {
    create: '原料登记',
    harvest: '采收出库',
    amend: '信息修正',
    receive: '接收确认',
    process: '加工处理',
    inspect: '质量检测',
    stock: '入库登记'
  }
  return map[action] || action
}
</script>

<template>
  <div class="receive-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span class="title">
            <el-icon><Box /></el-icon>
            原料接收
          </span>
        </div>
      </template>

      <!-- Tab 切换 -->
      <el-tabs v-model="activeTab" class="receive-tabs">
        <el-tab-pane name="pool">
          <template #label>
            <span>
              <el-icon><Collection /></el-icon>
              公共池
              <el-badge :value="poolProducts.length" :max="99" class="tab-badge" />
            </span>
          </template>
        </el-tab-pane>
        <el-tab-pane name="assigned">
          <template #label>
            <span>
              <el-icon><Position /></el-icon>
              指定接收
              <el-badge
                :value="assignedProducts.length"
                :max="99"
                class="tab-badge"
                type="warning"
              />
            </span>
          </template>
        </el-tab-pane>
        <el-tab-pane name="received">
          <template #label>
            <span>
              已接收
              <el-badge
                :value="receivedProducts.length"
                :max="99"
                class="tab-badge"
                type="success"
              />
            </span>
          </template>
        </el-tab-pane>
      </el-tabs>

      <!-- 提示信息 -->
      <div v-if="activeTab === 'pool'" class="tab-tip">
        <el-icon><InfoFilled /></el-icon>
        公共池中的原料可由任意加工商自由选择接收
      </div>
      <div v-else-if="activeTab === 'assigned'" class="tab-tip assigned">
        <el-icon><Position /></el-icon>
        以下原料由供应商指定发送给您
      </div>

      <el-table :data="currentList" stripe v-loading="loading">
        <el-table-column prop="name" label="产品名称" min-width="140">
          <template #default="{ row }">
            <div class="product-info">
              <el-avatar :size="36" shape="square" style="background: #1890ff">
                {{ row.name.charAt(0) }}
              </el-avatar>
              <div class="info">
                <span class="name">{{ row.name }}</span>
                <span class="code">{{ row.trace_code }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="供应商" width="120">
          <template #default="{ row }">
            {{ row.creator_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="产地" min-width="120">
          <template #default="{ row }">
            {{ row.origin || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="数量" width="120">
          <template #default="{ row }">
            <span class="quantity">
              {{ row.quantity || 0 }}
              {{ row.unit || 'kg' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="statusMap[row.status]?.type || 'success'">
              <el-icon v-if="row.status === 'PENDING_CHAIN'" class="is-loading"><Loading /></el-icon>
              {{ statusMap[row.status]?.label || '已上链' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="activeTab !== 'received'"
              type="success"
              text
              size="small"
              @click="openReceiveDialog(row)"
            >
              <el-icon><Check /></el-icon>
              确认接收
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态 -->
      <el-empty
        v-if="currentList.length === 0"
        :description="activeTab === 'received' ? '暂无已接收的原料' : '暂无待接收的原料'"
      />
    </el-card>

    <!-- 接收确认对话框 -->
    <ChainConfirm
      ref="chainConfirmRef"
      v-model:visible="chainConfirmVisible"
      title="确认接收原料"
      :data="pendingReceive?.data"
      :data-labels="pendingReceive?.labels"
      @confirm="onReceiveConfirm"
    >
      <template #extra>
        <div class="receive-form">
          <h4>接收信息</h4>
          <el-form :model="receiveForm" label-width="100px" size="default">
            <el-form-item label="实收数量">
              <el-input-number
                v-model="receiveForm.receivedQuantity"
                :min="0"
                style="width: 200px"
              />
              <span style="margin-left: 10px">kg</span>
            </el-form-item>
            <el-form-item label="质量等级">
              <el-radio-group v-model="receiveForm.quality">
                <el-radio-button value="A">A级（优）</el-radio-button>
                <el-radio-button value="B">B级（良）</el-radio-button>
                <el-radio-button value="C">C级（中）</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="备注">
              <el-input
                v-model="receiveForm.notes"
                type="textarea"
                :rows="2"
                placeholder="可选填写接收备注"
              />
            </el-form-item>
          </el-form>
        </div>
      </template>
    </ChainConfirm>
  </div>
</template>

<style scoped>
.receive-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

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

.receive-tabs {
  margin-bottom: 16px;
}

.tab-badge {
  margin-left: 6px;
}

.tab-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: #e6f7ff;
  border: 1px solid #91d5ff;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 13px;
  color: #1890ff;
}

.tab-tip.assigned {
  background: #fff7e6;
  border-color: #ffd591;
  color: #fa8c16;
}

.product-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.product-info .info {
  display: flex;
  flex-direction: column;
}

.product-info .name {
  font-weight: 500;
}

.product-info .code {
  font-size: 12px;
  color: var(--text-muted);
  font-family: monospace;
}

.quantity {
  font-weight: 500;
  color: var(--primary-color);
}

/* 接收表单 */
.receive-form {
  margin-top: 16px;
  padding: 16px;
  background: var(--bg-color);
  border-radius: 8px;
}

.receive-form h4 {
  font-size: 14px;
  margin-bottom: 16px;
  color: var(--text-primary);
}

/* 详情抽屉样式 */
.detail-section {
  margin-bottom: 24px;
}

.detail-section h4 {
  font-size: 14px;
  color: var(--text-primary);
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.record-item {
  padding: 8px 0;
}

.record-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}

.record-header .action {
  font-weight: 500;
}

.record-header .operator {
  color: var(--text-secondary);
  font-size: 13px;
}

.record-hash {
  font-size: 12px;
  color: var(--text-muted);
  font-family: monospace;
  display: flex;
  align-items: center;
  gap: 4px;
}
</style>
