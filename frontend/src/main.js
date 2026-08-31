import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import Vant from 'vant'
import 'vant/lib/index.css'
import './styles.css'

import App from './App.vue'
import Home from './views/Home.vue'
import Camera from './views/Camera.vue'
import QuestionList from './views/QuestionList.vue'
import QuestionDetail from './views/QuestionDetail.vue'
import Practice from './views/Practice.vue'
import ExportView from './views/ExportView.vue'
import Report from './views/Report.vue'
import Settings from './views/Settings.vue'
import Children from './views/Children.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: Home, meta: { title: '首页' } },
    { path: '/camera', component: Camera, meta: { title: '拍照录入' } },
    { path: '/questions', component: QuestionList, meta: { title: '错题本' } },
    { path: '/questions/:id', component: QuestionDetail, meta: { title: '错题详情' } },
    { path: '/practice/:id', component: Practice, meta: { title: '相似题练习' } },
    { path: '/export/:id', component: ExportView, meta: { title: '导出练习' } },
    { path: '/reports', component: Report, meta: { title: '学情报告' } },
    { path: '/settings', component: Settings, meta: { title: 'AI 设置' } },
    { path: '/children', component: Children, meta: { title: '孩子管理' } },
  ],
})

const app = createApp(App)
app.use(router)
app.use(Vant)
app.mount('#app')