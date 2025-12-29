/**
 * API 基础配置
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 60000,  // 增加到 60 秒，区块链操作可能需要较长时间
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器 - 添加 token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器 - 处理错误
api.interceptors.response.use(
  (response) => {
    // 安全地返回响应数据
    try {
      return response.data
    } catch (e) {
      console.error('响应数据解析失败:', e)
      return response.data
    }
  },
  (error) => {
    // 如果有响应，显示服务器返回的错误信息
    if (error.response) {
      const message = error.response.data?.detail || error.message || '请求失败'
      ElMessage.error(message)

      // 401 未授权，跳转登录
      if (error.response.status === 401) {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        window.location.href = '/login'
      }
    } else if (error.request) {
      // 请求已发送但没有收到响应（网络错误、超时等）
      console.error('网络错误:', error.message)
      ElMessage.error('网络连接失败，请检查网络')
    } else {
      // 其他错误
      console.error('请求错误:', error.message)
      ElMessage.error(error.message || '请求失败')
    }

    return Promise.reject(error)
  }
)

export default api
export { aiApi } from './ai'
export { blockchainApi } from './blockchain'
