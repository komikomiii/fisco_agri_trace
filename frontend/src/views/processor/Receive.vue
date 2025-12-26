<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useProductStore } from '../../store/product'
import { useUserStore } from '../../store/user'
import { useNotificationStore } from '../../store/notification'
import ChainConfirm from '../../components/common/ChainConfirm.vue'
import TraceCode from '../../components/common/TraceCode.vue'

const productStore = useProductStore()
const userStore = useUserStore()
const notificationStore = useNotificationStore()

// Tab 切换
const activeTab = ref('pool')

// 公共池中的产品（池子自选）
const poolProducts = computed(() => {
  return productStore.productChains.filter(c =>
    c.status === 'on_chain' &&
    c.currentStage === 'producer' &&
    c.distribution?.type === 'pool'
  )
})

// 指定给当前加工商的产品
const assignedProducts = computed(() => {
  const currentUserId = userStore.user?.id || 2
  return productStore.productChains.filter(c =>
    c.status === 'on_chain' &&
    c.currentStage === 'producer' &&
    c.distribution?.type === 'assigned' &&
    c.distribution?.assignedTo?.id === currentUserId
  )
})

// 已接收的产品（在加工商阶段）
const receivedProducts = computed(() => {
  return productStore.productChains.filter(c =>
    c.status === 'on_chain' &&
    c.currentStage === 'processor'
  )
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
  received: { label: '已接收', type: 'success' }
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

const openReceiveDialog = (chain) => {
  const data = productStore.getMergedData(chain)
  receiveForm.value = {
    receivedQuantity: data.quantity || 0,
    quality: 'A',
    notes: ''
  }
  pendingReceive.value = {
    chain,
    data: {
      productName: chain.productName,
      traceCode: chain.traceCode,
      origin: data.origin,
      quantity: `${data.quantity} ${data.unit}`,
      supplier: chain.records[0]?.operator?.name || '-'
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

const onReceiveConfirm = async () => {
  if (!pendingReceive.value) return

  chainConfirmRef.value?.setLoading()

  try {
    // 添加接收记录到产品链
    const result = await productStore.addRecord(pendingReceive.value.chain.id, {
      stage: 'processor',
      action: 'receive',
      data: {
        receivedQuantity: receiveForm.value.receivedQuantity,
        quality: receiveForm.value.quality,
        notes: receiveForm.value.notes
      },
      operator: {
        id: userStore.user?.id || 2,
        name: userStore.user?.name || '绿源加工厂',
        role: 'processor'
      }
    })

    if (result) {
      // 更新产品链当前阶段
      pendingReceive.value.chain.currentStage = 'processor'

      chainConfirmRef.value?.setSuccess(result.txHash, result.blockNumber)

      // 移除待处理通知
      const notification = notificationStore.notifications.find(
        n => n.relatedTraceCode === pendingReceive.value.chain.traceCode &&
             n.type === notificationStore.NOTIFICATION_TYPES.PENDING
      )
      if (notification) {
        notificationStore.markAsRead(notification.id)
      }

      ElMessage.success('接收成功，产品已进入加工环节')
    } else {
      chainConfirmRef.value?.setError('接收失败，请重试')
    }
  } catch (error) {
    chainConfirmRef.value?.setError(error.message || '接收失败')
  }
}

// ==================== 溯源信息查看 ====================
const traceDrawerVisible = ref(false)
const traceChain = ref(null)

const viewTrace = (chain) => {
  traceChain.value = chain
  traceDrawerVisible.value = true
}

// 格式化时间
const formatTime = (timestamp) => {
  if (!timestamp) return '-'
  return new Date(timestamp).toLocaleString('zh-CN')
}

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

      <el-table :data="currentList" stripe>
        <el-table-column prop="productName" label="产品名称" min-width="140">
          <template #default="{ row }">
            <div class="product-info">
              <el-avatar :size="36" shape="square" style="background: #1890ff">
                {{ row.productName.charAt(0) }}
              </el-avatar>
              <div class="info">
                <span class="name">{{ row.productName }}</span>
                <span class="code">{{ row.traceCode }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="供应商" width="120">
          <template #default="{ row }">
            {{ row.records[0]?.operator?.name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="产地" min-width="120">
          <template #default="{ row }">
            {{ productStore.getMergedData(row)?.origin || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="数量" width="120">
          <template #default="{ row }">
            <span class="quantity">
              {{ productStore.getMergedData(row)?.quantity || 0 }}
              {{ productStore.getMergedData(row)?.unit || 'kg' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="分配类型" width="120" v-if="activeTab !== 'received'">
          <template #default="{ row }">
            <el-tag v-if="row.distribution?.type === 'pool'" type="info" size="small">
              公共池
            </el-tag>
            <el-tag v-else type="warning" size="small">
              指定发送
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" v-if="activeTab === 'received'">
          <template #default>
            <el-tag type="success">已接收</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" text size="small" @click="viewTrace(row)">
              溯源信息
            </el-button>
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

    <!-- 溯源信息抽屉 -->
    <el-drawer
      v-model="traceDrawerVisible"
      title="溯源信息"
      size="500px"
    >
      <template v-if="traceChain">
        <!-- 溯源码 -->
        <div class="detail-section">
          <TraceCode :trace-code="traceChain.traceCode" size="large" />
        </div>

        <!-- 基本信息 -->
        <div class="detail-section">
          <h4>产品信息</h4>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="产品名称">
              {{ traceChain.productName }}
            </el-descriptions-item>
            <el-descriptions-item label="产品类别">
              {{ traceChain.category }}
            </el-descriptions-item>
            <el-descriptions-item label="产地">
              {{ productStore.getMergedData(traceChain)?.origin || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="种植日期">
              {{ productStore.getMergedData(traceChain)?.plantDate || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="数量">
              {{ productStore.getMergedData(traceChain)?.quantity }}
              {{ productStore.getMergedData(traceChain)?.unit }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 链上记录 -->
        <div class="detail-section">
          <h4>
            链上记录
            <el-tag v-if="productStore.hasAmendments(traceChain)" type="warning" size="small">
              有修正记录
            </el-tag>
          </h4>
          <el-timeline>
            <el-timeline-item
              v-for="record in traceChain.records"
              :key="record.id"
              :timestamp="formatTime(record.timestamp)"
              :type="record.action === 'amend' ? 'warning' : 'primary'"
            >
              <div class="record-item">
                <div class="record-header">
                  <span class="action">{{ getActionLabel(record.action) }}</span>
                  <span class="operator">{{ record.operator?.name }}</span>
                </div>
                <div v-if="record.txHash" class="record-hash">
                  <el-icon><Link /></el-icon>
                  {{ record.txHash.slice(0, 10) }}...{{ record.txHash.slice(-8) }}
                </div>
              </div>
            </el-timeline-item>
          </el-timeline>
        </div>
      </template>
    </el-drawer>
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
