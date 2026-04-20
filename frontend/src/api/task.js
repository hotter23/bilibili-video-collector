import request from './index'

// 创建任务
export function createTaskAPI(data) {
  return request({
    url: '/tasks',
    method: 'POST',
    data
  })
}

// 获取任务列表
export function getTaskListAPI(params) {
  return request({
    url: '/tasks',
    method: 'GET',
    params
  })
}

// 获取任务详情
export function getTaskDetailAPI(taskId) {
  return request({
    url: `/tasks/${taskId}`,
    method: 'GET'
  })
}

// 取消任务
export function cancelTaskAPI(taskId) {
  return request({
    url: `/tasks/${taskId}/cancel`,
    method: 'POST'
  })
}

// 重试任务
export function retryTaskAPI(taskId) {
  return request({
    url: `/tasks/${taskId}/retry`,
    method: 'POST'
  })
}

// 批量创建任务
export function batchCreateTasksAPI(urls, options = {}) {
  return request({
    url: '/tasks/batch',
    method: 'POST',
    data: { urls, ...options }
  })
}

// 获取任务统计
export function getTaskStatsAPI() {
  return request({
    url: '/tasks/stats',
    method: 'GET'
  })
}
