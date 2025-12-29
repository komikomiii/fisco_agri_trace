<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../../store/user'
import ChainConfirm from '../../components/common/ChainConfirm.vue'
import ChainVerify from '../../components/common/ChainVerify.vue'
import TraceCode from '../../components/common/TraceCode.vue'
import { sellerApi } from '../../api/seller'

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

// 监听 tab 切换，切换到上架记录时加载数据
watch(activeTab, async (newTab) => {
  if (newTab === 'sold' && soldProducts.value.length === 0) {
    await fetchSoldProducts()
  }
})

// ==================== 入库功能 ====================
const stockInVisible = ref(false)
const stockInConfirmVisible = ref(false)
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

const onStockInConfirm = () => {
  if (!stockInForm.value.productId) return
  // 关闭表单对话框，打开确认对话框
  stockInVisible.value = false
  stockInConfirmVisible.value = true
}

const onStockInChainConfirm = async () => {
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

    stockInConfirmVisible.value = false
    await fetchInventoryProducts()
    await fetchStatistics()
  } catch (error) {
    stockInRef.value?.setError(error.response?.data?.detail || '入库失败')
  }
}

// ==================== 上架功能 ====================
const sellVisible = ref(false)
const sellConfirmVisible = ref(false)
const sellForm = ref({
  productId: null,
  productName: '',
  traceCode: '',
  quantity: null,
  availableQuantity: null,
  unit: '',
  price: null,
  shelfLocation: '',
  notes: ''
})
const sellRef = ref(null)

const openSell = (product) => {
  sellForm.value = {
    productId: product.id,
    productName: product.name,
    traceCode: product.trace_code,
    quantity: product.available_quantity,
    availableQuantity: product.available_quantity,
    unit: product.unit,
    price: null,
    shelfLocation: '',
    notes: ''
  }
  sellVisible.value = true
}

const onSellConfirm = async () => {
  if (!sellForm.value.productId) return

  if (!sellForm.value.price || sellForm.value.price <= 0) {
    ElMessage.warning('请输入销售单价')
    return
  }

  if (!sellForm.value.shelfLocation) {
    ElMessage.warning('请输入上架位置')
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
        buyer_name: sellForm.value.shelfLocation,
        buyer_phone: String(sellForm.value.price),
        notes: sellForm.value.notes
      }
    )

    sellRef.value?.setSuccess(result)
    ElMessage.success('上架成功')

    sellConfirmVisible.value = false

    // 上架成功后刷新上架记录列表
    await fetchSoldProducts()
    await fetchStatistics()
  } catch (error) {
    sellRef.value?.setError(error.response?.data?.detail || '上架失败')
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
  verifyTxHash.value = product.tx_hash || ''
  verifyBlockNumber.value = product.block_number || null
  chainVerifyVisible.value = true
}

const openChainVerify = (record) => {
  console.log('[Products] openChainVerify called with:', record)
  verifyTxHash.value = record?.tx_hash || ''
  verifyTraceCode.value = detailProduct.value?.trace_code || ''
  verifyBlockNumber.value = record?.block_number || null
  console.log('[Products] Setting verifyTxHash:', verifyTxHash.value)
  console.log('[Products] Setting verifyBlockNumber:', verifyBlockNumber.value)
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
    sell: '产品上架',
    amend: '修正信息'
  }
  return map[actionLower] || action
}

// 获取状态标签
const getStatusTag = (product) => {
  if (!product.warehouse || product.warehouse === '未入库') {
    return { type: 'warning', text: '待入库' }
  }
  return { type: 'success', text: '已上架' }
}

// ==================== 数据加载 ====================
// 加工类型映射
const processTypeMap = {
  wash: '清洗分拣',
  cut: '切割加工',
  juice: '榨汁加工',
  pack: '包装封装',
  freeze: '冷冻处理',
  dry: '烘干处理'
}

// 检测类型映射
const inspectTypeMap = {
  quality: '质量检测',
  safety: '安全检测',
  appearance: '外观检测'
}

