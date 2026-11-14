/**
 * 题目图片 URL 修正
 *
 * 后端返回的是 /uploads/questions/xxx.png，本地开发时根路径可用；
 * 线上站点挂在 /chem/app/ 下，图片实际在 /chem/uploads/...。
 * 这里统一补上 BASE_URL 对应的站点前缀，避免 404。
 */
export function mediaUrl(url) {
  if (!url || typeof url !== 'string') return ''
  if (/^(https?:|data:|blob:)/i.test(url)) return url
  const base = import.meta.env.BASE_URL || '/'
  const root = base.replace(/app\/$/, '')
  if (url.startsWith(root)) return url
  if (url.startsWith('/uploads/')) {
    return root.replace(/\/$/, '') + url
  }
  return url
}
