<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../../store/user'
import ChainConfirm from '../../components/common/ChainConfirm.vue'
import ChainVerify from '../../components/common/ChainVerify.vue'
import TraceCode from '../../components/common/TraceCode.vue'
import * as sellerApi from '../../api/seller'

const userStore = useUserStore()

// 产品数据
const inventoryProducts = ref([])
const soldProducts = ref([])
const loading = ref(false)

// 统计数据
const statistics = ref({
  inventory_count: 0,
  sold_count: 0,
  total_sales_quantity: 0
})

// 链上数据验证
const chainVerifyVisible = ref(false)
const verifyTraceCode = ref('')
const verifyTxHash = ref('')
const verifyBlockNumber = ref(null)

// Tab 切换
const activeTab = ref('inventory')

// 当前显示的列表
const currentList = computed(() => {
  if (activeTab.value === 'inventory') return inventoryProducts.value
  if (activeTab.value === 'sold') return soldProducts.value
  return []
})

// ==================== 入库功能 ====================
const stockInVisible = ref(false)
const stockInForm = ref({
  productId: null,
  productName: '',
  traceCode: '',
  quantity: null,
  warehouse: '主仓库',
  notes: ''
})
const stockInRef = ref(null)

const openStockIn = (product) => {
  stockInForm.value = {
    productId: product.id,
    productName: product.name,
    traceCode: product.trace_code,
    quantity: product.quantity,
    warehouse: '主仓库',
    notes: ''
  }
  stockInVisible.value = true
}

const onStockInConfirm = async () => {
  if (!stockInForm.value.productId) return

  stockInRef.value?.setLoading()

  try {
    const result = await sellerApi.stockIn(
      stockInForm.value.productId,
      {
        product_id: stockInForm.value.productId,
        quantity: stockInForm.value.quantity,
        warehouse: stockInForm.value.warehouse,
        notes: stockInForm.value.notes
      }
    )

    stockInRef.value?.setSuccess(result)
    ElMessage.success('入库成功')

    stockInVisible.value = false
    await fetchInventoryProducts()
    await fetchStatistics()
  } catch (error) {
    stockInRef.value?.setError(error.response?.data?.detail || '入库失败')
  }
}

// ==================== 销售功能 ====================
const sellVisible = ref(false)
const sellConfirmVisible = ref(false)
const sellForm = ref({
  productId: null,
  productName: '',
  traceCode: '',
  quantity: null,
  availableQuantity: null,
  unit: '',
  buyerName: '',
  buyerPhone: '',
  notes: ''
})
const sellRef = ref(null)

const openSell = (product) => {
  sellForm.value = {
    productId: product.id,
    productName: product.name,
    traceCode: product.trace_code,
    quantity: null,
    availableQuantity: product.available_quantity,
    unit: product.unit,
    buyerName: '',
    buyerPhone: '',
    notes: ''
  }
  sellVisible.value = true
}

const onSellConfirm = async () => {
  if (!sellForm.value.productId) return

  if (!sellForm.value.quantity || sellForm.value.quantity <= 0) {
    ElMessage.warning('请输入销售数量')
    return
  }

  if (sellForm.value.quantity > sellForm.value.availableQuantity) {
    ElMessage.warning(`销售数量不能超过可用库存 (${sellForm.value.availableQuantity} ${sellForm.value.unit})`)
    return
  }

  if (!sellForm.value.buyerName) {
    ElMessage.warning('请输入买家名称')
    return
  }

  // 关闭表单对话框，打开确认对话框
  sellVisible.value = false
  sellConfirmVisible.value = true
}

