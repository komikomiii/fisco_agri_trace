<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../../store/user'
import { useProductStore } from '../../store/product'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()
const productStore = useProductStore()

// 复制区块链地址
const copyAddress = () => {
  if (userStore.user?.blockchainAddress) {
    navigator.clipboard.writeText(userStore.user.blockchainAddress).then(() => {
      ElMessage.success('地址已复制到剪贴板')
    }).catch(() => {
      ElMessage.error('复制失败，请手动复制')
    })
  }
}

// 模拟统计数据
const stats = ref({
  producer: [
    { label: '原料品种', value: 12, icon: 'Grape', trend: '+3' },
    { label: '本月采收', value: 156, icon: 'Calendar', trend: '+28' },
    { label: '待出库', value: 43, icon: 'Box', trend: '-5' },
    { label: '质检通过', value: 98, icon: 'CircleCheck', suffix: '%' }
  ],
  processor: [
    { label: '待接收', value: 8, icon: 'Inbox', trend: '+2' },
    { label: '加工中', value: 15, icon: 'Loading', trend: '' },
    { label: '已完成', value: 234, icon: 'Select', trend: '+18' },
    { label: '出货批次', value: 67, icon: 'Van', trend: '+5' }
  ],
  inspector: [
    { label: '待检产品', value: 23, icon: 'Document', trend: '+7' },
    { label: '今日检测', value: 12, icon: 'Timer', trend: '+3' },
    { label: '合格率', value: 96.5, icon: 'Trophy', suffix: '%' },
    { label: '报告数', value: 458, icon: 'Tickets', trend: '+45' }
  ],
  seller: [
    { label: '库存品类', value: 45, icon: 'GoodsFilled', trend: '+2' },
    { label: '今日销售', value: 128, icon: 'ShoppingCart', trend: '+35' },
    { label: '销售额', value: 18.6, icon: 'Money', suffix: '万', trend: '+2.3' },
    { label: '客户数', value: 1256, icon: 'User', trend: '+86' }
  ],
  consumer: [
    { label: '溯源查询', value: 28, icon: 'Search', trend: '+5' },
    { label: '购买记录', value: 156, icon: 'List', trend: '+12' },
    { label: '收藏产品', value: 23, icon: 'Star', trend: '+3' },
    { label: '积分', value: 2680, icon: 'Medal', trend: '+150' }
  ]
})

const currentStats = computed(() => {
  const role = userStore.user?.role || 'consumer'
  return stats.value[role] || []
})

// 最近活动 - 根据角色显示不同内容
const activities = computed(() => {
  const role = userStore.user?.role || 'consumer'
  const activityMap = {
    producer: [
      { time: '10:30', content: '原料 有机番茄 已完成采收登记', type: 'success' },
      { time: '09:45', content: '原料 有机黄瓜 已确认上链', type: 'primary' },
      { time: '昨天 16:20', content: '原料 有机胡萝卜 已发送给加工商', type: 'info' }
    ],
    processor: [
      { time: '10:30', content: '番茄酱 500g 加工完成，已送检', type: 'success' },
      { time: '09:15', content: '接收新原料：有机番茄 500kg', type: 'primary' },
      { time: '昨天 17:00', content: '黄瓜脆片 加工记录已上链', type: 'info' }
    ],
    inspector: [
      { time: '11:00', content: '番茄酱 500g 检测完成：合格', type: 'success' },
      { time: '09:30', content: '开始检测：黄瓜脆片', type: 'primary' },
      { time: '昨天 15:00', content: '产品退回：农残超标，已通知加工商', type: 'warning' }
    ],
    seller: [
      { time: '10:45', content: '番茄酱 500g 入库登记完成', type: 'success' },
      { time: '09:20', content: '销售出库：黄瓜脆片 x 50', type: 'primary' },
      { time: '昨天 18:00', content: '生成溯源二维码：有机果蔬礼盒', type: 'info' }
    ],
    consumer: [
      { time: '10:30', content: '查询溯源：番茄酱 500g', type: 'success' },
      { time: '昨天 14:00', content: '收藏产品：有机蔬菜礼盒', type: 'primary' },
      { time: '前天', content: '浏览溯源详情：黄瓜脆片', type: 'info' }
    ]
  }
  return activityMap[role] || []
})

