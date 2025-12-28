<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '../../store/user'
import { useProductStore } from '../../store/product'
import { useNotificationStore } from '../../store/notification'
import { ElMessageBox } from 'element-plus'
import NotificationCenter from '../../components/common/NotificationCenter.vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const productStore = useProductStore()
const notificationStore = useNotificationStore()

const isCollapse = ref(false)
const activeMenu = computed(() => route.path)

// 初始化数据
onMounted(() => {
  productStore.initMockData()
  notificationStore.initMockData(userStore.user?.role)
})

// 根据角色获取菜单
const menuItems = computed(() => {
  const role = userStore.user?.role || 'consumer'
  const baseMenus = [
    { path: '/dashboard/home', icon: 'HomeFilled', title: '工作台' }
  ]

  const roleMenus = {
    producer: [
      { path: '/dashboard/producer/products', icon: 'Grape', title: '原料管理' },
      { path: '/dashboard/producer/harvest', icon: 'Calendar', title: '采收登记' }
    ],
    processor: [
      { path: '/dashboard/processor/receive', icon: 'Box', title: '原料接收' },
      { path: '/dashboard/processor/process', icon: 'SetUp', title: '加工记录' }
    ],
    inspector: [
      { path: '/dashboard/inspector/pending', icon: 'Document', title: '待检产品' },
      { path: '/dashboard/inspector/reports', icon: 'DataAnalysis', title: '检测报告' }
    ],
    seller: [
      { path: '/dashboard/seller/inventory', icon: 'GoodsFilled', title: '库存管理' },
      { path: '/dashboard/seller/sales', icon: 'ShoppingCart', title: '销售记录' }
    ],
    consumer: [
      { path: '/dashboard/consumer/scan', icon: 'Camera', title: '扫码溯源' },
      { path: '/dashboard/consumer/history', icon: 'Clock', title: '查询记录' }
    ]
  }

  return [...baseMenus, ...(roleMenus[role] || [])]
})

// 角色颜色
const roleColors = {
  producer: '#52c41a',
  processor: '#1890ff',
  inspector: '#722ed1',
  seller: '#fa8c16',
  consumer: '#eb2f96'
}

const roleColor = computed(() => roleColors[userStore.user?.role] || '#2db84d')

// 未读通知数量
const unreadCount = computed(() => notificationStore.unreadCount)

// 打开通知中心
const openNotificationCenter = () => {
  notificationStore.openDrawer()
}

const handleLogout = () => {
  ElMessageBox.confirm('确定要退出登录吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    userStore.logout()
    router.push('/login')
  }).catch(() => {})
}
</script>

