import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

/**
 * 产品链状态管理
 * 管理产品从原料到销售的完整生命周期
 */
export const useProductStore = defineStore('product', () => {
  // ==================== 状态 ====================

  // 所有产品链数据
  const productChains = ref([])

  // 当前选中的产品链
  const currentChain = ref(null)

  // 加载状态
  const loading = ref(false)

  // ==================== 模拟数据 ====================

  // 初始化模拟数据
  const initMockData = () => {
    productChains.value = [
      {
        id: 1,
        traceCode: 'TRACE-20241226-001',
        productName: '有机番茄',
        category: '蔬菜',
        status: 'on_chain',
        currentStage: 'seller',
        distribution: { type: 'pool', assignedTo: null },
        createdAt: '2024-12-20T08:00:00Z',
        records: [
          {
            id: 1,
            stage: 'producer',
            action: 'create',
            data: {
              name: '有机番茄',
              origin: '山东省寿光市',
              plantDate: '2024-03-15',
              quantity: 500,
              unit: 'kg'
            },
            operator: { id: 1, name: '张三农场', role: 'producer' },
            timestamp: '2024-12-20T08:00:00Z',
            txHash: '0x7a8b9c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b',
            blockNumber: 12345001
          },
          {
            id: 2,
            stage: 'processor',
            action: 'receive',
            data: { receivedQuantity: 500, quality: 'A' },
            operator: { id: 2, name: '绿源加工厂', role: 'processor' },
            timestamp: '2024-12-21T10:00:00Z',
            txHash: '0x8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c',
            blockNumber: 12345002
          },
          {
            id: 3,
            stage: 'processor',
            action: 'process',
            data: {
              processType: '清洗分拣',
              outputProduct: '精选番茄',
              outputQuantity: 480
            },
            operator: { id: 2, name: '绿源加工厂', role: 'processor' },
            timestamp: '2024-12-22T14:00:00Z',
            txHash: '0x9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d',
            blockNumber: 12345003
          },
          {
            id: 4,
            stage: 'inspector',
            action: 'inspect',
            data: {
              result: 'pass',
              items: [
                { name: '农药残留', value: '未检出', standard: '≤0.1mg/kg', pass: true },
                { name: '重金属', value: '0.02mg/kg', standard: '≤0.5mg/kg', pass: true }
              ],
              reportNo: 'R20241223001'
            },
            operator: { id: 3, name: '李质检', role: 'inspector' },
            timestamp: '2024-12-23T16:00:00Z',
            txHash: '0x0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e',
            blockNumber: 12345004
          },
          {
            id: 5,
            stage: 'seller',
            action: 'stock',
            data: { stockQuantity: 480, price: 8.5, location: '北京朝阳店' },
            operator: { id: 4, name: '优鲜超市', role: 'seller' },
            timestamp: '2024-12-24T09:00:00Z',
            txHash: '0x1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f',
            blockNumber: 12345005
          }
        ]
      },
      {
        id: 2,
        traceCode: 'TRACE-20241226-002',
        productName: '红富士苹果',
        category: '水果',
        status: 'on_chain',
        currentStage: 'inspector',
        distribution: { type: 'assigned', assignedTo: { id: 2, name: '绿源加工厂' } },
        createdAt: '2024-12-22T08:00:00Z',
        records: [
          {
            id: 1,
            stage: 'producer',
            action: 'create',
            data: {
              name: '红富士苹果',
              origin: '陕西省洛川县',
              plantDate: '2024-01-10',
              quantity: 2000,
              unit: 'kg'
            },
            operator: { id: 1, name: '张三农场', role: 'producer' },
            timestamp: '2024-12-22T08:00:00Z',
            txHash: '0x2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a',
            blockNumber: 12345010
          },
          {
            id: 2,
            stage: 'processor',
            action: 'receive',
            data: { receivedQuantity: 2000, quality: 'A' },
            operator: { id: 2, name: '绿源加工厂', role: 'processor' },
            timestamp: '2024-12-23T10:00:00Z',
            txHash: '0x3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b',
            blockNumber: 12345011
          },
          {
            id: 3,
            stage: 'processor',
            action: 'process',
            data: {
              processType: '榨汁加工',
              outputProduct: '鲜榨苹果汁',
              outputQuantity: 500
            },
            operator: { id: 2, name: '绿源加工厂', role: 'processor' },
            timestamp: '2024-12-24T14:00:00Z',
            txHash: '0x4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c',
            blockNumber: 12345012
          }
        ]
      },
      {
        id: 3,
        traceCode: null, // 草稿状态，还没有溯源码
        productName: '五常大米',
        category: '粮食',
        status: 'draft',
        currentStage: 'producer',
        distribution: { type: 'pool', assignedTo: null },
        createdAt: '2024-12-25T08:00:00Z',
        records: [
          {
            id: 1,
            stage: 'producer',
            action: 'create',
            data: {
              name: '五常大米',
              origin: '黑龙江省五常市',
              plantDate: '2024-04-20',
              quantity: 10000,
              unit: 'kg'
            },
            operator: { id: 1, name: '张三农场', role: 'producer' },
            timestamp: '2024-12-25T08:00:00Z',
            txHash: null,
            blockNumber: null
          }
        ]
      },
      {
        id: 4,
        traceCode: 'TRACE-20241226-003',
        productName: '草莓',
        category: '水果',
        status: 'terminated',
        currentStage: 'inspector',
        terminatedReason: '检测发现农药残留超标，无法处理',
        distribution: { type: 'pool', assignedTo: null },
        createdAt: '2024-12-20T08:00:00Z',
        records: [
          {
            id: 1,
            stage: 'producer',
            action: 'create',
            data: { name: '草莓', origin: '辽宁丹东', quantity: 300, unit: 'kg' },
            operator: { id: 1, name: '张三农场', role: 'producer' },
            timestamp: '2024-12-20T08:00:00Z',
            txHash: '0x5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d',
            blockNumber: 12345020
          },
          {
            id: 2,
            stage: 'processor',
            action: 'receive',
            data: { receivedQuantity: 300 },
            operator: { id: 2, name: '绿源加工厂', role: 'processor' },
            timestamp: '2024-12-21T10:00:00Z',
            txHash: '0x6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e',
            blockNumber: 12345021
          },
          {
            id: 3,
            stage: 'inspector',
            action: 'terminate',
            data: {
              reason: '农药残留超标 (检测值: 0.8mg/kg, 标准: ≤0.1mg/kg)',
              disposal: '退回原料商销毁处理'
            },
            operator: { id: 3, name: '李质检', role: 'inspector' },
            timestamp: '2024-12-22T16:00:00Z',
            txHash: '0x7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f',
            blockNumber: 12345022
          }
        ]
      }
    ]
  }

  // ==================== 计算属性 ====================

  // 按状态筛选
  const draftChains = computed(() =>
    productChains.value.filter(c => c.status === 'draft')
  )

  const onChainProducts = computed(() =>
    productChains.value.filter(c => c.status === 'on_chain')
  )

  const terminatedChains = computed(() =>
    productChains.value.filter(c => c.status === 'terminated')
  )

  // 按当前阶段筛选
  const getChainsByStage = (stage) => {
    return productChains.value.filter(c =>
      c.status === 'on_chain' && c.currentStage === stage
    )
  }

  // 获取待加工池中的产品（原料商已上链，等待加工商接收）
  const poolProducts = computed(() => {
    return productChains.value.filter(c =>
      c.status === 'on_chain' &&
      c.currentStage === 'producer' &&
      c.distribution.type === 'pool'
    )
  })

  // 获取指定给某加工商的产品
  const getAssignedProducts = (processorId) => {
    return productChains.value.filter(c =>
      c.status === 'on_chain' &&
      c.currentStage === 'producer' &&
      c.distribution.type === 'assigned' &&
      c.distribution.assignedTo?.id === processorId
    )
  }

  // ==================== 方法 ====================

  // 生成溯源码
  const generateTraceCode = () => {
    const date = new Date().toISOString().slice(0, 10).replace(/-/g, '')
    const seq = String(productChains.value.length + 1).padStart(3, '0')
    return `TRACE-${date}-${seq}`
  }

  // 生成模拟的交易哈希
  const generateTxHash = () => {
    const chars = '0123456789abcdef'
    let hash = '0x'
    for (let i = 0; i < 40; i++) {
      hash += chars[Math.floor(Math.random() * chars.length)]
    }
    return hash
  }

  // 创建新的产品链（草稿）
  const createProductChain = (data) => {
    const chain = {
      id: Date.now(),
      traceCode: null,
      productName: data.name,
      category: data.category,
      status: 'draft',
      currentStage: 'producer',
      distribution: {
        type: data.distributionType || 'pool',
        assignedTo: data.assignedTo || null
      },
      createdAt: new Date().toISOString(),
      records: [
        {
          id: 1,
          stage: 'producer',
          action: 'create',
          data: data,
          operator: data.operator,
          timestamp: new Date().toISOString(),
          txHash: null,
          blockNumber: null
        }
      ]
    }
    productChains.value.unshift(chain)
    return chain
  }

  // 确认上链（草稿 → 已上链）
  const confirmOnChain = async (chainId) => {
    const chain = productChains.value.find(c => c.id === chainId)
    if (!chain || chain.status !== 'draft') return null

    // 模拟上链延迟
    loading.value = true
    await new Promise(resolve => setTimeout(resolve, 1500))

    // 生成溯源码和链上信息
    chain.traceCode = generateTraceCode()
    chain.status = 'on_chain'

    // 更新记录的链上信息
    chain.records.forEach(record => {
      if (!record.txHash) {
        record.txHash = generateTxHash()
        record.blockNumber = 12345000 + Math.floor(Math.random() * 1000)
      }
    })

    loading.value = false
    return chain
  }

  // 添加新记录到产品链
  const addRecord = async (chainId, record) => {
    const chain = productChains.value.find(c => c.id === chainId)
    if (!chain) return null

    const newRecord = {
      id: chain.records.length + 1,
      ...record,
      timestamp: new Date().toISOString(),
      txHash: generateTxHash(),
      blockNumber: 12345000 + Math.floor(Math.random() * 1000)
    }

    chain.records.push(newRecord)

    // 更新当前阶段
    if (record.stage) {
      chain.currentStage = record.stage
    }

    return newRecord
  }

  // 添加修正记录
  const addAmendRecord = async (chainId, originalRecordId, amendData, reason) => {
    const chain = productChains.value.find(c => c.id === chainId)
    if (!chain) return null

    const originalRecord = chain.records.find(r => r.id === originalRecordId)
    if (!originalRecord) return null

    const amendRecord = {
      id: chain.records.length + 1,
      stage: originalRecord.stage,
      action: 'amend',
      previousRecordId: originalRecordId,
      data: amendData,
      reason: reason,
      operator: amendData.operator,
      timestamp: new Date().toISOString(),
      txHash: generateTxHash(),
      blockNumber: 12345000 + Math.floor(Math.random() * 1000)
    }

    chain.records.push(amendRecord)
    return amendRecord
  }

  // 质检退回
  const rejectToStage = async (chainId, rejectTo, reason, operator) => {
    const chain = productChains.value.find(c => c.id === chainId)
    if (!chain) return null

    const rejectRecord = {
      id: chain.records.length + 1,
      stage: 'inspector',
      action: 'reject',
      data: { rejectTo, reason },
      operator,
      timestamp: new Date().toISOString(),
      txHash: generateTxHash(),
      blockNumber: 12345000 + Math.floor(Math.random() * 1000)
    }

    chain.records.push(rejectRecord)
    chain.currentStage = rejectTo // 退回到指定环节

    return rejectRecord
  }

  // 质检终止
  const terminateChain = async (chainId, reason, disposal, operator) => {
    const chain = productChains.value.find(c => c.id === chainId)
    if (!chain) return null

    const terminateRecord = {
      id: chain.records.length + 1,
      stage: 'inspector',
      action: 'terminate',
      data: { reason, disposal },
      operator,
      timestamp: new Date().toISOString(),
      txHash: generateTxHash(),
      blockNumber: 12345000 + Math.floor(Math.random() * 1000)
    }

    chain.records.push(terminateRecord)
    chain.status = 'terminated'
    chain.terminatedReason = reason

    return terminateRecord
  }

  // 根据溯源码查询
  const getChainByTraceCode = (traceCode) => {
    return productChains.value.find(c => c.traceCode === traceCode)
  }

  // 获取产品链的最新状态数据（合并修正记录后）
  const getMergedData = (chain) => {
    if (!chain) return null

    const merged = {}

    // 按时间顺序处理记录，后面的覆盖前面的
    chain.records
      .filter(r => r.action === 'create' || r.action === 'amend')
      .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
      .forEach(record => {
        Object.assign(merged, record.data)
      })

    return merged
  }

  // 检查是否有修正记录
  const hasAmendments = (chain) => {
    return chain?.records.some(r => r.action === 'amend') || false
  }

  // 获取修正历史
  const getAmendmentHistory = (chain, originalRecordId) => {
    if (!chain) return []
    return chain.records.filter(r =>
      r.action === 'amend' && r.previousRecordId === originalRecordId
    )
  }

  return {
    // 状态
    productChains,
    currentChain,
    loading,

    // 计算属性
    draftChains,
    onChainProducts,
    terminatedChains,
    poolProducts,

    // 方法
    initMockData,
    getChainsByStage,
    getAssignedProducts,
    generateTraceCode,
    createProductChain,
    confirmOnChain,
    addRecord,
    addAmendRecord,
    rejectToStage,
    terminateChain,
    getChainByTraceCode,
    getMergedData,
    hasAmendments,
    getAmendmentHistory
  }
})
