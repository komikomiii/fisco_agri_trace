/**
 * Inspector (质检员) API
 */
import api from './index'

/**
 * 获取待检测产品列表
 * @returns {Promise} 产品列表
 */
export const getPendingProducts = () => {
  return api.get('/inspector/products/pending')
}

/**
 * 获取检测中的产品列表
 * @returns {Promise} 产品列表
 */
export const getTestingProducts = () => {
  return api.get('/inspector/products/testing')
}

/**
 * 获取已完成检测的产品列表
 * @returns {Promise} 产品列表
 */
export const getCompletedProducts = () => {
  return api.get('/inspector/products/completed')
}

/**
 * 开始检测
 * @param {number} productId - 产品ID
 * @param {Object} data - 检测数据
 * @param {string} data.inspect_type - 检测类型
 * @param {string} data.notes - 备注
 * @returns {Promise} 检测结果
 */
export const startInspect = (productId, data) => {
  return api.post(`/inspector/products/${productId}/start-inspect`, data)
}

/**
 * 完成检测
 * @param {number} productId - 产品ID
 * @param {Object} data - 检测结果数据
 * @param {boolean} data.qualified - 是否合格
 * @param {string} data.quality_grade - 质量等级
 * @param {string} data.inspect_result - 检测结果描述
 * @param {string} data.issues - 存在的问题
 * @param {string} data.notes - 备注
 * @returns {Promise} 检测结果
 */
export const inspectProduct = (productId, data) => {
  return api.post(`/inspector/products/${productId}/inspect`, data)
}

/**
 * 获取产品流转记录
 * @param {number} productId - 产品ID
 * @returns {Promise} 流转记录列表
 */
export const getProductRecords = (productId) => {
  return api.get(`/inspector/products/${productId}/records`)
}

/**
 * 获取统计数据
 * @returns {Promise} 统计数据
 */
export const getStatistics = () => {
  return api.get('/inspector/statistics')
}

export default {
  getPendingProducts,
  getTestingProducts,
  getCompletedProducts,
  startInspect,
  inspectProduct,
  getProductRecords,
  getStatistics
}