// 溯源统计图表数据
const chartData = ref({
  labels: ['1月', '2月', '3月', '4月', '5月', '6月'],
  values: [120, 200, 150, 280, 220, 350]
})

// 待办事项 - 根据角色显示
const todos = computed(() => {
  const role = userStore.user?.role || 'consumer'
  const todoMap = {
    producer: [
      { id: 1, title: '确认上链待发布的原料 (2)', done: false, priority: 'high' },
      { id: 2, title: '更新有机番茄产地信息', done: false, priority: 'medium' },
      { id: 3, title: '处理加工商接收确认', done: true, priority: 'low' }
    ],
    processor: [
      { id: 1, title: '接收待处理原料 (3)', done: false, priority: 'high' },
      { id: 2, title: '完成番茄酱加工记录', done: false, priority: 'medium' },
      { id: 3, title: '送检黄瓜脆片', done: true, priority: 'low' }
    ],
    inspector: [
      { id: 1, title: '待检测产品 (5)', done: false, priority: 'high' },
      { id: 2, title: '完成番茄酱检测报告', done: false, priority: 'medium' },
      { id: 3, title: '处理退回产品复检', done: false, priority: 'medium' }
    ],
    seller: [
      { id: 1, title: '待入库产品 (2)', done: false, priority: 'high' },
      { id: 2, title: '处理销售订单', done: false, priority: 'medium' },
      { id: 3, title: '生成产品二维码', done: true, priority: 'low' }
    ],
    consumer: [
      { id: 1, title: '查看收藏产品更新', done: false, priority: 'low' },
      { id: 2, title: '完成产品评价', done: false, priority: 'low' }
    ]
  }
  return todoMap[role] || []
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

// 最近产品链 - 根据角色筛选
const recentProducts = computed(() => {
  const role = userStore.user?.role || 'consumer'
  let chains = productStore.productChains || []

  // 根据角色筛选相关产品
  switch (role) {
    case 'producer':
      // 原料商：显示自己创建的产品
      chains = chains.filter(c => c.records.some(r => r.stage === 'producer'))
      break
    case 'processor':
      // 加工商：显示已接收或待接收的产品
      chains = chains.filter(c =>
        c.records.some(r => r.stage === 'processor') ||
        (c.status === 'on_chain' && c.currentStage === 'producer')
      )
      break
    case 'inspector':
      // 质检员：显示已检测或待检测的产品
      chains = chains.filter(c =>
        c.records.some(r => r.stage === 'inspector') ||
        c.records.some(r => r.action === 'send_inspect')
      )
      break
    case 'seller':
      // 销售商：显示已入库或可入库的产品
      chains = chains.filter(c =>
        c.records.some(r => r.stage === 'seller') ||
        c.records.some(r => r.action === 'inspect' && r.data?.result === 'pass')
      )
      break
    case 'consumer':
      // 消费者：显示已售出的可查询产品
      chains = chains.filter(c =>
        c.status === 'on_chain' && c.traceCode
      )
      break
  }

  return chains.slice(0, 4)
})

// 获取产品显示名称
const getProductName = (chain) => {
  const processRecord = chain.records.find(r => r.action === 'process')
  return processRecord?.data?.outputProduct || chain.productName
}

// 获取产品当前阶段
const getStageLabel = (chain) => {
  const stageMap = {
    producer: '原料登记',
    processor: '加工中',
    inspector: '质检中',
    seller: '销售中',
    sold: '已售出'
  }
  return stageMap[chain.currentStage] || '处理中'
}

// 获取阶段颜色
const getStageColor = (stage) => {
  const colorMap = {
    producer: '#52c41a',
    processor: '#1890ff',
    inspector: '#722ed1',
    seller: '#fa8c16',
    sold: '#909399'
  }
  return colorMap[stage] || '#909399'
}

// 获取产地
const getOrigin = (chain) => {
  return productStore.getMergedData(chain)?.origin || '-'
}

// 查看产品详情
const viewProduct = (chain) => {
  if (chain.traceCode) {
    router.push(`/dashboard/trace/${chain.traceCode}`)
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
        <el-timeline>
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
      </el-card>

      <!-- 中间 - 溯源趋势 -->
      <el-card class="chart-card">
        <template #header>
          <div class="card-header">
            <span class="card-title">
              <el-icon><TrendCharts /></el-icon>
              溯源查询趋势
            </span>
            <el-radio-group size="small">
              <el-radio-button label="周" />
              <el-radio-button label="月" />
              <el-radio-button label="年" />
            </el-radio-group>
          </div>
        </template>
        <div class="chart-placeholder">
          <div class="chart-bars">
            <div
              v-for="(value, index) in chartData.values"
              :key="index"
              class="chart-bar"
              :style="{ height: (value / 400 * 100) + '%' }"
            >
              <span class="bar-value">{{ value }}</span>
              <span class="bar-label">{{ chartData.labels[index] }}</span>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 右侧 - 待办事项 -->
      <el-card class="todo-card">
        <template #header>
          <div class="card-header">
            <span class="card-title">
              <el-icon><List /></el-icon>
              待办事项
            </span>
          </div>
        </template>
        <div class="todo-list">
          <div
            v-for="todo in todos"
            :key="todo.id"
            class="todo-item"
            :class="{ done: todo.done }"
          >
            <el-checkbox v-model="todo.done" />
            <span class="todo-text">{{ todo.title }}</span>
            <el-tag
              v-if="!todo.done"
              :type="todo.priority === 'high' ? 'danger' : todo.priority === 'medium' ? 'warning' : 'info'"
              size="small"
              effect="plain"
            >
              {{ todo.priority === 'high' ? '紧急' : todo.priority === 'medium' ? '普通' : '低' }}
            </el-tag>
          </div>
        </div>
        <el-empty v-if="todos.length === 0" description="暂无待办事项" :image-size="60" />
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

      <div v-if="recentProducts.length > 0" class="products-grid">
        <div
          v-for="chain in recentProducts"
          :key="chain.id"
          class="product-card"
          @click="viewProduct(chain)"
        >
          <div class="product-avatar" :style="{ background: getStageColor(chain.currentStage) }">
            <el-icon :size="24"><GoodsFilled /></el-icon>
          </div>
          <div class="product-info">
            <h4>{{ getProductName(chain) }}</h4>
            <p class="product-origin">{{ getOrigin(chain) }}</p>
            <div class="product-meta">
              <el-tag size="small" :color="getStageColor(chain.currentStage)" effect="dark">
                {{ getStageLabel(chain) }}
              </el-tag>
              <span v-if="chain.traceCode" class="trace-code">{{ chain.traceCode }}</span>
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

/* 图表区域 */
.chart-placeholder {
  height: 220px;
  display: flex;
  align-items: flex-end;
  padding: 20px 0;
}

.chart-bars {
  display: flex;
  justify-content: space-around;
  align-items: flex-end;
  width: 100%;
  height: 100%;
}

.chart-bar {
  width: 48px;
  background: linear-gradient(to top, var(--primary-color), var(--primary-light));
  border-radius: 8px 8px 0 0;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  transition: all 0.3s ease;
  min-height: 20px;
}

.chart-bar:hover {
  transform: scaleY(1.05);
  background: linear-gradient(to top, var(--primary-dark), var(--primary-color));
}

.bar-value {
  position: absolute;
  top: -24px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}

.bar-label {
  position: absolute;
  bottom: -24px;
  font-size: 12px;
  color: var(--text-muted);
}

/* 待办事项 */
.todo-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.todo-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--bg-color);
  border-radius: 10px;
  transition: all 0.2s ease;
}

.todo-item:hover {
  background: #f0f2f5;
}

.todo-item.done {
  opacity: 0.6;
}

.todo-item.done .todo-text {
  text-decoration: line-through;
  color: var(--text-muted);
}

.todo-text {
  flex: 1;
  font-size: 14px;
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
