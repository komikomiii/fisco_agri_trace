<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../../store/user'
import { authApi } from '../../api/auth'

const router = useRouter()
const userStore = useUserStore()

// 当前模式：login / register
const mode = ref('login')
const loading = ref(false)

// 登录表单
const loginForm = reactive({
  username: '',
  password: ''
})

// 注册表单
const registerForm = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  role: '',
  realName: '',
  phone: ''
})

// 角色选项
const roles = [
  { key: 'producer', name: '原料商', icon: 'Sunrise', desc: '农产品种植/养殖', color: '#52c41a' },
  { key: 'processor', name: '加工商', icon: 'SetUp', desc: '产品加工处理', color: '#1890ff' },
  { key: 'inspector', name: '质检员', icon: 'DocumentChecked', desc: '质量检测认证', color: '#722ed1' },
  { key: 'seller', name: '销售商', icon: 'Shop', desc: '产品销售配送', color: '#fa8c16' },
  { key: 'consumer', name: '消费者', icon: 'User', desc: '扫码溯源查询', color: '#eb2f96' }
]

// 平台特点
const platformStats = [
  { label: '安全可靠', icon: 'Lock' },
  { label: '高效便捷', icon: 'Odometer' },
  { label: '开放透明', icon: 'View' }
]

// 注册时选择角色
const selectRegisterRole = (role) => {
  registerForm.role = role.key
}

// 切换模式
const switchMode = (newMode) => {
  mode.value = newMode
  // 清空表单
  if (newMode === 'login') {
    loginForm.username = ''
    loginForm.password = ''
  } else {
    registerForm.username = ''
    registerForm.password = ''
    registerForm.confirmPassword = ''
    registerForm.role = ''
    registerForm.realName = ''
    registerForm.phone = ''
  }
}

// 登录
const handleLogin = async () => {
  if (!loginForm.username || !loginForm.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }

  loading.value = true
  try {
    await userStore.login(loginForm.username, loginForm.password)
    ElMessage.success('登录成功')
    router.push('/dashboard/home')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

// 注册
const handleRegister = async () => {
  if (!registerForm.username) {
    ElMessage.warning('请输入用户名')
    return
  }
  if (!registerForm.password) {
    ElMessage.warning('请输入密码')
    return
  }
  if (registerForm.password.length < 6) {
    ElMessage.warning('密码至少6位')
    return
  }
  if (registerForm.password !== registerForm.confirmPassword) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }
  if (!registerForm.role) {
    ElMessage.warning('请选择角色')
    return
  }
  if (!registerForm.realName) {
    ElMessage.warning('请输入真实姓名/企业名称')
    return
  }

  loading.value = true
  try {
    // 调用真实注册 API
    await authApi.register({
      username: registerForm.username,
      password: registerForm.password,
      role: registerForm.role,
      real_name: registerForm.realName,
      phone: registerForm.phone || null
    })

    ElMessage.success('注册成功，请登录')

    // 切换到登录模式，并填充用户名
    mode.value = 'login'
    loginForm.username = registerForm.username
    loginForm.password = ''
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || error.message || '注册失败')
  } finally {
    loading.value = false
  }
}

// 获取选中角色的颜色
const selectedRoleColor = computed(() => {
  const role = roles.find(r => r.key === registerForm.role)
  return role?.color || '#909399'
})
</script>

