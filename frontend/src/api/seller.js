/**
 * Seller (销售商) API
 */
import api from './index'

export const sellerApi = {
  // 获取库存产品列表
  getInventoryProducts() {
    return api.get('/seller/products/inventory')
  },

  // 获取已售出产品列表
  getSoldProducts() {
    return api.get('/seller/products/sold')
  },

  // 产品入库
  stockIn(productId, data) {
    return api.post(`/seller/products/${productId}/stock-in`, data)
  },

  // 销售产品
  sellProduct(productId, data) {
    return api.post(`/seller/products/${productId}/sell`, data)
  },

  // 获取产品流转记录
  getProductRecords(productId) {
    return api.get(`/seller/products/${productId}/records`)
  },

  // 获取统计数据
  getStatistics() {
    return api.get('/seller/statistics')
  }
}
