<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../../store/user'
import ChainConfirm from '../../components/common/ChainConfirm.vue'
import ChainVerify from '../../components/common/ChainVerify.vue'
import TraceCode from '../../components/common/TraceCode.vue'
import * as inspectorApi from '../../api/inspector'

const userStore = useUserStore()

// 产品数据
const pendingProducts = ref([])
const testingProducts = ref([])
const completedProducts = ref([])
const loading = ref(false)

// 链上数据验证
const chainVerifyVisible = ref(false)
const verifyTraceCode = ref('')

// Tab 切换
const activeTab = ref('pending')

// 当前显示的列表
const currentList = computed(() => {
  if (activeTab.value === 'pending') return pendingProducts.value
  if (activeTab.value === 'testing') return testingProducts.value
  if (activeTab.value === 'completed') return completedProducts.value
  return []
})

// 状态映射
const statusMap = {
  pending: { label: '待检测', type: 'warning' },
  testing: { label: '检测中', type: 'primary' },
  completed: { label: '已完成', type: 'success' }
}

// 质检类型映射
const inspectTypeMap = {
  quality: '质量检测',
  safety: '安全检测',
  appearance: '外观检测'
}

// ==================== 开始检测 ====================
const startInspectVisible = ref(false)
const startInspectForm = ref({
  productId: null,
  inspectType: 'quality',
  notes: ''
})
const startInspectRef = ref(null)

const openStartInspect = (product) => {
  startInspectForm.value = {
    productId: product.id,
    inspectType: product.inspect_type || 'quality',
    notes: ''
  }
  startInspectVisible.value = true
}

const onStartInspectConfirm = async () => {
  if (!startInspectForm.value.productId) return

  startInspectRef.value?.setLoading()

  try {
    await inspectorApi.startInspect(
      startInspectForm.value.productId,
      {
        product_id: startInspectForm.value.productId,
        inspect_type: startInspectForm.value.inspectType,
        notes: startInspectForm.value.notes
      }
    )

    startInspectRef.value?.setSuccess()
    ElMessage.success('开始检测成功')

    startInspectVisible.value = false
    await fetchPendingProducts()
    await fetchTestingProducts()
  } catch (error) {
    startInspectRef.value?.setError(error.response?.data?.detail || '开始检测失败')
  }
}

// ==================== 完成检测 ====================
const inspectVisible = ref(false)
const inspectConfirmVisible = ref(false)  // 新增：上链确认对话框
const inspectForm = ref({
  productId: null,
  productName: '',
  traceCode: '',
  qualified: true,
  qualityGrade: 'A',
  inspectResult: '',
  issues: '',
  notes: ''
})
const inspectRef = ref(null)

const openInspect = (product) => {
  inspectForm.value = {
    productId: product.id,
    productName: product.name,
    traceCode: product.trace_code,
    qualified: true,
    qualityGrade: 'A',
    inspectResult: '',
    issues: '',
    notes: ''
  }
  inspectVisible.value = true
}

const onInspectConfirm = async () => {
  if (!inspectForm.value.productId) return

  if (!inspectForm.value.inspectResult) {
    ElMessage.warning('请填写检测结果')
    return
  }

  // 关闭表单对话框，打开确认对话框
  inspectVisible.value = false
  inspectConfirmVisible.value = true
}

const onInspectChainConfirm = async () => {
  if (!inspectForm.value.productId) return

  inspectRef.value?.setLoading()

  try {
    const result = await inspectorApi.inspectProduct(
      inspectForm.value.productId,
      {
        product_id: inspectForm.value.productId,
        qualified: inspectForm.value.qualified,
        quality_grade: inspectForm.value.qualityGrade,
        inspect_result: inspectForm.value.inspectResult,
        issues: inspectForm.value.issues,
        notes: inspectForm.value.notes
      }
    )

    inspectRef.value?.setSuccess(result.trace_code, result.block_number, result.tx_hash)

    if (result.qualified) {
      ElMessage.success('检测合格，产品已进入销售环节')
    } else {
      ElMessage.warning('检测不合格，产品已被标记')
    }

    await fetchTestingProducts()
    await fetchCompletedProducts()
  } catch (error) {
    inspectRef.value?.setError(error.response?.data?.detail || '检测失败')
  }
}

// ==================== 数据获取 ====================
const fetchPendingProducts = async () => {
  try {
    loading.value = true
    const data = await inspectorApi.getPendingProducts()
    pendingProducts.value = data
  } catch (error) {
    ElMessage.error('获取待检测产品列表失败')
  } finally {
    loading.value = false
  }
}

