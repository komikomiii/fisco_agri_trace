<script setup>
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useProductStore } from '../../store/product'
import { useUserStore } from '../../store/user'
import { useNotificationStore } from '../../store/notification'
import ChainConfirm from '../../components/common/ChainConfirm.vue'
import TraceCode from '../../components/common/TraceCode.vue'

const productStore = useProductStore()
const userStore = useUserStore()
const notificationStore = useNotificationStore()

// 采收记录（基于已上链的产品生成）
const harvestRecords = ref([
  {
    id: 1,
    chainId: 1,
    traceCode: 'TRACE-20241226-001',
    productName: '有机番茄',
    batchNo: 'H20241201001',
    quantity: 150,
    harvestDate: '2024-12-01',
    operator: '张三农场',
    status: 'shipped',
    shippedAt: '2024-12-01T14:00:00Z'
  },
  {
    id: 2,
    chainId: 2,
    traceCode: 'TRACE-20241226-002',
    productName: '红富士苹果',
    batchNo: 'H20241130002',
    quantity: 500,
    harvestDate: '2024-11-30',
    operator: '张三农场',
    status: 'shipped',
    shippedAt: '2024-11-30T16:00:00Z'
  }
])

// Tab 切换
const activeTab = ref('pending')

// 可采收的产品（已上链且在原料商阶段）
const harvestableProducts = computed(() => {
  return productStore.onChainProducts.filter(c => c.currentStage === 'producer')
})

// 筛选记录
const filteredRecords = computed(() => {
  if (activeTab.value === 'pending') {
    return harvestRecords.value.filter(r => r.status === 'pending')
  } else if (activeTab.value === 'shipped') {
    return harvestRecords.value.filter(r => r.status === 'shipped')
  }
  return harvestRecords.value
})

// 状态映射
const statusMap = {
  pending: { label: '待出库', type: 'warning' },
  shipped: { label: '已出库', type: 'success' }
}

// ==================== 采收登记 ====================
const dialogVisible = ref(false)
const harvestForm = ref({
  chainId: null,
  quantity: 0,
  harvestDate: new Date().toISOString().split('T')[0],
  notes: ''
})

const openHarvestDialog = () => {
  harvestForm.value = {
    chainId: null,
    quantity: 0,
    harvestDate: new Date().toISOString().split('T')[0],
    notes: ''
  }
  dialogVisible.value = true
}

const handleHarvestSubmit = () => {
  if (!harvestForm.value.chainId || harvestForm.value.quantity <= 0) {
    ElMessage.warning('请填写完整信息')
    return
  }

  const chain = productStore.productChains.find(c => c.id === harvestForm.value.chainId)
  if (!chain) {
    ElMessage.error('未找到对应产品')
    return
  }

  // 生成批次号
  const batchNo = `H${new Date().toISOString().slice(0, 10).replace(/-/g, '')}${String(harvestRecords.value.length + 1).padStart(3, '0')}`

  // 添加采收记录
  harvestRecords.value.unshift({
    id: Date.now(),
    chainId: chain.id,
    traceCode: chain.traceCode,
    productName: chain.productName,
    batchNo,
    quantity: harvestForm.value.quantity,
    harvestDate: harvestForm.value.harvestDate,
    notes: harvestForm.value.notes,
    operator: userStore.user?.name || '张三农场',
    status: 'pending'
  })

  ElMessage.success('采收登记成功，批次号：' + batchNo)
  dialogVisible.value = false
}

// ==================== 出库确认（上链） ====================
const chainConfirmVisible = ref(false)
const pendingShipment = ref(null)
const chainConfirmRef = ref(null)

const handleShip = (record) => {
  const chain = productStore.productChains.find(c => c.traceCode === record.traceCode)
  if (!chain) {
    ElMessage.error('未找到对应产品链')
    return
  }

  pendingShipment.value = {
    record,
    chain,
    data: {
      batchNo: record.batchNo,
      productName: record.productName,
      quantity: `${record.quantity} kg`,
      harvestDate: record.harvestDate,
      notes: record.notes || '无'
    },
    labels: {
      batchNo: '批次号',
      productName: '产品名称',
      quantity: '采收数量',
      harvestDate: '采收日期',
      notes: '备注'
    }
  }
  chainConfirmVisible.value = true
}

