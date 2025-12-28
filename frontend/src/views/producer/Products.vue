<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useProductStore } from '../../store/product'
import { useUserStore } from '../../store/user'
import { producerApi } from '../../api/producer'
import ChainConfirm from '../../components/common/ChainConfirm.vue'
import TraceCode from '../../components/common/TraceCode.vue'
import AmendRecord from '../../components/common/AmendRecord.vue'
import ChainVerify from '../../components/common/ChainVerify.vue'

const productStore = useProductStore()
const userStore = useUserStore()

// 是否使用真实 API
const USE_REAL_API = true

// 产品列表（从后端获取）
const products = ref([])
const loading = ref(false)

// 各状态数量统计
const statusCounts = reactive({
  draft: 0,
  on_chain: 0,
  all: 0,
  invalidated: 0
})

// 搜索表单
const searchForm = reactive({
  name: '',
  category: '',
  status: ''
})

// 分类选项
const categories = ['蔬菜', '水果', '粮食', '水产', '畜禽', '其他']

// 状态映射 (支持后端返回的枚举值)
const chainStatusMap = {
  DRAFT: { label: '未上链', type: 'warning', icon: 'EditPen' },
  ON_CHAIN: { label: '已上链', type: 'success', icon: 'CircleCheckFilled' },
  INVALIDATED: { label: '已作废', type: 'info', icon: 'Delete' },
  // 兼容前端小写格式
  draft: { label: '未上链', type: 'warning', icon: 'EditPen' },
  on_chain: { label: '已上链', type: 'success', icon: 'CircleCheckFilled' },
  invalidated: { label: '已作废', type: 'info', icon: 'Delete' }
}

// Tab 切换
const activeTab = ref('draft')

