<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useProductStore } from '../../store/product'
import { useUserStore } from '../../store/user'
import { useNotificationStore } from '../../store/notification'
import ChainConfirm from '../../components/common/ChainConfirm.vue'
import TraceCode from '../../components/common/TraceCode.vue'
import RejectDialog from '../../components/common/RejectDialog.vue'

const productStore = useProductStore()
const userStore = useUserStore()
const notificationStore = useNotificationStore()

// Tab 切换
const activeTab = ref('pending')

// 待检测产品
const pendingProducts = computed(() => {
  return productStore.productChains.filter(c =>
    c.status === 'on_chain' &&
    c.currentStage === 'inspector' &&
    !c.records.some(r => r.action === 'inspect')
  )
})

// 检测中的产品
const testingProducts = computed(() => {
  return productStore.productChains.filter(c =>
    c.status === 'on_chain' &&
    c.currentStage === 'inspector' &&
    c.records.some(r => r.action === 'start_inspect') &&
    !c.records.some(r => r.action === 'inspect')
  )
})

// 已完成的产品
const completedProducts = computed(() => {
  return productStore.productChains.filter(c =>
    c.records.some(r => r.action === 'inspect')
  )
})

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

// ==================== 开始检测 ====================
const startInspect = async (chain) => {
  await productStore.addRecord(chain.id, {
    stage: 'inspector',
    action: 'start_inspect',
    data: {
      startTime: new Date().toISOString()
    },
    operator: {
      id: userStore.user?.id || 3,
      name: userStore.user?.name || '李质检',
      role: 'inspector'
    }
  })
  ElMessage.success('开始检测')
}

// ==================== 填写检测报告 ====================
const reportDialogVisible = ref(false)
const currentChain = ref(null)
const inspectForm = ref({
  result: 'pass',
  items: [
    { name: '农药残留', value: '未检出', standard: '≤0.1mg/kg', pass: true },
    { name: '重金属', value: '0.02mg/kg', standard: '≤0.5mg/kg', pass: true },
    { name: '微生物', value: '合格', standard: '无致病菌', pass: true }
  ],
  notes: ''
})

const openReportDialog = (chain) => {
  currentChain.value = chain
  inspectForm.value = {
    result: 'pass',
    items: [
      { name: '农药残留', value: '', standard: '≤0.1mg/kg', pass: true },
      { name: '重金属', value: '', standard: '≤0.5mg/kg', pass: true },
      { name: '微生物', value: '', standard: '无致病菌', pass: true }
    ],
    notes: ''
  }
  reportDialogVisible.value = true
}

// 更新检测项结果
const updateItemResult = (item) => {
  // 根据检测值和标准值判断是否合格（简化处理）
  item.pass = !item.value.includes('超标') && !item.value.includes('不合格')
}

// ==================== 提交检测报告（上链） ====================
const chainConfirmVisible = ref(false)
const chainConfirmRef = ref(null)

const confirmReport = () => {
  // 验证
  const hasEmpty = inspectForm.value.items.some(item => !item.value)
  if (hasEmpty) {
    ElMessage.warning('请填写所有检测项的检测值')
    return
  }

  reportDialogVisible.value = false
  chainConfirmVisible.value = true
}

const getReportPreviewData = () => {
  if (!currentChain.value) return {}
  const processRecord = currentChain.value.records.find(r => r.action === 'process')
  return {
    productName: processRecord?.data?.outputProduct || currentChain.value.productName,
    traceCode: currentChain.value.traceCode,
    result: inspectForm.value.result === 'pass' ? '合格' : '不合格',
    itemsCount: `${inspectForm.value.items.filter(i => i.pass).length}/${inspectForm.value.items.length} 项合格`
  }
}

const onReportConfirm = async () => {
  if (!currentChain.value) return

  chainConfirmRef.value?.setLoading()

  try {
    const reportNo = `R${new Date().toISOString().slice(0, 10).replace(/-/g, '')}${String(Math.floor(Math.random() * 1000)).padStart(3, '0')}`

    const result = await productStore.addRecord(currentChain.value.id, {
      stage: 'inspector',
      action: 'inspect',
      data: {
        result: inspectForm.value.result,
        items: inspectForm.value.items,
        notes: inspectForm.value.notes,
        reportNo
      },
      operator: {
        id: userStore.user?.id || 3,
        name: userStore.user?.name || '李质检',
        role: 'inspector'
      }
    })

    if (result) {
      // 如果合格，更新产品链阶段到销售商
      if (inspectForm.value.result === 'pass') {
        currentChain.value.currentStage = 'seller'

        // 通知销售商
        notificationStore.addNotification({
          type: notificationStore.NOTIFICATION_TYPES.PENDING,
          title: '新产品可入库',
          content: `${getReportPreviewData().productName}已通过质检，可以入库销售。`,
          relatedTraceCode: currentChain.value.traceCode
        })
      }

      chainConfirmRef.value?.setSuccess(result.txHash, result.blockNumber)
      ElMessage.success('检测报告已提交上链')
    } else {
      chainConfirmRef.value?.setError('提交失败，请重试')
    }
  } catch (error) {
    chainConfirmRef.value?.setError(error.message || '提交失败')
  }
}

