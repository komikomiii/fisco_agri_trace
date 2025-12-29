<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../../store/user'
import { useNotificationStore } from '../../store/notification'
import ChainConfirm from '../../components/common/ChainConfirm.vue'
import ChainVerify from '../../components/common/ChainVerify.vue'
import TraceCode from '../../components/common/TraceCode.vue'
import AmendRecord from '../../components/common/AmendRecord.vue'
import * as processorApi from '../../api/processor'

const userStore = useUserStore()
const notificationStore = useNotificationStore()

// 产品数据
const pendingProducts = ref([])
const processingProducts = ref([])
const sentProducts = ref([])
const loading = ref(false)

// 链上数据验证
const chainVerifyVisible = ref(false)
const verifyTraceCode = ref('')
const verifyTxHash = ref('')
const verifyBlockNumber = ref(null)

// Tab 切换
const activeTab = ref('pending')

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

const openProcessDialog = (product = null) => {
  if (product) {
    processForm.value = {
      productId: product.id,
      traceCode: product.trace_code,
      productName: product.name,
      processType: '',
      outputProduct: '',
      outputQuantity: Math.floor(product.quantity || 100), // 默认产量
      notes: ''
    }
  } else {
    processForm.value = {
      productId: null,
      traceCode: '',
      productName: '',
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
  if (!processForm.value.productId || !processForm.value.processType || !processForm.value.outputProduct) {
    ElMessage.warning('请填写完整信息')
    return
  }

  const processTypeLabel = processTypes.find(t => t.value === processForm.value.processType)?.label

  pendingProcess.value = {
    form: { ...processForm.value },
    data: {
      rawMaterial: processForm.value.productName,
      traceCode: processForm.value.traceCode,
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
    // 调用后端 API 进行加工
    const result = await processorApi.processProduct(
      pendingProcess.value.form.productId,
      {
        product_id: pendingProcess.value.form.productId,
        result_product: pendingProcess.value.form.outputProduct,
        result_quantity: pendingProcess.value.form.outputQuantity,
        process_type: pendingProcess.value.form.processType,
        notes: pendingProcess.value.form.notes
      }
    )

    chainConfirmRef.value?.setSuccess(result.trace_code, result.block_number, result.tx_hash)

    ElMessage.success('加工记录已上链')

    // 刷新列表
    await fetchPendingProducts()
    await fetchProcessingProducts()
  } catch (error) {
    chainConfirmRef.value?.setError(error.response?.data?.detail || '加工失败')
  }
}

// ==================== 送检确认 ====================
const sendInspectVisible = ref(false)
const pendingSendInspect = ref(null)
const sendInspectRef = ref(null)

const openSendInspectDialog = (product) => {
  pendingSendInspect.value = {
    form: product,
    data: {
      productName: product.name,
      traceCode: product.trace_code,
      processType: processTypes.find(t => t.value === product.process_type)?.label || '-',
      quantity: `${product.quantity} ${product.unit || '件'}`
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

// ==================== 数据获取 ====================
// 获取待加工产品列表
const fetchPendingProducts = async () => {
  try {
    loading.value = true
    const data = await processorApi.getPendingProducts()
    pendingProducts.value = data
  } catch (error) {
    ElMessage.error('获取待加工产品列表失败')
  } finally {
    loading.value = false
  }
}

// 获取加工中产品列表
const fetchProcessingProducts = async () => {
  try {
    loading.value = true
    const data = await processorApi.getProcessingProducts()
    processingProducts.value = data
  } catch (error) {
    ElMessage.error('获取加工中产品列表失败')
  } finally {
    loading.value = false
  }
}

// 获取已送检产品列表
const fetchSentProducts = async () => {
  try {
    loading.value = true
    const data = await processorApi.getSentProducts()
    sentProducts.value = data
  } catch (error) {
    ElMessage.error('获取已送检产品列表失败')
  } finally {
    loading.value = false
  }
}

// 页面加载时获取数据
onMounted(() => {
  fetchPendingProducts()
  fetchProcessingProducts()
  fetchSentProducts()
})

// ==================== 查看详情 ====================
const detailDrawerVisible = ref(false)
const detailProduct = ref(null)
const detailRecords = ref([])
const detailLoading = ref(false)

const viewDetail = async (product) => {
  detailProduct.value = product
  detailDrawerVisible.value = true

  // 获取产品流转记录
  try {
    detailLoading.value = true
    const records = await processorApi.getProductRecords(product.id)
    detailRecords.value = records
  } catch (error) {
    console.error('获取记录失败:', error)
    detailRecords.value = []
  } finally {
    detailLoading.value = false
  }
}

// 查看链上数据
const viewChainData = (product) => {
  verifyTraceCode.value = product.trace_code
  chainVerifyVisible.value = true
}

// 打开链上验证
const openChainVerify = (record) => {
  verifyTxHash.value = record?.tx_hash || ''
  verifyTraceCode.value = detailProduct.value.trace_code
  verifyBlockNumber.value = record?.block_number || null
  chainVerifyVisible.value = true
}

// 送检功能
const onSendInspectConfirm = async () => {
  if (!pendingSendInspect.value) return

  sendInspectRef.value?.setLoading()

  try {
    // 调用送检API
    const result = await processorApi.sendInspectProduct(
      pendingSendInspect.value.form.id,
      {
        product_id: pendingSendInspect.value.form.id,
        inspection_type: 'quality',
        notes: '加工完成，请求质检'
      }
    )

    sendInspectRef.value?.setSuccess(result.trace_code, result.block_number, result.tx_hash)

    ElMessage.success('送检成功，产品已进入质检环节')

    // 刷新列表
    await fetchProcessingProducts()
    await fetchSentProducts()
  } catch (error) {
    sendInspectRef.value?.setError(error.response?.data?.detail || '送检失败')
  }
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
  const actionLower = action?.toLowerCase() || ''
  const map = {
    create: '创建记录',
    amend: '修正信息',
    harvest: '采收上链',
    receive: '接收原料',
    process: '加工处理',
    send_inspect: '送检',
    inspect: '质量检测',
    stock: '入库登记',
    reject: '退回处理',
    terminate: '终止链条'
  }
  return map[actionLower] || action
}

// 翻译备注中的加工类型（向后兼容旧数据）
const translateRemark = (remark) => {
  if (!remark) return remark

  const typeMap = {
    'wash': '清洗分拣',
    'cut': '切割加工',
    'juice': '榨汁加工',
    'pack': '包装封装',
    'freeze': '冷冻处理',
    'dry': '烘干处理'
  }

  const inspectionMap = {
    'quality': '质量检测',
    'safety': '安全检测',
    'appearance': '外观检测'
  }

  // 替换 "加工: juice → 草莓酱" 为 "加工: 榨汁加工 → 草莓酱"
  let result = remark.replace(/加工:\s*(\w+)\s*→/g, (match, type) => {
    const chineseType = typeMap[type] || type
    return `加工: ${chineseType} →`
  })

  // 替换 "送检: quality" 为 "送检: 质量检测"
  result = result.replace(/送检:\s*(\w+)/g, (match, type) => {
    const chineseType = inspectionMap[type] || type
    return `送检: ${chineseType}`
  })

  // 替换 "开始检测: quality" 为 "开始检测: 质量检测"
  result = result.replace(/开始检测:\s*(\w+)/g, (match, type) => {
    const chineseType = inspectionMap[type] || type
    return `开始检测: ${chineseType}`
  })

  // 移除接收原料备注中的 "质量等级A/B/C" 信息（因为那时还未质检）
  result = result.replace(/接收原料，质量等级：[ABC]/g, '接收原料')

  return result
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

      <el-table :data="currentList" stripe v-loading="loading">
        <el-table-column prop="name" label="产品" min-width="160">
          <template #default="{ row }">
            <div class="product-info">
              <el-avatar :size="36" shape="square" style="background: #1890ff">
                {{ row.name.charAt(0) }}
              </el-avatar>
              <div class="info">
                <span class="name">{{ row.name }}</span>
                <span class="code">{{ row.trace_code }}</span>
                <span v-if="row.process_type" class="raw-material">
                  加工: {{ processTypes.find(t => t.value === row.process_type)?.label }}
                </span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="加工类型" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.process_type" type="primary" effect="plain">
              {{ processTypes.find(t => t.value === row.process_type)?.label || '-' }}
            </el-tag>
            <span v-else class="text-muted">未加工</span>
          </template>
        </el-table-column>
        <el-table-column label="成品数量" width="100">
          <template #default="{ row }">
            <span v-if="row.quantity" class="quantity">
              {{ row.quantity }} {{ row.unit || '件' }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusMap[row.status]?.type">
              {{ statusMap[row.status]?.label }}
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
              v-if="row.status === 'pending'"
              type="success"
              text
              size="small"
              @click="openProcessDialog(row)"
            >
              <el-icon><SetUp /></el-icon>
              开始加工
            </el-button>

            <!-- 加工中：送检 -->
            <el-button
              v-if="row.status === 'processing'"
              type="success"
              text
              size="small"
              @click="openSendInspectDialog(row)"
            >
              <el-icon><Van /></el-icon>
              送检
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态 -->
      <el-empty v-if="currentList.length === 0" description="暂无记录" />
    </el-card>

    <!-- 新建加工对话框 -->
    <el-dialog v-model="processDialogVisible" title="新建加工记录" width="500px">
      <el-form :model="processForm" label-width="100px">
        <el-form-item label="原材料">
          <span>{{ processForm.productName }}</span>
          <span class="form-hint">({{ processForm.traceCode }})</span>
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
          <el-input
            v-model="processForm.outputProduct"
            placeholder="请输入成品名称"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="预计产量" required>
          <el-input-number v-model="processForm.outputQuantity" :min="1" style="width: 200px" />
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
      title="产品详情"
      size="500px"
    >
      <template v-if="detailProduct">
        <!-- 溯源码 -->
        <div class="detail-section">
          <TraceCode :code="detailProduct.trace_code" size="large" />
        </div>

        <!-- 基本信息 -->
        <div class="detail-section">
          <h4>基本信息</h4>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="产品名称">
              {{ detailProduct.name }}
            </el-descriptions-item>
            <el-descriptions-item label="溯源码">
              {{ detailProduct.trace_code }}
            </el-descriptions-item>
            <el-descriptions-item label="数量">
              {{ detailProduct.quantity }} {{ detailProduct.unit || 'kg' }}
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusMap[detailProduct.status]?.type">
                {{ statusMap[detailProduct.status]?.label }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item v-if="detailProduct.process_type" label="加工类型">
              {{ processTypes.find(t => t.value === detailProduct.process_type)?.label || '-' }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 链上记录 -->
        <div class="detail-section">
          <div class="section-header">
            <h4>
              链上记录
              <el-tag v-if="detailRecords.some(r => r.action === 'amend')" type="warning" size="small">
                有修正记录
              </el-tag>
            </h4>
            <el-button
              v-if="detailRecords.length > 0"
              type="primary"
              link
              size="small"
              @click="viewChainData(detailProduct)"
            >
              <el-icon><Connection /></el-icon>
              查看链信息
            </el-button>
          </div>
          <div v-if="detailLoading" class="loading-records">
            <el-icon class="is-loading"><Loading /></el-icon>
            加载中...
          </div>
          <el-timeline v-else>
            <el-timeline-item
              v-for="record in detailRecords"
              :key="record.id"
              :timestamp="formatTime(record.timestamp || record.created_at)"
              :type="record.action === 'amend' ? 'warning' : 'primary'"
            >
              <div class="record-item">
                <div class="record-header">
                  <span class="action">{{ getActionLabel(record.action) }}</span>
                  <span class="operator">{{ record.operator_name }}</span>
                </div>
                <div v-if="record.remark" class="record-remark">
                  {{ translateRemark(record.remark) }}
                </div>
                <div v-if="record.tx_hash" class="chain-info-box" @click="openChainVerify(record)">
                  <div class="chain-badge">
                    <el-icon><Connection /></el-icon>
                    <span>FISCO BCOS</span>
                  </div>
                  <div class="chain-details">
                    <div class="chain-row">
                      <span class="chain-label">交易哈希</span>
                      <span class="chain-value">{{ record.tx_hash.slice(0, 10) }}...{{ record.tx_hash.slice(-8) }}</span>
                    </div>
                    <div v-if="record.block_number" class="chain-row">
                      <span class="chain-label">区块高度</span>
                      <span class="chain-value">#{{ record.block_number }}</span>
                    </div>
                  </div>
                  <div class="verify-btn">
                    <el-icon><View /></el-icon>
                    <span>验证</span>
                  </div>
                </div>
              </div>
            </el-timeline-item>
          </el-timeline>
        </div>
      </template>
    </el-drawer>

    <!-- 链上数据弹窗 -->
    <ChainVerify
      v-model:visible="chainVerifyVisible"
      :trace-code="verifyTraceCode"
      :tx-hash="verifyTxHash"
      :block-number="verifyBlockNumber"
    />
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

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-header h4 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
}

.loading-records {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 40px 0;
  color: var(--text-muted);
}

.record-remark {
  margin-top: 4px;
  font-size: 13px;
  color: var(--text-secondary);
}

/* 链上信息卡片 */
.chain-info-box {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
  padding: 10px 14px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.08), rgba(118, 75, 162, 0.08));
  border: 1px solid rgba(102, 126, 234, 0.2);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.chain-info-box:hover {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.15), rgba(118, 75, 162, 0.15));
  border-color: rgba(102, 126, 234, 0.4);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
}

.chain-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.chain-badge .el-icon {
  font-size: 12px;
}

.chain-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.chain-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.chain-label {
  color: var(--text-muted);
}

.chain-value {
  color: #667eea;
  font-family: monospace;
  font-weight: 500;
}

.verify-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  background: rgba(102, 126, 234, 0.1);
  color: #667eea;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.2s;
}

.chain-info-box:hover .verify-btn {
  background: #667eea;
  color: white;
}

.form-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-left: 8px;
}
</style>