const fetchTestingProducts = async () => {
  try {
    loading.value = true
    const data = await inspectorApi.getTestingProducts()
    testingProducts.value = data
  } catch (error) {
    ElMessage.error('获取检测中产品列表失败')
  } finally {
    loading.value = false
  }
}

const fetchCompletedProducts = async () => {
  try {
    loading.value = true
    const data = await inspectorApi.getCompletedProducts()
    completedProducts.value = data
  } catch (error) {
    ElMessage.error('获取已完成产品列表失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchPendingProducts()
  fetchTestingProducts()
  fetchCompletedProducts()
})

// ==================== 查看详情 ====================
const detailDrawerVisible = ref(false)
const detailProduct = ref(null)
const detailRecords = ref([])
const detailLoading = ref(false)

const viewDetail = async (product) => {
  detailProduct.value = product
  detailDrawerVisible.value = true

  try {
    detailLoading.value = true
    const records = await inspectorApi.getProductRecords(product.id)
    detailRecords.value = records
  } catch (error) {
    console.error('获取记录失败:', error)
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
  verifyTraceCode.value = detailProduct.value.trace_code
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
    amend: '修正信息',
    harvest: '采收上链',
    receive: '接收原料',
    process: '加工处理',
    send_inspect: '送检',
    inspect: '质量检测',
    stock: '入库登记',
    reject: '退回处理',
    terminate: '终止链条',
    start_inspect: '开始检测'
  }
  return map[actionLower] || action
}
</script>

<template>
  <div class="inspector-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>
        <el-icon><DocumentChecked /></el-icon>
        质量检测
      </h2>
      <p>对待检测产品进行质量检验</p>
    </div>

    <!-- 检测记录卡片 -->
    <el-card class="inspector-card">
      <template #header>
        <div class="card-header">
          <span>检测记录</span>
        </div>
      </template>

      <!-- Tab 切换 -->
      <el-tabs v-model="activeTab" class="inspector-tabs">
        <el-tab-pane name="pending">
          <template #label>
            <span>
              待检测
              <el-badge :value="pendingProducts.length" :max="99" class="tab-badge" />
            </span>
          </template>
        </el-tab-pane>
        <el-tab-pane name="testing">
          <template #label>
            <span>
              检测中
              <el-badge :value="testingProducts.length" :max="99" class="tab-badge" type="primary" />
            </span>
          </template>
        </el-tab-pane>
        <el-tab-pane name="completed">
          <template #label>
            <span>
              已完成
              <el-badge :value="completedProducts.length" :max="99" class="tab-badge" type="success" />
            </span>
          </template>
        </el-tab-pane>
      </el-tabs>

      <el-table :data="currentList" stripe v-loading="loading">
        <el-table-column prop="name" label="产品" min-width="160">
          <template #default="{ row }">
            <div class="product-info">
              <el-avatar :size="36" shape="square" style="background: #67c23a">
                {{ row.name.charAt(0) }}
              </el-avatar>
              <div class="info">
                <span class="name">{{ row.name }}</span>
                <span class="code">{{ row.trace_code }}</span>
                <span v-if="row.process_type" class="process-info">
                  加工: {{ row.process_type }}
                </span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="检测类型" width="120">
          <template #default="{ row }">
            <el-tag type="warning" effect="plain">
              {{ inspectTypeMap[row.inspect_type] || '质量检测' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="数量" width="100">
          <template #default="{ row }">
            <span class="quantity">{{ row.quantity }} {{ row.unit || 'kg' }}</span>
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

            <!-- 待检测：开始检测 -->
            <el-button
              v-if="row.status === 'pending'"
              type="success"
              text
              size="small"
              @click="openStartInspect(row)"
            >
              <el-icon><VideoPlay /></el-icon>
              开始检测
            </el-button>

            <!-- 检测中：完成检测 -->
            <el-button
              v-if="row.status === 'testing'"
              type="success"
              text
              size="small"
              @click="openInspect(row)"
            >
              <el-icon><Select /></el-icon>
              完成检测
            </el-button>

            <!-- 已完成：查看结果 -->
            <el-tag v-if="row.status === 'completed' && row.qualified" type="success" size="small">
              合格 {{ row.quality_grade }}级
            </el-tag>
            <el-tag v-else-if="row.status === 'completed'" type="danger" size="small">
              不合格
            </el-tag>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态 -->
      <el-empty v-if="currentList.length === 0" description="暂无记录" />
    </el-card>

    <!-- 开始检测对话框 -->
    <el-dialog v-model="startInspectVisible" title="开始检测" width="500px">
      <el-form :model="startInspectForm" label-width="100px">
        <el-form-item label="检测类型">
          <el-select v-model="startInspectForm.inspectType" style="width: 100%">
            <el-option label="质量检测" value="quality" />
            <el-option label="安全检测" value="safety" />
            <el-option label="外观检测" value="appearance" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="startInspectForm.notes"
            type="textarea"
            :rows="3"
            placeholder="可选填写检测备注"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="startInspectVisible = false">取消</el-button>
        <el-button type="primary" @click="onStartInspectConfirm">
          确认开始
        </el-button>
      </template>
    </el-dialog>

    <!-- 完成检测对话框 -->
    <el-dialog v-model="inspectVisible" title="完成检测" width="600px">
      <el-form :model="inspectForm" label-width="100px">
        <el-form-item label="产品名称">
          <span>{{ inspectForm.productName }}</span>
          <span class="form-hint">({{ inspectForm.traceCode }})</span>
        </el-form-item>
        <el-form-item label="检测结果" required>
          <el-radio-group v-model="inspectForm.qualified">
            <el-radio :label="true">合格</el-radio>
            <el-radio :label="false">不合格</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="质量等级" required>
          <el-radio-group v-model="inspectForm.qualityGrade">
            <el-radio label="A">A级</el-radio>
            <el-radio label="B">B级</el-radio>
            <el-radio label="C">C级</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="检测结果描述" required>
          <el-input
            v-model="inspectForm.inspectResult"
            type="textarea"
            :rows="3"
            placeholder="请详细描述检测结果"
          />
        </el-form-item>
        <el-form-item v-if="!inspectForm.qualified" label="存在问题">
          <el-input
            v-model="inspectForm.issues"
            type="textarea"
            :rows="2"
            placeholder="请描述发现的问题"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="inspectForm.notes"
            type="textarea"
            :rows="2"
            placeholder="可选填写备注"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="inspectVisible = false">取消</el-button>
        <el-button type="primary" @click="onInspectConfirm">
          <el-icon><DocumentChecked /></el-icon>
          下一步
        </el-button>
      </template>
    </el-dialog>

    <!-- 开始检测确认弹窗 -->
    <ChainConfirm
      v-model:visible="startInspectVisible"
      title="确认开始检测"
      :data="{
        product: startInspectForm.product?.name || '',
        inspectType: inspectTypeMap[startInspectForm.inspectType] || '质量检测',
        notes: startInspectForm.notes || '无'
      }"
      :data-labels="{
        product: '产品名称',
        inspectType: '检测类型',
        notes: '备注'
      }"
      :loading="false"
      @confirm="onStartInspectConfirm"
      ref="startInspectRef"
    />

    <!-- 完成检测上链确认弹窗 -->
    <ChainConfirm
      v-model:visible="inspectConfirmVisible"
      title="确认上链"
      :data="{
        product: inspectForm.productName || '',
        qualified: inspectForm.qualified ? '合格' : '不合格',
        qualityGrade: `${inspectForm.qualityGrade}级`,
        inspectResult: inspectForm.inspectResult,
        issues: inspectForm.issues || '无'
      }"
      :data-labels="{
        product: '产品名称',
        qualified: '检测结果',
        qualityGrade: '质量等级',
        inspectResult: '检测描述',
        issues: '存在问题'
      }"
      :loading="false"
      @confirm="onInspectChainConfirm"
      ref="inspectRef"
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
                  {{ record.remark }}
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
    />
  </div>
</template>

<style scoped>
.inspector-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.page-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-header p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 14px;
}

.inspector-card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.card-header {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.inspector-tabs {
  margin-top: 16px;
}

.tab-badge {
  margin-left: 8px;
}

.product-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.product-info .info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.product-info .name {
  font-weight: 500;
  color: var(--text-primary);
}

.product-info .code {
  font-size: 12px;
  color: var(--text-muted);
  font-family: monospace;
}

.product-info .process-info {
  font-size: 12px;
  color: var(--primary-color);
}

.quantity {
  font-weight: 500;
  color: var(--text-primary);
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

.form-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-left: 8px;
}
</style>