// 翻译备注中的英文
const translateRemark = (remark) => {
  if (!remark) return remark

  let result = remark

  // 替换 "加工: juice → 草莓酱" 为 "加工: 榨汁加工 → 草莓酱"
  result = result.replace(/加工:\s*(\w+)\s*→/g, (match, type) => {
    const chineseType = processTypeMap[type] || type
    return `加工: ${chineseType} →`
  })

  // 替换 "送检: quality" 为 "送检: 质量检测"
  result = result.replace(/送检:\s*(\w+)/g, (match, type) => {
    const chineseType = inspectTypeMap[type] || type
    return `送检: ${chineseType}`
  })

  // 替换 "开始检测: quality" 为 "开始检测: 质量检测"
  result = result.replace(/开始检测:\s*(\w+)/g, (match, type) => {
    const chineseType = inspectTypeMap[type] || type
    return `开始检测: ${chineseType}`
  })

  // 移除接收原料备注中的 "质量等级A/B/C" 信息（因为那时还未质检）
  result = result.replace(/接收原料，质量等级：[ABC]/g, '接收原料')

  return result
}

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
        库存与上架管理
      </h2>
      <div class="statistics">
        <div class="stat-item">
          <span class="stat-value">{{ statistics.inventory_count }}</span>
          <span class="stat-label">库存产品</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ statistics.sold_count }}</span>
          <span class="stat-label">上架记录</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ statistics.total_sales_quantity }}</span>
          <span class="stat-label">上架总量</span>
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
                上架
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

      <el-tab-pane label="上架记录" name="sold">
        <div v-if="loading" class="loading-state">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>加载中...</span>
        </div>
        <div v-else-if="currentList.length === 0" class="empty-state">
          <el-icon><Box /></el-icon>
          <span>暂无上架记录</span>
        </div>
        <el-table v-else :data="currentList" stripe>
          <el-table-column prop="trace_code" label="溯源码" width="180" />
          <el-table-column prop="name" label="产品名称" />
          <el-table-column label="上架数量" width="120">
            <template #default="scope">
              {{ scope.row.quantity }} {{ scope.row.unit }}
            </template>
          </el-table-column>
          <el-table-column label="价格" width="120">
            <template #default="scope">
              ¥{{ scope.row.price || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="shelf_location" label="上架位置" width="150" />
          <el-table-column label="上架时间" width="160">
            <template #default="scope">
              {{ formatTime(scope.row.listing_time) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="scope">
              <el-button
                type="info"
                link
                size="small"
                @click="viewDetail(scope.row)"
              >
                <el-icon><View /></el-icon>
                详情
              </el-button>
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

    <!-- 入库表单对话框 -->
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
      v-model:visible="stockInConfirmVisible"
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
      @confirm="onStockInChainConfirm"
      ref="stockInRef"
    />

    <!-- 上架对话框 -->
    <el-dialog v-model="sellVisible" title="产品上架" width="500px">
      <el-form :model="sellForm" label-width="100px">
        <el-form-item label="产品名称">
          <span>{{ sellForm.productName }}</span>
          <span class="form-hint">({{ sellForm.traceCode }})</span>
        </el-form-item>
        <el-form-item label="上架数量">
          <span class="stock-info">{{ sellForm.quantity }} {{ sellForm.unit }}</span>
        </el-form-item>
        <el-form-item label="销售单价" required>
          <el-input-number
            v-model="sellForm.price"
            :min="0.01"
            :precision="2"
            controls-position="right"
          />
          <span class="unit-hint">元 / {{ sellForm.unit }}</span>
        </el-form-item>
        <el-form-item label="上架位置" required>
          <el-input
            v-model="sellForm.shelfLocation"
            placeholder="请输入上架位置，如：A区-1号货架"
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

    <!-- 上架确认弹窗 -->
    <ChainConfirm
      v-model:visible="sellConfirmVisible"
      title="确认上架上链"
      :data="{
        product: sellForm.productName || '',
        quantity: `${sellForm.quantity} ${sellForm.unit}`,
        price: `¥${sellForm.price} / ${sellForm.unit}`,
        location: sellForm.shelfLocation
      }"
      :data-labels="{
        product: '产品名称',
        quantity: '上架数量',
        price: '销售单价',
        location: '上架位置'
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
            <el-descriptions-item label="品类">
              {{ detailProduct.category || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="产地">
              {{ detailProduct.origin || '-' }}
            </el-descriptions-item>
            <el-descriptions-item v-if="detailProduct.quantity" label="数量">
              {{ detailProduct.quantity }} {{ detailProduct.unit || 'kg' }}
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
              :timestamp="formatTime(record.created_at)"
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

/* 详情相关样式 */
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
</style>