<template>
  <el-container class="layout-container">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapse ? '64px' : '240px'" class="layout-aside">
      <div class="aside-header">
        <div class="logo">
          <el-icon :size="28" :color="roleColor"><Connection /></el-icon>
          <transition name="fade">
            <span v-if="!isCollapse" class="logo-text">农链溯源</span>
          </transition>
        </div>
      </div>

      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapse"
        :collapse-transition="false"
        router
        class="aside-menu"
      >
        <el-menu-item
          v-for="item in menuItems"
          :key="item.path"
          :index="item.path"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <template #title>{{ item.title }}</template>
        </el-menu-item>
      </el-menu>

      <!-- 用户信息 -->
      <div class="aside-footer">
        <div class="user-card" :class="userStore.user?.role">
          <el-avatar :size="36" :style="{ background: roleColor }">
            {{ userStore.user?.name?.charAt(0) || 'U' }}
          </el-avatar>
          <transition name="fade">
            <div v-if="!isCollapse" class="user-info">
              <span class="user-name">{{ userStore.user?.name }}</span>
              <span class="user-role">{{ userStore.user?.roleName }}</span>
              <span v-if="userStore.user?.blockchainAddress" class="user-address">
                {{ userStore.user?.blockchainAddress?.slice(0, 8) }}...{{ userStore.user?.blockchainAddress?.slice(-6) }}
              </span>
            </div>
          </transition>
        </div>
      </div>
    </el-aside>

    <!-- 主内容区 -->
    <el-container class="layout-main">
      <!-- 顶部导航 -->
      <el-header class="layout-header">
        <div class="header-left">
          <el-button
            :icon="isCollapse ? 'Expand' : 'Fold'"
            text
            @click="isCollapse = !isCollapse"
          />
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/dashboard/home' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="route.meta.title !== '工作台'">
              {{ route.meta.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="header-right">
          <!-- 通知按钮 -->
          <el-tooltip content="消息通知" placement="bottom">
            <div class="notification-btn" @click="openNotificationCenter">
              <el-badge :value="unreadCount" :max="99" :hidden="unreadCount === 0">
                <div class="notification-icon-wrapper">
                  <el-icon :size="20"><Bell /></el-icon>
                </div>
              </el-badge>
            </div>
          </el-tooltip>

          <!-- 用户下拉菜单 -->
          <el-dropdown trigger="click">
            <div class="user-dropdown">
              <el-avatar :size="32" :style="{ background: roleColor }">
                {{ userStore.user?.name?.charAt(0) || 'U' }}
              </el-avatar>
              <span class="user-dropdown-name">{{ userStore.user?.name }}</span>
              <el-icon><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item :icon="User" disabled>
                  <div class="user-dropdown-info">
                    <span class="user-dropdown-label">用户名</span>
                    <span class="user-dropdown-value">{{ userStore.user?.name }}</span>
                  </div>
                </el-dropdown-item>
                <el-dropdown-item :icon="User" disabled>
                  <div class="user-dropdown-info">
                    <span class="user-dropdown-label">角色</span>
                    <span class="user-dropdown-value">{{ userStore.user?.roleName }}</span>
                  </div>
                </el-dropdown-item>
                <el-dropdown-item v-if="userStore.user?.blockchainAddress" :icon="Wallet" disabled>
                  <div class="user-dropdown-info">
                    <span class="user-dropdown-label">区块链地址</span>
                    <span class="user-dropdown-address">{{ userStore.user?.blockchainAddress }}</span>
                  </div>
                </el-dropdown-item>
                <el-dropdown-item divided :icon="SwitchButton" @click="handleLogout">
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 内容区 -->
      <el-main class="layout-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>

    <!-- 通知中心抽屉 -->
    <NotificationCenter />
  </el-container>
</template>

<style scoped>
.layout-container {
  height: 100vh;
  background: var(--bg-color);
}

/* 侧边栏 */
.layout-aside {
  background: #fff;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  overflow: hidden;
}

.aside-header {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid var(--border-color);
  padding: 0 16px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  background: linear-gradient(135deg, #2db84d, #1a9938);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  white-space: nowrap;
}

.aside-menu {
  flex: 1;
  border: none;
  padding: 12px 0;
}

.aside-menu .el-menu-item {
  margin: 4px 12px;
  border-radius: 8px;
  height: 44px;
}

.aside-menu .el-menu-item.is-active {
  background: linear-gradient(135deg, rgba(45, 184, 77, 0.1), rgba(45, 184, 77, 0.05));
  color: var(--primary-color);
}

.aside-menu .el-menu-item:hover {
  background: rgba(45, 184, 77, 0.08);
}

/* 用户卡片 */
.aside-footer {
  padding: 16px;
  border-top: 1px solid var(--border-color);
}

.user-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(45, 184, 77, 0.08), rgba(45, 184, 77, 0.02));
}

.user-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.user-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-role {
  font-size: 12px;
  color: var(--text-muted);
}

.user-address {
  font-size: 11px;
  color: var(--primary-color);
  font-family: 'Courier New', monospace;
  margin-top: 4px;
  opacity: 0.8;
}

/* 顶部导航 */
.layout-header {
  height: 64px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.notification-btn {
  cursor: pointer;
  padding: 4px;
  border-radius: 8px;
  transition: background 0.2s;
}

.notification-btn:hover {
  background: var(--bg-color);
}

.notification-icon-wrapper {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.notification-icon-wrapper:hover {
  color: var(--primary-color);
  background: rgba(45, 184, 77, 0.1);
}

.user-dropdown {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 8px;
  transition: background 0.2s;
}

.user-dropdown:hover {
  background: var(--bg-color);
}

.user-dropdown-name {
  font-size: 14px;
  color: var(--text-primary);
}

/* 下拉菜单用户信息 */
.user-dropdown-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 4px 0;
}

.user-dropdown-label {
  font-size: 12px;
  color: var(--text-muted);
}

.user-dropdown-value {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
}

.user-dropdown-address {
  font-size: 12px;
  color: var(--primary-color);
  font-family: 'Courier New', monospace;
  word-break: break-all;
  line-height: 1.4;
}

/* 内容区 */
.layout-content {
  padding: 24px;
  background: var(--bg-color);
  overflow-y: auto;
}

/* 过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
