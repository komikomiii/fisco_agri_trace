<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { blockchainApi } from '../../api/blockchain'
import { Html5Qrcode } from 'html5-qrcode'

const router = useRouter()
const traceCode = ref('')
const showCamera = ref(false)
const searching = ref(false)

let html5QrCode = null
const scannerReady = ref(false)

const startScanner = async () => {
  await nextTick()
  const container = document.getElementById('qr-reader')
  if (!container) return
  try {
    html5QrCode = new Html5Qrcode('qr-reader')
    scannerReady.value = true
    await html5QrCode.start(
      { facingMode: 'environment' },
      { fps: 10, qrbox: { width: 250, height: 250 } },
      (decodedText) => {
        stopScanner()
        showCamera.value = false
        const code = decodedText.includes('trace/') ? decodedText.split('trace/').pop() : decodedText
        traceCode.value = code.trim()
        handleSearch()
      },
      () => {}
    )
  } catch (err) {
    console.error('摄像头启动失败:', err)
    ElMessage.error('无法访问摄像头，请检查权限或使用手动输入')
    scannerReady.value = false
  }
}

const stopScanner = async () => {
  if (html5QrCode) {
    try {
      const state = html5QrCode.getState()
      if (state === 2) await html5QrCode.stop()
    } catch {}
    html5QrCode = null
    scannerReady.value = false
  }
}

watch(showCamera, async (val) => {
  if (val) {
    await startScanner()
  } else {
    await stopScanner()
  }
})

onBeforeUnmount(() => {
  stopScanner()
})

const imageFileRef = ref(null)
const scanningImage = ref(false)

const handleImageScan = async (uploadFile) => {
  const file = uploadFile.raw || uploadFile
  if (!file) return
  scanningImage.value = true
  try {
    const qr = new Html5Qrcode('qr-image-scan-tmp')
    const result = await qr.scanFile(file, false)
    await qr.clear()
    const code = result.includes('trace/') ? result.split('trace/').pop() : result
    traceCode.value = code.trim()
    ElMessage.success('识别成功')
    handleSearch()
  } catch {
    ElMessage.error('未能从图片中识别出二维码，请确认图片包含有效二维码')
  } finally {
    scanningImage.value = false
  }
}

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
  router.push(`/trace/${code}`)
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
            摄像头扫码
          </el-button>
          <el-upload
            ref="imageFileRef"
            :show-file-list="false"
            :auto-upload="false"
            accept="image/*"
            :on-change="handleImageScan"
          >
            <el-button size="large" :icon="Picture" :loading="scanningImage">
              图片识别
            </el-button>
          </el-upload>
        </div>
        <div id="qr-image-scan-tmp" style="display:none"></div>

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

    <el-dialog v-model="showCamera" title="扫描二维码" width="500px" :destroy-on-close="true" @closed="stopScanner">
      <div class="camera-container">
        <div id="qr-reader" class="qr-reader"></div>
        <p v-if="!scannerReady" class="camera-tip">正在启动摄像头...</p>
        <p v-else class="camera-tip">请将二维码对准扫描框</p>
      </div>
      <template #footer>
        <el-button @click="showCamera = false">关闭</el-button>
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

.camera-container {
  text-align: center;
}

.qr-reader {
  width: 100%;
  min-height: 300px;
  border-radius: 12px;
  overflow: hidden;
}

.camera-tip {
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 12px;
}

</style>
