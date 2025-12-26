<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  originalData: {
    type: Object,
    default: () => ({})
  },
  dataLabels: {
    type: Object,
    default: () => ({})
  },
  editableFields: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:visible', 'submit'])

const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
})

const amendForm = ref({
  reason: '',
  changes: {}
})

// 初始化修改表单
watch(dialogVisible, (val) => {
  if (val) {
    amendForm.value = {
      reason: '',
      changes: { ...props.originalData }
    }
  }
})

// 检查是否有修改
const hasChanges = computed(() => {
  return Object.keys(props.originalData).some(key =>
    amendForm.value.changes[key] !== props.originalData[key]
  )
})

// 获取修改的字段
const changedFields = computed(() => {
  const changes = []
  for (const key of Object.keys(props.originalData)) {
    if (amendForm.value.changes[key] !== props.originalData[key]) {
      changes.push({
        key,
        label: props.dataLabels[key] || key,
        oldValue: props.originalData[key],
        newValue: amendForm.value.changes[key]
      })
    }
  }
  return changes
})

const handleSubmit = () => {
  if (!amendForm.value.reason) {
    return
  }
  if (!hasChanges.value) {
    return
  }

  emit('submit', {
    reason: amendForm.value.reason,
    changes: amendForm.value.changes,
    changedFields: changedFields.value
  })
  dialogVisible.value = false
}

const resetField = (key) => {
  amendForm.value.changes[key] = props.originalData[key]
}
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    title="修正信息"
    width="600px"
    :close-on-click-modal="false"
  >
    <div class="amend-tip">
      <el-icon><InfoFilled /></el-icon>
      <span>修正记录将作为新记录追加到链上，原记录保持不变。消费者可查看完整修改历史。</span>
    </div>

    <el-form :model="amendForm" label-position="top">
      <!-- 可编辑字段 -->
      <div class="edit-section">
        <h4>修改信息</h4>
        <div class="fields-grid">
          <el-form-item
            v-for="field in editableFields"
            :key="field.key"
            :label="dataLabels[field.key] || field.key"
          >
            <template v-if="field.type === 'input'">
              <el-input v-model="amendForm.changes[field.key]" :placeholder="field.placeholder" />
            </template>
            <template v-else-if="field.type === 'number'">
              <el-input-number v-model="amendForm.changes[field.key]" :min="0" style="width: 100%" />
            </template>
            <template v-else-if="field.type === 'select'">
              <el-select v-model="amendForm.changes[field.key]" style="width: 100%">
                <el-option
                  v-for="opt in field.options"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>
            </template>
            <template v-else-if="field.type === 'date'">
              <el-date-picker
                v-model="amendForm.changes[field.key]"
                type="date"
                style="width: 100%"
                value-format="YYYY-MM-DD"
              />
            </template>
            <template v-else-if="field.type === 'textarea'">
              <el-input
                v-model="amendForm.changes[field.key]"
                type="textarea"
                :rows="3"
              />
            </template>
            <template v-else>
              <el-input v-model="amendForm.changes[field.key]" />
            </template>
          </el-form-item>
        </div>
      </div>

      <!-- 修改对比 -->
      <div v-if="changedFields.length > 0" class="changes-preview">
        <h4>
          <el-icon><Edit /></el-icon>
          修改预览
        </h4>
        <div class="changes-list">
          <div v-for="change in changedFields" :key="change.key" class="change-item">
            <span class="change-label">{{ change.label }}</span>
            <div class="change-values">
              <span class="old-value">
                <el-icon><Close /></el-icon>
                {{ change.oldValue || '(空)' }}
              </span>
              <el-icon class="arrow"><Right /></el-icon>
              <span class="new-value">
                <el-icon><Check /></el-icon>
                {{ change.newValue || '(空)' }}
              </span>
            </div>
            <el-button
              type="text"
              size="small"
              @click="resetField(change.key)"
            >
              撤销
            </el-button>
          </div>
        </div>
      </div>

      <!-- 修正原因 -->
      <el-form-item label="修正原因" required class="reason-field">
        <el-input
          v-model="amendForm.reason"
          type="textarea"
          :rows="2"
          placeholder="请说明修正原因，例如：产地信息录入错误，更正为正确地址"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button
        type="primary"
        :disabled="!hasChanges || !amendForm.reason"
        @click="handleSubmit"
      >
        <el-icon><Connection /></el-icon>
        提交修正
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.amend-tip {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 16px;
  background: #fffbe6;
  border: 1px solid #ffe58f;
  border-radius: 8px;
  margin-bottom: 24px;
  font-size: 13px;
  color: #ad6800;
}

.amend-tip .el-icon {
  font-size: 16px;
  margin-top: 2px;
}

.edit-section h4,
.changes-preview h4 {
  font-size: 14px;
  color: var(--text-primary);
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.fields-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.changes-preview {
  margin: 24px 0;
  padding: 16px;
  background: var(--bg-color);
  border-radius: 12px;
}

.changes-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.change-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: white;
  border-radius: 8px;
}

.change-label {
  font-size: 13px;
  color: var(--text-secondary);
  min-width: 80px;
}

.change-values {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
}

.old-value,
.new-value {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 13px;
}

.old-value {
  background: #fff1f0;
  color: #cf1322;
  text-decoration: line-through;
}

.new-value {
  background: #f6ffed;
  color: #389e0d;
}

.arrow {
  color: var(--text-muted);
}

.reason-field {
  margin-top: 24px;
}
</style>
