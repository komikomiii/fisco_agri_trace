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

  // 获取产品链上数据
  getProductChainData(traceCode) {
    return api.get(`/blockchain/product/${traceCode}/chain-data`)
  },

  // 检查区块链健康状态
  getHealth() {
    return api.get('/blockchain/health')
  }
}
