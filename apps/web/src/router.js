import { createRouter, createWebHistory } from 'vue-router'
import Home from './views/Home.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: Home
    },
    {
      path: '/terminal',
      component: () => import('./views/Terminal.vue')
    },
    {
      path: '/modules/cmts-swapper',
      component: () => import('./views/modules/CMTS_Swapper.vue')
    },
    {
      path: '/modules/cmts-tmpfs',
      component: () => import('./views/modules/CMTS_TMPFS.vue')
    },
    {
      path: '/modules/ssh-executor',
      component: () => import('./views/modules/SSHExecutor.vue')
    },
    {
      path: '/modules/cmts-modem-reset',
      component: () => import('./views/modules/CMTS_ModemReset.vue')
    },
    {
      path: '/modules/cmts-compare',
      component: () => import('./views/modules/CMTS_Compare.vue')
    },
    {
      path: '/modules/wo-raport',
      component: () => import('./views/modules/WO_Raport.vue')
    },
    {
      path: '/settings',
      children: [
        {
          path: 'general',
          component: () => import('./views/settings/General.vue')
        },
        {
          path: 'accounts',
          component: () => import('./views/settings/Accounts.vue')
        },
        {
          path: 'devices',
          component: () => import('./views/settings/Devices.vue')
        },
        {
          path: 'tunnel',
          component: () => import('./views/settings/Tunnel.vue')
        },
        {
          path: 'modules',
          component: () => import('./views/settings/Modules.vue')
        },
        {
          path: 'sites',
          component: () => import('./views/settings/Sites.vue')
        },
        {
          path: 'raports',
          component: () => import('./views/settings/Raports.vue')
        },
        {
          path: 'map',
          component: () => import('./views/settings/Map.vue')
        },
        {
          path: 'cache-debug',
          component: () => import('./views/settings/CacheDebug.vue')
        }
      ]
    }
  ]
})

export default router
