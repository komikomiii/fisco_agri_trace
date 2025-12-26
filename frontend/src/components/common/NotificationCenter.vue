<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificationStore } from '../../store/notification'

const router = useRouter()
const notificationStore = useNotificationStore()

const notifications = computed(() => notificationStore.notifications)
const unreadCount = computed(() => notificationStore.unreadCount)

const handleNotificationClick = (notification) => {
  // 标记为已读
  notificationStore.markAsRead(notification.id)

  // 如果有关联的产品链，跳转到详情页
  if (notification.relatedTraceCode) {
    router.push(`/dashboard/trace/${notification.relatedTraceCode}`)
    notificationStore.closeDrawer()
  }
}

const handleMarkAllRead = () => {
  notificationStore.markAllAsRead()
}

const handleClearAll = () => {
  notificationStore.clearAll()
}

const getTypeLabel = (type) => {
  const labels = {
    pending: '待处理',
    chain_update: '产品链更新',
    amend: '信息修正',
    reject: '产品退回',
    terminate: '产品链终止',
    system: '系统通知'
  }
  return labels[type] || '通知'
}

const getTypeTagType = (type) => {
  const types = {
    pending: 'primary',
    chain_update: 'success',
    amend: 'warning',
    reject: 'warning',
    terminate: 'danger',
    system: 'info'
  }
  return types[type] || 'info'
}
</script>

<template>
  <el-drawer
    v-model="notificationStore.drawerVisible"
    title="消息通知"
    direction="rtl"
    size="380px"
  >
    <template #header>
      <div class="drawer-header">
        <span class="drawer-title">
          消息通知
          <el-badge v-if="unreadCount > 0" :value="unreadCount" class="unread-badge" />
        </span>
        <div class="header-actions">
          <el-button text size="small" @click="handleMarkAllRead" :disabled="unreadCount === 0">
            全部已读
          </el-button>
          <el-button text size="small" type="danger" @click="handleClearAll" :disabled="notifications.length === 0">
            清空
          </el-button>
        </div>
      </div>
    </template>

    <div class="notification-list" v-if="notifications.length > 0">
      <div
        v-for="notification in notifications"
        :key="notification.id"
        class="notification-item"
        :class="{ unread: !notification.read }"
        @click="handleNotificationClick(notification)"
      >
        <div class="notification-icon" :style="{ background: notificationStore.getNotificationColor(notification.type) }">
          <el-icon><component :is="notificationStore.getNotificationIcon(notification.type)" /></el-icon>
        </div>

        <div class="notification-content">
          <div class="notification-header">
            <el-tag :type="getTypeTagType(notification.type)" size="small" effect="plain">
              {{ getTypeLabel(notification.type) }}
            </el-tag>
            <span class="notification-time">
              {{ notificationStore.formatTime(notification.createdAt) }}
            </span>
          </div>
          <h4 class="notification-title">{{ notification.title }}</h4>
          <p class="notification-text">{{ notification.content }}</p>
          <div v-if="notification.relatedTraceCode" class="notification-trace">
            <el-icon><Connection /></el-icon>
            <span>{{ notification.relatedTraceCode }}</span>
          </div>
        </div>

        <div v-if="!notification.read" class="unread-dot"></div>
      </div>
    </div>

    <el-empty v-else description="暂无通知" :image-size="120" />
  </el-drawer>
</template>

<style scoped>
.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.drawer-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.notification-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.notification-item {
  display: flex;
  gap: 12px;
  padding: 16px;
  background: var(--bg-color);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
}

.notification-item:hover {
  background: #f0f2f5;
  transform: translateX(-4px);
}

.notification-item.unread {
  background: linear-gradient(135deg, rgba(24, 144, 255, 0.06), rgba(24, 144, 255, 0.02));
}

.notification-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.notification-content {
  flex: 1;
  min-width: 0;
}

.notification-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.notification-time {
  font-size: 12px;
  color: var(--text-muted);
}

.notification-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.notification-text {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.notification-trace {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 6px 10px;
  background: rgba(45, 184, 77, 0.08);
  border-radius: 6px;
  font-size: 12px;
  color: var(--primary-color);
  font-family: monospace;
}

.unread-dot {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 8px;
  height: 8px;
  background: #1890ff;
  border-radius: 50%;
}
</style>
