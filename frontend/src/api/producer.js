/**
 * 原料商 API
 */
import api from './index'

export const producerApi = {
  // 获取原料列表
  getProducts(status = null) {
    const params = status ? { status } : {}
    return api.get('/producer/products', { params })
  },

  // 获取原料详情
  getProduct(id) {
    return api.get(`/producer/products/${id}`)
  },

  // 创建原料
  createProduct(data) {
    return api.post('/producer/products', data)
  },

  // 更新原料
  updateProduct(id, data) {
    return api.put(`/producer/products/${id}`, data)
  },

  // 删除原料
  deleteProduct(id) {
    return api.delete(`/producer/products/${id}`)
  },

  // 作废产品
  invalidateProduct(id, data) {
    return api.post(`/producer/products/${id}/invalidate`, data)
  },

  // 获取已作废产品列表
  getInvalidatedProducts() {
    return api.get('/producer/invalidated')
  },

  // 提交上链
  submitToChain(id) {
    return api.post(`/producer/products/${id}/submit`)
  },

  // 获取产品流转记录
  getProductRecords(id) {
    return api.get(`/producer/products/${id}/records`)
  },

  // 提交修正记录
  amendProduct(id, data) {
    return api.post(`/producer/products/${id}/amend`, data)
  },

  // 获取统计数据
  getStatistics() {
    return api.get('/producer/statistics')
  },

  // 获取加工商列表（用于指定发送）
  getProcessors() {
    return api.get('/producer/processors')
  }
}
