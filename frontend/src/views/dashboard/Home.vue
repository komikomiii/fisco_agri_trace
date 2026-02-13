<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../../store/user'
import { ElMessage } from 'element-plus'
import { producerApi } from '../../api/producer'
import processorApi from '../../api/processor'
import inspectorApi from '../../api/inspector'
import { sellerApi } from '../../api/seller'
import { blockchainApi } from '../../api/blockchain'

const router = useRouter()
const userStore = useUserStore()

const copyAddress = () => {
  if (userStore.user?.blockchainAddress) {
    navigator.clipboard.writeText(userStore.user.blockchainAddress).then(() => {
      ElMessage.success('地址已复制到剪贴板')
    }).catch(() => {
      ElMessage.error('复制失败，请手动复制')
    })
  }
}

const currentStats = ref([])

const fetchStats = async () => {
  const role = userStore.user?.role
  try {
    if (role === 'producer') {
      const data = await producerApi.getStatistics()
      currentStats.value = [
        { label: '产品总数', value: data.total || 0, icon: 'Grape' },
        { label: '已上链', value: data.on_chain || 0, icon: 'CircleCheckFilled' },
        { label: '草稿', value: data.draft || 0, icon: 'EditPen' },
        { label: '已终止', value: data.terminated || 0, icon: 'RemoveFilled' }
      ]
    } else if (role === 'processor') {
      const data = await processorApi.getStatistics()
      currentStats.value = [
        { label: '加工中', value: data.in_processing || 0, icon: 'Loading' },
        { label: '已接收', value: data.total_received || 0, icon: 'Select' }
      ]
    } else if (role === 'inspector') {
      const data = await inspectorApi.getStatistics()
      currentStats.value = [
        { label: '待检产品', value: data.pending_count || 0, icon: 'Document' },
        { label: '已检测', value: data.completed_count || 0, icon: 'Select' },
        { label: '合格', value: data.qualified_count || 0, icon: 'CircleCheck' },
        { label: '合格率', value: data.pass_rate || 0, icon: 'Trophy', suffix: '%' }
      ]
    } else if (role === 'seller') {
      const data = await sellerApi.getStatistics()
      currentStats.value = [
        { label: '库存', value: data.inventory_count || 0, icon: 'GoodsFilled' },
        { label: '已售出', value: data.sold_count || 0, icon: 'ShoppingCart' },
        { label: '总销量', value: data.total_sales_quantity || 0, icon: 'Money' }
      ]
    } else {
      const history = JSON.parse(localStorage.getItem('trace_history') || '[]')
      currentStats.value = [
        { label: '溯源查询', value: history.length, icon: 'Search' }
      ]
    }
  } catch {
    currentStats.value = []
  }
}

const recentOnChainProducts = ref([])

const fetchRecentProducts = async () => {
  try {
    const products = await blockchainApi.getOnChainProducts(4, 0)
    recentOnChainProducts.value = products || []
  } catch {
    recentOnChainProducts.value = []
  }
}

onMounted(async () => {
  await fetchStats()
  fetchActivities()
  fetchRecentProducts()
})

const activities = ref([])

const actionLabelMap = {
  create: '创建产品', harvest: '采收出库', receive: '接收原料', process: '加工处理',
  send_inspect: '送检', start_inspect: '开始检测', inspect: '检测完成',
  reject: '退回处理', terminate: '终止链条', stock_in: '入库登记', sell: '销售出库', amend: '信息修正'
}

const fetchActivities = async () => {
  const role = userStore.user?.role
  try {
    let products = []
    if (role === 'producer') products = await producerApi.getProducts()
    else if (role === 'processor') products = await processorApi.getReceivedProducts()
    else if (role === 'inspector') products = await inspectorApi.getCompletedProducts()
    else if (role === 'seller') products = await sellerApi.getSoldProducts()
    else {
      const history = JSON.parse(localStorage.getItem('trace_history') || '[]')
      activities.value = history.slice(0, 5).map(h => ({
        time: h.scanDate || '-',
        content: `查询溯源：${h.name || h.code}`,
        type: h.result === 'verified' ? 'success' : 'danger'
      }))
      return
    }
    if (!Array.isArray(products)) products = []
    activities.value = products.slice(0, 5).map(p => {
      const statusMap = {
        DRAFT: { text: '创建草稿', type: 'info' },
        ON_CHAIN: { text: '已上链', type: 'success' },
        PENDING_CHAIN: { text: '正在上链', type: 'warning' },
        INVALIDATED: { text: '已作废', type: 'danger' }
      }
      const info = statusMap[p.status] || { text: p.status || '更新', type: 'info' }
      const time = p.updated_at || p.created_at || ''
      const timeStr = time ? new Date(time).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '-'
      return { time: timeStr, content: `${p.name || '产品'} - ${info.text}`, type: info.type }
    })
  } catch {
    activities.value = []
  }
}

