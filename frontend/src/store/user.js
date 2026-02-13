import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../api/auth'

const roleNameMap = {
  producer: '原料商',
  processor: '加工商',
  inspector: '质检员',
  seller: '销售商',
  consumer: '消费者'
}

export const useUserStore = defineStore('user', () => {
  const user = ref(null)
  const token = ref(localStorage.getItem('token') || '')

  const isLoggedIn = computed(() => !!user.value)
  const userRole = computed(() => user.value?.role || '')

  async function login(username, password) {
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
  }

  async function register(data) {
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