const onSellChainConfirm = async () => {
  if (!sellForm.value.productId) return

  sellRef.value?.setLoading()

  try {
    const result = await sellerApi.sellProduct(
      sellForm.value.productId,
      {
        product_id: sellForm.value.productId,
        quantity: sellForm.value.quantity,
        buyer_name: sellForm.value.buyerName,
        buyer_phone: sellForm.value.buyerPhone,
        notes: sellForm.value.notes
      }
    )

    sellRef.value?.setSuccess(result)
    ElMessage.success('销售成功')

    sellConfirmVisible.value = false

    if (result.is_fully_sold) {
      // 全部售完，刷新库存列表
      await fetchInventoryProducts()
    } else {
      // 部分销售，更新数量
      await fetchInventoryProducts()
    }

    await fetchSoldProducts()
    await fetchStatistics()
  } catch (error) {
    sellRef.value?.setError(error.response?.data?.detail || '销售失败')
  }
}

// ==================== 详情 ====================
const detailDrawerVisible = ref(false)
const detailProduct = ref(null)
const detailRecords = ref([])
const detailLoading = ref(false)

const viewDetail = async (product) => {
  detailProduct.value = product
  detailDrawerVisible.value = true

  // 加载流转记录
  detailLoading.value = true
  try {
    const records = await sellerApi.getProductRecords(product.id)
    detailRecords.value = records
  } catch (error) {
    console.error('获取记录失败', error)
    detailRecords.value = []
  } finally {
    detailLoading.value = false
  }
}

const viewChainData = (product) => {
  verifyTraceCode.value = product.trace_code
  chainVerifyVisible.value = true
}

const openChainVerify = (record) => {
  verifyTxHash.value = record?.tx_hash || ''
  verifyTraceCode.value = detailProduct.value.trace_code
  verifyBlockNumber.value = record?.block_number || null
  chainVerifyVisible.value = true
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
    harvest: '采收上链',
    receive: '接收原料',
    process: '加工处理',
    send_inspect: '送检测',
    start_inspect: '开始检测',
    inspect: '质量检测',
    stock_in: '产品入库',
    sell: '产品销售',
    amend: '修正信息'
  }
  return map[actionLower] || action
}

// 获取状态标签
const getStatusTag = (product) => {
  if (!product.warehouse || product.warehouse === '未入库') {
    return { type: 'warning', text: '待入库' }
  }
  return { type: 'success', text: '在售' }
}

// ==================== 数据加载 ====================
const fetchInventoryProducts = async () => {
  loading.value = true
  try {
    const data = await sellerApi.getInventoryProducts()
    inventoryProducts.value = data
  } catch (error) {
    ElMessage.error('获取库存列表失败')
  } finally {
    loading.value = false
  }
}

const fetchSoldProducts = async () => {
  loading.value = true
  try {
    const data = await sellerApi.getSoldProducts()
    soldProducts.value = data
  } catch (error) {
    ElMessage.error('获取已售列表失败')
  } finally {
    loading.value = false
  }
}

const fetchStatistics = async () => {
  try {
    const data = await sellerApi.getStatistics()
    statistics.value = data
  } catch (error) {
    console.error('获取统计数据失败', error)
  }
}

onMounted(() => {
  fetchInventoryProducts()
  fetchStatistics()
})
</script>

