import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/login'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/auth/Login.vue'),
    meta: { title: '登录 - 农产品溯源平台' }
  },
  {
    path: '/trace/:code',
    name: 'PublicTrace',
    component: () => import('../views/trace/PublicTrace.vue'),
    meta: { title: '溯源查询' }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/dashboard/Layout.vue'),
    redirect: '/dashboard/home',
    children: [
      {
        path: 'home',
        name: 'Home',
        component: () => import('../views/dashboard/Home.vue'),
        meta: { title: '工作台' }
      },
      // 原料商
      {
        path: 'producer/products',
        name: 'ProducerProducts',
        component: () => import('../views/producer/Products.vue'),
        meta: { title: '原料管理', role: 'producer' }
      },
      {
        path: 'producer/harvest',
        name: 'ProducerHarvest',
        component: () => import('../views/producer/Harvest.vue'),
        meta: { title: '采收登记', role: 'producer' }
      },
      // 加工商
      {
        path: 'processor/receive',
        name: 'ProcessorReceive',
        component: () => import('../views/processor/Receive.vue'),
        meta: { title: '原料接收', role: 'processor' }
      },
      {
        path: 'processor/process',
        name: 'ProcessorProcess',
        component: () => import('../views/processor/Process.vue'),
        meta: { title: '加工记录', role: 'processor' }
      },
      // 质检员
      {
        path: 'inspector/pending',
        name: 'InspectorPending',
        component: () => import('../views/inspector/Pending.vue'),
        meta: { title: '待检产品', role: 'inspector' }
      },
      {
        path: 'inspector/reports',
        name: 'InspectorReports',
        component: () => import('../views/inspector/Reports.vue'),
        meta: { title: '检测报告', role: 'inspector' }
      },
      // 销售商
      {
        path: 'seller/inventory',
        name: 'SellerInventory',
        component: () => import('../views/seller/Products.vue'),
        meta: { title: '库存管理', role: 'seller' }
      },
      {
        path: 'seller/sales',
        name: 'SellerSales',
        component: () => import('../views/seller/Sales.vue'),
        meta: { title: '销售记录', role: 'seller' }
      },
      // 消费者
      {
        path: 'consumer/scan',
        name: 'ConsumerScan',
        component: () => import('../views/consumer/Scan.vue'),
        meta: { title: '扫码溯源', role: 'consumer' }
      },
      {
        path: 'consumer/report/:code',
        name: 'ConsumerReport',
        component: () => import('../views/consumer/Report.vue'),
        meta: { title: '溯源简报', role: 'consumer' }
      },
      {
        path: 'consumer/history',
        name: 'ConsumerHistory',
        component: () => import('../views/consumer/History.vue'),
        meta: { title: '查询记录', role: 'consumer' }
      },
      // 通用 - 溯源详情
      {
        path: 'trace/:code',
        name: 'TraceDetail',
        component: () => import('../views/trace/Detail.vue'),
        meta: { title: '溯源详情' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  document.title = to.meta.title || '农产品溯源平台'
  next()
})

export default router
