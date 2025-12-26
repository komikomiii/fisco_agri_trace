<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useProductStore } from '../../store/product'
import { useUserStore } from '../../store/user'
import ChainConfirm from '../../components/common/ChainConfirm.vue'
import TraceCode from '../../components/common/TraceCode.vue'

const productStore = useProductStore()
const userStore = useUserStore()

// Tab 切换
const activeTab = ref('available')

// 可售产品（已入库的产品）
const availableProducts = computed(() => {
  return productStore.productChains.filter(c =>
    c.status === 'on_chain' &&
    c.records.some(r => r.action === 'stock') &&
    !c.records.some(r => r.action === 'sell')
  )
})

// 已售产品
const soldProducts = computed(() => {
  return productStore.productChains.filter(c =>
    c.status === 'on_chain' &&
    c.records.some(r => r.action === 'sell')
  )
})

// 当前显示的列表
const currentList = computed(() => {
  if (activeTab.value === 'available') return availableProducts.value
  if (activeTab.value === 'sold') return soldProducts.value
  return []
})

// 状态映射
const saleStatusMap = {
  available: { label: '可售', type: 'success' },
  sold: { label: '已售', type: 'info' }
}

// ==================== 销售登记 ====================
const saleDialogVisible = ref(false)
const currentChain = ref(null)
const saleForm = ref({
  quantity: 0,
  totalAmount: 0,
  customer: '',
  notes: ''
})

const openSaleDialog = (chain) => {
  currentChain.value = chain
  const stockInfo = getStockInfo(chain)
  saleForm.value = {
    quantity: stockInfo.stockQuantity || 0,
    totalAmount: (stockInfo.stockQuantity || 0) * (stockInfo.price || 0),
    customer: '',
    notes: ''
  }
  saleDialogVisible.value = true
}

// 计算总金额
const updateTotalAmount = () => {
  if (currentChain.value) {
    const stockInfo = getStockInfo(currentChain.value)
    saleForm.value.totalAmount = saleForm.value.quantity * (stockInfo.price || 0)
  }
}

// ==================== 销售上链确认 ====================
const chainConfirmVisible = ref(false)
const chainConfirmRef = ref(null)

const confirmSale = () => {
  if (!saleForm.value.quantity || saleForm.value.quantity <= 0) {
    ElMessage.warning('请填写销售数量')
    return
  }

  saleDialogVisible.value = false
  chainConfirmVisible.value = true
}

const getSalePreviewData = () => {
  if (!currentChain.value) return {}
  const processRecord = currentChain.value.records.find(r => r.action === 'process')
  const stockInfo = getStockInfo(currentChain.value)
  return {
    productName: processRecord?.data?.outputProduct || currentChain.value.productName,
    traceCode: currentChain.value.traceCode,
    quantity: `${saleForm.value.quantity} 件`,
    unitPrice: `¥${(stockInfo.price || 0).toFixed(2)}`,
    totalAmount: `¥${saleForm.value.totalAmount.toFixed(2)}`,
    customer: saleForm.value.customer || '散客'
  }
}

const onSaleConfirm = async () => {
  if (!currentChain.value) return

  chainConfirmRef.value?.setLoading()

  try {
    const result = await productStore.addRecord(currentChain.value.id, {
      stage: 'seller',
      action: 'sell',
      data: {
        quantity: saleForm.value.quantity,
        totalAmount: saleForm.value.totalAmount,
        customer: saleForm.value.customer || '散客',
        notes: saleForm.value.notes,
        saleTime: new Date().toISOString()
      },
      operator: {
        id: userStore.user?.id || 4,
        name: userStore.user?.name || '优鲜超市',
        role: 'seller'
      }
    })

    if (result) {
      // 更新产品链阶段为已售
      currentChain.value.currentStage = 'sold'
      chainConfirmRef.value?.setSuccess(result.txHash, result.blockNumber)
      ElMessage.success('销售记录已上链，消费者可通过溯源码查询完整信息')
    } else {
      chainConfirmRef.value?.setError('销售记录上链失败，请重试')
    }
  } catch (error) {
    chainConfirmRef.value?.setError(error.message || '销售记录上链失败')
  }
}

// ==================== 查看详情 ====================
const detailDrawerVisible = ref(false)
const detailChain = ref(null)

const viewDetail = (chain) => {
  detailChain.value = chain
  detailDrawerVisible.value = true
}

// 获取加工信息
const getProcessInfo = (chain) => {
  const processRecord = chain.records.find(r => r.action === 'process')
  return processRecord?.data || {}
}

// 获取入库信息
const getStockInfo = (chain) => {
  const stockRecord = chain.records.find(r => r.action === 'stock')
  return stockRecord?.data || {}
}

// 获取销售信息
const getSaleInfo = (chain) => {
  const saleRecord = chain.records.find(r => r.action === 'sell')
  return saleRecord?.data || {}
}

