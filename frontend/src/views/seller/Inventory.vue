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
const activeTab = ref('pending')

// 待入库产品（质检合格，等待入库）
const pendingProducts = computed(() => {
  return productStore.productChains.filter(c =>
    c.status === 'on_chain' &&
    c.currentStage === 'seller' &&
    !c.records.some(r => r.action === 'stock')
  )
})

// 已入库产品
const stockedProducts = computed(() => {
  return productStore.productChains.filter(c =>
    c.status === 'on_chain' &&
    c.records.some(r => r.action === 'stock')
  )
})

// 当前显示的列表
const currentList = computed(() => {
  if (activeTab.value === 'pending') return pendingProducts.value
  if (activeTab.value === 'stocked') return stockedProducts.value
  return []
})

// 状态映射
const inventoryStatusMap = {
  normal: { label: '正常', type: 'success' },
  low: { label: '库存不足', type: 'warning' },
  expired: { label: '临期', type: 'danger' }
}

// ==================== 入库登记 ====================
const stockDialogVisible = ref(false)
const currentChain = ref(null)
const stockForm = ref({
  stockQuantity: 0,
  price: 0,
  location: '',
  shelfLife: ''
})

const openStockDialog = (chain) => {
  currentChain.value = chain
  const processRecord = chain.records.find(r => r.action === 'process')
  stockForm.value = {
    stockQuantity: processRecord?.data?.outputQuantity || 0,
    price: 0,
    location: '',
    shelfLife: ''
  }
  stockDialogVisible.value = true
}

// ==================== 入库上链确认 ====================
const chainConfirmVisible = ref(false)
const chainConfirmRef = ref(null)

const confirmStock = () => {
  if (!stockForm.value.price || !stockForm.value.location) {
    ElMessage.warning('请填写完整信息')
    return
  }

  stockDialogVisible.value = false
  chainConfirmVisible.value = true
}

const getStockPreviewData = () => {
  if (!currentChain.value) return {}
  const processRecord = currentChain.value.records.find(r => r.action === 'process')
  return {
    productName: processRecord?.data?.outputProduct || currentChain.value.productName,
    traceCode: currentChain.value.traceCode,
    stockQuantity: `${stockForm.value.stockQuantity} 件`,
    price: `¥${stockForm.value.price.toFixed(2)}`,
    location: stockForm.value.location
  }
}

const onStockConfirm = async () => {
  if (!currentChain.value) return

  chainConfirmRef.value?.setLoading()

  try {
    const result = await productStore.addRecord(currentChain.value.id, {
      stage: 'seller',
      action: 'stock',
      data: {
        stockQuantity: stockForm.value.stockQuantity,
        price: stockForm.value.price,
        location: stockForm.value.location,
        shelfLife: stockForm.value.shelfLife,
        stockTime: new Date().toISOString()
      },
      operator: {
        id: userStore.user?.id || 4,
        name: userStore.user?.name || '优鲜超市',
        role: 'seller'
      }
    })

    if (result) {
      chainConfirmRef.value?.setSuccess(result.txHash, result.blockNumber)
      ElMessage.success('入库成功，可生成二维码供消费者扫码溯源')
    } else {
      chainConfirmRef.value?.setError('入库失败，请重试')
    }
  } catch (error) {
    chainConfirmRef.value?.setError(error.message || '入库失败')
  }
}

// ==================== 生成二维码 ====================
const qrcodeDialogVisible = ref(false)
const qrcodeChain = ref(null)

const openQRCodeDialog = (chain) => {
  qrcodeChain.value = chain
  qrcodeDialogVisible.value = true
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

// 获取检测信息
const getInspectInfo = (chain) => {
  const inspectRecord = chain.records.find(r => r.action === 'inspect')
  return inspectRecord?.data || {}
}

// 判断库存状态
const getInventoryStatus = (chain) => {
  const stockInfo = getStockInfo(chain)
  if (!stockInfo.stockQuantity) return 'normal'
  if (stockInfo.stockQuantity < 50) return 'low'
  return 'normal'
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
    stock: '入库登记'
  }
  return map[action] || action
}
</script>

