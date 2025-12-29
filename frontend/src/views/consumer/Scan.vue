<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { blockchainApi } from '../../api/blockchain'

const router = useRouter()
const traceCode = ref('')
const showCamera = ref(false)
const showUpload = ref(false)
const searching = ref(false)
const ocrProcessing = ref(false)

// 已上架产品列表（从真实 API 获取）
const onChainProducts = ref([])
const loadingProducts = ref(false)

// 加载已上架产品列表
const loadOnChainProducts = async () => {
  loadingProducts.value = true
  try {
    const products = await blockchainApi.getOnChainProducts(5, 0)
    onChainProducts.value = products
  } catch (error) {
    console.error('获取产品列表失败:', error)
    onChainProducts.value = []
  } finally {
    loadingProducts.value = false
  }
}

// 页面加载时获取产品列表
onMounted(() => {
  loadOnChainProducts()
})

// 获取产品 emoji 图标
const getProductEmoji = (name, category) => {
  const n = (name + ' ' + (category || '')).toLowerCase()
  if (n.includes('苹果') || n.includes('果')) return '🍎'
  if (n.includes('石榴')) return '🌰'
  if (n.includes('橙') || n.includes('橘')) return '🍊'
  if (n.includes('香蕉')) return '🍌'
  if (n.includes('葡萄')) return '🍇'
  if (n.includes('西瓜')) return '🍉'
  if (n.includes('番茄') || n.includes('茄')) return '🍅'
  if (n.includes('胡萝卜')) return '🥕'
  if (n.includes('玉米')) return '🌽'
  if (n.includes('菜') || n.includes('芹')) return '🥬'
  if (n.includes('蛋')) return '🥚'
  if (n.includes('奶') || n.includes('牛')) return '🥛'
  if (n.includes('麦') || n.includes('米') || n.includes('粮')) return '🌾'
  if (n.includes('鱼')) return '🐟'
  if (n.includes('肉')) return '🥩'
  return '📦'
}

// 获取阶段名称
const getStageName = (stage) => {
  const stageNames = {
    0: '原料种植',
    1: '加工生产',
    2: '质量检测',
    3: '销售',
    4: '已售出'
  }
  return stageNames[stage] || '未知阶段'
}