<template>
  <div class="login-container">
    <!-- 装饰背景 -->
    <div class="bg-decoration dec-1"></div>
    <div class="bg-decoration dec-2"></div>
    <div class="bg-decoration dec-3"></div>

    <!-- 左侧品牌区 -->
    <div class="brand-section">
      <div class="brand-content">
        <!-- Logo 和标题 -->
        <div class="logo-wrapper">
          <div class="logo-icon">
            <el-icon :size="48"><Connection /></el-icon>
          </div>
          <div class="logo-text">
            <h1 class="brand-title">农链溯源</h1>
            <p class="brand-subtitle">FISCO BCOS 区块链驱动</p>
          </div>
        </div>

        <p class="brand-slogan">让每一份农产品都有迹可循，让每一次消费都安心放心</p>

        <!-- 核心特性 -->
        <div class="features-grid">
          <div class="feature-card">
            <div class="feature-icon">
              <el-icon :size="28"><Link /></el-icon>
            </div>
            <div class="feature-text">
              <h4>全程可追溯</h4>
              <p>从田间到餐桌，每个环节清晰可查</p>
            </div>
          </div>
          <div class="feature-card">
            <div class="feature-icon">
              <el-icon :size="28"><Lock /></el-icon>
            </div>
            <div class="feature-text">
              <h4>数据不可篡改</h4>
              <p>区块链存证，信息真实可信</p>
            </div>
          </div>
          <div class="feature-card">
            <div class="feature-icon">
              <el-icon :size="28"><View /></el-icon>
            </div>
            <div class="feature-text">
              <h4>信息透明公开</h4>
              <p>扫码即查，消费更安心</p>
            </div>
          </div>
          <div class="feature-card">
            <div class="feature-icon">
              <el-icon :size="28"><Cpu /></el-icon>
            </div>
            <div class="feature-text">
              <h4>AI智能分析</h4>
              <p>智能生成溯源简报，一目了然</p>
            </div>
          </div>
        </div>

        <!-- 供应链流程 -->
        <div class="chain-section">
          <h3 class="section-title">供应链全程追溯</h3>
          <div class="chain-visual">
            <div class="chain-node" v-for="(role, index) in roles" :key="role.key">
              <div class="node-circle" :class="role.key">
                <el-icon :size="20"><component :is="role.icon" /></el-icon>
              </div>
              <span class="node-label">{{ role.name }}</span>
              <div class="node-line" v-if="index < roles.length - 1">
                <div class="line-arrow"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- 平台特点 -->
        <div class="stats-section">
          <div class="stat-item" v-for="stat in platformStats" :key="stat.label">
            <el-icon :size="20"><component :is="stat.icon" /></el-icon>
            <span class="stat-label">{{ stat.label }}</span>
          </div>
        </div>

        <!-- 底部信息 -->
        <div class="brand-footer">
          <p>技术支持：FISCO BCOS 联盟链 | Vue 3 + Element Plus</p>
        </div>
      </div>
    </div>

    <!-- 右侧登录/注册区 -->
    <div class="login-section">
      <div class="login-card">
        <!-- 标签切换 -->
        <div class="mode-tabs">
          <div
            class="mode-tab"
            :class="{ active: mode === 'login' }"
            @click="switchMode('login')"
          >
            登录
          </div>
          <div
            class="mode-tab"
            :class="{ active: mode === 'register' }"
            @click="switchMode('register')"
          >
            注册
          </div>
          <div class="tab-indicator" :class="{ register: mode === 'register' }"></div>
        </div>

        <!-- 登录表单 -->
        <div v-show="mode === 'login'" class="form-container">
          <div class="form-header">
            <p>请输入您的账号密码登录</p>
          </div>

          <!-- 登录表单 -->
          <el-form class="auth-form" @submit.prevent="handleLogin">
            <el-form-item>
              <el-input
                v-model="loginForm.username"
                placeholder="用户名"
                size="large"
                prefix-icon="User"
              />
            </el-form-item>
            <el-form-item>
              <el-input
                v-model="loginForm.password"
                type="password"
                placeholder="密码"
                size="large"
                prefix-icon="Lock"
                show-password
                @keyup.enter="handleLogin"
              />
            </el-form-item>

            <el-button
              type="primary"
              size="large"
              :loading="loading"
              @click="handleLogin"
              class="submit-btn"
            >
              {{ loading ? '登录中...' : '登录' }}
            </el-button>
          </el-form>

          <div class="form-footer">
            <span class="hint">还没有账号？<a @click="switchMode('register')">立即注册</a></span>
          </div>
        </div>

        <!-- 注册表单 -->
        <div v-show="mode === 'register'" class="form-container">
          <div class="form-header">
            <p>创建新账号，加入农产品溯源平台</p>
          </div>

          <!-- 角色选择 -->
          <div class="register-role-section">
            <label class="section-label">选择角色 <span class="required">*</span></label>
            <div class="role-selector register-roles">
              <div
                class="role-card"
                v-for="role in roles"
                :key="role.key"
                :class="[role.key, { active: registerForm.role === role.key }]"
                @click="selectRegisterRole(role)"
              >
                <el-icon :size="22"><component :is="role.icon" /></el-icon>
                <span class="role-name">{{ role.name }}</span>
              </div>
            </div>
          </div>

          <!-- 注册表单 -->
          <el-form class="auth-form" @submit.prevent="handleRegister">
            <el-form-item>
              <el-input
                v-model="registerForm.username"
                placeholder="用户名（用于登录）"
                size="large"
                prefix-icon="User"
              />
            </el-form-item>
            <el-form-item>
              <el-input
                v-model="registerForm.realName"
                placeholder="真实姓名/企业名称"
                size="large"
                prefix-icon="Postcard"
              />
            </el-form-item>
            <el-form-item>
              <el-input
                v-model="registerForm.phone"
                placeholder="手机号（选填）"
                size="large"
                prefix-icon="Phone"
              />
            </el-form-item>
            <el-form-item>
              <el-input
                v-model="registerForm.password"
                type="password"
                placeholder="密码（至少6位）"
                size="large"
                prefix-icon="Lock"
                show-password
              />
            </el-form-item>
            <el-form-item>
              <el-input
                v-model="registerForm.confirmPassword"
                type="password"
                placeholder="确认密码"
                size="large"
                prefix-icon="Lock"
                show-password
                @keyup.enter="handleRegister"
              />
            </el-form-item>

            <el-button
              type="primary"
              size="large"
              :loading="loading"
              @click="handleRegister"
              class="submit-btn"
              :style="{ background: `linear-gradient(135deg, ${selectedRoleColor}, ${selectedRoleColor}dd)` }"
            >
              {{ loading ? '注册中...' : '注册' }}
            </el-button>
          </el-form>

          <div class="form-footer">
            <span class="hint">注册即表示同意《用户协议》和《隐私政策》</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  background: linear-gradient(135deg, #1a1f36 0%, #0f1225 100%);
  position: relative;
  overflow: hidden;
}

