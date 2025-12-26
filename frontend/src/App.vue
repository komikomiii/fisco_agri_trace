<script setup>
import { onMounted } from 'vue'
import { useUserStore } from './store/user'

const userStore = useUserStore()

onMounted(() => {
  userStore.restoreSession()
})
</script>

<template>
  <router-view v-slot="{ Component }">
    <transition name="fade" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>

<style>
#app {
  min-height: 100vh;
}
</style>
