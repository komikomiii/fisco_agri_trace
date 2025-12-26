<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useProductStore } from '../../store/product'
import { useUserStore } from '../../store/user'
import { useNotificationStore } from '../../store/notification'
import ChainConfirm from '../../components/common/ChainConfirm.vue'
import TraceCode from '../../components/common/TraceCode.vue'
import AmendRecord from '../../components/common/AmendRecord.vue'

const productStore = useProductStore()
const userStore = useUserStore()
const notificationStore = useNotificationStore()

// Tab 切换
const activeTab = ref('pending')

// 待加工产品（已接收但未加工）
const pendingProducts = computed(() => {
  return productStore.productChains.filter(c =>
    c.status === 'on_chain' &&
    c.currentStage === 'processor' &&
    !c.records.some(r => r.action === 'process')
  )
})

// 加工中的产品
const processingProducts = computed(() => {
  return productStore.productChains.filter(c =>
    c.status === 'on_chain' &&
    c.currentStage === 'processor' &&
    c.records.some(r => r.action === 'process') &&
    !c.records.some(r => r.action === 'send_inspect')
  )
})

// 已送检的产品
const sentProducts = computed(() => {
  return productStore.productChains.filter(c =>
    c.status === 'on_chain' &&
    (c.currentStage === 'inspector' || c.records.some(r => r.action === 'send_inspect'))
  )
})

// 当前显示的列表
const currentList = computed(() => {
  if (activeTab.value === 'pending') return pendingProducts.value
  if (activeTab.value === 'processing') return processingProducts.value
  if (activeTab.value === 'sent') return sentProducts.value
  return []
})

// 状态映射
const statusMap = {
  pending: { label: '待加工', type: 'warning' },
  processing: { label: '加工中', type: 'primary' },
  sent: { label: '已送检', type: 'success' }
}

// 加工类型选项
const processTypes = [
  { value: 'wash', label: '清洗分拣' },
  { value: 'cut', label: '切割加工' },
  { value: 'juice', label: '榨汁加工' },
  { value: 'pack', label: '包装封装' },
  { value: 'freeze', label: '冷冻处理' },
  { value: 'dry', label: '烘干处理' }
]

// ==================== 新建加工记录 ====================
const processDialogVisible = ref(false)
const processForm = ref({
  chainId: null,
  processType: '',
  outputProduct: '',
  outputQuantity: 0,
  notes: ''
})

const openProcessDialog = (chain = null) => {
  if (chain) {
    processForm.value = {
      chainId: chain.id,
      processType: '',
      outputProduct: '',
      outputQuantity: 0,
      notes: ''
    }
  } else {
    processForm.value = {
      chainId: null,
      processType: '',
      outputProduct: '',
      outputQuantity: 0,
      notes: ''
    }
  }
  processDialogVisible.value = true
}

// ==================== 加工上链确认 ====================
const chainConfirmVisible = ref(false)
const pendingProcess = ref(null)
const chainConfirmRef = ref(null)

const confirmProcess = () => {
  if (!processForm.value.chainId || !processForm.value.processType || !processForm.value.outputProduct) {
    ElMessage.warning('请填写完整信息')
    return
  }

  const chain = productStore.productChains.find(c => c.id === processForm.value.chainId)
  if (!chain) {
    ElMessage.error('未找到对应产品')
    return
  }

  const processTypeLabel = processTypes.find(t => t.value === processForm.value.processType)?.label

  pendingProcess.value = {
    chain,
    form: { ...processForm.value },
    data: {
      rawMaterial: chain.productName,
      traceCode: chain.traceCode,
      processType: processTypeLabel,
      outputProduct: processForm.value.outputProduct,
      outputQuantity: `${processForm.value.outputQuantity} 件`
    },
    labels: {
      rawMaterial: '原材料',
      traceCode: '溯源码',
      processType: '加工类型',
      outputProduct: '成品名称',
      outputQuantity: '产出数量'
    }
  }

  processDialogVisible.value = false
  chainConfirmVisible.value = true
}