// 加载产品列表
const fetchProducts = async () => {
  if (!USE_REAL_API) return

  loading.value = true
  try {
    // 同时获取正常产品和已作废产品
    const [normalProducts, invalidatedProducts] = await Promise.all([
      producerApi.getProducts(null),
      producerApi.getInvalidatedProducts()
    ])

    // 合并所有产品
    const allProducts = [...normalProducts, ...invalidatedProducts]
    products.value = allProducts

    // 更新各状态数量
    statusCounts.draft = normalProducts.filter(p => p.status === 'DRAFT').length
    statusCounts.on_chain = normalProducts.filter(p => p.status === 'ON_CHAIN').length
    statusCounts.invalidated = invalidatedProducts.length
    statusCounts.all = allProducts.length
  } catch (error) {
    ElMessage.error('获取产品列表失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

// 监听 Tab 切换（不需要重新加载，只需前端过滤）
const handleTabChange = () => {
  // 数据已在内存中，无需重新请求
}

// 筛选后的产品列表
const filteredProducts = computed(() => {
  if (USE_REAL_API) {
    let list = [...products.value]

    // Tab name 到状态值的映射
    const statusMap = {
      'draft': 'DRAFT',
      'on_chain': 'ON_CHAIN',
      'invalidated': 'INVALIDATED'
    }

    // 根据当前 Tab 过滤状态
    if (activeTab.value !== 'all') {
      const targetStatus = statusMap[activeTab.value]
      if (targetStatus) {
        list = list.filter(p => p.status === targetStatus)
      }
    }

    // 应用搜索过滤
    if (searchForm.name) {
      list = list.filter(p => p.name.includes(searchForm.name))
    }
    if (searchForm.category) {
      list = list.filter(p => p.category === searchForm.category)
    }

    return list
  }

  // 原有的本地 store 逻辑作为备用
  let list = []
  if (activeTab.value === 'DRAFT') {
    list = productStore.draftChains
  } else if (activeTab.value === 'ON_CHAIN') {
    list = productStore.onChainProducts.filter(c => c.currentStage === 'producer')
  } else if (activeTab.value === 'all') {
    list = productStore.productChains.filter(c => {
      const firstRecord = c.records[0]
      return firstRecord?.operator?.role === 'producer'
    })
  }

  if (searchForm.name) {
    list = list.filter(c => c.productName.includes(searchForm.name))
  }
  if (searchForm.category) {
    list = list.filter(c => c.category === searchForm.category)
  }

  return list
})

// 组件挂载时加载数据
onMounted(() => {
  fetchProducts()
})

// ==================== 新增/编辑产品 ====================
const dialogVisible = ref(false)
const dialogTitle = ref('新增产品')
const isEdit = ref(false)
const editingChainId = ref(null)

const productForm = reactive({
  name: '',
  category: '',
  origin: '',
  plantDate: '',
  quantity: 0,
  unit: 'kg',
  distributionType: 'pool',
  assignedTo: null
})

// 模拟的加工商列表
const processors = [
  { id: 2, name: '绿源加工厂' },
  { id: 5, name: '鑫达食品公司' },
  { id: 6, name: '优品加工中心' }
]

const openDialog = (product = null) => {
  if (product) {
    dialogTitle.value = '编辑产品'
    isEdit.value = true
    editingChainId.value = product.id

    // 适配两种数据格式（API 返回 和 本地 store）
    const isApiFormat = !product.records
    if (isApiFormat) {
      Object.assign(productForm, {
        name: product.name,
        category: product.category,
        origin: product.origin || '',
        plantDate: product.plant_date || '',
        quantity: product.quantity || 0,
        unit: product.unit || 'kg',
        distributionType: product.distribution_type || 'pool',
        assignedTo: product.assigned_processor_id ? { id: product.assigned_processor_id } : null
      })
    } else {
      const data = productStore.getMergedData(product)
      Object.assign(productForm, {
        name: data.name || product.productName,
        category: product.category,
        origin: data.origin || '',
        plantDate: data.plantDate || '',
        quantity: data.quantity || 0,
        unit: data.unit || 'kg',
        distributionType: product.distribution?.type || 'pool',
        assignedTo: product.distribution?.assignedTo || null
      })
    }
  } else {
    dialogTitle.value = '新增产品'
    isEdit.value = false
    editingChainId.value = null
    Object.assign(productForm, {
      name: '',
      category: '',
      origin: '',
      plantDate: '',
      quantity: 0,
      unit: 'kg',
      distributionType: 'pool',
      assignedTo: null
    })
  }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!productForm.name || !productForm.category) {
    ElMessage.warning('请填写完整信息')
    return
  }

  if (USE_REAL_API) {
    try {
      const data = {
        name: productForm.name,
        category: productForm.category,
        origin: productForm.origin,
        plant_date: productForm.plantDate,
        quantity: productForm.quantity,
        unit: productForm.unit,
        distribution_type: productForm.distributionType,
        assigned_processor_id: productForm.distributionType === 'assigned' ? productForm.assignedTo?.id : null
      }

      if (isEdit.value) {
        await producerApi.updateProduct(editingChainId.value, data)
        ElMessage.success('产品更新成功')
      } else {
        await producerApi.createProduct(data)
        ElMessage.success('产品添加成功（草稿）')
      }

      dialogVisible.value = false
      fetchProducts() // 刷新列表
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    }
    return
  }

  // 原有本地逻辑作为备用
  if (isEdit.value) {
    const chain = productStore.productChains.find(c => c.id === editingChainId.value)
    if (chain && chain.status === 'DRAFT') {
      chain.productName = productForm.name
      chain.category = productForm.category
      chain.distribution = {
        type: productForm.distributionType,
        assignedTo: productForm.distributionType === 'assigned' ? productForm.assignedTo : null
      }
      chain.records[0].data = {
        name: productForm.name,
        category: productForm.category,
        origin: productForm.origin,
        plantDate: productForm.plantDate,
        quantity: productForm.quantity,
        unit: productForm.unit
      }
      ElMessage.success('产品更新成功')
    }
  } else {
    productStore.createProductChain({
      name: productForm.name,
      category: productForm.category,
      origin: productForm.origin,
      plantDate: productForm.plantDate,
      quantity: productForm.quantity,
      unit: productForm.unit,
      distributionType: productForm.distributionType,
      assignedTo: productForm.assignedTo,
      operator: {
        id: userStore.user?.id || 1,
        name: userStore.user?.name || '张三农场',
        role: 'producer'
      }
    })
    ElMessage.success('产品添加成功（草稿）')
  }
  dialogVisible.value = false
}

const handleDelete = async (product) => {
  if (product.status !== 'DRAFT') {
    ElMessage.warning('只能删除草稿状态的产品')
    return
  }

  try {
    await ElMessageBox.confirm(`确定删除产品「${product.name || product.productName}」吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    if (USE_REAL_API) {
      await producerApi.deleteProduct(product.id)
      ElMessage.success('删除成功')
      fetchProducts()
    } else {
      const index = productStore.productChains.findIndex(c => c.id === product.id)
      if (index > -1) {
        productStore.productChains.splice(index, 1)
        ElMessage.success('删除成功')
      }
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

// ==================== 产品作废 ====================
const handleInvalidate = async (product) => {
  try {
    const { value: reason } = await ElMessageBox.prompt(
      `<div style="margin-bottom: 16px;">
        <p style="color: #e6a23c; font-weight: bold; margin-bottom: 8px;">
          <i class="el-icon-warning"></i> 重要提示
        </p>
        <ul style="color: #666; font-size: 13px; line-height: 1.8; padding-left: 20px;">
          <li>该产品溯源码：<strong>${product.trace_code || product.traceCode}</strong></li>
          <li>作废后，产品将从列表中移除，移至"已作废"列表</li>
          <li><strong style="color: #f56c6c;">区块链上的数据无法删除</strong>，溯源码将永久失效</li>
          <li>如果该产品涉及生产流转环节，整条链路将受影响</li>
        </ul>
      </div>
      <p style="margin-top: 12px;">请输入作废原因：</p>`,
      '作废产品',
      {
        confirmButtonText: '确认作废',
        cancelButtonText: '取消',
        inputPlaceholder: '例如：数据录入错误、产品质量问题等',
        inputPattern: /.+/,
        inputErrorMessage: '请输入作废原因',
        dangerouslyUseHTMLString: true,
        type: 'warning',
        inputValidator: (value) => {
          if (!value || value.trim().length === 0) {
            return '作废原因不能为空'
          }
          if (value.trim().length < 5) {
            return '作废原因至少需要5个字符'
          }
          return true
        }
      }
    )

    if (USE_REAL_API) {
      const result = await producerApi.invalidateProduct(product.id, { reason: reason.trim() })

      if (result.deleted) {
        ElMessage.success('草稿已删除')
      } else {
        ElMessage.success(result.message || '产品已作废')
      }

      fetchProducts()
    } else {
      const index = productStore.productChains.findIndex(c => c.id === product.id)
      if (index > -1) {
        productStore.productChains[index].status = 'invalidated'
        ElMessage.success('产品已作废（链上数据无法删除）')
      }
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || error.message || '作废失败')
    }
  }
}

// ==================== 上链确认 ====================
const chainConfirmVisible = ref(false)
const pendingChainData = ref(null)
const chainConfirmRef = ref(null)

const handleConfirmOnChain = (product) => {
  // 适配两种数据格式（API 返回格式和本地 store 格式）
  const isApiFormat = !product.records
  const data = isApiFormat ? product : productStore.getMergedData(product)

  pendingChainData.value = {
    chainId: product.id,
    labels: {
      name: '产品名称',
      category: '产品类别',
      origin: '产地',
      plantDate: '种植日期',
      quantity: '预计产量',
      unit: '单位'
    },
    data: {
      name: isApiFormat ? product.name : data.name,
      category: product.category,
      origin: isApiFormat ? product.origin : data.origin,
      plantDate: isApiFormat ? product.plant_date : data.plantDate,
      quantity: `${isApiFormat ? product.quantity : data.quantity} ${isApiFormat ? product.unit : data.unit}`,
      unit: undefined
    },
    distribution: isApiFormat ? {
      type: product.distribution_type,
      assignedTo: product.assigned_processor_id ? { id: product.assigned_processor_id } : null
    } : product.distribution
  }
  chainConfirmVisible.value = true
}

const onChainConfirm = async () => {
  if (!pendingChainData.value) return

  chainConfirmRef.value?.setLoading()

  try {
    if (USE_REAL_API) {
      const result = await producerApi.submitToChain(pendingChainData.value.chainId)
      chainConfirmRef.value?.setSuccess(
        result.trace_code,
        result.block_number,
        result.tx_hash
      )
      ElMessage.success('上链成功！溯源码：' + result.trace_code)
      fetchProducts()
    } else {
      const result = await productStore.confirmOnChain(pendingChainData.value.chainId)
      if (result) {
        chainConfirmRef.value?.setSuccess(result.records[0].txHash, result.records[0].blockNumber)
        ElMessage.success('上链成功！溯源码：' + result.traceCode)
      } else {
        chainConfirmRef.value?.setError('上链失败，请重试')
      }
    }
  } catch (error) {
    chainConfirmRef.value?.setError(error.response?.data?.detail || error.message || '上链失败')
  }
}

// ==================== 修正记录 ====================
const amendVisible = ref(false)
const amendingChain = ref(null)
const amendChainConfirmVisible = ref(false)
const amendChainConfirmRef = ref(null)
const pendingAmendData = ref(null)

const amendDataLabels = {
  name: '产品名称',
  category: '产品类别',
  origin: '产地',
  harvestDate: '采收日期',
  quantity: '数量',
  unit: '单位'
}

const amendEditableFields = [
  { key: 'name', type: 'input', placeholder: '请输入产品名称' },
  {
    key: 'category',
    type: 'select',
    options: [
      { label: '蔬菜', value: '蔬菜' },
      { label: '水果', value: '水果' },
      { label: '粮食', value: '粮食' },
      { label: '水产', value: '水产' },
      { label: '畜禽', value: '畜禽' },
      { label: '其他', value: '其他' }
    ]
  },
  { key: 'origin', type: 'input', placeholder: '请输入产地' },
  { key: 'harvestDate', type: 'date' },
  { key: 'quantity', type: 'number' },
  {
    key: 'unit',
    type: 'select',
    options: [
      { label: 'kg', value: 'kg' },
      { label: '只', value: '只' },
      { label: '箱', value: '箱' }
    ]
  }
]

const openAmendDialog = (chain) => {
  amendingChain.value = chain
  amendVisible.value = true
}

// 前端字段名到后端字段名的映射
const fieldNameMap = {
  harvestDate: 'harvest_date',
  batchNo: 'batch_no'
}

// AmendRecord 提交后，打开 ChainConfirm 确认
const handleAmendSubmit = (amendData) => {
  if (!amendingChain.value) return

  // 获取产品当前数据
  const product = amendingChain.value
  const currentData = getDetailData(product)

  // 找出真正被修改的字段（比较原值和新值）
  const changedFields = Object.keys(amendData.changes).filter(key => {
    return amendData.changes[key] !== currentData[key]
  })

  if (changedFields.length === 0) {
    ElMessage.warning('没有修改任何字段')
    return
  }

  // 准备确认弹窗数据
  const amendPreviewData = {}
  const amendPreviewLabels = {}

  changedFields.forEach(field => {
    const label = amendDataLabels[field] || field
    amendPreviewLabels[field] = label
    amendPreviewData[field] = `${currentData[field] || '(空)'} → ${amendData.changes[field] || '(空)'}`
  })

  pendingAmendData.value = {
    product,
    currentData,
    amendData,
    changedFields,
    previewData: amendPreviewData,
    previewLabels: amendPreviewLabels
  }

  // 关闭 AmendRecord，打开 ChainConfirm
  amendVisible.value = false
  amendChainConfirmVisible.value = true
}

// 修正信息上链确认
const onAmendChainConfirm = async () => {
  if (!pendingAmendData.value) return

  amendChainConfirmRef.value?.setLoading()

  const { product, currentData, amendData, changedFields } = pendingAmendData.value

  if (USE_REAL_API) {
    try {
      let lastResult = null

      // 提交每个修改的字段
      for (const field of changedFields) {
        // 转换字段名为后端格式
        const backendField = fieldNameMap[field] || field

        lastResult = await producerApi.amendProduct(product.id, {
          field: backendField,
          old_value: String(currentData[field] || ''),
          new_value: String(amendData.changes[field]),
          reason: amendData.reason
        })
      }

      // 显示成功状态
      amendChainConfirmRef.value?.setSuccess(
        product.trace_code || product.traceCode,
        lastResult?.block_number,
        lastResult?.tx_hash
      )

      // 刷新数据
      fetchProducts()
    } catch (error) {
      amendChainConfirmRef.value?.setError(error.response?.data?.detail || error.message || '修正记录上链失败')
    }
    return
  }

  // 原有本地逻辑作为备用
  const originalRecord = amendingChain.value.records.find(r => r.action === 'create')
  if (!originalRecord) {
    amendChainConfirmRef.value?.setError('未找到原始记录')
    return
  }

  try {
    await productStore.addAmendRecord(
      amendingChain.value.id,
      originalRecord.id,
      {
        ...amendData.changes,
        operator: {
          id: userStore.user?.id || 1,
          name: userStore.user?.name || '张三农场',
          role: 'producer'
        }
      },
      amendData.reason
    )
    amendChainConfirmRef.value?.setSuccess('修正记录已提交')
  } catch (error) {
    amendChainConfirmRef.value?.setError('修正记录上链失败')
  }
}

// ==================== 查看详情 ====================
const detailDrawerVisible = ref(false)
const detailChain = ref(null)
const detailRecords = ref([])
const detailLoading = ref(false)

// ==================== 链上验证 ====================
const chainVerifyVisible = ref(false)
const verifyTxHash = ref('')
const verifyTraceCode = ref('')
const verifyBlockNumber = ref(null)

const openChainVerify = (record) => {
  verifyTxHash.value = record?.tx_hash || record?.txHash || ''
  verifyTraceCode.value = detailChain.value?.trace_code || detailChain.value?.traceCode || ''
  // 从记录或产品中获取区块高度
  verifyBlockNumber.value = record?.block_number || record?.blockNumber ||
                            detailChain.value?.block_number || detailChain.value?.blockNumber || null

  console.log('openChainVerify - detailChain:', detailChain.value)
  console.log('openChainVerify - verifyTraceCode:', verifyTraceCode.value)
  console.log('openChainVerify - verifyTxHash:', verifyTxHash.value)
  console.log('openChainVerify - verifyBlockNumber:', verifyBlockNumber.value)

  chainVerifyVisible.value = true
}

const viewDetail = async (product) => {
  console.log('viewDetail - product:', product)
  console.log('viewDetail - trace_code:', product?.trace_code || product?.traceCode)

  detailChain.value = product
  detailDrawerVisible.value = true

  // 如果是 API 格式，需要加载记录
  if (USE_REAL_API && !product.records) {
    detailLoading.value = true
    try {
      const records = await producerApi.getProductRecords(product.id)
      detailRecords.value = records
    } catch (error) {
      console.error('获取记录失败', error)
      detailRecords.value = []
    } finally {
      detailLoading.value = false
    }
  } else {
    detailRecords.value = product.records || []
  }
}

// 获取详情数据（兼容两种数据格式）
const getDetailData = (product) => {
  if (!product) return {}

  const isApiFormat = !product.records
  if (isApiFormat) {
    // 处理日期格式 - API 返回的可能是 ISO 格式或 null
    let harvestDate = product.harvest_date || ''
    if (harvestDate && harvestDate.includes('T')) {
      harvestDate = harvestDate.split('T')[0]  // 转换为 YYYY-MM-DD 格式
    }

    return {
      name: product.name || '',
      origin: product.origin || '',
      quantity: product.quantity || 0,
      unit: product.unit || 'kg',
      harvestDate: harvestDate,
      category: product.category || '',
      batch_no: product.batch_no || ''
    }
  }
  return productStore.getMergedData(product)
}

// 获取产品名称（兼容两种格式）
const getProductName = (product) => {
  return product?.name || product?.productName || ''
}

// 获取溯源码（兼容两种格式）
const getTraceCode = (product) => {
  return product?.trace_code || product?.traceCode || ''
}

// 格式化时间
const formatTime = (timestamp) => {
  if (!timestamp) return '-'
  return new Date(timestamp).toLocaleString('zh-CN')
}

// 获取操作描述
const getActionLabel = (action) => {
  const actionLower = action?.toLowerCase() || ''
  const map = {
    create: '创建记录',
    amend: '修正信息',
    harvest: '采收上链',
    receive: '接收原料',
    process: '加工处理',
    inspect: '质量检测',
    stock: '入库登记',
    reject: '退回处理',
    terminate: '终止链条'
  }
  return map[actionLower] || action
}

// 字段标签映射
const fieldLabelMap = {
  name: '产品名称',
  category: '产品类别',
  origin: '产地',
  harvest_date: '采收日期',
  harvestDate: '采收日期',
  quantity: '数量',
  unit: '单位',
  batch_no: '批次号',
  batchNo: '批次号'
}

// 获取字段中文名
const getFieldLabel = (field) => {
  return fieldLabelMap[field] || field
}

// 解析修正记录数据
const parseAmendData = (dataStr) => {
  if (!dataStr) return []

  try {
    const data = typeof dataStr === 'string' ? JSON.parse(dataStr) : dataStr

    // 如果是单个修改记录格式 { field, old_value, new_value }
    if (data.field) {
      return [{
        field: data.field,
        old_value: data.old_value,
        new_value: data.new_value
      }]
    }

    // 如果是多个字段的对象格式
    return Object.keys(data).map(key => ({
      field: key,
      old_value: data[key]?.old,
      new_value: data[key]?.new || data[key]
    }))
  } catch {
    return []
  }
}

// 重置搜索
const resetSearch = () => {
  searchForm.name = ''
  searchForm.category = ''
  searchForm.status = ''
}
</script>

<template>
  <div class="products-container">
    <!-- 搜索栏 -->
    <el-card class="search-card">
      <el-form :model="searchForm" inline>
        <el-form-item label="产品名称">
          <el-input v-model="searchForm.name" placeholder="请输入产品名称" clearable />
        </el-form-item>
        <el-form-item label="产品类别">
          <el-select v-model="searchForm.category" placeholder="请选择" clearable>
            <el-option v-for="cat in categories" :key="cat" :label="cat" :value="cat" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search">搜索</el-button>
          <el-button :icon="Refresh" @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 产品列表 -->
    <el-card class="table-card">
      <template #header>
        <div class="card-header">
          <span class="title">
            <el-icon><Grape /></el-icon>
            原料管理
          </span>
          <el-button type="primary" :icon="Plus" @click="openDialog()">新增产品</el-button>
        </div>
      </template>

      <!-- Tab 切换 -->
      <el-tabs v-model="activeTab" class="product-tabs" @tab-change="handleTabChange">
        <el-tab-pane label="未上链" name="draft">
          <template #label>
            <span class="tab-label">
              <el-icon><EditPen /></el-icon>
              未上链
              <el-badge :value="statusCounts.draft" :max="99" class="tab-badge" type="warning" />
            </span>
          </template>
        </el-tab-pane>
        <el-tab-pane label="已上链" name="on_chain">
          <template #label>
            <span class="tab-label">
              <el-icon><CircleCheckFilled /></el-icon>
              已上链
              <el-badge
                :value="statusCounts.on_chain"
                :max="99"
                class="tab-badge"
                type="success"
              />
            </span>
          </template>
        </el-tab-pane>
        <el-tab-pane label="全部" name="all">
          <template #label>
            <span class="tab-label">
              <el-icon><List /></el-icon>
              全部
              <el-badge :value="statusCounts.all" :max="99" class="tab-badge" />
            </span>
          </template>
        </el-tab-pane>
        <el-tab-pane label="已作废" name="invalidated">
          <template #label>
            <span class="tab-label">
              <el-icon><Delete /></el-icon>
              已作废
              <el-badge
                :value="statusCounts.invalidated"
                :max="99"
                class="tab-badge"
                type="info"
              />
            </span>
          </template>
        </el-tab-pane>
      </el-tabs>

      <el-table :data="filteredProducts" stripe style="width: 100%" v-loading="loading" :header-cell-style="{ background: '#f5f7fa', color: '#606266' }">
        <el-table-column prop="name" label="产品名称" min-width="180">
          <template #default="{ row }">
            <div class="product-name">
              <el-avatar :size="36" shape="square" style="background: var(--primary-color)">
                {{ (row.name || row.productName || '?').charAt(0) }}
              </el-avatar>
              <div class="name-info">
                <span class="name">{{ row.name || row.productName }}</span>
                <span v-if="row.trace_code || row.traceCode" class="trace-code">
                  {{ row.trace_code || row.traceCode }}
                </span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="类别" width="90" align="center">
          <template #default="{ row }">
            <el-tag effect="plain" size="small">{{ row.category }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="产地" min-width="140">
          <template #default="{ row }">
            {{ row.origin || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="数量" width="100" align="right">
          <template #default="{ row }">
            <span class="quantity-text">{{ row.quantity || 0 }} <small>{{ row.unit || 'kg' }}</small></span>
          </template>
        </el-table-column>
        <el-table-column label="分配方式" width="100" align="center">
          <template #default="{ row }">
            <el-tooltip
              :content="(row.distribution_type || row.distribution?.type) === 'assigned' ? '指定发送给加工商' : '等待加工商领取'"
              placement="top"
            >
              <span class="tag-content">
                <el-icon class="tag-icon" :class="(row.distribution_type || row.distribution?.type) === 'assigned' ? 'warning' : 'info'">
                  <Position v-if="(row.distribution_type || row.distribution?.type) === 'assigned'" />
                  <Collection v-else />
                </el-icon>
                <span class="tag-text">{{ (row.distribution_type || row.distribution?.type) === 'assigned' ? '指定' : '公共池' }}</span>
              </span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="chainStatusMap[row.status]?.type || 'info'" size="small">
              {{ chainStatusMap[row.status]?.label || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <!-- 草稿状态的操作 -->
            <template v-if="row.status === 'DRAFT'">
              <el-button type="primary" text size="small" @click="openDialog(row)">
                编辑
              </el-button>
              <el-button type="success" text size="small" @click="handleConfirmOnChain(row)">
                <el-icon><Connection /></el-icon>
                确认上链
              </el-button>
              <el-button type="danger" text size="small" @click="handleDelete(row)">
                删除
              </el-button>
            </template>

            <!-- 已上链状态的操作 -->
            <template v-else-if="row.status === 'ON_CHAIN'">
              <el-button type="primary" text size="small" @click="viewDetail(row)">
                查看详情
              </el-button>
              <el-button type="warning" text size="small" @click="openAmendDialog(row)">
                <el-icon><Edit /></el-icon>
                修正信息
              </el-button>
              <el-button type="danger" text size="small" @click="handleInvalidate(row)">
                <el-icon><Delete /></el-icon>
                作废
              </el-button>
            </template>

            <!-- 已终止/已作废的只能查看 -->
            <template v-else>
              <el-button type="primary" text size="small" @click="viewDetail(row)">
                查看详情
              </el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          layout="total, sizes, prev, pager, next, jumper"
          :total="filteredProducts.length"
          :page-sizes="[10, 20, 50]"
          :prev-page-icon="ArrowLeft"
          :next-page-icon="ArrowRight"
        />
      </div>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="560px">
      <el-form :model="productForm" label-width="100px">
        <el-form-item label="产品名称" required>
          <el-input v-model="productForm.name" placeholder="请输入产品名称" />
        </el-form-item>
        <el-form-item label="产品类别" required>
          <el-select v-model="productForm.category" placeholder="请选择类别" style="width: 100%">
            <el-option v-for="cat in categories" :key="cat" :label="cat" :value="cat" />
          </el-select>
        </el-form-item>
        <el-form-item label="产地">
          <el-input v-model="productForm.origin" placeholder="请输入产地" />
        </el-form-item>
        <el-form-item label="种植日期">
          <el-date-picker
            v-model="productForm.plantDate"
            type="date"
            placeholder="选择日期"
            style="width: 100%"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item label="预计产量">
          <el-input-number v-model="productForm.quantity" :min="0" style="width: 200px" />
          <el-select v-model="productForm.unit" style="width: 80px; margin-left: 10px">
            <el-option label="kg" value="kg" />
            <el-option label="只" value="只" />
            <el-option label="箱" value="箱" />
          </el-select>
        </el-form-item>

        <el-divider content-position="left">分配设置</el-divider>

        <el-form-item label="分配方式">
          <el-radio-group v-model="productForm.distributionType">
            <el-radio-button value="pool">
              <el-icon><Collection /></el-icon>
              公共池（加工商自选）
            </el-radio-button>
            <el-radio-button value="assigned">
              <el-icon><Position /></el-icon>
              指定发送
            </el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="productForm.distributionType === 'assigned'" label="指定加工商">
          <el-select v-model="productForm.assignedTo" placeholder="请选择加工商" style="width: 100%">
            <el-option
              v-for="p in processors"
              :key="p.id"
              :label="p.name"
              :value="p"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">
          {{ isEdit ? '保存修改' : '保存草稿' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 上链确认组件 -->
    <ChainConfirm
      ref="chainConfirmRef"
      v-model:visible="chainConfirmVisible"
      title="确认产品上链"
      :data="pendingChainData?.data"
      :data-labels="pendingChainData?.labels"
      @confirm="onChainConfirm"
    >
      <template #extra>
        <div v-if="pendingChainData?.distribution" class="distribution-info">
          <span class="label">分配方式：</span>
          <el-tag v-if="pendingChainData.distribution.type === 'pool'" type="info">
            公共池（加工商自选）
          </el-tag>
          <el-tag v-else type="warning">
            指定发送给：{{ pendingChainData.distribution.assignedTo?.name }}
          </el-tag>
        </div>
      </template>
    </ChainConfirm>

    <!-- 修正记录组件 -->
    <AmendRecord
      v-model:visible="amendVisible"
      :original-data="amendingChain ? getDetailData(amendingChain) : {}"
      :data-labels="amendDataLabels"
      :editable-fields="amendEditableFields"
      @submit="handleAmendSubmit"
    />

    <!-- 修正信息上链确认组件 -->
    <ChainConfirm
      ref="amendChainConfirmRef"
      v-model:visible="amendChainConfirmVisible"
      title="确认修正信息上链"
      :data="pendingAmendData?.previewData"
      :data-labels="pendingAmendData?.previewLabels"
      @confirm="onAmendChainConfirm"
    >
      <template #extra>
        <div class="amend-confirm-info">
          <div class="info-item">
            <span class="label">产品名称：</span>
            <span class="value">{{ pendingAmendData?.product?.name || pendingAmendData?.product?.productName }}</span>
          </div>
          <div class="info-item">
            <span class="label">溯源码：</span>
            <span class="value code">{{ pendingAmendData?.product?.trace_code || pendingAmendData?.product?.traceCode }}</span>
          </div>
          <div class="info-item">
            <span class="label">修正原因：</span>
            <span class="value reason">{{ pendingAmendData?.amendData?.reason }}</span>
          </div>
        </div>
      </template>
    </ChainConfirm>

    <!-- 详情抽屉 -->
    <el-drawer
      v-model="detailDrawerVisible"
      title="产品详情"
      size="500px"
    >
      <template v-if="detailChain">
        <!-- 溯源码 -->
        <div class="detail-section">
          <TraceCode
            v-if="getTraceCode(detailChain)"
            :code="getTraceCode(detailChain)"
            size="large"
          />
          <div v-else class="no-trace-code">
            <el-empty description="暂无溯源码" :image-size="60" />
          </div>
        </div>

        <!-- 基本信息 -->
        <div class="detail-section">
          <h4>基本信息</h4>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="产品名称">
              {{ getProductName(detailChain) }}
            </el-descriptions-item>
            <el-descriptions-item label="产品类别">
              {{ detailChain.category }}
            </el-descriptions-item>
            <el-descriptions-item label="产地">
              {{ getDetailData(detailChain)?.origin || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="数量">
              {{ getDetailData(detailChain)?.quantity || 0 }}
              {{ getDetailData(detailChain)?.unit || 'kg' }}
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="chainStatusMap[detailChain.status]?.type">
                {{ chainStatusMap[detailChain.status]?.label }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 链上记录 -->
        <div class="detail-section">
          <div class="section-header">
            <h4>
              链上记录
              <el-tag v-if="detailRecords.some(r => r.action === 'AMEND' || r.action === 'amend')" type="warning" size="small">
                有修正记录
              </el-tag>
            </h4>
            <el-button
              v-if="detailChain.status === 'ON_CHAIN' && detailRecords.length > 0"
              type="primary"
              link
              size="small"
              @click="openChainVerify(detailRecords[0])"
            >
              <el-icon><Connection /></el-icon>
              查看链信息
            </el-button>
          </div>
          <div v-if="detailLoading" class="loading-records">
            <el-icon class="is-loading"><Loading /></el-icon>
            加载中...
          </div>
          <el-timeline v-else>
            <el-timeline-item
              v-for="record in detailRecords"
              :key="record.id"
              :timestamp="formatTime(record.timestamp || record.created_at)"
              :type="(record.action === 'AMEND' || record.action === 'amend') ? 'warning' : 'primary'"
            >
              <div class="record-item">
                <div class="record-header">
                  <span class="action">{{ getActionLabel(record.action) }}</span>
                  <span class="operator">{{ record.operator?.name || record.operator_name }}</span>
                </div>

                <!-- 修正记录的具体修改内容 -->
                <div v-if="(record.action === 'AMEND' || record.action === 'amend') && record.data" class="amend-changes">
                  <div class="amend-change-item" v-for="change in parseAmendData(record.data)" :key="change.field">
                    <span class="field-label">{{ getFieldLabel(change.field) }}</span>
                    <div class="change-values">
                      <span class="old-val">{{ change.old_value || '(空)' }}</span>
                      <el-icon class="arrow-icon"><Right /></el-icon>
                      <span class="new-val">{{ change.new_value || '(空)' }}</span>
                    </div>
                  </div>
                </div>

                <div v-if="record.txHash || record.tx_hash" class="chain-info-box" @click="openChainVerify(record)">
                  <div class="chain-badge">
                    <el-icon><Connection /></el-icon>
                    <span>FISCO BCOS</span>
                  </div>
                  <div class="chain-details">
                    <div class="chain-row">
                      <span class="chain-label">交易哈希</span>
                      <span class="chain-value">{{ (record.txHash || record.tx_hash).slice(0, 10) }}...{{ (record.txHash || record.tx_hash).slice(-8) }}</span>
                    </div>
                    <div v-if="record.block_number || record.blockNumber" class="chain-row">
                      <span class="chain-label">区块高度</span>
                      <span class="chain-value">#{{ record.block_number || record.blockNumber }}</span>
                    </div>
                  </div>
                  <div class="verify-btn">
                    <el-icon><View /></el-icon>
                    <span>验证</span>
                  </div>
                </div>
                <div v-if="record.reason || record.amend_reason" class="record-reason">
                  修正原因：{{ record.reason || record.amend_reason }}
                </div>
              </div>
            </el-timeline-item>
          </el-timeline>
        </div>
      </template>
    </el-drawer>

    <!-- 链上数据验证组件 -->
    <ChainVerify
      v-model:visible="chainVerifyVisible"
      :tx-hash="verifyTxHash"
      :trace-code="verifyTraceCode"
      :block-number="verifyBlockNumber"
      :product-data="detailChain"
    />
  </div>
</template>

<style scoped>
.products-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.search-card :deep(.el-form-item) {
  margin-bottom: 0;
}

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

.product-tabs {
  margin-bottom: 16px;
}

.tab-label {
  display: flex;
  align-items: center;
  gap: 6px;
}

.tab-badge {
  margin-left: 6px;
}

/* 表格标签样式 */
.tag-content {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
}

.tag-icon {
  font-size: 14px;
}

.tag-icon.info {
  color: #909399;
}

.tag-icon.warning {
  color: #e6a23c;
}

.tag-icon.success {
  color: #67c23a;
}

.tag-icon.danger {
  color: #f56c6c;
}

.tag-icon.primary {
  color: #409eff;
}

.tag-text {
  color: var(--text-primary);
}

.quantity-text {
  font-weight: 500;
}

.quantity-text small {
  color: var(--text-muted);
  font-weight: normal;
}

.product-name {
  display: flex;
  align-items: center;
  gap: 12px;
}

.name-info {
  display: flex;
  flex-direction: column;
}

.name-info .name {
  font-weight: 500;
}

.name-info .trace-code {
  font-size: 12px;
  color: var(--text-muted);
  font-family: monospace;
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.distribution-info {
  margin-top: 12px;
  padding: 12px;
  background: var(--bg-color);
  border-radius: 8px;
}

.distribution-info .label {
  color: var(--text-secondary);
  margin-right: 8px;
}

/* 详情抽屉样式 */
.detail-section {
  margin-bottom: 24px;
}

.no-trace-code {
  padding: 20px 0;
  text-align: center;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-header h4 {
  margin-bottom: 0;
}

.detail-section h4 {
  font-size: 14px;
  color: var(--text-primary);
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.record-item {
  padding: 8px 0;
}

.record-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}

.record-header .action {
  font-weight: 500;
}

.record-header .operator {
  color: var(--text-secondary);
  font-size: 13px;
}

/* 链上信息卡片 */
.chain-info-box {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
  padding: 10px 14px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.08), rgba(118, 75, 162, 0.08));
  border: 1px solid rgba(102, 126, 234, 0.2);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.chain-info-box:hover {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.15), rgba(118, 75, 162, 0.15));
  border-color: rgba(102, 126, 234, 0.4);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
}

.chain-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.chain-badge .el-icon {
  font-size: 12px;
}

.chain-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.chain-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.chain-label {
  color: var(--text-muted);
}

.chain-value {
  color: #667eea;
  font-family: monospace;
  font-weight: 500;
}

.verify-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  background: rgba(102, 126, 234, 0.1);
  color: #667eea;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.2s;
}

.chain-info-box:hover .verify-btn {
  background: #667eea;
  color: white;
}

.record-reason {
  margin-top: 6px;
  padding: 8px 12px;
  background: #fffbe6;
  border-radius: 6px;
  font-size: 13px;
  color: #ad6800;
}

.loading-records {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px;
  color: var(--text-secondary);
}

/* 修正信息确认样式 */
.amend-confirm-info {
  margin-top: 16px;
  padding: 16px;
  background: linear-gradient(135deg, rgba(230, 162, 60, 0.1), rgba(230, 162, 60, 0.05));
  border: 1px solid rgba(230, 162, 60, 0.3);
  border-radius: 10px;
}

.amend-confirm-info .info-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 0;
}

.amend-confirm-info .info-item:not(:last-child) {
  border-bottom: 1px dashed rgba(230, 162, 60, 0.2);
}

.amend-confirm-info .label {
  color: var(--text-muted);
  font-size: 13px;
  flex-shrink: 0;
  min-width: 80px;
}

.amend-confirm-info .value {
  font-size: 14px;
  font-weight: 500;
}

.amend-confirm-info .value.code {
  font-family: monospace;
  color: #667eea;
}

.amend-confirm-info .value.reason {
  color: #e6a23c;
}

/* 修正记录变更详情样式 */
.amend-changes {
  margin: 10px 0;
  padding: 12px;
  background: linear-gradient(135deg, rgba(230, 162, 60, 0.08), rgba(230, 162, 60, 0.03));
  border: 1px solid rgba(230, 162, 60, 0.2);
  border-radius: 8px;
}

.amend-change-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 0;
}

.amend-change-item:not(:last-child) {
  border-bottom: 1px dashed rgba(230, 162, 60, 0.15);
}

.amend-change-item .field-label {
  min-width: 70px;
  font-size: 12px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.amend-change-item .change-values {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  font-size: 13px;
}

.amend-change-item .old-val {
  padding: 2px 8px;
  background: rgba(245, 108, 108, 0.1);
  color: #f56c6c;
  border-radius: 4px;
  text-decoration: line-through;
}

.amend-change-item .arrow-icon {
  color: var(--text-muted);
  font-size: 12px;
}

.amend-change-item .new-val {
  padding: 2px 8px;
  background: rgba(103, 194, 58, 0.1);
  color: #67c23a;
  border-radius: 4px;
  font-weight: 500;
}

</style>
