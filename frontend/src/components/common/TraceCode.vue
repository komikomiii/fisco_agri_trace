<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  code: {
    type: String,
    default: ''
  },
  showQrcode: {
    type: Boolean,
    default: true
  },
  size: {
    type: String,
    default: 'default' // small | default | large
  }
})

const emit = defineEmits(['viewDetail', 'generateQrcode'])

const qrcodeVisible = ref(false)

const copyCode = async () => {
  try {
    await navigator.clipboard.writeText(props.code)
    ElMessage.success('溯源码已复制到剪贴板')
  } catch (err) {
    ElMessage.error('复制失败，请手动复制')
  }
}

const showQrcodeDialog = () => {
  qrcodeVisible.value = true
  emit('generateQrcode', props.code)
}
</script>

<template>
  <div class="trace-code" :class="size">
    <div class="code-content">
      <el-icon class="code-icon"><Connection /></el-icon>
      <span class="code-text">{{ code || '暂无溯源码' }}</span>
    </div>

    <div v-if="code" class="code-actions">
      <el-tooltip content="复制溯源码" placement="top">
        <el-button :icon="DocumentCopy" circle size="small" @click="copyCode" />
      </el-tooltip>
      <el-tooltip v-if="showQrcode" content="查看二维码" placement="top">
        <el-button :icon="Camera" circle size="small" @click="showQrcodeDialog" />
      </el-tooltip>
      <el-tooltip content="查看详情" placement="top">
        <el-button :icon="View" circle size="small" @click="$emit('viewDetail', code)" />
      </el-tooltip>
    </div>

    <!-- 二维码弹窗 -->
    <el-dialog v-model="qrcodeVisible" title="产品溯源二维码" width="360px" center>
      <div class="qrcode-content">
        <div class="qrcode-placeholder">
          <!-- 这里后续替换为真实二维码 -->
          <div class="mock-qrcode">
            <el-icon :size="80" color="#2db84d"><Grid /></el-icon>
          </div>
          <p class="qrcode-tip">扫描二维码查看溯源信息</p>
        </div>
        <div class="qrcode-code">
          <span>{{ code }}</span>
        </div>
      </div>
      <template #footer>
        <el-button type="primary" :icon="Download">下载二维码</el-button>
        <el-button :icon="Printer">打印</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.trace-code {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: linear-gradient(135deg, rgba(45, 184, 77, 0.08), rgba(45, 184, 77, 0.02));
  border: 1px solid rgba(45, 184, 77, 0.2);
  border-radius: 8px;
}

.trace-code.small {
  padding: 4px 8px;
  gap: 8px;
}

.trace-code.small .code-text {
  font-size: 12px;
}

.trace-code.large {
  padding: 12px 16px;
}

.trace-code.large .code-text {
  font-size: 16px;
}

.code-content {
  display: flex;
  align-items: center;
  gap: 8px;
}

.code-icon {
  color: var(--primary-color);
}

.code-text {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 14px;
  font-weight: 600;
  color: var(--primary-color);
  letter-spacing: 0.5px;
}

.code-actions {
  display: flex;
  gap: 4px;
}

.code-actions .el-button {
  --el-button-bg-color: transparent;
  --el-button-border-color: transparent;
  --el-button-hover-bg-color: rgba(45, 184, 77, 0.1);
  --el-button-hover-border-color: transparent;
  color: var(--text-muted);
}

.code-actions .el-button:hover {
  color: var(--primary-color);
}

/* 二维码弹窗 */
.qrcode-content {
  text-align: center;
}

.qrcode-placeholder {
  padding: 24px;
}

.mock-qrcode {
  width: 180px;
  height: 180px;
  margin: 0 auto 16px;
  background: #f5f5f5;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px dashed #ddd;
}

.qrcode-tip {
  color: var(--text-muted);
  font-size: 13px;
}

.qrcode-code {
  padding: 12px;
  background: var(--bg-color);
  border-radius: 8px;
  font-family: monospace;
  font-size: 14px;
  color: var(--primary-color);
}
</style>