<template>
  <div class="seller-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>
        <el-icon><Shop /></el-icon>
        销售管理
      </h2>
      <div class="statistics">
        <div class="stat-item">
          <span class="stat-value">{{ statistics.inventory_count }}</span>
          <span class="stat-label">库存产品</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ statistics.sold_count }}</span>
          <span class="stat-label">销售记录</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ statistics.total_sales_quantity }}</span>
          <span class="stat-label">销售总量</span>
        </div>
      </div>
    </div>

    <!-- Tab 切换 -->
    <el-tabs v-model="activeTab" class="data-tabs">
      <el-tab-pane label="库存产品" name="inventory">
        <div v-if="loading" class="loading-state">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>加载中...</span>
        </div>
        <div v-else-if="currentList.length === 0" class="empty-state">
          <el-icon><Box /></el-icon>
          <span>暂无库存产品</span>
        </div>
        <div v-else class="product-grid">
          <div
            v-for="product in currentList"
            :key="product.id"
            class="product-card"
          >
            <!-- 产品信息 -->
            <div class="product-header">
              <div class="product-title">
                <h3>{{ product.name }}</h3>
                <el-tag :type="getStatusTag(product).type" size="small">
                  {{ getStatusTag(product).text }}
                </el-tag>
              </div>
              <div class="product-meta">
                <span class="trace-code">{{ product.trace_code }}</span>
              </div>
            </div>

            <div class="product-info">
              <div class="info-row">
                <span class="label">品类</span>
                <span class="value">{{ product.category || '-' }}</span>
              </div>
              <div class="info-row">
                <span class="label">产地</span>
                <span class="value">{{ product.origin || '-' }}</span>
              </div>
              <div class="info-row">
                <span class="label">库存</span>
                <span class="value highlight">
                  {{ product.available_quantity }} / {{ product.quantity }} {{ product.unit }}
                </span>
              </div>
              <div class="info-row">
                <span class="label">仓库</span>
                <span class="value">{{ product.warehouse }}</span>
              </div>
            </div>

            <!-- 操作按钮 -->
            <div class="product-actions">
              <el-button
                v-if="!product.warehouse || product.warehouse === '未入库'"
                type="primary"
                size="small"
                @click="openStockIn(product)"
              >
                <el-icon><Box /></el-icon>
                入库
              </el-button>
              <el-button
                type="success"
                size="small"
                @click="openSell(product)"
                :disabled="!product.warehouse || product.warehouse === '未入库'"
              >
                <el-icon><ShoppingCart /></el-icon>
                销售
              </el-button>
              <el-button
                type="info"
                size="small"
                @click="viewDetail(product)"
              >
                <el-icon><View /></el-icon>
                详情
              </el-button>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="销售记录" name="sold">
        <div v-if="loading" class="loading-state">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>加载中...</span>
        </div>
        <div v-else-if="currentList.length === 0" class="empty-state">
          <el-icon><Box /></el-icon>
          <span>暂无销售记录</span>
        </div>
        <el-table v-else :data="currentList" stripe>
          <el-table-column prop="trace_code" label="溯源码" width="200" />
          <el-table-column prop="name" label="产品名称" />
          <el-table-column label="销售数量" width="150">
            <template #default="scope">
              {{ scope.row.quantity }} {{ scope.row.unit }}
            </template>
          </el-table-column>
          <el-table-column prop="buyer_name" label="买家" />
          <el-table-column label="销售时间" width="180">
            <template #default="scope">
              {{ formatTime(scope.row.sell_time) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="scope">
              <el-button
                v-if="scope.row.tx_hash"
                type="primary"
                link
                size="small"
                @click="viewChainData(scope.row)"
              >
                <el-icon><Connection /></el-icon>
                链上数据
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 入库对话框 -->
    <el-dialog v-model="stockInVisible" title="产品入库" width="500px">
      <el-form :model="stockInForm" label-width="100px">
        <el-form-item label="产品名称">
          <span>{{ stockInForm.productName }}</span>
          <span class="form-hint">({{ stockInForm.traceCode }})</span>
        </el-form-item>
        <el-form-item label="入库数量">
          <el-input-number
            v-model="stockInForm.quantity"
            :min="0"
            :max="stockInForm.quantity"
            :precision="2"
            controls-position="right"
          />
          <span class="unit-hint">{{ stockInForm.quantity }} {{ stockInForm.unit }}</span>
        </el-form-item>
        <el-form-item label="仓库位置">
          <el-input
            v-model="stockInForm.warehouse"
            placeholder="请输入仓库位置"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="stockInForm.notes"
            type="textarea"
            :rows="3"
            placeholder="可选填写备注"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="stockInVisible = false">取消</el-button>
        <el-button type="primary" @click="onStockInConfirm">
          确认入库
        </el-button>
      </template>
    </el-dialog>

    <!-- 入库确认弹窗 -->
    <ChainConfirm
      v-model:visible="stockInVisible"
      title="确认入库"
      :data="{
        product: stockInForm.productName || '',
        quantity: `${stockInForm.quantity} ${stockInForm.unit}`,
        warehouse: stockInForm.warehouse
      }"
      :data-labels="{
        product: '产品名称',
        quantity: '入库数量',
        warehouse: '仓库位置'
      }"
      :loading="false"
      @confirm="onStockInConfirm"
      ref="stockInRef"
    />

    <!-- 销售对话框 -->
    <el-dialog v-model="sellVisible" title="产品销售" width="500px">
      <el-form :model="sellForm" label-width="100px">
        <el-form-item label="产品名称">
          <span>{{ sellForm.productName }}</span>
          <span class="form-hint">({{ sellForm.traceCode }})</span>
        </el-form-item>
        <el-form-item label="可用库存">
          <span class="stock-info">{{ sellForm.availableQuantity }} {{ sellForm.unit }}</span>
        </el-form-item>
        <el-form-item label="销售数量" required>
          <el-input-number
            v-model="sellForm.quantity"
            :min="0.1"
            :max="sellForm.availableQuantity"
            :precision="2"
            controls-position="right"
          />
          <span class="unit-hint">{{ sellForm.unit }}</span>
        </el-form-item>
        <el-form-item label="买家名称" required>
          <el-input
            v-model="sellForm.buyerName"
            placeholder="请输入买家名称"
          />
        </el-form-item>
        <el-form-item label="买家电话">
          <el-input
            v-model="sellForm.buyerPhone"
            placeholder="可选输入"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="sellForm.notes"
            type="textarea"
            :rows="3"
            placeholder="可选填写备注"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="sellVisible = false">取消</el-button>
        <el-button type="primary" @click="onSellConfirm">
          下一步
        </el-button>
      </template>
    </el-dialog>

    <!-- 销售确认弹窗 -->
    <ChainConfirm
      v-model:visible="sellConfirmVisible"
      title="确认销售上链"
      :data="{
        product: sellForm.productName || '',
        quantity: `${sellForm.quantity} ${sellForm.unit}`,
        buyerName: sellForm.buyerName,
        buyerPhone: sellForm.buyerPhone || '无'
      }"
      :data-labels="{
        product: '产品名称',
        quantity: '销售数量',
        buyerName: '买家名称',
        buyerPhone: '买家电话'
      }"
      :loading="false"
      @confirm="onSellChainConfirm"
      ref="sellRef"
    />

    <!-- 详情抽屉 -->
    <el-drawer
      v-model="detailDrawerVisible"
      title="产品详情"
      size="500px"
    >
      <div v-if="detailProduct" class="detail-content">
        <!-- 产品基本信息 -->
        <div class="detail-section">
          <h4>基本信息</h4>
          <div class="detail-info">
            <div class="info-item">
              <span class="label">溯源码</span>
              <div class="value-wrapper">
                <TraceCode :code="detailProduct.trace_code" />
              </div>
            </div>
            <div class="info-item">
              <span class="label">产品名称</span>
              <span class="value">{{ detailProduct.name }}</span>
            </div>
            <div class="info-item">
              <span class="label">品类</span>
              <span class="value">{{ detailProduct.category || '-' }}</span>
            </div>
            <div class="info-item">
              <span class="label">产地</span>
              <span class="value">{{ detailProduct.origin || '-' }}</span>
            </div>
          </div>
        </div>

        <!-- 流转记录 -->
        <div class="detail-section">
          <h4>流转记录</h4>
          <div v-if="detailLoading" class="loading-state">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>加载中...</span>
          </div>
          <el-timeline v-else-if="detailRecords.length > 0">
            <el-timeline-item
              v-for="record in detailRecords"
              :key="record.id"
              :timestamp="formatTime(record.created_at)"
              placement="top"
            >
              <div class="record-item">
                <div class="record-header">
                  <span class="action">{{ getActionLabel(record.action) }}</span>
                  <span class="operator">{{ record.operator_name }}</span>
                </div>
                <div v-if="record.remark" class="record-remark">
                  {{ record.remark }}
                </div>
                <div v-if="record.tx_hash" class="chain-info-box" @click="openChainVerify(record)">
                  <div class="chain-badge">
                    <el-icon><Connection /></el-icon>
                    <span>FISCO BCOS</span>
                  </div>
                  <div class="chain-details">
                    <div class="chain-row">
                      <span class="chain-label">区块</span>
                      <span class="chain-value">#{{ record.block_number }}</span>
                    </div>
                  </div>
                  <div class="verify-btn">查看详情 →</div>
                </div>
              </div>
            </el-timeline-item>
          </el-timeline>
          <div v-else class="empty-state">
            <span>暂无记录</span>
          </div>
        </div>
      </div>
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
.seller-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-header h2 {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0;
  font-size: 24px;
  color: var(--text-primary);
}