const chartBarColors = ['#52c41a', '#1890ff', '#722ed1', '#fa8c16', '#eb2f96', '#13c2c2']

const chartMax = computed(() => {
  const vals = currentStats.value.map(s => Number(s.value) || 0)
  return Math.max(...vals, 1)
})

const quickActions = computed(() => {
  const role = userStore.user?.role
  const map = {
    producer: [
      { label: '创建原料', icon: 'Plus', path: '/dashboard/producer/products' },
      { label: '原料管理', icon: 'Grape', path: '/dashboard/producer/products' }
    ],
    processor: [
      { label: '接收原料', icon: 'Inbox', path: '/dashboard/processor/receive' },
      { label: '加工记录', icon: 'SetUp', path: '/dashboard/processor/process' }
    ],
    inspector: [
      { label: '待检产品', icon: 'Document', path: '/dashboard/inspector/pending' }
    ],
    seller: [
      { label: '库存管理', icon: 'GoodsFilled', path: '/dashboard/seller/inventory' }
    ],
    consumer: [
      { label: '扫码溯源', icon: 'Search', path: '/dashboard/consumer/scan' },
      { label: '查询记录', icon: 'Clock', path: '/dashboard/consumer/history' }
    ]
  }
  return map[role] || map.consumer
})

const greetingText = computed(() => {
  const hour = new Date().getHours()
  if (hour < 12) return '早上好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

const roleColors = {
  producer: ['#52c41a', '#73d13d'],
  processor: ['#1890ff', '#40a9ff'],
  inspector: ['#722ed1', '#9254de'],
  seller: ['#fa8c16', '#ffa940'],
  consumer: ['#eb2f96', '#f759ab']
}

const getGradient = (index) => {
  const role = userStore.user?.role || 'consumer'
  const colors = roleColors[role] || ['#2db84d', '#67d17e']
  return `linear-gradient(135deg, ${colors[0]}, ${colors[1]})`
}

const stageNameMap = {
  0: 'producer', 1: 'processor', 2: 'inspector', 3: 'seller', 4: 'sold'
}

const getProductName = (product) => product.name || '-'

const getStageLabel = (product) => {
  const stage = stageNameMap[product.current_stage] || product.current_stage
  const map = { producer: '原料登记', processor: '加工中', inspector: '质检中', seller: '销售中', sold: '已售出' }
  return map[stage] || '处理中'
}

const getStageColor = (product) => {
  const stage = stageNameMap[product.current_stage] || product.current_stage
  const map = { producer: '#52c41a', processor: '#1890ff', inspector: '#722ed1', seller: '#fa8c16', sold: '#909399' }
  return map[stage] || '#909399'
}

const viewProduct = (product) => {
  if (product.trace_code) {
    router.push(`/trace/${product.trace_code}`)
  }
}

// 底部卡片标题和描述
const bottomCardInfo = computed(() => {
  const role = userStore.user?.role || 'consumer'
  const infoMap = {
    producer: { title: '我的原料', desc: '最近登记的原料信息', icon: 'Grape' },
    processor: { title: '加工产品', desc: '最近加工的产品信息', icon: 'SetUp' },
    inspector: { title: '检测产品', desc: '最近检测的产品信息', icon: 'DocumentChecked' },
    seller: { title: '库存产品', desc: '最近入库的产品信息', icon: 'GoodsFilled' },
    consumer: { title: '可查产品', desc: '最近上链的可溯源产品', icon: 'Search' }
  }
  return infoMap[role] || infoMap.consumer
})
</script>

<template>
  <div class="home-container">
    <!-- 欢迎区域 -->
    <div class="welcome-section">
      <div class="welcome-text">
        <h1>{{ greetingText }}，{{ userStore.user?.name }} !</h1>
        <p>欢迎使用农产品溯源平台，这是您今天的工作概览</p>
        <div v-if="userStore.user?.blockchainAddress" class="blockchain-address-display">
          <el-icon><Wallet /></el-icon>
          <span class="address-label">区块链地址：</span>
          <span class="address-value">{{ userStore.user?.blockchainAddress }}</span>
          <el-button
            text
            size="small"
            @click="copyAddress"
            class="copy-btn"
          >
            <el-icon><DocumentCopy /></el-icon>
          </el-button>
        </div>
      </div>
      <div class="welcome-date">
        <el-icon :size="20"><Calendar /></el-icon>
        <span>{{ new Date().toLocaleDateString('zh-CN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }) }}</span>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div
        v-for="(stat, index) in currentStats"
        :key="index"
        class="stat-card"
        :style="{ background: getGradient(index) }"
      >
        <div class="stat-icon">
          <el-icon :size="32"><component :is="stat.icon" /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">
            {{ stat.value }}<span class="stat-suffix">{{ stat.suffix || '' }}</span>
          </div>
          <div class="stat-label">{{ stat.label }}</div>
        </div>
        <div v-if="stat.trend" class="stat-trend" :class="{ down: stat.trend.startsWith('-') }">
          <el-icon v-if="stat.trend.startsWith('-')"><Bottom /></el-icon>
          <el-icon v-else><Top /></el-icon>
          {{ stat.trend }}
        </div>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="content-grid">
      <!-- 左侧 - 最近活动 -->
      <el-card class="activity-card">
        <template #header>
          <div class="card-header">
            <span class="card-title">
              <el-icon><Clock /></el-icon>
              最近活动
            </span>
          </div>
        </template>
        <el-timeline v-if="activities.length > 0">
          <el-timeline-item
            v-for="(activity, index) in activities"
            :key="index"
            :type="activity.type"
            :timestamp="activity.time"
            placement="top"
          >
            {{ activity.content }}
          </el-timeline-item>
        </el-timeline>
        <el-empty v-else description="暂无最近活动" :image-size="60" />
      </el-card>

      <el-card class="chart-card">
        <template #header>
          <div class="card-header">
            <span class="card-title">
              <el-icon><TrendCharts /></el-icon>
              数据概览
            </span>
          </div>
        </template>
        <div class="chart-area" v-if="currentStats.length > 0">
          <div class="chart-bars">
            <div
              v-for="(stat, index) in currentStats"
              :key="index"
              class="chart-bar-wrapper"
            >
              <span class="bar-value">{{ stat.value }}{{ stat.suffix || '' }}</span>
              <div
                class="chart-bar"
                :style="{
                  height: Math.max((Number(stat.value) / chartMax) * 100, 8) + '%',
                  background: `linear-gradient(to top, ${chartBarColors[index % chartBarColors.length]}, ${chartBarColors[index % chartBarColors.length]}cc)`
                }"
              ></div>
              <span class="bar-label">{{ stat.label }}</span>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无数据" :image-size="60" />
      </el-card>

      <el-card class="todo-card">
        <template #header>
          <div class="card-header">
            <span class="card-title">
              <el-icon><Promotion /></el-icon>
              快捷操作
            </span>
          </div>
        </template>
        <div class="quick-actions">
          <div
            v-for="action in quickActions"
            :key="action.path"
            class="quick-action-item"
            @click="router.push(action.path)"
          >
            <div class="action-icon">
              <el-icon :size="24"><component :is="action.icon" /></el-icon>
            </div>
            <span class="action-label">{{ action.label }}</span>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 最近产品 -->
    <el-card class="products-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">
            <el-icon><component :is="bottomCardInfo.icon" /></el-icon>
            {{ bottomCardInfo.title }}
          </span>
          <span class="card-desc">{{ bottomCardInfo.desc }}</span>
        </div>
      </template>

      <div v-if="recentOnChainProducts.length > 0" class="products-grid">
        <div
          v-for="product in recentOnChainProducts"
          :key="product.trace_code"
          class="product-card"
          @click="viewProduct(product)"
        >
          <div class="product-avatar" :style="{ background: getStageColor(product) }">
            <el-icon :size="24"><GoodsFilled /></el-icon>
          </div>
          <div class="product-info">
            <h4>{{ getProductName(product) }}</h4>
            <p class="product-origin">{{ product.origin || '-' }}</p>
            <div class="product-meta">
              <el-tag size="small" :color="getStageColor(product)" effect="dark">
                {{ getStageLabel(product) }}
              </el-tag>
              <span v-if="product.trace_code" class="trace-code">{{ product.trace_code }}</span>
            </div>
          </div>
          <el-icon class="arrow-icon"><ArrowRight /></el-icon>
        </div>
      </div>

      <el-empty v-else description="暂无相关产品" :image-size="80" />
    </el-card>
  </div>
</template>

<style scoped>
.home-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 欢迎区域 */
.welcome-section {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 8px 0;
}

.welcome-text h1 {
  font-size: 26px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.welcome-text p {
  color: var(--text-muted);
  font-size: 14px;
}

/* 区块链地址显示 */
.blockchain-address-display {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding: 10px 16px;
  background: linear-gradient(135deg, rgba(45, 184, 77, 0.08), rgba(45, 184, 77, 0.03));
  border: 1px solid rgba(45, 184, 77, 0.2);
  border-radius: 10px;
  max-width: 600px;
}

.blockchain-address-display .el-icon {
  color: var(--primary-color);
  font-size: 18px;
}

.address-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.address-value {
  flex: 1;
  font-size: 12px;
  color: var(--primary-color);
  font-family: 'Courier New', monospace;
  word-break: break-all;
  line-height: 1.5;
}

.copy-btn {
  padding: 4px 8px;
  color: var(--primary-color);
}

.copy-btn:hover {
  background: rgba(45, 184, 77, 0.1);
}

.welcome-date {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 14px;
  background: white;
  padding: 10px 16px;
  border-radius: 10px;
  box-shadow: var(--shadow-sm);
}

/* 统计卡片 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.stat-card {
  padding: 24px;
  border-radius: 16px;
  color: white;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: flex-start;
  gap: 16px;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.15);
}

.stat-card::before {
  content: '';
  position: absolute;
  top: -40%;
  right: -20%;
  width: 120px;
  height: 120px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 50%;
}

.stat-icon {
  width: 56px;
  height: 56px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  line-height: 1.2;
}

.stat-suffix {
  font-size: 16px;
  font-weight: 400;
  margin-left: 2px;
}

.stat-label {
  font-size: 14px;
  opacity: 0.85;
  margin-top: 4px;
}

.stat-trend {
  position: absolute;
  top: 16px;
  right: 16px;
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 13px;
  padding: 4px 8px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 20px;
}

.stat-trend.down {
  background: rgba(255, 77, 79, 0.3);
}

/* 内容网格 */
.content-grid {
  display: grid;
  grid-template-columns: 1fr 1.5fr 1fr;
  gap: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.card-desc {
  font-size: 13px;
  color: var(--text-muted);
}

/* 活动时间线 */
.activity-card :deep(.el-timeline-item__content) {
  font-size: 13px;
  color: var(--text-secondary);
}

.chart-area {
  padding: 16px 0 8px;
  height: 200px;
}

.chart-bars {
  display: flex;
  justify-content: space-around;
  align-items: flex-end;
  height: 100%;
  gap: 12px;
  padding: 0 8px;
}

.chart-bar-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  flex: 1;
  height: 100%;
  justify-content: flex-end;
}

.bar-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.chart-bar {
  width: 100%;
  max-width: 48px;
  min-height: 8px;
  border-radius: 6px 6px 2px 2px;
  transition: height 0.6s ease;
}

.bar-label {
  font-size: 12px;
  color: var(--text-muted);
  text-align: center;
  white-space: nowrap;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.quick-action-item {
  display: flex;
  align-items: center;
  gap: 14px;
  cursor: pointer;
  padding: 14px 16px;
  border-radius: 12px;
  background: var(--bg-color);
  transition: all 0.3s ease;
}

.quick-action-item:hover {
  background: #e8f5e9;
  transform: translateX(4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.action-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: linear-gradient(135deg, var(--primary-color), var(--primary-light, #67d17e));
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.action-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

/* 产品卡片 */
.products-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.product-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: var(--bg-color);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.product-card:hover {
  background: #e8f5e9;
  transform: translateX(4px);
}

.product-avatar {
  width: 52px;
  height: 52px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.product-info {
  flex: 1;
  min-width: 0;
}

.product-info h4 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.product-origin {
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.product-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.trace-code {
  font-size: 11px;
  font-family: monospace;
  color: var(--text-muted);
}

.arrow-icon {
  color: var(--text-muted);
  font-size: 16px;
}

/* 响应式 */
@media (max-width: 1400px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .content-grid {
    grid-template-columns: 1fr;
  }

  .products-grid {
    grid-template-columns: 1fr;
  }
}
</style>
