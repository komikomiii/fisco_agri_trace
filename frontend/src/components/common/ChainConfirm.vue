<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: '确认上链'
  },
  data: {
    type: Object,
    default: () => ({})
  },
  dataLabels: {
    type: Object,
    default: () => ({})
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:visible', 'confirm', 'cancel'])

const status = ref('pending') // pending | loading | success | error
const resultData = ref(null)

const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
})

// 格式化显示数据
const displayData = computed(() => {
  const result = []
  for (const [key, value] of Object.entries(props.data)) {
    if (value !== null && value !== undefined && value !== '') {
      result.push({
        key,
        label: props.dataLabels[key] || key,
        value: typeof value === 'object' ? JSON.stringify(value) : value
      })
    }
  }
  return result
})

const handleConfirm = async () => {
  status.value = 'loading'
  emit('confirm')
}

const handleCancel = () => {
  status.value = 'pending'
  emit('cancel')
  dialogVisible.value = false
}

const handleSuccess = (data) => {
  status.value = 'success'
  resultData.value = data
}

const handleError = (error) => {
  status.value = 'error'
  resultData.value = { error: error.message || '上链失败' }
}

const handleClose = () => {
  status.value = 'pending'
  resultData.value = null
  dialogVisible.value = false
}

// 暴露方法给父组件
defineExpose({
  handleSuccess,
  handleError
})
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    :title="title"
    width="520px"
    :close-on-click-modal="false"
    :close-on-press-escape="status !== 'loading'"
    :show-close="status !== 'loading'"
    @close="handleClose"
  >
    <!-- 待确认状态 -->
    <div v-if="status === 'pending'" class="confirm-content">
      <div class="warning-banner">
        <el-icon :size="20"><Warning /></el-icon>
        <span>数据上链后将无法修改，请确认信息无误</span>
      </div>

      <div class="data-preview">
        <h4>即将上链的数据：</h4>
        <div class="data-list">
          <div v-for="item in displayData" :key="item.key" class="data-item">
            <span class="data-label">{{ item.label }}</span>
            <span class="data-value">{{ item.value }}</span>
          </div>
        </div>
      </div>

      <div class="chain-info">
        <el-icon><Connection /></el-icon>
        <span>数据将被记录到 FISCO BCOS 区块链</span>
      </div>
    </div>

    <!-- 上链中状态 -->
    <div v-else-if="status === 'loading'" class="loading-content">
      <div class="loading-animation">
        <div class="chain-icon">
          <el-icon :size="48" class="rotating"><Loading /></el-icon>
        </div>
        <div class="loading-text">
          <h3>正在上链...</h3>
          <p>数据正在写入区块链，请稍候</p>
        </div>
      </div>
      <div class="loading-steps">
        <div class="step active">
          <el-icon><Check /></el-icon>
          <span>数据验证</span>
        </div>
        <div class="step active">
          <el-icon><Loading class="rotating" /></el-icon>
          <span>写入区块链</span>
        </div>
        <div class="step">
          <el-icon><Clock /></el-icon>
          <span>确认完成</span>
        </div>
      </div>
    </div>

    <!-- 成功状态 -->
    <div v-else-if="status === 'success'" class="success-content">
      <div class="success-icon">
        <el-icon :size="64" color="#52c41a"><CircleCheckFilled /></el-icon>
      </div>
      <h3>上链成功</h3>
      <p>数据已成功写入区块链</p>

      <div v-if="resultData" class="result-info">
        <div class="result-item" v-if="resultData.traceCode">
          <span class="result-label">溯源码</span>
          <span class="result-value code">{{ resultData.traceCode }}</span>
        </div>
        <div class="result-item" v-if="resultData.txHash">
          <span class="result-label">交易哈希</span>
          <span class="result-value hash">{{ resultData.txHash }}</span>
        </div>
        <div class="result-item" v-if="resultData.blockNumber">
          <span class="result-label">区块高度</span>
          <span class="result-value">{{ resultData.blockNumber }}</span>
        </div>
      </div>
    </div>

    <!-- 失败状态 -->
    <div v-else-if="status === 'error'" class="error-content">
      <div class="error-icon">
        <el-icon :size="64" color="#f5222d"><CircleCloseFilled /></el-icon>
      </div>
      <h3>上链失败</h3>
      <p>{{ resultData?.error || '请稍后重试' }}</p>
    </div>

    <template #footer>
      <template v-if="status === 'pending'">
        <el-button @click="handleCancel">取消</el-button>
        <el-button type="primary" @click="handleConfirm">
          <el-icon><Connection /></el-icon>
          确认上链
        </el-button>
      </template>
      <template v-else-if="status === 'success' || status === 'error'">
        <el-button type="primary" @click="handleClose">完成</el-button>
      </template>
    </template>
  </el-dialog>
</template>

<style scoped>
.confirm-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.warning-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: #fff7e6;
  border: 1px solid #ffd591;
  border-radius: 8px;
  color: #d46b08;
  font-size: 14px;
}

.data-preview h4 {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.data-list {
  background: var(--bg-color);
  border-radius: 8px;
  padding: 16px;
}

.data-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px dashed var(--border-color);
}

.data-item:last-child {
  border-bottom: none;
}

.data-label {
  color: var(--text-muted);
  font-size: 13px;
}

.data-value {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 500;
}

.chain-info {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
  font-size: 13px;
}

/* 加载状态 */
.loading-content {
  text-align: center;
  padding: 20px;
}

.loading-animation {
  margin-bottom: 30px;
}

.chain-icon {
  width: 80px;
  height: 80px;
  margin: 0 auto 16px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.rotating {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.loading-text h3 {
  font-size: 18px;
  margin-bottom: 8px;
}

.loading-text p {
  color: var(--text-muted);
}

.loading-steps {
  display: flex;
  justify-content: center;
  gap: 40px;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
  font-size: 13px;
}

.step.active {
  color: var(--primary-color);
}

.step .el-icon {
  font-size: 20px;
}

/* 成功状态 */
.success-content,
.error-content {
  text-align: center;
  padding: 20px;
}

.success-icon,
.error-icon {
  margin-bottom: 16px;
}

.success-content h3,
.error-content h3 {
  font-size: 20px;
  margin-bottom: 8px;
}

.success-content p,
.error-content p {
  color: var(--text-muted);
  margin-bottom: 24px;
}

.result-info {
  background: var(--bg-color);
  border-radius: 12px;
  padding: 20px;
  text-align: left;
}

.result-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-color);
}

.result-item:last-child {
  border-bottom: none;
}

.result-label {
  color: var(--text-muted);
  font-size: 13px;
}

.result-value {
  font-size: 14px;
  font-weight: 500;
}

.result-value.code {
  color: var(--primary-color);
  font-family: monospace;
}

.result-value.hash {
  color: #667eea;
  font-family: monospace;
  font-size: 12px;
}
</style>
