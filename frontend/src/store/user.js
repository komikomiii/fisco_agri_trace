import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../api/auth'

// 角色名称映射
const roleNameMap = {
  producer: '原料商',
  processor: '加工商',
  inspector: '质检员',
  seller: '销售商',
  consumer: '消费者'
}

// 模拟用户数据 (开发备用)
const mockUsers = {
  producer: { id: 1, username: 'producer', name: '张三农场', role: 'producer', roleName: '原料商', avatar: '' },
  processor: { id: 2, username: 'processor', name: '绿源加工厂', role: 'processor', roleName: '加工商', avatar: '' },
  inspector: { id: 3, username: 'inspector', name: '李质检', role: 'inspector', roleName: '质检员', avatar: '' },
  seller: { id: 4, username: 'seller', name: '优鲜超市', role: 'seller', roleName: '销售商', avatar: '' },
  consumer: { id: 5, username: 'consumer', name: '王小明', role: 'consumer', roleName: '消费者', avatar: '' }
}

// 是否使用真实API
const USE_REAL_API = true

export const useUserStore = defineStore('user', () => {
  const user = ref(null)
  const token = ref(localStorage.getItem('token') || '')

  const isLoggedIn = computed(() => !!user.value)
  const userRole = computed(() => user.value?.role || '')

  // 登录
  async function login(username, password) {
    if (USE_REAL_API) {
      try {
        const response = await authApi.login(username, password)
        const userData = {
          ...response.user,
          name: response.user.real_name || response.user.username,
          roleName: roleNameMap[response.user.role] || response.user.role,
          blockchainAddress: response.user.blockchain_address || null
        }
        user.value = userData
        token.value = response.access_token
        localStorage.setItem('token', response.access_token)
        localStorage.setItem('user', JSON.stringify(userData))
        return userData
      } catch (error) {
        throw new Error(error.response?.data?.detail || '登录失败')
      }
    } else {
      // 使用模拟数据
      return new Promise((resolve, reject) => {
        setTimeout(() => {
          const foundUser = mockUsers[username]
          if (foundUser && password === '123456') {
            user.value = foundUser
            token.value = 'mock_token_' + Date.now()
            localStorage.setItem('token', token.value)
            localStorage.setItem('user', JSON.stringify(foundUser))
            resolve(foundUser)
          } else {
            reject(new Error('用户名或密码错误'))
          }
        }, 500)
      })
    }
  }

  // 注册
  async function register(data) {
    if (USE_REAL_API) {
      try {
        const response = await authApi.register({
          username: data.username,
          password: data.password,
          role: data.role,
          real_name: data.realName,
          phone: data.phone,
          company: data.company
        })
        return response
      } catch (error) {
        throw new Error(error.response?.data?.detail || '注册失败')
      }
    }
  }

  // 登出
  function logout() {
    user.value = null
    token.value = ''
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  // 恢复登录状态
  function restoreSession() {
    const savedUser = localStorage.getItem('user')
    if (savedUser && token.value) {
      user.value = JSON.parse(savedUser)
    }
  }

  return {
    user,
    token,
    isLoggedIn,
    userRole,
    login,
    register,
    logout,
    restoreSession
  }
})
