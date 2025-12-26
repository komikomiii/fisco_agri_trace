<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const history = ref([
  { id: 1, code: 'P20241201001', name: '番茄酱 500g', origin: '山东寿光', scanDate: '2024-12-01 14:30', result: 'verified' },
  { id: 2, code: 'P20241130002', name: '苹果汁 1L', origin: '陕西洛川', scanDate: '2024-11-30 10:15', result: 'verified' },
  { id: 3, code: 'FAKE12345', name: '未知产品', origin: '-', scanDate: '2024-11-28 16:45', result: 'failed' }
])

const viewDetail = (code) => {
  router.push(`/dashboard/trace/${code}`)
}
</script>

<template>
  <div class="history-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span class="title">
            <el-icon><Clock /></el-icon>
            查询记录
          </span>
          <el-button type="danger" text :icon="Delete">清空记录</el-button>
        </div>
      </template>

      <el-table :data="history" stripe>
        <el-table-column prop="code" label="溯源码">
          <template #default="{ row }">
            <el-tag effect="plain" type="info">{{ row.code }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="产品名称" />
        <el-table-column prop="origin" label="产地" />
        <el-table-column prop="scanDate" label="查询时间" />
        <el-table-column prop="result" label="验证结果" width="120">
          <template #default="{ row }">
            <el-tag :type="row.result === 'verified' ? 'success' : 'danger'">
              {{ row.result === 'verified' ? '验证通过' : '验证失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button
              v-if="row.result === 'verified'"
              type="primary"
              text
              size="small"
              @click="viewDetail(row.code)"
            >
              查看详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
}
</style>