/* 装饰背景 */
.bg-decoration {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
}

.dec-1 {
  width: 600px;
  height: 600px;
  background: rgba(45, 184, 77, 0.15);
  top: -200px;
  left: -100px;
  animation: float 20s ease-in-out infinite;
}

.dec-2 {
  width: 400px;
  height: 400px;
  background: rgba(24, 144, 255, 0.15);
  bottom: -100px;
  left: 30%;
  animation: float 15s ease-in-out infinite reverse;
}

.dec-3 {
  width: 300px;
  height: 300px;
  background: rgba(114, 46, 209, 0.1);
  top: 30%;
  left: 50%;
  animation: float 18s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0) scale(1); }
  50% { transform: translateY(-30px) scale(1.05); }
}

/* 左侧品牌区 */
.brand-section {
  flex: 1.2;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 80px;
  position: relative;
  z-index: 1;
}

.brand-content {
  color: white;
  max-width: 600px;
  width: 100%;
}

/* Logo */
.logo-wrapper {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 24px;
}

.logo-icon {
  width: 80px;
  height: 80px;
  background: linear-gradient(135deg, var(--primary-color), var(--primary-dark));
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 32px rgba(45, 184, 77, 0.3);
  flex-shrink: 0;
}

.logo-text {
  display: flex;
  flex-direction: column;
}

.brand-title {
  font-size: 40px;
  font-weight: 700;
  background: linear-gradient(90deg, #fff, #a8e6cf);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1.2;
}

.brand-subtitle {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
  margin-top: 4px;
}

.brand-slogan {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.75);
  margin-bottom: 40px;
  line-height: 1.6;
}

/* 特性网格 */
.features-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 40px;
}

.feature-card {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 20px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  transition: all 0.3s;
}

.feature-card:hover {
  background: rgba(255, 255, 255, 0.08);
  transform: translateY(-2px);
}

.feature-icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, rgba(45, 184, 77, 0.2), rgba(45, 184, 77, 0.1));
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary-color);
  flex-shrink: 0;
}

.feature-text h4 {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 4px;
  color: white;
}

.feature-text p {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
  line-height: 1.4;
}

/* 供应链流程 */
.chain-section {
  margin-bottom: 36px;
}

.section-title {
  font-size: 14px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 16px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.chain-visual {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 0;
}

.chain-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  flex: 1;
}

.node-circle {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  margin-bottom: 10px;
  position: relative;
  z-index: 2;
  transition: transform 0.3s, box-shadow 0.3s;
}

.node-circle:hover {
  transform: scale(1.1);
}