// ==================== 退回/终止功能 ====================
const rejectDialogVisible = ref(false)
const rejectingChain = ref(null)

const openRejectDialog = (chain) => {
  rejectingChain.value = chain
  rejectDialogVisible.value = true
}

const handleReject = async (data) => {
  if (!rejectingChain.value) return

  try {
    if (data.action === 'reject') {
      await productStore.rejectToStage(
        rejectingChain.value.id,
        data.rejectTo,
        data.reason,
        {
          id: userStore.user?.id || 3,
          name: userStore.user?.name || '李质检',
          role: 'inspector'
        }
      )

      // 通知被退回方
      notificationStore.addNotification({
        type: notificationStore.NOTIFICATION_TYPES.REJECT,
        title: '产品被退回',
        content: `您的产品"${rejectingChain.value.productName}"被质检员退回，原因：${data.reason}。请重新处理后再次送检。`,
        relatedTraceCode: rejectingChain.value.traceCode
      })

      ElMessage.success('已退回，相关方已收到通知')
    } else if (data.action === 'terminate') {
      await productStore.terminateChain(
        rejectingChain.value.id,
        data.reason,
        data.disposal,
        {
          id: userStore.user?.id || 3,
          name: userStore.user?.name || '李质检',
          role: 'inspector'
        }
      )

      // 通知所有参与方
      notificationStore.addNotification({
        type: notificationStore.NOTIFICATION_TYPES.TERMINATE,
        title: '产品链已终止',
        content: `您参与的产品链 ${rejectingChain.value.traceCode}（${rejectingChain.value.productName}）已被终止。原因：${data.reason}。`,
        relatedTraceCode: rejectingChain.value.traceCode
      })

      ElMessage.success('产品链已终止，相关方已收到通知')
    }
  } catch (error) {
    ElMessage.error(error.message || '操作失败')
  }
}

// ==================== 查看详情 ====================
const detailDrawerVisible = ref(false)
const detailChain = ref(null)

const viewDetail = (chain) => {
  detailChain.value = chain
  detailDrawerVisible.value = true
}

// 获取产品状态
const getProductStatus = (chain) => {
  if (chain.records.some(r => r.action === 'inspect')) return 'completed'
  if (chain.records.some(r => r.action === 'start_inspect')) return 'testing'
  return 'pending'
}

// 获取检测记录数据
const getInspectData = (chain) => {
  const inspectRecord = chain.records.find(r => r.action === 'inspect')
  return inspectRecord?.data || {}
}