const onProcessConfirm = async () => {
  if (!pendingProcess.value) return

  chainConfirmRef.value?.setLoading()

  try {
    const result = await productStore.addRecord(pendingProcess.value.chain.id, {
      stage: 'processor',
      action: 'process',
      data: {
        processType: pendingProcess.value.form.processType,
        outputProduct: pendingProcess.value.form.outputProduct,
        outputQuantity: pendingProcess.value.form.outputQuantity,
        notes: pendingProcess.value.form.notes
      },
      operator: {
        id: userStore.user?.id || 2,
        name: userStore.user?.name || '绿源加工厂',
        role: 'processor'
      }
    })

    if (result) {
      chainConfirmRef.value?.setSuccess(result.txHash, result.blockNumber)
      ElMessage.success('加工记录已上链')
    } else {
      chainConfirmRef.value?.setError('上链失败，请重试')
    }
  } catch (error) {
    chainConfirmRef.value?.setError(error.message || '上链失败')
  }
}

// ==================== 送检确认 ====================
const sendInspectVisible = ref(false)
const pendingSendInspect = ref(null)
const sendInspectRef = ref(null)

const openSendInspectDialog = (chain) => {
  const processRecord = chain.records.find(r => r.action === 'process')
  pendingSendInspect.value = {
    chain,
    data: {
      productName: processRecord?.data?.outputProduct || chain.productName,
      traceCode: chain.traceCode,
      processType: processTypes.find(t => t.value === processRecord?.data?.processType)?.label || '-',
      quantity: `${processRecord?.data?.outputQuantity || 0} 件`
    },
    labels: {
      productName: '产品名称',
      traceCode: '溯源码',
      processType: '加工方式',
      quantity: '送检数量'
    }
  }
  sendInspectVisible.value = true
}

const onSendInspectConfirm = async () => {
  if (!pendingSendInspect.value) return

  sendInspectRef.value?.setLoading()

  try {
    const result = await productStore.addRecord(pendingSendInspect.value.chain.id, {
      stage: 'processor',
      action: 'send_inspect',
      data: {
        sendTime: new Date().toISOString()
      },
      operator: {
        id: userStore.user?.id || 2,
        name: userStore.user?.name || '绿源加工厂',
        role: 'processor'
      }
    })

    if (result) {
      // 更新产品链阶段
      pendingSendInspect.value.chain.currentStage = 'inspector'

      sendInspectRef.value?.setSuccess(result.txHash, result.blockNumber)

      // 通知质检员
      notificationStore.addNotification({
        type: notificationStore.NOTIFICATION_TYPES.PENDING,
        title: '新产品待检测',
        content: `${userStore.user?.name || '绿源加工厂'}送检的"${pendingSendInspect.value.data.productName}"等待您的检测。`,
        relatedTraceCode: pendingSendInspect.value.chain.traceCode
      })

      ElMessage.success('已送检，等待质检员检测')
    } else {
      sendInspectRef.value?.setError('送检失败，请重试')
    }
  } catch (error) {
    sendInspectRef.value?.setError(error.message || '送检失败')
  }
}

// ==================== 修正记录 ====================
const amendVisible = ref(false)
const amendingChain = ref(null)

const amendDataLabels = {
  outputProduct: '成品名称',
  outputQuantity: '产出数量',
  processType: '加工类型'
}

const amendEditableFields = [
  { key: 'outputProduct', type: 'input', placeholder: '请输入成品名称' },
  { key: 'outputQuantity', type: 'number' },
  {
    key: 'processType',
    type: 'select',
    options: processTypes.map(t => ({ value: t.value, label: t.label }))
  }
]

const openAmendDialog = (chain) => {
  amendingChain.value = chain
  amendVisible.value = true
}

const handleAmendSubmit = async (amendData) => {
  if (!amendingChain.value) return

  const processRecord = amendingChain.value.records.find(r => r.action === 'process')
  if (!processRecord) return

  await productStore.addAmendRecord(
    amendingChain.value.id,
    processRecord.id,
    {
      ...amendData.changes,
      operator: {
        id: userStore.user?.id || 2,
        name: userStore.user?.name || '绿源加工厂',
        role: 'processor'
      }
    },
    amendData.reason
  )

  ElMessage.success('修正记录已提交上链')
}

// ==================== 查看详情 ====================
const detailDrawerVisible = ref(false)
const detailChain = ref(null)

const viewDetail = (chain) => {
  detailChain.value = chain
  detailDrawerVisible.value = true
}