.node-circle.producer { background: linear-gradient(135deg, #52c41a, #73d13d); box-shadow: 0 4px 16px rgba(82, 196, 26, 0.4); }
.node-circle.processor { background: linear-gradient(135deg, #1890ff, #40a9ff); box-shadow: 0 4px 16px rgba(24, 144, 255, 0.4); }
.node-circle.inspector { background: linear-gradient(135deg, #722ed1, #9254de); box-shadow: 0 4px 16px rgba(114, 46, 209, 0.4); }
.node-circle.seller { background: linear-gradient(135deg, #fa8c16, #ffa940); box-shadow: 0 4px 16px rgba(250, 140, 22, 0.4); }
.node-circle.consumer { background: linear-gradient(135deg, #eb2f96, #f759ab); box-shadow: 0 4px 16px rgba(235, 47, 150, 0.4); }

.node-label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
  font-weight: 500;
}

.node-line {
  position: absolute;
  top: 24px;
  left: calc(50% + 24px);
  width: calc(100% - 48px);
  height: 2px;
  background: linear-gradient(90deg, rgba(255,255,255,0.3), rgba(255,255,255,0.1));
  z-index: 1;
}

.line-arrow {
  position: absolute;
  right: -4px;
  top: -3px;
  width: 0;
  height: 0;
  border-top: 4px solid transparent;
  border-bottom: 4px solid transparent;
  border-left: 6px solid rgba(255,255,255,0.3);
}

/* 平台特点 */
.stats-section {
  display: flex;
  justify-content: center;
  gap: 48px;
  padding: 24px 0;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  margin-bottom: 24px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.stat-item .el-icon {
  color: var(--primary-color);
}

.stat-label {
  font-size: 14px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.8);
}

/* 底部信息 */
.brand-footer {
  text-align: center;
}

.brand-footer p {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.35);
}

/* 右侧登录区 */
.login-section {
  width: 460px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  position: relative;
  z-index: 1;
}

.login-card {
  width: 100%;
  padding: 32px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}

/* 模式切换标签 */
.mode-tabs {
  display: flex;
  position: relative;
  background: #f5f7fa;
  border-radius: 12px;
  padding: 4px;
  margin-bottom: 24px;
}

.mode-tab {
  flex: 1;
  text-align: center;
  padding: 12px 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  transition: color 0.3s;
  position: relative;
  z-index: 2;
}

.mode-tab.active {
  color: var(--primary-color);
}

.tab-indicator {
  position: absolute;
  top: 4px;
  left: 4px;
  width: calc(50% - 4px);
  height: calc(100% - 8px);
  background: white;
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: transform 0.3s ease;
}

.tab-indicator.register {
  transform: translateX(100%);
}

/* 表单容器 */
.form-container {
  min-height: 380px;
}

.form-header {
  text-align: center;
  margin-bottom: 20px;
}

.form-header p {
  color: var(--text-muted);
  font-size: 14px;
}

/* 角色选择器（仅注册使用） */
.role-selector {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
  margin-bottom: 16px;
}

.register-roles {
  margin-bottom: 16px;
}

.role-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 6px;
  border-radius: 10px;
  border: 2px solid var(--border-color);
  cursor: pointer;
  transition: all 0.3s ease;
  background: white;
}

.role-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.role-card.active {
  border-color: currentColor;
}

.role-card.producer { color: var(--producer-color); }
.role-card.processor { color: var(--processor-color); }
.role-card.inspector { color: var(--inspector-color); }
.role-card.seller { color: var(--seller-color); }
.role-card.consumer { color: var(--consumer-color); }

.role-card.active.producer { border-color: var(--producer-color); background: rgba(82, 196, 26, 0.08); }
.role-card.active.processor { border-color: var(--processor-color); background: rgba(24, 144, 255, 0.08); }
.role-card.active.inspector { border-color: var(--inspector-color); background: rgba(114, 46, 209, 0.08); }
.role-card.active.seller { border-color: var(--seller-color); background: rgba(250, 140, 22, 0.08); }
.role-card.active.consumer { border-color: var(--consumer-color); background: rgba(235, 47, 150, 0.08); }

.role-name {
  font-size: 11px;
  font-weight: 600;
  margin-top: 6px;
  color: var(--text-primary);
}

/* 注册角色选择 */
.register-role-section {
  margin-bottom: 16px;
}

.section-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 10px;
}

.required {
  color: #f56c6c;
}

/* 表单 */
.auth-form {
  margin-bottom: 16px;
}

.auth-form .el-form-item {
  margin-bottom: 16px;
}

.auth-form :deep(.el-input__wrapper) {
  padding: 4px 16px;
  border-radius: 10px;
  box-shadow: 0 0 0 1px var(--border-color);
}

.auth-form :deep(.el-input__wrapper:hover),
.auth-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px var(--primary-color);
}

.submit-btn {
  width: 100%;
  height: 46px;
  font-size: 15px;
  font-weight: 600;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--primary-color), var(--primary-dark));
  border: none;
  transition: all 0.3s ease;
}

.submit-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(45, 184, 77, 0.35);
}

.form-footer {
  text-align: center;
  padding-top: 8px;
}

.hint {
  font-size: 12px;
  color: var(--text-muted);
}

.hint a {
  color: var(--primary-color);
  cursor: pointer;
  text-decoration: none;
}

.hint a:hover {
  text-decoration: underline;
}

/* 响应式 */
@media (max-width: 1200px) {
  .brand-section {
    padding: 40px;
  }

  .features-grid {
    grid-template-columns: 1fr;
  }

  .stats-section {
    flex-wrap: wrap;
    gap: 20px;
  }
}

@media (max-width: 1024px) {
  .login-container {
    flex-direction: column;
  }

  .brand-section {
    padding: 40px 20px;
    flex: none;
  }

  .brand-content {
    max-width: 100%;
  }

  .login-section {
    width: 100%;
    padding: 20px;
  }

  .chain-visual {
    display: none;
  }

  .features-grid {
    display: none;
  }

  .stats-section {
    justify-content: center;
  }
}

@media (max-width: 480px) {
  .login-card {
    padding: 24px 20px;
  }

  .role-selector {
    grid-template-columns: repeat(3, 1fr);
  }

  .stats-section {
    flex-direction: column;
    align-items: center;
    gap: 16px;
  }
}
</style>