// 获取加工信息
const getProcessInfo = (chain) => {
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
  <div class="pending-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span class="title">
            <el-icon><Document /></el-icon>
            待检产品
          </span>
        </div>
      </template>

      <!-- Tab 切换 -->
      <el-tabs v-model="activeTab" class="inspect-tabs">
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
              <el-badge
                :value="testingProducts.length"
                :max="99"
                class="tab-badge"
                type="primary"
              />
            </span>
          </template>
        </el-tab-pane>
        <el-tab-pane name="completed">
          <template #label>
            <span>
              已完成
              <el-badge
                :value="completedProducts.length"
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
              <el-avatar :size="36" shape="square" style="background: #722ed1">
                {{ (getProcessInfo(row).outputProduct || row.productName).charAt(0) }}
              </el-avatar>
              <div class="info">
                <span class="name">{{ getProcessInfo(row).outputProduct || row.productName }}</span>
                <span class="code">{{ row.traceCode }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="送检单位" width="120">
          <template #default="{ row }">
            {{ row.records.find(r => r.action === 'process')?.operator?.name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="送检时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.records.find(r => r.action === 'send_inspect')?.timestamp) }}
          </template>
        </el-table-column>
        <el-table-column label="检测结果" width="100" v-if="activeTab === 'completed'">
          <template #default="{ row }">
            <el-tag :type="getInspectData(row).result === 'pass' ? 'success' : 'danger'">
              {{ getInspectData(row).result === 'pass' ? '合格' : '不合格' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" v-else>
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

            <!-- 待检测：开始检测 -->
            <el-button
              v-if="getProductStatus(row) === 'pending'"
              type="primary"
              text
              size="small"
              @click="startInspect(row)"
            >
              <el-icon><VideoPlay /></el-icon>
              开始检测
            </el-button>

            <!-- 检测中：填写报告、退回/终止 -->
            <template v-if="getProductStatus(row) === 'testing'">
              <el-button type="success" text size="small" @click="openReportDialog(row)">
                <el-icon><Edit /></el-icon>
                填写报告
              </el-button>
              <el-button type="danger" text size="small" @click="openRejectDialog(row)">
                <el-icon><Close /></el-icon>
                退回/终止
              </el-button>
            </template>

            <!-- 已完成：查看报告 -->
            <el-button
              v-if="getProductStatus(row) === 'completed'"
              type="success"
              text
              size="small"
              @click="viewDetail(row)"
            >
              查看报告
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态 -->
      <el-empty v-if="currentList.length === 0" description="暂无记录" />
    </el-card>

    <!-- 填写检测报告对话框 -->
    <el-dialog v-model="reportDialogVisible" title="填写检测报告" width="650px">
      <el-form :model="inspectForm" label-width="100px">
        <el-form-item label="检测结果">
          <el-radio-group v-model="inspectForm.result" size="large">
            <el-radio-button value="pass">
              <el-icon><CircleCheck /></el-icon>
              合格
            </el-radio-button>
            <el-radio-button value="fail">
              <el-icon><CircleClose /></el-icon>
              不合格
            </el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="检测项目">
          <el-table :data="inspectForm.items" border size="small">
            <el-table-column prop="name" label="检测项" width="120" />
            <el-table-column label="检测值" width="160">
              <template #default="{ row }">
                <el-input
                  v-model="row.value"
                  size="small"
                  placeholder="请输入检测值"
                  @change="updateItemResult(row)"
                />
              </template>
            </el-table-column>
            <el-table-column prop="standard" label="标准值" width="140" />
            <el-table-column label="结果" width="100">
              <template #default="{ row }">
                <el-switch
                  v-model="row.pass"
                  active-text="合格"
                  inactive-text="不合格"
                  inline-prompt
                />
              </template>
            </el-table-column>
          </el-table>
        </el-form-item>

        <el-form-item label="备注说明">
          <el-input
            v-model="inspectForm.notes"
            type="textarea"
            :rows="3"
            placeholder="可选填写检测备注"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="reportDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmReport">
          <el-icon><Connection /></el-icon>
          提交上链
        </el-button>
      </template>
    </el-dialog>

    <!-- 上链确认 -->
    <ChainConfirm
      ref="chainConfirmRef"
      v-model:visible="chainConfirmVisible"
      title="确认检测报告上链"
      :data="getReportPreviewData()"
      :data-labels="{
        productName: '产品名称',
        traceCode: '溯源码',
        result: '检测结果',
        itemsCount: '检测项目'
      }"
      @confirm="onReportConfirm"
    >
      <template #extra>
        <div class="result-preview" :class="inspectForm.result">
          <el-icon v-if="inspectForm.result === 'pass'"><CircleCheck /></el-icon>
          <el-icon v-else><CircleClose /></el-icon>
          <span>{{ inspectForm.result === 'pass' ? '检测合格，产品将流转至销售环节' : '检测不合格' }}</span>
        </div>
      </template>
    </ChainConfirm>

    <!-- 退回/终止对话框 -->
    <RejectDialog
      v-model:visible="rejectDialogVisible"
      :product-name="rejectingChain?.productName"
      :trace-code="rejectingChain?.traceCode"
      @submit="handleReject"
    />

    <!-- 详情抽屉 -->
    <el-drawer
      v-model="detailDrawerVisible"
      title="检测详情"
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
            <el-descriptions-item label="送检单位">
              {{ detailChain.records.find(r => r.action === 'process')?.operator?.name || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusMap[getProductStatus(detailChain)]?.type">
                {{ statusMap[getProductStatus(detailChain)]?.label }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 检测报告（如果已完成） -->
        <div v-if="getInspectData(detailChain).result" class="detail-section">
          <h4>检测报告</h4>
          <div class="report-result" :class="getInspectData(detailChain).result">
            <el-icon v-if="getInspectData(detailChain).result === 'pass'"><CircleCheck /></el-icon>
            <el-icon v-else><CircleClose /></el-icon>
            <span>{{ getInspectData(detailChain).result === 'pass' ? '检测合格' : '检测不合格' }}</span>
          </div>

          <el-table :data="getInspectData(detailChain).items" border size="small" class="report-table">
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

          <div v-if="getInspectData(detailChain).notes" class="report-notes">
            备注：{{ getInspectData(detailChain).notes }}
          </div>
        </div>

        <!-- 链上记录 -->
        <div class="detail-section">
          <h4>链上记录</h4>
          <el-timeline>
            <el-timeline-item
              v-for="record in detailChain.records"
              :key="record.id"
              :timestamp="formatTime(record.timestamp)"
              :type="record.action === 'amend' ? 'warning' : record.action === 'reject' || record.action === 'terminate' ? 'danger' : 'primary'"
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
.pending-container {
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

.inspect-tabs {
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

/* 结果预览 */
.result-preview {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 12px;
  padding: 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
}

.result-preview.pass {
  background: #f6ffed;
  color: #389e0d;
  border: 1px solid #b7eb8f;
}

.result-preview.fail {
  background: #fff1f0;
  color: #cf1322;
  border: 1px solid #ffa39e;
}

.result-preview .el-icon {
  font-size: 20px;
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

.report-result {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 16px;
  font-weight: 600;
}

.report-result.pass {
  background: #f6ffed;
  color: #389e0d;
}

.report-result.fail {
  background: #fff1f0;
  color: #cf1322;
}

.report-result .el-icon {
  font-size: 24px;
}

.report-table {
  margin-bottom: 12px;
}

.report-notes {
  padding: 12px;
  background: var(--bg-color);
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-secondary);
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