// 格式化时间
const formatTime = (timestamp) => {
  if (!timestamp) return '-'
  const date = new Date(timestamp * 1000)
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

// 搜索溯源 - 调用真实 API
const handleSearch = async () => {
  if (!traceCode.value.trim()) {
    ElMessage.warning('请输入溯源码')
    return
  }

  searching.value = true

  try {
    // 调用区块链 API 验证溯源码
    const response = await blockchainApi.getProductChainData(traceCode.value.trim())

    if (response && response.exists) {
      // 保存到历史记录
      const history = JSON.parse(localStorage.getItem('trace_history') || '[]')
      const existingIndex = history.findIndex(h => h.code === traceCode.value.trim())
      const record = {
        id: Date.now(),
        code: traceCode.value.trim(),
        name: response.product_info?.name || '未知产品',
        origin: response.product_info?.origin || '-',
        scanDate: new Date().toLocaleString('zh-CN'),
        result: 'verified',
        summary: null,
        summaryStatus: 'none'
      }

      if (existingIndex >= 0) {
        history[existingIndex] = record
      } else {
        history.unshift(record)
      }
      localStorage.setItem('trace_history', JSON.stringify(history.slice(0, 20)))

      // 跳转到公共溯源页面（不需要登录）
      router.push(`/trace/${traceCode.value.trim()}`)
    } else {
      // 保存失败的记录
      const history = JSON.parse(localStorage.getItem('trace_history') || '[]')
      history.unshift({
        id: Date.now(),
        code: traceCode.value.trim(),
        name: '未知产品',
        origin: '-',
        scanDate: new Date().toLocaleString('zh-CN'),
        result: 'failed'
      })
      localStorage.setItem('trace_history', JSON.stringify(history.slice(0, 20)))

      ElMessage.error('未找到该溯源码对应的产品信息')
    }
  } catch (error) {
    console.error('查询溯源码失败:', error)
    ElMessage.error('查询失败，请检查网络或稍后重试')
  } finally {
    searching.value = false
  }
}

// 快捷查询 - 直接跳转到公共溯源页面
const quickTrace = (code) => {
  router.push(`/trace/${code}`)
}

// 查看完整链上记录
const viewFullTrace = (code) => {
  router.push(`/dashboard/trace/${code}`)
}

// ==================== 图片OCR识别 ====================
const uploadRef = ref(null)
const uploadedImage = ref(null)
const recognizedCode = ref('')

const openUploadDialog = () => {
  uploadedImage.value = null
  recognizedCode.value = ''
  showUpload.value = true
}

// 处理图片上传
const handleImageUpload = (file) => {
  const reader = new FileReader()
  reader.onload = (e) => {
    uploadedImage.value = e.target.result
  }
  reader.readAsDataURL(file.raw)
  return false // 阻止自动上传
}

// 模拟OCR识别
const performOCR = async () => {
  if (!uploadedImage.value) {
    ElMessage.warning('请先上传图片')
    return
  }

  ocrProcessing.value = true

  // 模拟OCR处理延迟
  await new Promise(resolve => setTimeout(resolve, 1500))

  // 模拟识别结果 - 实际项目中接入OCR API
  // 这里随机返回一个存在的溯源码
  const existingCodes = onChainProducts.value.map(p => p.trace_code)

  if (existingCodes.length > 0) {
    recognizedCode.value = existingCodes[Math.floor(Math.random() * existingCodes.length)]
    ElMessage.success('识别成功！')
  } else {
    recognizedCode.value = ''
    ElMessage.warning('未能识别出溯源码，请手动输入')
  }

  ocrProcessing.value = false
}

// 使用识别结果查询
const useRecognizedCode = () => {
  if (recognizedCode.value) {
    showUpload.value = false
    // 跳转到公共溯源页面
    router.push(`/trace/${recognizedCode.value}`)
  }
}
</script>

<template>
  <div class="scan-container">
    <!-- 扫码区域 -->
    <el-card class="scan-card">
      <div class="scan-header">
        <div class="scan-icon">
          <el-icon :size="48"><Search /></el-icon>
        </div>
        <h2>产品溯源查询</h2>
        <p>扫描产品二维码或输入溯源码，查看完整供应链信息</p>
      </div>

      <div class="scan-actions">
        <div class="action-buttons">
          <el-button type="primary" size="large" :icon="Camera" @click="showCamera = true">
            扫描二维码
          </el-button>
          <el-button size="large" :icon="Picture" @click="openUploadDialog">
            上传图片识别
          </el-button>
        </div>

        <div class="divider">
          <span>或手动输入溯源码</span>
        </div>

        <div class="manual-input">
          <el-input
            v-model="traceCode"
            placeholder="请输入溯源码，如：TRACE-20241226-001"
            size="large"
            :disabled="searching"
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <el-icon><Document /></el-icon>
            </template>
            <template #append>
              <el-button :icon="Search" :loading="searching" @click="handleSearch">
                查询
              </el-button>
            </template>
          </el-input>
        </div>
      </div>
    </el-card>

    <!-- 快捷查询 -->
    <el-card class="quick-card">
      <template #header>
        <div class="card-header">
          <span class="title">
            <el-icon><Clock /></el-icon>
            最近上架产品
          </span>
          <span class="subtitle">点击可快速查询</span>
        </div>
      </template>

      <div v-if="onChainProducts.length > 0" class="product-grid">
        <div
          v-for="product in onChainProducts"
          :key="product.trace_code"
          class="product-item"
          @click="quickTrace(product.trace_code)"
        >
          <div class="product-icon">
            <span class="product-emoji">{{ getProductEmoji(product.name, product.category) }}</span>
          </div>
          <div class="product-info">
            <span class="product-name">{{ product.name }}</span>
            <span class="product-meta">{{ product.origin }} · {{ getStageName(product.current_stage) }}</span>
            <el-tag size="small" effect="plain" class="trace-tag">{{ product.trace_code }}</el-tag>
          </div>
          <div class="product-actions">
            <el-button type="primary" text size="small" @click.stop="quickTrace(product.trace_code)">
              查看详情
            </el-button>
          </div>
        </div>
      </div>

      <el-empty v-if="!loadingProducts && onChainProducts.length === 0" description="暂无可查询的产品" />
      <div v-if="loadingProducts" class="loading-wrapper">
        <el-skeleton :rows="2" animated />
      </div>
    </el-card>

    <!-- 使用说明 -->
    <el-card class="help-card">
      <template #header>
        <span class="title">
          <el-icon><QuestionFilled /></el-icon>
          如何使用溯源查询
        </span>
      </template>

      <div class="help-steps">
        <div class="step">
          <div class="step-number">1</div>
          <div class="step-content">
            <h4>获取溯源码</h4>
            <p>在产品包装上找到溯源二维码或溯源码</p>
          </div>
        </div>
        <div class="step">
          <div class="step-number">2</div>
          <div class="step-content">
            <h4>扫码或输入</h4>
            <p>使用摄像头扫描二维码，或手动输入溯源码</p>
          </div>
        </div>
        <div class="step">
          <div class="step-number">3</div>
          <div class="step-content">
            <h4>查看溯源信息</h4>
            <p>获取产品从原料到销售的完整供应链信息</p>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 模拟摄像头 -->
    <el-dialog v-model="showCamera" title="扫描二维码" width="400px">
      <div class="camera-placeholder">
        <div class="scan-frame">
          <div class="corner top-left"></div>
          <div class="corner top-right"></div>
          <div class="corner bottom-left"></div>
          <div class="corner bottom-right"></div>
          <div class="scan-line"></div>
        </div>
        <p>请将二维码对准扫描框</p>
        <p class="camera-tip">（演示环境，实际项目中接入摄像头API）</p>
      </div>
      <template #footer>
        <el-button @click="showCamera = false">取消</el-button>
      </template>
    </el-dialog>

    <!-- 图片上传识别 -->
    <el-dialog v-model="showUpload" title="上传图片识别溯源码" width="500px">
      <div class="upload-container">
        <el-upload
          ref="uploadRef"
          class="image-uploader"
          :show-file-list="false"
          :auto-upload="false"
          accept="image/*"
          :on-change="handleImageUpload"
        >
          <div v-if="uploadedImage" class="uploaded-preview">
            <img :src="uploadedImage" alt="预览" />
            <div class="preview-overlay">
              <el-icon :size="24"><RefreshRight /></el-icon>
              <span>点击更换图片</span>
            </div>
          </div>
          <div v-else class="upload-placeholder">
            <el-icon :size="48"><Upload /></el-icon>
            <p>点击或拖拽上传图片</p>
            <span>支持 JPG、PNG 格式</span>
          </div>
        </el-upload>

        <div v-if="uploadedImage" class="ocr-actions">
          <el-button
            type="primary"
            :loading="ocrProcessing"
            @click="performOCR"
          >
            <el-icon v-if="!ocrProcessing"><View /></el-icon>
            {{ ocrProcessing ? '识别中...' : '开始识别' }}
          </el-button>
        </div>

        <div v-if="recognizedCode" class="ocr-result">
          <div class="result-header">
            <el-icon class="success-icon"><CircleCheck /></el-icon>
            <span>识别成功</span>
          </div>
          <div class="result-code">
            <span class="label">溯源码：</span>
            <span class="code">{{ recognizedCode }}</span>
          </div>
          <el-button type="primary" @click="useRecognizedCode">
            查询该产品
          </el-button>
        </div>
      </div>
      <template #footer>
        <el-button @click="showUpload = false">取消</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.scan-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 800px;
  margin: 0 auto;
}