// 获取检测信息
const getInspectInfo = (chain) => {
  const inspectRecord = chain.records.find(r => r.action === 'inspect')
  return inspectRecord?.data || {}
}

// 判断产品状态
const getProductStatus = (chain) => {
  if (chain.records.some(r => r.action === 'sell')) return 'sold'
  return 'available'
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
    start_inspect: '开始检测',
    inspect: '检测完成',
    reject: '退回处理',
    terminate: '终止链条',
    stock: '入库登记',
    sell: '销售出库'
  }
  return map[action] || action
}

// 统计信息
const stats = computed(() => {
  const available = availableProducts.value.length
  const sold = soldProducts.value.length

  // 计算总销售额
  let totalSales = 0
  soldProducts.value.forEach(chain => {
    const saleInfo = getSaleInfo(chain)
    totalSales += saleInfo.totalAmount || 0
  })

  // 计算总库存
  let totalStock = 0
  availableProducts.value.forEach(chain => {
    const stockInfo = getStockInfo(chain)
    totalStock += stockInfo.stockQuantity || 0
  })

  return { available, sold, totalSales, totalStock }
})
</script>

<template>
  <div class="sales-container">
    <!-- 统计卡片 -->
    <div class="stats-row">
      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon available">
            <el-icon><ShoppingBag /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.available }}</span>
            <span class="stat-label">可售产品</span>
          </div>
        </div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon stock">
            <el-icon><Box /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.totalStock }}</span>
            <span class="stat-label">库存数量</span>
          </div>
        </div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon sold">
            <el-icon><ShoppingCart /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.sold }}</span>
            <span class="stat-label">已售产品</span>
          </div>
        </div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon amount">
            <el-icon><Money /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-value">¥{{ stats.totalSales.toFixed(2) }}</span>
            <span class="stat-label">销售总额</span>
          </div>
        </div>
      </el-card>
    </div>

    <el-card>
      <template #header>
        <div class="card-header">
          <span class="title">
            <el-icon><ShoppingCart /></el-icon>
            销售管理
          </span>
        </div>
      </template>

      <!-- Tab 切换 -->
      <el-tabs v-model="activeTab" class="sales-tabs">
        <el-tab-pane name="available">
          <template #label>
            <span>
              可售
              <el-badge :value="availableProducts.length" :max="99" class="tab-badge" type="success" />
            </span>
          </template>
        </el-tab-pane>
        <el-tab-pane name="sold">
          <template #label>
            <span>
              已售
              <el-badge :value="soldProducts.length" :max="99" class="tab-badge" />
            </span>
          </template>
        </el-tab-pane>
      </el-tabs>

      <el-table :data="currentList" stripe>
        <el-table-column label="产品" min-width="160">
          <template #default="{ row }">
            <div class="product-info">
              <el-avatar :size="36" shape="square" style="background: #52c41a">
                {{ (getProcessInfo(row).outputProduct || row.productName).charAt(0) }}
              </el-avatar>
              <div class="info">
                <span class="name">{{ getProcessInfo(row).outputProduct || row.productName }}</span>
                <span class="code">{{ row.traceCode }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="库存" width="100" v-if="activeTab === 'available'">
          <template #default="{ row }">
            {{ getStockInfo(row).stockQuantity || 0 }} 件
          </template>
        </el-table-column>
        <el-table-column label="单价" width="100">
          <template #default="{ row }">
            ¥{{ (getStockInfo(row).price || 0).toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column label="销售数量" width="100" v-if="activeTab === 'sold'">
          <template #default="{ row }">
            {{ getSaleInfo(row).quantity || 0 }} 件
          </template>
        </el-table-column>
        <el-table-column label="销售金额" width="120" v-if="activeTab === 'sold'">
          <template #default="{ row }">
            <span class="amount">¥{{ (getSaleInfo(row).totalAmount || 0).toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="客户" width="100" v-if="activeTab === 'sold'">
          <template #default="{ row }">
            {{ getSaleInfo(row).customer || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="销售时间" width="160" v-if="activeTab === 'sold'">
          <template #default="{ row }">
            {{ formatTime(getSaleInfo(row).saleTime) }}
          </template>
        </el-table-column>
        <el-table-column label="位置" width="120" v-if="activeTab === 'available'">
          <template #default="{ row }">
            {{ getStockInfo(row).location || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="saleStatusMap[getProductStatus(row)]?.type">
              {{ saleStatusMap[getProductStatus(row)]?.label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" text size="small" @click="viewDetail(row)">
              溯源信息
            </el-button>

            <!-- 可售：销售登记 -->
            <el-button
              v-if="activeTab === 'available'"
              type="success"
              text
              size="small"
              @click="openSaleDialog(row)"
            >
              <el-icon><ShoppingCart /></el-icon>
              销售
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态 -->
      <el-empty v-if="currentList.length === 0" description="暂无记录" />
    </el-card>

    <!-- 销售登记对话框 -->
    <el-dialog v-model="saleDialogVisible" title="销售登记" width="500px">
      <el-form :model="saleForm" label-width="100px">
        <el-form-item label="销售数量" required>
          <el-input-number
            v-model="saleForm.quantity"
            :min="1"
            :max="currentChain ? getStockInfo(currentChain).stockQuantity : 999"
            style="width: 200px"
            @change="updateTotalAmount"
          />
          <span style="margin-left: 10px">件</span>
        </el-form-item>
        <el-form-item label="销售总额">
          <div class="total-amount">¥{{ saleForm.totalAmount.toFixed(2) }}</div>
        </el-form-item>
        <el-form-item label="客户信息">
          <el-input v-model="saleForm.customer" placeholder="请输入客户名称（选填，默认为散客）" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="saleForm.notes"
            type="textarea"
            :rows="2"
            placeholder="可选填写备注信息"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="saleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmSale">
          <el-icon><Connection /></el-icon>
          确认上链
        </el-button>
      </template>
    </el-dialog>

    <!-- 上链确认 -->
    <ChainConfirm
      ref="chainConfirmRef"
      v-model:visible="chainConfirmVisible"
      title="确认销售记录上链"
      :data="getSalePreviewData()"
      :data-labels="{
        productName: '产品名称',
        traceCode: '溯源码',
        quantity: '销售数量',
        unitPrice: '单价',
        totalAmount: '销售总额',
        customer: '客户'
      }"
      @confirm="onSaleConfirm"
    >
      <template #extra>
        <div class="sale-tip">
          <el-icon><InfoFilled /></el-icon>
          销售记录上链后，消费者可通过溯源码查询完整供应链信息
        </div>
      </template>
    </ChainConfirm>

    <!-- 详情抽屉 -->
    <el-drawer
      v-model="detailDrawerVisible"
      title="溯源信息"
      size="550px"
    >
      <template v-if="detailChain">
        <!-- 溯源码 -->
        <div class="detail-section">
          <TraceCode :trace-code="detailChain.traceCode" size="large" />
        </div>

        <!-- 产品信息 -->
        <div class="detail-section">
          <h4>产品信息</h4>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="产品名称">
              {{ getProcessInfo(detailChain).outputProduct || detailChain.productName }}
            </el-descriptions-item>
            <el-descriptions-item label="原材料">
              {{ detailChain.productName }}
            </el-descriptions-item>
            <el-descriptions-item label="产地">
              {{ productStore.getMergedData(detailChain)?.origin || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="加工方式">
              {{ getProcessInfo(detailChain).processType || '-' }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 检测信息 -->
        <div class="detail-section">
          <h4>检测信息</h4>
          <div class="inspect-result pass">
            <el-icon><CircleCheck /></el-icon>
            <span>检测合格</span>
          </div>
          <el-table
            v-if="getInspectInfo(detailChain).items"
            :data="getInspectInfo(detailChain).items"
            border
            size="small"
          >
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
        </div>

        <!-- 销售信息 -->
        <div v-if="getSaleInfo(detailChain).quantity" class="detail-section">
          <h4>销售信息</h4>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="销售数量">
              {{ getSaleInfo(detailChain).quantity }} 件
            </el-descriptions-item>
            <el-descriptions-item label="销售金额">
              ¥{{ (getSaleInfo(detailChain).totalAmount || 0).toFixed(2) }}
            </el-descriptions-item>
            <el-descriptions-item label="客户">
              {{ getSaleInfo(detailChain).customer || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="销售时间">
              {{ formatTime(getSaleInfo(detailChain).saleTime) }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 链上记录 -->
        <div class="detail-section">
          <h4>供应链全程记录</h4>
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
              </div>
            </el-timeline-item>
          </el-timeline>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
.sales-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 统计卡片 */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stat-card {
  padding: 0;
}

.stat-card :deep(.el-card__body) {
  padding: 20px;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.stat-icon.available {
  background: rgba(82, 196, 26, 0.1);
  color: #52c41a;
}

.stat-icon.stock {
  background: rgba(24, 144, 255, 0.1);
  color: #1890ff;
}

.stat-icon.sold {
  background: rgba(250, 140, 22, 0.1);
  color: #fa8c16;
}

.stat-icon.amount {
  background: rgba(114, 46, 209, 0.1);
  color: #722ed1;
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
}

.stat-label {
  font-size: 13px;
  color: var(--text-secondary);
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

.sales-tabs {
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

.amount {
  font-weight: 600;
  color: #722ed1;
}

.total-amount {
  font-size: 24px;
  font-weight: 600;
  color: #722ed1;
}

.sale-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding: 12px;
  background: #f6ffed;
  border-radius: 8px;
  font-size: 13px;
  color: #389e0d;
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

.inspect-result {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 500;
}

.inspect-result.pass {
  background: #f6ffed;
  color: #389e0d;
}

.inspect-result .el-icon {
  font-size: 18px;
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
