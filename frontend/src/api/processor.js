/**
 * Processor (加工商) API
 */
import api from './index'

/**
 * 获取可接收的原料列表
 * @returns {Promise} 产品列表
 */
export const getAvailableProducts = () => {
  return api.get('/processor/products')
}

/**
 * 获取已接收的产品列表
 * @returns {Promise} 产品列表
 */
export const getReceivedProducts = () => {
  return api.get('/processor/products/received')
}

/**
 * 获取待加工产品列表
 * @returns {Promise} 产品列表
 */
export const getPendingProducts = () => {
  return api.get('/processor/products/pending')
}

/**
 * 获取加工中产品列表
 * @returns {Promise} 产品列表
 */
export const getProcessingProducts = () => {
  return api.get('/processor/products/processing')
}

/**
 * 获取已送检产品列表
 * @returns {Promise} 产品列表
 */
export const getSentProducts = () => {
  return api.get('/processor/products/sent')
}

/**
 * 接收原料
 * @param {number} productId - 产品ID
 * @param {Object} data - 接收数据
 * @param {number} data.received_quantity - 接收数量
 * @param {string} data.quality - 质检等级
 * @param {string} data.notes - 备注
 * @returns {Promise} 接收结果
 */
export const receiveProduct = (productId, data) => {
  return api.post(`/processor/products/${productId}/receive`, data)
}

/**
 * 加工处理
 * @param {number} productId - 产品ID
 * @param {Object} data - 加工数据
 * @param {string} data.process_type - 加工类型
 * @param {string} data.result_product - 加工后产品名称
 * @param {number} data.result_quantity - 加工后数量
 * @param {string} data.notes - 备注
 * @returns {Promise} 处理结果
 */
export const processProduct = (productId, data) => {
  return api.post(`/processor/products/${productId}/process`, data)
}

/**
 * 送检
 * @param {number} productId - 产品ID
 * @param {Object} data - 送检数据
 * @returns {Promise} 送检结果
 */
export const sendInspectProduct = (productId, data) => {
  return api.post(`/processor/products/${productId}/send-inspect`, data)
}

/**
 * 获取产品流转记录
 * @param {number} productId - 产品ID
 * @returns {Promise} 流转记录列表
 */
export const getProductRecords = (productId) => {
  return api.get(`/processor/products/${productId}/records`)
}

/**
 * 获取统计数据
 * @returns {Promise} 统计数据
 */
export const getStatistics = () => {
  return api.get('/processor/statistics')
}

export default {
  getAvailableProducts,
  getReceivedProducts,
  getPendingProducts,
  getProcessingProducts,
  getSentProducts,
  receiveProduct,
  processProduct,
  sendInspectProduct,
  getProductRecords,
  getStatistics
}
