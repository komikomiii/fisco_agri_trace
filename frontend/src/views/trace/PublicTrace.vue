<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const loading = ref(true)
const traceCode = ref(route.params.code)

// 复用Detail.vue的数据结构
const traceData = ref({
  product: {
    name: '番茄酱 500g',
    code: 'P20241201001',
    producer: '绿源加工厂',
    productionDate: '2024-12-01',
    shelfLife: '12个月'
  },
  verified: true,
  timeline: [
    { stage: '原料种植', date: '2024-03-15', operator: '张三农场' },
    { stage: '采收登记', date: '2024-11-28', operator: '张三农场' },
    { stage: '加工生产', date: '2024-12-01', operator: '绿源加工厂' },
    { stage: '质量检测', date: '2024-12-01', operator: '食品质检中心' },
    { stage: '入库销售', date: '2024-12-02', operator: '优鲜超市' }
  ]
})

onMounted(() => {
  setTimeout(() => loading.value = false, 500)
})
</script>

<template>
  <div class="public-trace" v-loading="loading">
    <div class="trace-container">
      <div class="header">
        <div class="logo">
          <el-icon :size="32" color="#2db84d"><Connection /></el-icon>
          <span>农链溯源</span>
        </div>
      </div>

      <div class="verify-badge" v-if="traceData.verified">
        <el-icon :size="48"><CircleCheck /></el-icon>
        <span>验证通过</span>
      </div>

      <div class="product-card">
        <h2>{{ traceData.product.name }}</h2>
        <p>溯源码：{{ traceCode }}</p>
        <div class="info-row">
          <span>生产商：{{ traceData.product.producer }}</span>
          <span>生产日期：{{ traceData.product.productionDate }}</span>
        </div>
      </div>

      <div class="timeline-simple">
        <div v-for="(item, index) in traceData.timeline" :key="index" class="timeline-step">
          <div class="step-dot"></div>
          <div class="step-content">
            <span class="step-title">{{ item.stage }}</span>
            <span class="step-info">{{ item.operator }} · {{ item.date }}</span>
          </div>
        </div>
      </div>

      <el-button type="primary" size="large" style="width: 100%">
        查看完整溯源信息
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.public-trace {
  min-height: 100vh;
  background: linear-gradient(135deg, #e8f5e9, #f1f8e9);
  display: flex;
  justify-content: center;
  padding: 20px;
}

.trace-container {
  max-width: 420px;
  width: 100%;
}

.header {
  text-align: center;
  margin-bottom: 24px;
}

.logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 20px;
  font-weight: 700;
  color: #2db84d;
}

.verify-badge {
  background: linear-gradient(135deg, #52c41a, #73d13d);
  color: white;
  padding: 24px;
  border-radius: 16px;
  text-align: center;
  margin-bottom: 20px;
}

.verify-badge span {
  display: block;
  font-size: 18px;
  font-weight: 600;
  margin-top: 8px;
}

.product-card {
  background: white;
  padding: 24px;
  border-radius: 16px;
  margin-bottom: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.product-card h2 {
  font-size: 22px;
  margin-bottom: 8px;
}

.product-card p {
  color: #909399;
  margin-bottom: 16px;
}

.info-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 14px;
  color: #606266;
}

.timeline-simple {
  background: white;
  padding: 24px;
  border-radius: 16px;
  margin-bottom: 20px;
}

.timeline-step {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding-bottom: 20px;
  position: relative;
}

.timeline-step:last-child {
  padding-bottom: 0;
}

.timeline-step:not(:last-child)::after {
  content: '';
  position: absolute;
  left: 6px;
  top: 20px;
  width: 2px;
  height: calc(100% - 8px);
  background: #e4e7ed;
}

.step-dot {
  width: 14px;
  height: 14px;
  background: #52c41a;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 4px;
}

.step-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.step-title {
  font-weight: 600;
  color: #303133;
}

.step-info {
  font-size: 13px;
  color: #909399;
}
</style>