const onShipConfirm = async () => {
  if (!pendingShipment.value) return

  chainConfirmRef.value?.setLoading()

  try {
    // 添加采收出库记录到产品链
    const result = await productStore.addRecord(pendingShipment.value.chain.id, {
      stage: 'producer',
      action: 'harvest',
      data: {
        batchNo: pendingShipment.value.record.batchNo,
        quantity: pendingShipment.value.record.quantity,
        harvestDate: pendingShipment.value.record.harvestDate,
        notes: pendingShipment.value.record.notes
      },
      operator: {
        id: userStore.user?.id || 1,
        name: userStore.user?.name || '张三农场',
        role: 'producer'
      }
    })

    if (result) {
      // 更新采收记录状态
      const record = harvestRecords.value.find(r => r.id === pendingShipment.value.record.id)
      if (record) {
        record.status = 'shipped'
        record.shippedAt = new Date().toISOString()
      }

      chainConfirmRef.value?.setSuccess(result.txHash, result.blockNumber)

      // 发送通知给加工商
      notificationStore.addNotification({
        type: notificationStore.NOTIFICATION_TYPES.PENDING,
        title: '新原料待接收',
        content: `来自${userStore.user?.name || '张三农场'}的${pendingShipment.value.record.productName} ${pendingShipment.value.record.quantity}kg 已到达，请尽快处理。`,
        relatedTraceCode: pendingShipment.value.chain.traceCode
      })

      ElMessage.success('出库成功，已通知加工商')
    } else {
      chainConfirmRef.value?.setError('出库失败，请重试')
    }
  } catch (error) {
    chainConfirmRef.value?.setError(error.message || '出库失败')
  }
}

// ==================== 查看详情 ====================
const detailDrawerVisible = ref(false)
const detailRecord = ref(null)

const viewDetail = (record) => {
  detailRecord.value = record
  detailDrawerVisible.value = true
}

// 获取产品链详情
const getChainForRecord = (record) => {
  return productStore.productChains.find(c => c.traceCode === record.traceCode)
}

// 取消采收
const cancelHarvest = (record) => {
  if (record.status !== 'pending') {
    ElMessage.warning('只能取消待出库的记录')
    return
  }

  ElMessageBox.confirm('确定要取消这条采收记录吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    const index = harvestRecords.value.findIndex(r => r.id === record.id)
    if (index > -1) {
      harvestRecords.value.splice(index, 1)
      ElMessage.success('已取消')
    }
  })
}

// 格式化时间
const formatTime = (timestamp) => {
  if (!timestamp) return '-'
  return new Date(timestamp).toLocaleString('zh-CN')
}
</script>