.statistics {
  display: flex;
  gap: 32px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--primary-color);
}

.stat-label {
  font-size: 13px;
  color: var(--text-muted);
}

.data-tabs {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 60px 20px;
  color: var(--text-muted);
}

.product-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.product-card {
  background: white;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
  transition: all 0.3s;
}

.product-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.product-header {
  margin-bottom: 16px;
}

.product-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.product-title h3 {
  margin: 0;
  font-size: 18px;
  color: var(--text-primary);
}

.product-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.trace-code {
  font-size: 12px;
  font-family: monospace;
  color: var(--text-muted);
  background: var(--bg-color);
  padding: 4px 8px;
  border-radius: 4px;
}

.product-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
}

.info-row .label {
  color: var(--text-muted);
}

.info-row .value {
  color: var(--text-primary);
  font-weight: 500;
}

.info-row .value.highlight {
  color: var(--primary-color);
  font-weight: 600;
}

.product-actions {
  display: flex;
  gap: 8px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

.form-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-left: 8px;
}

.unit-hint {
  font-size: 13px;
  color: var(--text-muted);
  margin-left: 8px;
}

.stock-info {
  font-size: 16px;
  font-weight: 600;
  color: var(--success-color);
}

.detail-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.detail-section h4 {
  font-size: 16px;
  color: var(--text-primary);
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--primary-color);
}

