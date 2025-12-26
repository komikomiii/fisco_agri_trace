import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

/**
 * 通知状态管理
 * 处理待处理通知、关联产品链变动通知等
 */
export const useNotificationStore = defineStore('notification', () => {
  // ==================== 状态 ====================

  // 所有通知
  const notifications = ref([])

  // 通知抽屉是否打开
  const drawerVisible = ref(false)

  // ==================== 通知类型 ====================
  const NOTIFICATION_TYPES = {
    PENDING: 'pending',           // 待处理
    CHAIN_UPDATE: 'chain_update', // 产品链变动
    AMEND: 'amend',               // 修正通知
    REJECT: 'reject',             // 退回通知
    TERMINATE: 'terminate',       // 终止通知
    SYSTEM: 'system'              // 系统通知
  }

  // ==================== 模拟数据 ====================

  const initMockData = (userRole) => {
    const now = new Date()
    const baseNotifications = []

    // 根据角色生成不同的通知
    if (userRole === 'producer') {
      baseNotifications.push(
        {
          id: 1,
          type: NOTIFICATION_TYPES.REJECT,
          title: '产品被退回',
          content: '您的产品"草莓"被质检员退回，原因：农药残留超标。请重新处理后再次送检。',
          relatedTraceCode: 'TRACE-20241226-003',
          read: false,
          createdAt: new Date(now - 2 * 60 * 60 * 1000).toISOString()
        }
      )
    }

    if (userRole === 'processor') {
      baseNotifications.push(
        {
          id: 2,
          type: NOTIFICATION_TYPES.PENDING,
          title: '新原料待接收',
          content: '来自张三农场的有机番茄 500kg 已到达，请尽快处理。',
          relatedTraceCode: 'TRACE-20241226-001',
          read: false,
          createdAt: new Date(now - 1 * 60 * 60 * 1000).toISOString()
        },
        {
          id: 3,
          type: NOTIFICATION_TYPES.PENDING,
          title: '指定原料待接收',
          content: '张三农场指定发送给您的红富士苹果 2000kg 已到达。',
          relatedTraceCode: 'TRACE-20241226-002',
          read: true,
          createdAt: new Date(now - 24 * 60 * 60 * 1000).toISOString()
        }
      )
    }

    if (userRole === 'inspector') {
      baseNotifications.push(
        {
          id: 4,
          type: NOTIFICATION_TYPES.PENDING,
          title: '新产品待检测',
          content: '绿源加工厂送检的"鲜榨苹果汁"等待您的检测。',
          relatedTraceCode: 'TRACE-20241226-002',
          read: false,
          createdAt: new Date(now - 30 * 60 * 1000).toISOString()
        }
      )
    }

    if (userRole === 'seller') {
      baseNotifications.push(
        {
          id: 5,
          type: NOTIFICATION_TYPES.PENDING,
          title: '新产品可入库',
          content: '精选番茄已通过质检，可以入库销售。',
          relatedTraceCode: 'TRACE-20241226-001',
          read: false,
          createdAt: new Date(now - 4 * 60 * 60 * 1000).toISOString()
        }
      )
    }

    // 所有角色都能收到的系统通知
    baseNotifications.push(
      {
        id: 100,
        type: NOTIFICATION_TYPES.SYSTEM,
        title: '系统维护通知',
        content: '系统将于今晚23:00-次日01:00进行维护升级，届时可能无法正常使用。',
        relatedTraceCode: null,
        read: true,
        createdAt: new Date(now - 48 * 60 * 60 * 1000).toISOString()
      }
    )

    // 关联产品链变动通知（所有参与过的人都能收到）
    baseNotifications.push(
      {
        id: 101,
        type: NOTIFICATION_TYPES.TERMINATE,
        title: '产品链已终止',
        content: '您参与的产品链 TRACE-20241226-003（草莓）已被终止。原因：农药残留超标，无法处理。',
        relatedTraceCode: 'TRACE-20241226-003',
        read: false,
        createdAt: new Date(now - 5 * 60 * 60 * 1000).toISOString()
      }
    )

    notifications.value = baseNotifications.sort(
      (a, b) => new Date(b.createdAt) - new Date(a.createdAt)
    )
  }

  // ==================== 计算属性 ====================

  // 未读通知数量
  const unreadCount = computed(() =>
    notifications.value.filter(n => !n.read).length
  )

  // 未读通知
  const unreadNotifications = computed(() =>
    notifications.value.filter(n => !n.read)
  )

  // 按类型分组
  const pendingNotifications = computed(() =>
    notifications.value.filter(n => n.type === NOTIFICATION_TYPES.PENDING)
  )

  const chainUpdateNotifications = computed(() =>
    notifications.value.filter(n =>
      [NOTIFICATION_TYPES.CHAIN_UPDATE, NOTIFICATION_TYPES.AMEND,
       NOTIFICATION_TYPES.REJECT, NOTIFICATION_TYPES.TERMINATE].includes(n.type)
    )
  )

  // ==================== 方法 ====================

  // 添加通知
  const addNotification = (notification) => {
    const newNotification = {
      id: Date.now(),
      read: false,
      createdAt: new Date().toISOString(),
      ...notification
    }
    notifications.value.unshift(newNotification)
    return newNotification
  }

  // 标记为已读
  const markAsRead = (notificationId) => {
    const notification = notifications.value.find(n => n.id === notificationId)
    if (notification) {
      notification.read = true
    }
  }

  // 全部标记为已读
  const markAllAsRead = () => {
    notifications.value.forEach(n => {
      n.read = true
    })
  }

  // 删除通知
  const removeNotification = (notificationId) => {
    const index = notifications.value.findIndex(n => n.id === notificationId)
    if (index > -1) {
      notifications.value.splice(index, 1)
    }
  }

  // 清空所有通知
  const clearAll = () => {
    notifications.value = []
  }

  // 打开/关闭通知抽屉
  const toggleDrawer = () => {
    drawerVisible.value = !drawerVisible.value
  }

  const openDrawer = () => {
    drawerVisible.value = true
  }

  const closeDrawer = () => {
    drawerVisible.value = false
  }

  // 获取通知图标
  const getNotificationIcon = (type) => {
    const iconMap = {
      [NOTIFICATION_TYPES.PENDING]: 'Clock',
      [NOTIFICATION_TYPES.CHAIN_UPDATE]: 'Refresh',
      [NOTIFICATION_TYPES.AMEND]: 'Edit',
      [NOTIFICATION_TYPES.REJECT]: 'Back',
      [NOTIFICATION_TYPES.TERMINATE]: 'CircleClose',
      [NOTIFICATION_TYPES.SYSTEM]: 'Bell'
    }
    return iconMap[type] || 'Bell'
  }

  // 获取通知颜色
  const getNotificationColor = (type) => {
    const colorMap = {
      [NOTIFICATION_TYPES.PENDING]: '#1890ff',
      [NOTIFICATION_TYPES.CHAIN_UPDATE]: '#52c41a',
      [NOTIFICATION_TYPES.AMEND]: '#faad14',
      [NOTIFICATION_TYPES.REJECT]: '#fa8c16',
      [NOTIFICATION_TYPES.TERMINATE]: '#f5222d',
      [NOTIFICATION_TYPES.SYSTEM]: '#722ed1'
    }
    return colorMap[type] || '#909399'
  }

  // 格式化时间
  const formatTime = (timestamp) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diff = now - date

    if (diff < 60 * 1000) {
      return '刚刚'
    } else if (diff < 60 * 60 * 1000) {
      return `${Math.floor(diff / (60 * 1000))}分钟前`
    } else if (diff < 24 * 60 * 60 * 1000) {
      return `${Math.floor(diff / (60 * 60 * 1000))}小时前`
    } else if (diff < 7 * 24 * 60 * 60 * 1000) {
      return `${Math.floor(diff / (24 * 60 * 60 * 1000))}天前`
    } else {
      return date.toLocaleDateString('zh-CN')
    }
  }

  return {
    // 状态
    notifications,
    drawerVisible,
    NOTIFICATION_TYPES,

    // 计算属性
    unreadCount,
    unreadNotifications,
    pendingNotifications,
    chainUpdateNotifications,

    // 方法
    initMockData,
    addNotification,
    markAsRead,
    markAllAsRead,
    removeNotification,
    clearAll,
    toggleDrawer,
    openDrawer,
    closeDrawer,
    getNotificationIcon,
    getNotificationColor,
    formatTime
  }
})