.scan-card {
  text-align: center;
  padding: 40px 20px;
}

.scan-header {
  margin-bottom: 32px;
}

.scan-icon {
  width: 80px;
  height: 80px;
  margin: 0 auto 16px;
  background: linear-gradient(135deg, var(--primary-color), var(--primary-dark));
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.scan-header h2 {
  font-size: 24px;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.scan-header p {
  color: var(--text-muted);
  font-size: 14px;
}

.scan-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
}

.action-buttons {
  display: flex;
  gap: 16px;
}

.divider {
  display: flex;
  align-items: center;
  width: 100%;
  max-width: 400px;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border-color);
}

.divider span {
  padding: 0 16px;
  color: var(--text-muted);
  font-size: 13px;
}

.manual-input {
  width: 100%;
  max-width: 450px;
}

/* 快捷查询卡片 */
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

.subtitle {
  font-size: 13px;
  color: var(--text-muted);
}

.product-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.product-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: var(--bg-color);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s;
}

.product-item:hover {
  background: #e8f5e9;
  transform: translateX(4px);
}

.product-icon {
  width: 52px;
  height: 52px;
  background: linear-gradient(135deg, var(--primary-color), var(--primary-light));
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.product-emoji {
  font-size: 28px;
}

.product-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.product-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.product-origin {
  font-size: 13px;
  color: var(--text-muted);
}

.product-meta {
  font-size: 13px;
  color: var(--text-muted);
}

.trace-tag {
  width: fit-content;
  font-family: monospace;
}

.product-actions {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.loading-wrapper {
  padding: 16px 0;
}

/* 帮助卡片 */
.help-card .title {
  font-size: 14px;
}

.help-steps {
  display: flex;
  gap: 24px;
}

.step {
  flex: 1;
  display: flex;
  gap: 12px;
}

.step-number {
  width: 32px;
  height: 32px;
  background: var(--primary-color);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  flex-shrink: 0;
}

.step-content h4 {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 4px;
}

.step-content p {
  font-size: 13px;
  color: var(--text-muted);
}

/* 摄像头占位 */
.camera-placeholder {
  height: 300px;
  background: #1a1a1a;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: relative;
}

.camera-placeholder p {
  color: rgba(255, 255, 255, 0.6);
  margin-top: 20px;
}

.camera-tip {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4) !important;
}

.scan-frame {
  width: 200px;
  height: 200px;
  position: relative;
}

.corner {
  position: absolute;
  width: 24px;
  height: 24px;
  border: 3px solid var(--primary-color);
}

.top-left { top: 0; left: 0; border-right: none; border-bottom: none; }
.top-right { top: 0; right: 0; border-left: none; border-bottom: none; }
.bottom-left { bottom: 0; left: 0; border-right: none; border-top: none; }
.bottom-right { bottom: 0; right: 0; border-left: none; border-top: none; }

.scan-line {
  position: absolute;
  left: 10%;
  width: 80%;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--primary-color), transparent);
  animation: scan 2s linear infinite;
}