.detail-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
}

.info-item .label {
  font-size: 14px;
  color: var(--text-muted);
}

.info-item .value {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
}

.value-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
}

.record-item {
  padding: 12px;
  background: var(--bg-color);
  border-radius: 8px;
  border-left: 3px solid var(--primary-color);
}

.record-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.record-header .action {
  font-weight: 600;
  color: var(--primary-color);
}

.record-header .operator {
  font-size: 12px;
  color: var(--text-muted);
}

.record-remark {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.chain-info-box {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
  padding: 10px 12px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.08), rgba(118, 75, 162, 0.08));
  border: 1px solid rgba(102, 126, 234, 0.2);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.chain-info-box:hover {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.12), rgba(118, 75, 162, 0.12));
  transform: translateX(4px);
}

.chain-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 6px;
  color: white;
  font-size: 12px;
  font-weight: 600;
}

.chain-details {
  display: flex;
  gap: 16px;
  flex: 1;
}

.chain-row {
  display: flex;
  gap: 6px;
  font-size: 12px;
}

.chain-label {
  color: var(--text-muted);
}

.chain-value {
  color: var(--primary-color);
  font-weight: 600;
  font-family: monospace;
}

.verify-btn {
  font-size: 12px;
  color: var(--primary-color);
  font-weight: 500;
  opacity: 0;
  transition: all 0.2s;
}

.chain-info-box:hover .verify-btn {
  opacity: 1;
}
</style>
