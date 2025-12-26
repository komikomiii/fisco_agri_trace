<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  traceCode: {
    type: String,
    default: ''
  },
  productName: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:visible', 'reject', 'terminate'])

const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
})

const actionType = ref('reject') // reject | terminate
const rejectForm = ref({
  rejectTo: 'processor',
  reason: ''
})
const terminateForm = ref({
  reason: '',
  disposal: ''
})

const rejectOptions = [
  { value: 'processor', label: '退回加工商', desc: '加工商重新处理后再次送检' },
  { value: 'producer', label: '退回原料商', desc: '原料商重新提供合格原料' }
]

const disposalOptions = [
  '销毁处理',
  '退回原料商处理',
  '降级处理',
  '其他'
]

watch(dialogVisible, (val) => {
  if (val) {
    // 重置表单
    actionType.value = 'reject'
    rejectForm.value = { rejectTo: 'processor', reason: '' }
    terminateForm.value = { reason: '', disposal: '' }
  }
})

const handleSubmit = () => {
  if (actionType.value === 'reject') {
    if (!rejectForm.value.reason) {
      return
    }
    emit('reject', {
      rejectTo: rejectForm.value.rejectTo,
      reason: rejectForm.value.reason
    })
  } else {
    if (!terminateForm.value.reason) {
      return
    }
    emit('terminate', {
      reason: terminateForm.value.reason,
      disposal: terminateForm.value.disposal
    })
  }
  dialogVisible.value = false
}
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    title="质检不合格处理"
    width="520px"
    :close-on-click-modal="false"
  >
    <div class="product-info">
      <el-icon><GoodsFilled /></el-icon>
      <span class="product-name">{{ productName }}</span>
      <el-tag type="info" size="small">{{ traceCode }}</el-tag>
    </div>

    <el-divider />

    <el-radio-group v-model="actionType" class="action-selector">
      <el-radio-button label="reject">
        <el-icon><RefreshLeft /></el-icon>
        退回处理
      </el-radio-button>
      <el-radio-button label="terminate">
        <el-icon><CircleClose /></el-icon>
        终止流程
      </el-radio-button>
    </el-radio-group>

    <!-- 退回表单 -->
    <div v-if="actionType === 'reject'" class="form-section">
      <div class="form-tip">
        <el-icon><InfoFilled /></el-icon>
        <span>产品将退回指定环节重新处理，处理完成后可再次送检。</span>
      </div>

      <el-form :model="rejectForm" label-position="top">
        <el-form-item label="退回至" required>
          <el-radio-group v-model="rejectForm.rejectTo" class="reject-options">
            <div
              v-for="option in rejectOptions"
              :key="option.value"
              class="reject-option"
              :class="{ active: rejectForm.rejectTo === option.value }"
              @click="rejectForm.rejectTo = option.value"
            >
              <el-radio :label="option.value">
                <span class="option-label">{{ option.label }}</span>
                <span class="option-desc">{{ option.desc }}</span>
              </el-radio>
            </div>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="退回原因" required>
          <el-input
            v-model="rejectForm.reason"
            type="textarea"
            :rows="3"
            placeholder="请详细说明退回原因，例如：农药残留超标，检测值0.3mg/kg，标准≤0.1mg/kg"
          />
        </el-form-item>
      </el-form>
    </div>

    <!-- 终止表单 -->
    <div v-else class="form-section">
      <div class="form-tip danger">
        <el-icon><WarningFilled /></el-icon>
        <span>终止后产品链将永久结束，无法继续流转，但所有记录将保留在链上。</span>
      </div>

      <el-form :model="terminateForm" label-position="top">
        <el-form-item label="终止原因" required>
          <el-input
            v-model="terminateForm.reason"
            type="textarea"
            :rows="3"
            placeholder="请详细说明终止原因，例如：重金属严重超标，存在食品安全风险"
          />
        </el-form-item>

        <el-form-item label="后续处理方式">
          <el-select v-model="terminateForm.disposal" placeholder="请选择" style="width: 100%">
            <el-option
              v-for="option in disposalOptions"
              :key="option"
              :label="option"
              :value="option"
            />
          </el-select>
        </el-form-item>
      </el-form>
    </div>

    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button
        :type="actionType === 'terminate' ? 'danger' : 'warning'"
        @click="handleSubmit"
      >
        <el-icon>
          <RefreshLeft v-if="actionType === 'reject'" />
          <CircleClose v-else />
        </el-icon>
        {{ actionType === 'reject' ? '确认退回' : '确认终止' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.product-info {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--bg-color);
  border-radius: 8px;
}

.product-info .el-icon {
  font-size: 24px;
  color: var(--primary-color);
}

.product-name {
  font-size: 16px;
  font-weight: 600;
  flex: 1;
}

.action-selector {
  width: 100%;
  display: flex;
  margin-bottom: 20px;
}

.action-selector .el-radio-button {
  flex: 1;
}

.action-selector :deep(.el-radio-button__inner) {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.form-section {
  min-height: 200px;
}

.form-tip {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 16px;
  background: #e6f7ff;
  border: 1px solid #91d5ff;
  border-radius: 8px;
  margin-bottom: 20px;
  font-size: 13px;
  color: #0958d9;
}

.form-tip.danger {
  background: #fff2f0;
  border-color: #ffccc7;
  color: #cf1322;
}

.form-tip .el-icon {
  font-size: 16px;
  margin-top: 2px;
}

.reject-options {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.reject-option {
  padding: 16px;
  border: 2px solid var(--border-color);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.reject-option:hover {
  border-color: #faad14;
  background: rgba(250, 173, 20, 0.04);
}

.reject-option.active {
  border-color: #faad14;
  background: rgba(250, 173, 20, 0.08);
}

.reject-option :deep(.el-radio) {
  width: 100%;
}

.reject-option :deep(.el-radio__label) {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.option-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.option-desc {
  font-size: 12px;
  color: var(--text-muted);
}
</style>