@keyframes scan {
  0% { top: 10%; }
  50% { top: 90%; }
  100% { top: 10%; }
}

/* 图片上传 */
.upload-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.image-uploader {
  width: 100%;
}

.image-uploader :deep(.el-upload) {
  width: 100%;
}

.upload-placeholder {
  width: 100%;
  height: 200px;
  border: 2px dashed var(--border-color);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.upload-placeholder:hover {
  border-color: var(--primary-color);
  background: rgba(82, 196, 26, 0.05);
}

.upload-placeholder p {
  font-size: 14px;
  color: var(--text-primary);
}

.upload-placeholder span {
  font-size: 12px;
  color: var(--text-muted);
}

.uploaded-preview {
  width: 100%;
  height: 200px;
  border-radius: 12px;
  overflow: hidden;
  position: relative;
  cursor: pointer;
}

.uploaded-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.preview-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: white;
  opacity: 0;
  transition: opacity 0.3s;
}

.uploaded-preview:hover .preview-overlay {
  opacity: 1;
}

.ocr-actions {
  display: flex;
  gap: 12px;
}

.ocr-result {
  width: 100%;
  padding: 20px;
  background: #f6ffed;
  border: 1px solid #b7eb8f;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #389e0d;
  font-weight: 600;
}

.success-icon {
  font-size: 20px;
}

.result-code {
  font-size: 16px;
}

.result-code .label {
  color: var(--text-secondary);
}

.result-code .code {
  font-family: monospace;
  font-weight: 600;
  color: var(--primary-color);
}
</style>
