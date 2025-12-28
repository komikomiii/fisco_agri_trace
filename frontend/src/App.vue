<script setup>
import { onMounted } from 'vue'
import { useUserStore } from './store/user'
import { ElConfigProvider } from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'

const userStore = useUserStore()

onMounted(() => {
  userStore.restoreSession()
})
</script>

<template>
  <el-config-provider :locale="zhCn">
    <router-view v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </el-config-provider>
</template>

<style>
#app {
  min-height: 100vh;
}
</style>
