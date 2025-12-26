<script setup>
import { ref, computed } from 'vue'
import { useProductStore } from '../../store/product'
import TraceCode from '../../components/common/TraceCode.vue'

const productStore = useProductStore()

// 搜索表单
const searchForm = ref({
  keyword: '',
  result: ''
})

// 所有检测报告（从已检测的产品链中提取）
const allReports = computed(() => {
  const reports = []
  productStore.productChains.forEach(chain => {
    const inspectRecord = chain.records.find(r => r.action === 'inspect')
    if (inspectRecord) {
      const processRecord = chain.records.find(r => r.action === 'process')
      reports.push({
        id: inspectRecord.id,
        chainId: chain.id,
        reportNo: inspectRecord.data.reportNo,
        traceCode: chain.traceCode,
        productName: processRecord?.data?.outputProduct || chain.productName,
        result: inspectRecord.data.result,
        items: inspectRecord.data.items,
        notes: inspectRecord.data.notes,
        inspector: inspectRecord.operator?.name,
        date: inspectRecord.timestamp,
        txHash: inspectRecord.txHash,
        blockNumber: inspectRecord.blockNumber
      })
    }
  })
  return reports.sort((a, b) => new Date(b.date) - new Date(a.date))
})

// 筛选后的报告
const filteredReports = computed(() => {
  let list = allReports.value
  if (searchForm.value.keyword) {
    list = list.filter(r =>
      r.productName.includes(searchForm.value.keyword) ||
      r.reportNo.includes(searchForm.value.keyword) ||
      r.traceCode.includes(searchForm.value.keyword)
    )
  }
  if (searchForm.value.result) {
    list = list.filter(r => r.result === searchForm.value.result)
  }
  return list
})

// 统计信息
const stats = computed(() => {
  const total = allReports.value.length
  const passed = allReports.value.filter(r => r.result === 'pass').length
  const failed = total - passed
  const passRate = total > 0 ? Math.round((passed / total) * 100) : 0
  return { total, passed, failed, passRate }
})

// ==================== 查看报告详情 ====================
const detailDrawerVisible = ref(false)
const currentReport = ref(null)

const viewDetail = (report) => {
  currentReport.value = report
  detailDrawerVisible.value = true
}

// 格式化时间
const formatTime = (timestamp) => {
  if (!timestamp) return '-'
  return new Date(timestamp).toLocaleString('zh-CN')
}

// 重置搜索
const resetSearch = () => {
  searchForm.value = {
    keyword: '',
    result: ''
  }
}

// 导出报告（模拟）
const exportReports = () => {
  // TODO: 实际导出功能
  console.log('导出报告', filteredReports.value)
}
</script>

<template>
  <div class="reports-container">
    <!-- 统计卡片 -->
    <div class="stats-row">
      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon total">
            <el-icon><Document /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.total }}</span>
            <span class="stat-label">总报告数</span>
          </div>
        </div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon passed">
            <el-icon><CircleCheck /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.passed }}</span>
            <span class="stat-label">合格数量</span>
          </div>
        </div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon failed">
            <el-icon><CircleClose /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.failed }}</span>
            <span class="stat-label">不合格数量</span>
          </div>
        </div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon rate">
            <el-icon><TrendCharts /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.passRate }}%</span>
            <span class="stat-label">合格率</span>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 报告列表 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span class="title">
            <el-icon><DataAnalysis /></el-icon>
            检测报告
          </span>
          <el-button :icon="Download" @click="exportReports">导出报告</el-button>
        </div>
      </template>

      <!-- 搜索栏 -->
      <div class="search-bar">
        <el-input
          v-model="searchForm.keyword"
          placeholder="搜索产品名称/报告编号/溯源码"
          clearable
          style="width: 300px"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-select v-model="searchForm.result" placeholder="检测结果" clearable style="width: 120px">
          <el-option label="合格" value="pass" />
          <el-option label="不合格" value="fail" />
        </el-select>
        <el-button @click="resetSearch">重置</el-button>
      </div>

      <el-table :data="filteredReports" stripe>
        <el-table-column prop="reportNo" label="报告编号" width="160">
          <template #default="{ row }">
            <el-tag effect="plain">{{ row.reportNo }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="productName" label="产品名称" min-width="140">
          <template #default="{ row }">
            <div class="product-info">
              <span class="name">{{ row.productName }}</span>
              <span class="code">{{ row.traceCode }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="result" label="检测结果" width="100">
          <template #default="{ row }">
            <el-tag :type="row.result === 'pass' ? 'success' : 'danger'">
              {{ row.result === 'pass' ? '合格' : '不合格' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="inspector" label="检测员" width="100" />
        <el-table-column prop="date" label="检测日期" width="160">
          <template #default="{ row }">
            {{ formatTime(row.date) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" text size="small" @click="viewDetail(row)">
              查看详情
            </el-button>
            <el-button type="primary" text size="small">
              <el-icon><Download /></el-icon>
              下载
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态 -->
      <el-empty v-if="filteredReports.length === 0" description="暂无检测报告" />
    </el-card>

    <!-- 报告详情抽屉 -->
    <el-drawer
      v-model="detailDrawerVisible"
      title="检测报告详情"
      size="550px"
    >
      <template v-if="currentReport">
        <!-- 溯源码 -->
        <div class="detail-section">
          <TraceCode :trace-code="currentReport.traceCode" size="large" />
        </div>

        <!-- 报告基本信息 -->
        <div class="detail-section">
          <h4>报告信息</h4>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="报告编号">
              <el-tag effect="plain">{{ currentReport.reportNo }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="产品名称">
              {{ currentReport.productName }}
            </el-descriptions-item>
            <el-descriptions-item label="检测员">
              {{ currentReport.inspector }}
            </el-descriptions-item>
            <el-descriptions-item label="检测时间">
              {{ formatTime(currentReport.date) }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 检测结果 -->
        <div class="detail-section">
          <h4>检测结果</h4>
          <div class="report-result" :class="currentReport.result">
            <el-icon v-if="currentReport.result === 'pass'"><CircleCheck /></el-icon>
            <el-icon v-else><CircleClose /></el-icon>
            <span>{{ currentReport.result === 'pass' ? '检测合格' : '检测不合格' }}</span>
          </div>

          <el-table :data="currentReport.items" border size="small" class="report-table">
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

          <div v-if="currentReport.notes" class="report-notes">
            备注：{{ currentReport.notes }}
          </div>
        </div>

        <!-- 区块链存证 -->
        <div class="detail-section">
          <h4>区块链存证</h4>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="交易哈希">
              <span class="hash">{{ currentReport.txHash }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="区块高度">
              {{ currentReport.blockNumber }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
.reports-container {
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

.stat-icon.total {
  background: rgba(24, 144, 255, 0.1);
  color: #1890ff;
}

.stat-icon.passed {
  background: rgba(82, 196, 26, 0.1);
  color: #52c41a;
}

.stat-icon.failed {
  background: rgba(255, 77, 79, 0.1);
  color: #ff4d4f;
}

.stat-icon.rate {
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

/* 卡片头部 */
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

/* 搜索栏 */
.search-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

/* 产品信息 */
.product-info {
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

.hash {
  font-family: monospace;
  font-size: 12px;
  word-break: break-all;
}
</style>
