import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const api = axios.create({
  baseURL: '/chem/api/v1',
  timeout: 60000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

/** 取出后端给的 detail：字符串直接用；FastAPI 校验错误是数组，拼起来 */
const extractDetail = (data) => {
  const d = data && data.detail
  if (!d) return ''
  if (typeof d === 'string') return d
  if (Array.isArray(d)) {
    return d
      .map((x) => (typeof x === 'string' ? x : x && x.msg ? x.msg : ''))
      .filter(Boolean)
      .join('；')
  }
  return ''
}

/** 登录/注册接口的 401 是「账号密码不对」，不是「登录过期」 */
const isAuthEndpoint = (config) => /\/auth\/(login|register)/.test((config && config.url) || '')

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const { response, config } = error

    if (response) {
      const { status, data } = response
      // 后端基本都给了具体原因（"用户名或密码错误，剩余尝试次数：4"），优先用它
      const detail = extractDetail(data)

      if (status === 401) {
        if (isAuthEndpoint(config)) {
          // 登录失败：只提示，不跳转、不清 token
          ElMessage.error(detail || '用户名或密码错误')
        } else {
          // token 失效：后端可能回英文（Not authenticated），统一成中文提示
          localStorage.removeItem('token')
          localStorage.removeItem('user')
          ElMessage.error('登录已过期，请重新登录')
          router.push('/login')
        }
      } else if (status === 403) {
        ElMessage.error(detail || '没有权限执行此操作')
      } else if (status === 404) {
        ElMessage.error(detail || '请求的内容不存在')
      } else if (status === 422) {
        ElMessage.error(detail || '提交的内容格式不正确')
      } else if (status === 429) {
        ElMessage.error(detail || '操作太频繁，请稍后再试')
      } else if (status >= 500) {
        ElMessage.error(detail || '服务器出错了，请稍后重试')
      } else {
        ElMessage.error(detail || `请求失败（${status}）`)
      }
    } else if (error.code === 'ECONNABORTED') {
      ElMessage.error('请求超时，请检查网络后重试')
    } else {
      ElMessage.error('网络错误，请检查连接')
    }

    return Promise.reject(error)
  }
)

export default api
