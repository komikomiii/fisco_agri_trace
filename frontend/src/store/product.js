import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useProductStore = defineStore('product', () => {
  const productChains = ref([])
  const currentChain = ref(null)
  const loading = ref(false)

  const draftChains = computed(() =>
    productChains.value.filter(c => c.status === 'draft')
  )

  const onChainProducts = computed(() =>
    productChains.value.filter(c => c.status === 'on_chain')
  )

  const terminatedChains = computed(() =>
    productChains.value.filter(c => c.status === 'terminated')
  )

  const poolProducts = computed(() => {
    return productChains.value.filter(c =>
      c.status === 'on_chain' &&
      c.currentStage === 'producer' &&
      c.distribution?.type === 'pool'
    )
  })

  const getChainsByStage = (stage) => {
    return productChains.value.filter(c =>
      c.status === 'on_chain' && c.currentStage === stage
    )
  }

  const getAssignedProducts = (processorId) => {
    return productChains.value.filter(c =>
      c.status === 'on_chain' &&
      c.currentStage === 'producer' &&
      c.distribution?.type === 'assigned' &&
      c.distribution.assignedTo?.id === processorId
    )
  }

  const getChainByTraceCode = (traceCode) => {
    return productChains.value.find(c => c.traceCode === traceCode)
  }

  const getMergedData = (chain) => {
    if (!chain) return null
    const merged = {}
    chain.records
      ?.filter(r => r.action === 'create' || r.action === 'amend')
      .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
      .forEach(record => {
        Object.assign(merged, record.data)
      })
    return merged
  }

  const hasAmendments = (chain) => {
    return chain?.records?.some(r => r.action === 'amend') || false
  }

  const getAmendmentHistory = (chain, originalRecordId) => {
    if (!chain) return []
    return chain.records.filter(r =>
      r.action === 'amend' && r.previousRecordId === originalRecordId
    )
  }

  return {
    productChains,
    currentChain,
    loading,
    draftChains,
    onChainProducts,
    terminatedChains,
    poolProducts,
    getChainsByStage,
    getAssignedProducts,
    getChainByTraceCode,
    getMergedData,
    hasAmendments,
    getAmendmentHistory
  }
})
