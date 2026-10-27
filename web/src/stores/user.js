import { defineStore } from 'pinia'
import api from '@/api'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: JSON.parse(localStorage.getItem('user') || 'null'),
  }),
  getters: {
    isLoggedIn: (state) => !!state.token,
    isAdmin: (state) => state.user?.role === 'admin',
  },
  actions: {
    async login(username, password) {
      const res = await api.post('/auth/login', { username, password })
      this.token = res.access_token
      this.user = res.user
      localStorage.setItem('token', res.access_token)
      localStorage.setItem('user', JSON.stringify(res.user))
      return res
    },
    async register(data) {
      const res = await api.post('/auth/register', data)
      this.token = res.access_token
      this.user = res.user
      localStorage.setItem('token', res.access_token)
      localStorage.setItem('user', JSON.stringify(res.user))
      return res
    },
    async fetchProfile() {
      const res = await api.get('/auth/me')
      this.user = res
      localStorage.setItem('user', JSON.stringify(res))
    },
    async updateProfile(data) {
      const res = await api.put('/auth/me', data)
      this.user = res
      localStorage.setItem('user', JSON.stringify(res))
      return res
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    },
  },
})
