<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useProductStore } from '../../store/product'
import { useUserStore } from '../../store/user'
import { producerApi } from '../../api/producer'
import ChainConfirm from '../../components/common/ChainConfirm.vue'
import TraceCode from '../../components/common/TraceCode.vue'
import AmendRecord from '../../components/common/AmendRecord.vue'

const productStore = useProductStore()
const userStore = useUserStore()

// 是否使用真实 API
const USE_REAL_API = true

// 产品列表（从后端获取）
const products = ref([])
const loading = ref(false)

// 搜索表单
const searchForm = reactive({
  name: '',
  category: '',
  status: ''
})

// 分类选项
const categories = ['蔬菜', '水果', '粮食', '水产', '畜禽', '其他']

// 状态映射
const chainStatusMap = {
  draft: { label: '草稿', type: 'info' },
  on_chain: { label: '已上链', type: 'success' },
  terminated: { label: '已终止', type: 'danger' }
}

// Tab 切换
const activeTab = ref('draft')

// 加载产品列表
const fetchProducts = async () => {
  if (!USE_REAL_API) return

  loading.value = true
  try {
    const status = activeTab.value === 'all' ? null : activeTab.value
    const data = await producerApi.getProducts(status)
    products.value = data
  } catch (error) {
    ElMessage.error('获取产品列表失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

// 监听 Tab 切换时重新加载
const handleTabChange = () => {
  fetchProducts()
}

// 筛选后的产品列表
const filteredProducts = computed(() => {
  if (USE_REAL_API) {
    let list = [...products.value]

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
  if (activeTab.value === 'draft') {
    list = productStore.draftChains
  } else if (activeTab.value === 'on_chain') {
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
    if (chain && chain.status === 'draft') {
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
  if (product.status !== 'draft') {
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
      chainConfirmRef.value?.setSuccess(result.trace_code || 'TX-' + Date.now(), 1)
      ElMessage.success('上链成功！溯源码：' + (result.trace_code || result.id))
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

const amendDataLabels = {
  name: '产品名称',
  origin: '产地',
  plantDate: '种植日期',
  quantity: '数量'
}

const amendEditableFields = [
  { key: 'name', type: 'input', placeholder: '请输入产品名称' },
  { key: 'origin', type: 'input', placeholder: '请输入产地' },
  { key: 'plantDate', type: 'date' },
  { key: 'quantity', type: 'number' }
]

const openAmendDialog = (chain) => {
  amendingChain.value = chain
  amendVisible.value = true
}

const handleAmendSubmit = async (amendData) => {
  if (!amendingChain.value) return

  if (USE_REAL_API) {
    try {
      // 从 amendData.changes 中获取修改的字段
      const changedFields = Object.keys(amendData.changes)
      if (changedFields.length === 0) {
        ElMessage.warning('没有修改任何字段')
        return
      }

      // 获取产品当前数据
      const product = amendingChain.value
      const isApiFormat = !product.records

      // 提交每个修改的字段
      for (const field of changedFields) {
        const oldValue = isApiFormat
          ? (product[field] || product[field.replace(/([A-Z])/g, '_$1').toLowerCase()])
          : productStore.getMergedData(product)[field]

        await producerApi.amendProduct(product.id, {
          field: field,
          old_value: String(oldValue || ''),
          new_value: String(amendData.changes[field]),
          reason: amendData.reason
        })
      }

      ElMessage.success('修正记录已提交上链')
      amendVisible.value = false
      fetchProducts()
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '提交修正记录失败')
    }
    return
  }

  // 原有本地逻辑作为备用
  const originalRecord = amendingChain.value.records.find(r => r.action === 'create')
  if (!originalRecord) return

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

  ElMessage.success('修正记录已提交上链')
}

// ==================== 查看详情 ====================
const detailDrawerVisible = ref(false)
const detailChain = ref(null)
const detailRecords = ref([])
const detailLoading = ref(false)

const viewDetail = async (product) => {
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
    return {
      name: product.name,
      origin: product.origin,
      quantity: product.quantity,
      unit: product.unit,
      plantDate: product.plant_date || product.harvest_date
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
        <el-tab-pane label="草稿" name="draft">
          <template #label>
            <span>
              草稿
              <el-badge :value="products.filter(p => p.status === 'draft').length" :max="99" class="tab-badge" />
            </span>
          </template>
        </el-tab-pane>
        <el-tab-pane label="已上链" name="on_chain">
          <template #label>
            <span>
              已上链
              <el-badge
                :value="products.filter(p => p.status === 'on_chain').length"
                :max="99"
                class="tab-badge"
                type="success"
              />
            </span>
          </template>
        </el-tab-pane>
        <el-tab-pane label="全部" name="all" />
      </el-tabs>

      <el-table :data="filteredProducts" stripe style="width: 100%" v-loading="loading">
        <el-table-column prop="name" label="产品名称" min-width="140">
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
        <el-table-column prop="category" label="类别" width="100">
          <template #default="{ row }">
            <el-tag effect="plain">{{ row.category }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="产地" min-width="120">
          <template #default="{ row }">
            {{ row.origin || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="数量" width="120">
          <template #default="{ row }">
            {{ row.quantity || 0 }} {{ row.unit || 'kg' }}
          </template>
        </el-table-column>
        <el-table-column label="分配方式" width="140">
          <template #default="{ row }">
            <el-tag v-if="(row.distribution_type || row.distribution?.type) === 'pool'" type="info" effect="plain">
              <el-icon><Collection /></el-icon>
              公共池
            </el-tag>
            <el-tag v-else-if="row.distribution_type === 'assigned' || row.distribution?.assignedTo" type="warning" effect="plain">
              <el-icon><Position /></el-icon>
              指定发送
            </el-tag>
            <el-tag v-else type="info" effect="plain">
              <el-icon><Collection /></el-icon>
              公共池
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="chainStatusMap[row.status]?.type">
              {{ chainStatusMap[row.status]?.label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <!-- 草稿状态的操作 -->
            <template v-if="row.status === 'draft'">
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
            <template v-else-if="row.status === 'on_chain'">
              <el-button type="primary" text size="small" @click="viewDetail(row)">
                查看详情
              </el-button>
              <el-button type="warning" text size="small" @click="openAmendDialog(row)">
                <el-icon><Edit /></el-icon>
                修正信息
              </el-button>
            </template>

            <!-- 已终止的只能查看 -->
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

    <!-- 详情抽屉 -->
    <el-drawer
      v-model="detailDrawerVisible"
      title="产品详情"
      size="500px"
    >
      <template v-if="detailChain">
        <!-- 溯源码 -->
        <div v-if="getTraceCode(detailChain)" class="detail-section">
          <TraceCode :trace-code="getTraceCode(detailChain)" size="large" />
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
          <h4>
            链上记录
            <el-tag v-if="detailRecords.some(r => r.action === 'AMEND' || r.action === 'amend')" type="warning" size="small">
              有修正记录
            </el-tag>
          </h4>
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
                <div v-if="record.txHash || record.tx_hash" class="record-hash">
                  <el-icon><Link /></el-icon>
                  {{ (record.txHash || record.tx_hash).slice(0, 10) }}...{{ (record.txHash || record.tx_hash).slice(-8) }}
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

.tab-badge {
  margin-left: 6px;
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

.record-hash {
  font-size: 12px;
  color: var(--text-muted);
  font-family: monospace;
  display: flex;
  align-items: center;
  gap: 4px;
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
</style>