<template>
  <div class="harvest-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span class="title">
            <el-icon><Calendar /></el-icon>
            采收管理
          </span>
          <el-button type="primary" :icon="Plus" @click="openHarvestDialog">
            采收登记
          </el-button>
        </div>
      </template>

      <!-- Tab 切换 -->
      <el-tabs v-model="activeTab" class="harvest-tabs">
        <el-tab-pane name="pending">
          <template #label>
            <span>
              待出库
              <el-badge
                :value="harvestRecords.filter(r => r.status === 'pending').length"
                :max="99"
                class="tab-badge"
              />
            </span>
          </template>
        </el-tab-pane>
        <el-tab-pane name="shipped">
          <template #label>
            <span>
              已出库
              <el-badge
                :value="harvestRecords.filter(r => r.status === 'shipped').length"
                :max="99"
                class="tab-badge"
                type="success"
              />
            </span>
          </template>
        </el-tab-pane>
        <el-tab-pane label="全部" name="all" />
      </el-tabs>

      <el-table :data="filteredRecords" stripe>
        <el-table-column prop="batchNo" label="批次号" width="160">
          <template #default="{ row }">
            <el-tag effect="plain" type="info">{{ row.batchNo }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="productName" label="产品名称" min-width="120">
          <template #default="{ row }">
            <div class="product-info">
              <span class="name">{{ row.productName }}</span>
              <span v-if="row.traceCode" class="trace-code">{{ row.traceCode }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="quantity" label="采收数量" width="120">
          <template #default="{ row }">
            <span class="quantity">{{ row.quantity }} kg</span>
          </template>
        </el-table-column>
        <el-table-column prop="harvestDate" label="采收日期" width="120" />
        <el-table-column prop="operator" label="操作人" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusMap[row.status]?.type">
              {{ statusMap[row.status]?.label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" text size="small" @click="viewDetail(row)">
              查看详情
            </el-button>
            <template v-if="row.status === 'pending'">
              <el-button type="success" text size="small" @click="handleShip(row)">
                <el-icon><Van /></el-icon>
                确认出库
              </el-button>
              <el-button type="danger" text size="small" @click="cancelHarvest(row)">
                取消
              </el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态 -->
      <el-empty
        v-if="filteredRecords.length === 0"
        description="暂无采收记录"
      />
    </el-card>

    <!-- 采收登记对话框 -->
    <el-dialog v-model="dialogVisible" title="采收登记" width="500px">
      <el-form :model="harvestForm" label-width="100px">
        <el-form-item label="选择产品" required>
          <el-select
            v-model="harvestForm.chainId"
            placeholder="请选择已上链的产品"
            style="width: 100%"
          >
            <el-option
              v-for="chain in harvestableProducts"
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
          <div v-if="harvestableProducts.length === 0" class="no-products-tip">
            暂无可采收的产品，请先在原料管理中添加产品并上链
          </div>
        </el-form-item>
        <el-form-item label="采收数量" required>
          <el-input-number
            v-model="harvestForm.quantity"
            :min="0"
            style="width: 200px"
          />
          <span style="margin-left: 10px">kg</span>
        </el-form-item>
        <el-form-item label="采收日期">
          <el-date-picker
            v-model="harvestForm.harvestDate"
            type="date"
            placeholder="选择日期"
            style="width: 100%"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="harvestForm.notes"
            type="textarea"
            :rows="3"
            placeholder="可选填写备注信息，如采收天气、质量等"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleHarvestSubmit">确认登记</el-button>
      </template>
    </el-dialog>

    <!-- 出库上链确认 -->
    <ChainConfirm
      ref="chainConfirmRef"
      v-model:visible="chainConfirmVisible"
      title="确认出库上链"
      :data="pendingShipment?.data"
      :data-labels="pendingShipment?.labels"
      @confirm="onShipConfirm"
    >
      <template #extra>
        <div v-if="pendingShipment?.chain" class="shipment-info">
          <div class="info-row">
            <span class="label">分配方式：</span>
            <el-tag v-if="pendingShipment.chain.distribution?.type === 'pool'" type="info">
              公共池（加工商自选）
            </el-tag>
            <el-tag v-else type="warning">
              指定发送给：{{ pendingShipment.chain.distribution?.assignedTo?.name }}
            </el-tag>
          </div>
          <div class="info-tip">
            <el-icon><InfoFilled /></el-icon>
            出库后将通知加工商接收原料
          </div>
        </div>
      </template>
    </ChainConfirm>

    <!-- 详情抽屉 -->
    <el-drawer
      v-model="detailDrawerVisible"
      title="采收记录详情"
      size="450px"
    >
      <template v-if="detailRecord">
        <!-- 溯源码 -->
        <div v-if="detailRecord.traceCode" class="detail-section">
          <TraceCode :trace-code="detailRecord.traceCode" />
        </div>

        <!-- 采收信息 -->
        <div class="detail-section">
          <h4>采收信息</h4>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="批次号">
              <el-tag effect="plain" type="info">{{ detailRecord.batchNo }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="产品名称">
              {{ detailRecord.productName }}
            </el-descriptions-item>
            <el-descriptions-item label="采收数量">
              {{ detailRecord.quantity }} kg
            </el-descriptions-item>
            <el-descriptions-item label="采收日期">
              {{ detailRecord.harvestDate }}
            </el-descriptions-item>
            <el-descriptions-item label="操作人">
              {{ detailRecord.operator }}
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusMap[detailRecord.status]?.type">
                {{ statusMap[detailRecord.status]?.label }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item v-if="detailRecord.shippedAt" label="出库时间">
              {{ formatTime(detailRecord.shippedAt) }}
            </el-descriptions-item>
            <el-descriptions-item v-if="detailRecord.notes" label="备注">
              {{ detailRecord.notes }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 产品链信息 -->
        <div v-if="getChainForRecord(detailRecord)" class="detail-section">
          <h4>产品链信息</h4>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="产地">
              {{ productStore.getMergedData(getChainForRecord(detailRecord))?.origin || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="种植日期">
              {{ productStore.getMergedData(getChainForRecord(detailRecord))?.plantDate || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="当前阶段">
              {{ getChainForRecord(detailRecord)?.currentStage === 'producer' ? '原料商' : '已流转' }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
.harvest-container {
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

.harvest-tabs {
  margin-bottom: 16px;
}

.tab-badge {
  margin-left: 6px;
}

.product-info {
  display: flex;
  flex-direction: column;
}

.product-info .name {
  font-weight: 500;
}

.product-info .trace-code {
  font-size: 12px;
  color: var(--text-muted);
  font-family: monospace;
}

.quantity {
  font-weight: 500;
  color: var(--primary-color);
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

.no-products-tip {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-muted);
}

/* 出库信息样式 */
.shipment-info {
  margin-top: 12px;
  padding: 12px;
  background: var(--bg-color);
  border-radius: 8px;
}

.info-row {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.info-row .label {
  color: var(--text-secondary);
  margin-right: 8px;
}

.info-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted);
}

/* 详情抽屉样式 */
.detail-section {
  margin-bottom: 24px;
}

.detail-section h4 {
  font-size: 14px;
  color: var(--text-primary);
  margin-bottom: 12px;
}
</style>
