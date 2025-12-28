<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Connection,
  DocumentCopy,
  Camera,
  View,
  Download,
  Printer
} from '@element-plus/icons-vue'
import VueQr from '@chenfengyuan/vue-qrcode'

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
const qrcodeCanvas = ref(null)
const qrcodeImage = ref(null)

// 二维码内容：指向公共溯源页面的 URL
const qrcodeValue = computed(() => {
  if (!props.code) return ''
  // 使用当前网站的 URL + 溯源页面路径
  const baseUrl = window.location.origin
  return `${baseUrl}/trace/${props.code}`
})

// 处理二维码生成完成事件
const onQrcodeReady = (canvas) => {
  qrcodeCanvas.value = canvas
}

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

// 下载二维码
const downloadQrcode = () => {
  // 查找 canvas 元素
  const canvas = document.querySelector('.qrcode-wrapper canvas')
  if (!canvas) {
    ElMessage.error('二维码未生成，请稍后重试')
    return
  }

  try {
    // 创建图片
    const image = canvas.toDataURL('image/png')

    // 创建下载链接
    const link = document.createElement('a')
    link.href = image
    link.download = `溯源码_${props.code}.png`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    ElMessage.success('二维码下载成功')
  } catch (err) {
    console.error('下载失败:', err)
    ElMessage.error('下载失败，请截图保存')
  }
}

// 打印二维码
const printQrcode = () => {
  // 查找 canvas 元素
  const canvas = document.querySelector('.qrcode-wrapper canvas')
  if (!canvas) {
    ElMessage.error('二维码未生成，请稍后重试')
    return
  }

  try {
    const image = canvas.toDataURL('image/png')

    // 创建新窗口进行打印
    const printWindow = window.open('', '_blank')
    if (!printWindow) {
      ElMessage.error('弹窗被拦截，请允许弹出窗口后重试')
      return
    }

    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>产品溯源二维码 - ${props.code}</title>
        <style>
          body {
            font-family: Arial, sans-serif;
            text-align: center;
            padding: 40px;
          }
          .qrcode-container {
            display: inline-block;
            padding: 30px;
            border: 2px solid #2db84d;
            border-radius: 16px;
          }
          .qrcode-image {
            margin-bottom: 20px;
          }
          .trace-code {
            font-size: 18px;
            font-weight: bold;
            color: #2db84d;
            margin-bottom: 10px;
          }
          .tip {
            color: #666;
            font-size: 14px;
          }
          @media print {
            body { padding: 0; }
            .qrcode-container { border: 2px solid #000; }
          }
        </style>
      </head>
      <body>
        <div class="qrcode-container">
          <img src="${image}" class="qrcode-image" width="200" height="200" />
          <div class="trace-code">${props.code}</div>
          <div class="tip">扫描二维码查看产品溯源信息</div>
        </div>
        <script>
          window.onload = function() {
            window.print()
            window.close()
          }
        <\/script>
      </body>
      </html>
    `)
    printWindow.document.close()
  } catch (err) {
    console.error('打印失败:', err)
    ElMessage.error('打印失败')
  }
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
    <el-dialog v-model="qrcodeVisible" title="产品溯源二维码" width="400px" center>
      <div class="qrcode-content">
        <div class="qrcode-wrapper">
          <div class="qrcode-border">
            <VueQr
              ref="qrcodeCanvas"
              :value="qrcodeValue"
              :size="200"
              :margin="10"
              :level="'H'"
              :render-as="'canvas'"
            />
          </div>
        </div>
        <div class="qrcode-code">
          <span>{{ code }}</span>
        </div>
        <p class="qrcode-tip">扫描二维码查看产品溯源信息</p>
      </div>
      <template #footer>
        <el-button type="primary" :icon="Download" @click="downloadQrcode">下载二维码</el-button>
        <el-button :icon="Printer" @click="printQrcode">打印</el-button>
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

.qrcode-wrapper {
  display: flex;
  justify-content: center;
  margin-bottom: 20px;
}

.qrcode-border {
  padding: 15px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  display: inline-block;
}

.qrcode-code {
  padding: 12px 24px;
  background: linear-gradient(135deg, rgba(45, 184, 77, 0.1), rgba(45, 184, 77, 0.05));
  border-radius: 8px;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 16px;
  font-weight: 600;
  color: var(--primary-color);
  display: inline-block;
  margin-bottom: 12px;
}

.qrcode-tip {
  color: var(--text-muted);
  font-size: 13px;
  margin: 0;
}
</style>
