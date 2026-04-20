import request from './index'

// 获取看板数据
export function getDashboardAPI() {
  return request({
    url: '/metrics/dashboard',
    method: 'GET'
  })
}

// 获取趋势数据
export function getTrendAPI(days = 7) {
  return request({
    url: '/metrics/trend',
    method: 'GET',
    params: { days }
  })
}

// 获取任务指标
export function getTaskMetricsAPI(taskId) {
  return request({
    url: `/metrics/task/${taskId}`,
    method: 'GET'
  })
}

// 获取速度曲线
export function getSpeedCurveAPI(taskId) {
  return request({
    url: `/metrics/speed-curve/${taskId}`,
    method: 'GET'
  })
}
