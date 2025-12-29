/**
 * 区块链 API
 */
import api from './index'

export const blockchainApi = {
  // 获取链信息
  getChainInfo() {
    return api.get('/blockchain/info')
  },

  // 获取交易详情
  getTransaction(txHash) {
    return api.get(`/blockchain/transaction/${txHash}`)
  },

  // 获取区块详情
  getBlock(blockNumber) {
    return api.get(`/blockchain/block/${blockNumber}`)
  },

  // 验证溯源码
  verifyTraceCode(traceCode) {
    return api.get(`/blockchain/verify/${traceCode}`)
  },

  // 获取产品链上数据(需要较长时间,增加超时)
  getProductChainData(traceCode) {
    return api.get(`/blockchain/product/${traceCode}/chain-data`, {
      timeout: 30000  // 30秒超时
    })
  },

  // 获取已上架产品列表
  getOnChainProducts(limit = 10, offset = 0) {
    return api.get('/blockchain/products', {
      params: { limit, offset }
    })
  },

  // 检查区块链健康状态
  getHealth() {
    return api.get('/blockchain/health')
  },

  // 获取已作废产品列表
  getInvalidatedProducts(userId = null) {
    const params = userId ? { user_id: userId } : {}
    return api.get('/blockchain/products/invalidated', { params })
  }
}