// 获取加工记录数据
const getProcessData = (chain) => {
  const processRecord = chain.records.find(r => r.action === 'process')
  return processRecord?.data || {}
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
    send_inspect: '送检',
    inspect: '质量检测',
    stock: '入库登记'
  }
  return map[action] || action
}

// 获取产品状态
const getProductStatus = (chain) => {
  if (chain.records.some(r => r.action === 'send_inspect')) return 'sent'
  if (chain.records.some(r => r.action === 'process')) return 'processing'
  return 'pending'
}
</script>

<template>
  <div class="process-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span class="title">
            <el-icon><SetUp /></el-icon>
            加工记录
          </span>
          <el-button type="primary" :icon="Plus" @click="openProcessDialog()">
            新建加工
          </el-button>
        </div>
      </template>

      <!-- Tab 切换 -->
      <el-tabs v-model="activeTab" class="process-tabs">
        <el-tab-pane name="pending">
          <template #label>
            <span>
              待加工
              <el-badge :value="pendingProducts.length" :max="99" class="tab-badge" />
            </span>
          </template>
        </el-tab-pane>
        <el-tab-pane name="processing">
          <template #label>
            <span>
              加工中
              <el-badge
                :value="processingProducts.length"
                :max="99"
                class="tab-badge"
                type="primary"
              />
            </span>
          </template>
        </el-tab-pane>
        <el-tab-pane name="sent">
          <template #label>
            <span>
              已送检
              <el-badge
                :value="sentProducts.length"
                :max="99"
                class="tab-badge"
                type="success"
              />
            </span>
          </template>
        </el-tab-pane>
      </el-tabs>

      <el-table :data="currentList" stripe>
        <el-table-column prop="productName" label="产品" min-width="160">
          <template #default="{ row }">
            <div class="product-info">
              <el-avatar :size="36" shape="square" style="background: #1890ff">
                {{ (getProcessData(row).outputProduct || row.productName).charAt(0) }}
              </el-avatar>
              <div class="info">
                <span class="name">{{ getProcessData(row).outputProduct || row.productName }}</span>
                <span class="code">{{ row.traceCode }}</span>
                <span v-if="getProcessData(row).outputProduct" class="raw-material">
                  原料：{{ row.productName }}
                </span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="加工类型" width="120">
          <template #default="{ row }">
            <el-tag v-if="getProcessData(row).processType" type="primary" effect="plain">
              {{ processTypes.find(t => t.value === getProcessData(row).processType)?.label || '-' }}
            </el-tag>
            <span v-else class="text-muted">未加工</span>
          </template>
        </el-table-column>
        <el-table-column label="产出数量" width="100">
          <template #default="{ row }">
            <span v-if="getProcessData(row).outputQuantity" class="quantity">
              {{ getProcessData(row).outputQuantity }} 件
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusMap[getProductStatus(row)]?.type">
              {{ statusMap[getProductStatus(row)]?.label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" text size="small" @click="viewDetail(row)">
              查看详情
            </el-button>

            <!-- 待加工：开始加工 -->
            <el-button
              v-if="getProductStatus(row) === 'pending'"
              type="success"
              text
              size="small"
              @click="openProcessDialog(row)"
            >
              <el-icon><SetUp /></el-icon>
              开始加工
            </el-button>

            <!-- 加工中：送检、修正 -->
            <template v-if="getProductStatus(row) === 'processing'">
              <el-button type="success" text size="small" @click="openSendInspectDialog(row)">
                <el-icon><Van /></el-icon>
                送检
              </el-button>
              <el-button type="warning" text size="small" @click="openAmendDialog(row)">
                <el-icon><Edit /></el-icon>
                修正
              </el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态 -->
      <el-empty v-if="currentList.length === 0" description="暂无记录" />
    </el-card>

    <!-- 新建加工对话框 -->
    <el-dialog v-model="processDialogVisible" title="新建加工记录" width="500px">
      <el-form :model="processForm" label-width="100px">
        <el-form-item label="选择原料" required>
          <el-select
            v-model="processForm.chainId"
            placeholder="选择待加工的原料"
            style="width: 100%"
          >
            <el-option
              v-for="chain in pendingProducts"
              :key="chain.id"
              :label="`${chain.productName} (${chain.traceCode})`"
              :value="chain.id"
            >
              <div class="select-option">
                <span class="name">{{ chain.productName }}</span>
                <span class="code">{{ chain.traceCode }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="加工类型" required>
          <el-select v-model="processForm.processType" placeholder="选择加工类型" style="width: 100%">
            <el-option
              v-for="type in processTypes"
              :key="type.value"
              :label="type.label"
              :value="type.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="成品名称" required>
          <el-input v-model="processForm.outputProduct" placeholder="请输入成品名称" />
        </el-form-item>
        <el-form-item label="预计产量">
          <el-input-number v-model="processForm.outputQuantity" :min="0" style="width: 200px" />
          <span style="margin-left: 10px">件</span>
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="processForm.notes"
            type="textarea"
            :rows="2"
            placeholder="可选填写加工备注"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="processDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmProcess">
          <el-icon><Connection /></el-icon>
          确认上链
        </el-button>
      </template>
    </el-dialog>

    <!-- 加工上链确认 -->
    <ChainConfirm
      ref="chainConfirmRef"
      v-model:visible="chainConfirmVisible"
      title="确认加工记录上链"
      :data="pendingProcess?.data"
      :data-labels="pendingProcess?.labels"
      @confirm="onProcessConfirm"
    />

    <!-- 送检确认 -->
    <ChainConfirm
      ref="sendInspectRef"
      v-model:visible="sendInspectVisible"
      title="确认送检"
      :data="pendingSendInspect?.data"
      :data-labels="pendingSendInspect?.labels"
      @confirm="onSendInspectConfirm"
    >
      <template #extra>
        <div class="send-tip">
          <el-icon><InfoFilled /></el-icon>
          送检后产品将进入质检环节，质检员会收到通知
        </div>
      </template>
    </ChainConfirm>

    <!-- 修正记录 -->
    <AmendRecord
      v-model:visible="amendVisible"
      :original-data="amendingChain ? getProcessData(amendingChain) : {}"
      :data-labels="amendDataLabels"
      :editable-fields="amendEditableFields"
      @submit="handleAmendSubmit"
    />

    <!-- 详情抽屉 -->
    <el-drawer
      v-model="detailDrawerVisible"
      title="加工详情"
      size="500px"
    >
      <template v-if="detailChain">
        <!-- 溯源码 -->
        <div class="detail-section">
          <TraceCode :trace-code="detailChain.traceCode" size="large" />
        </div>

        <!-- 加工信息 -->
        <div class="detail-section">
          <h4>加工信息</h4>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="原材料">
              {{ detailChain.productName }}
            </el-descriptions-item>
            <el-descriptions-item label="成品名称">
              {{ getProcessData(detailChain).outputProduct || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="加工类型">
              {{ processTypes.find(t => t.value === getProcessData(detailChain).processType)?.label || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="产出数量">
              {{ getProcessData(detailChain).outputQuantity || 0 }} 件
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusMap[getProductStatus(detailChain)]?.type">
                {{ statusMap[getProductStatus(detailChain)]?.label }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 链上记录 -->
        <div class="detail-section">
          <h4>
            链上记录
            <el-tag v-if="productStore.hasAmendments(detailChain)" type="warning" size="small">
              有修正记录
            </el-tag>
          </h4>
          <el-timeline>
            <el-timeline-item
              v-for="record in detailChain.records"
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
                <div v-if="record.reason" class="record-reason">
                  修正原因：{{ record.reason }}
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
.process-container {
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

.process-tabs {
  margin-bottom: 16px;
}

.tab-badge {
  margin-left: 6px;
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

.product-info .raw-material {
  font-size: 12px;
  color: var(--text-secondary);
}

.quantity {
  font-weight: 500;
  color: var(--primary-color);
}

.text-muted {
  color: var(--text-muted);
}

/* 下拉选项样式 */
.select-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.select-option .name {
  font-weight: 500;
}

.select-option .code {
  font-size: 12px;
  color: var(--text-muted);
  font-family: monospace;
}

.send-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding: 12px;
  background: #e6f7ff;
  border-radius: 8px;
  font-size: 13px;
  color: #1890ff;
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

.record-reason {
  margin-top: 6px;
  padding: 8px 12px;
  background: #fffbe6;
  border-radius: 6px;
  font-size: 13px;
  color: #ad6800;
}
</style>