<template>
  <div class="inventory-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span class="title">
            <el-icon><GoodsFilled /></el-icon>
            库存管理
          </span>
        </div>
      </template>

      <!-- Tab 切换 -->
      <el-tabs v-model="activeTab" class="inventory-tabs">
        <el-tab-pane name="pending">
          <template #label>
            <span>
              待入库
              <el-badge :value="pendingProducts.length" :max="99" class="tab-badge" />
            </span>
          </template>
        </el-tab-pane>
        <el-tab-pane name="stocked">
          <template #label>
            <span>
              已入库
              <el-badge
                :value="stockedProducts.length"
                :max="99"
                class="tab-badge"
                type="success"
              />
            </span>
          </template>
        </el-tab-pane>
      </el-tabs>

      <!-- 待入库提示 -->
      <div v-if="activeTab === 'pending' && pendingProducts.length > 0" class="pending-tip">
        <el-icon><InfoFilled /></el-icon>
        以下产品已通过质检，请及时完成入库登记
      </div>

      <el-table :data="currentList" stripe>
        <el-table-column label="产品" min-width="160">
          <template #default="{ row }">
            <div class="product-info">
              <el-avatar :size="36" shape="square" style="background: #fa8c16">
                {{ (getProcessInfo(row).outputProduct || row.productName).charAt(0) }}
              </el-avatar>
              <div class="info">
                <span class="name">{{ getProcessInfo(row).outputProduct || row.productName }}</span>
                <span class="code">{{ row.traceCode }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="数量" width="100">
          <template #default="{ row }">
            <span :class="{ 'text-warning': getInventoryStatus(row) === 'low' }">
              {{ getStockInfo(row).stockQuantity || getProcessInfo(row).outputQuantity || 0 }} 件
            </span>
          </template>
        </el-table-column>
        <el-table-column label="单价" width="100" v-if="activeTab === 'stocked'">
          <template #default="{ row }">
            ¥{{ (getStockInfo(row).price || 0).toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column label="位置" width="120" v-if="activeTab === 'stocked'">
          <template #default="{ row }">
            {{ getStockInfo(row).location || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="检测结果" width="100">
          <template #default="{ row }">
            <el-tag type="success">
              <el-icon><CircleCheck /></el-icon>
              合格
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" v-if="activeTab === 'stocked'">
          <template #default="{ row }">
            <el-tag :type="inventoryStatusMap[getInventoryStatus(row)]?.type">
              {{ inventoryStatusMap[getInventoryStatus(row)]?.label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" text size="small" @click="viewDetail(row)">
              溯源信息
            </el-button>

            <!-- 待入库：入库登记 -->
            <el-button
              v-if="activeTab === 'pending'"
              type="success"
              text
              size="small"
              @click="openStockDialog(row)"
            >
              <el-icon><Box /></el-icon>
              入库登记
            </el-button>

            <!-- 已入库：生成二维码 -->
            <el-button
              v-if="activeTab === 'stocked'"
              type="primary"
              text
              size="small"
              @click="openQRCodeDialog(row)"
            >
              <el-icon><Picture /></el-icon>
              二维码
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态 -->
      <el-empty v-if="currentList.length === 0" description="暂无记录" />
    </el-card>

    <!-- 入库登记对话框 -->
    <el-dialog v-model="stockDialogVisible" title="入库登记" width="500px">
      <el-form :model="stockForm" label-width="100px">
        <el-form-item label="入库数量">
          <el-input-number v-model="stockForm.stockQuantity" :min="0" style="width: 200px" />
          <span style="margin-left: 10px">件</span>
        </el-form-item>
        <el-form-item label="销售单价" required>
          <el-input-number v-model="stockForm.price" :min="0" :precision="2" style="width: 200px" />
          <span style="margin-left: 10px">元</span>
        </el-form-item>
        <el-form-item label="存放位置" required>
          <el-input v-model="stockForm.location" placeholder="请输入存放位置，如：A区-3号货架" />
        </el-form-item>
        <el-form-item label="保质期至">
          <el-date-picker
            v-model="stockForm.shelfLife"
            type="date"
            placeholder="选择保质期"
            style="width: 100%"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="stockDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmStock">
          <el-icon><Connection /></el-icon>
          确认上链
        </el-button>
      </template>
    </el-dialog>

    <!-- 上链确认 -->
    <ChainConfirm
      ref="chainConfirmRef"
      v-model:visible="chainConfirmVisible"
      title="确认入库记录上链"
      :data="getStockPreviewData()"
      :data-labels="{
        productName: '产品名称',
        traceCode: '溯源码',
        stockQuantity: '入库数量',
        price: '销售单价',
        location: '存放位置'
      }"
      @confirm="onStockConfirm"
    />

    <!-- 二维码对话框 -->
    <el-dialog v-model="qrcodeDialogVisible" title="溯源二维码" width="400px" center>
      <template v-if="qrcodeChain">
        <div class="qrcode-content">
          <div class="qrcode-placeholder">
            <el-icon :size="120"><Picture /></el-icon>
            <p>二维码预览区域</p>
            <p class="trace-code">{{ qrcodeChain.traceCode }}</p>
          </div>
          <div class="qrcode-info">
            <p><strong>产品：</strong>{{ getProcessInfo(qrcodeChain).outputProduct || qrcodeChain.productName }}</p>
            <p><strong>溯源码：</strong>{{ qrcodeChain.traceCode }}</p>
          </div>
          <div class="qrcode-actions">
            <el-button type="primary">
              <el-icon><Download /></el-icon>
              下载二维码
            </el-button>
            <el-button>
              <el-icon><Printer /></el-icon>
              打印标签
            </el-button>
          </div>
        </div>
      </template>
    </el-dialog>

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

        <!-- 入库信息 -->
        <div v-if="getStockInfo(detailChain).stockQuantity" class="detail-section">
          <h4>入库信息</h4>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="入库数量">
              {{ getStockInfo(detailChain).stockQuantity }} 件
            </el-descriptions-item>
            <el-descriptions-item label="销售单价">
              ¥{{ (getStockInfo(detailChain).price || 0).toFixed(2) }}
            </el-descriptions-item>
            <el-descriptions-item label="存放位置">
              {{ getStockInfo(detailChain).location }}
            </el-descriptions-item>
            <el-descriptions-item v-if="getStockInfo(detailChain).shelfLife" label="保质期至">
              {{ getStockInfo(detailChain).shelfLife }}
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
.inventory-container {
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

.inventory-tabs {
  margin-bottom: 16px;
}

.tab-badge {
  margin-left: 6px;
}

.pending-tip {
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

.text-warning {
  color: #fa8c16;
  font-weight: 600;
}

/* 二维码对话框 */
.qrcode-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.qrcode-placeholder {
  width: 200px;
  height: 200px;
  border: 2px dashed var(--border-color);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}

.qrcode-placeholder .trace-code {
  font-family: monospace;
  font-size: 12px;
  margin-top: 8px;
}

.qrcode-info {
  text-align: center;
}

.qrcode-info p {
  margin: 4px 0;
  font-size: 14px;
}

.qrcode-actions {
  display: flex;
  gap: 12px;
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
