/**
 * AI API
 * 智谱 GLM-4.7 简报生成接口
 */
import api from './index'

export const aiApi = {
  /**
   * 生成产品溯源 AI 简报
   * @param {string} traceCode - 溯源码
   * @param {object} chainData - 区块链数据（可选）
   * @returns {Promise<{summary: string, trace_code: string, success: boolean}>}
   */
  generateSummary(traceCode, chainData = null) {
    return api.post('/ai/summary', {
      trace_code: traceCode,
      chain_data: chainData
    })
  },

  /**
   * 检查 AI API 服务状态
   */
  getHealth() {
    return api.get('/ai/health')
  }
}
