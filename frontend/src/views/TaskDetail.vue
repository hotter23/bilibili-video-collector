<template>
  <div class="task-detail" v-loading="loading">
    <!-- 基本信息 -->
    <el-card>
      <template #header>任务信息</template>
      <el-descriptions :column="2" border v-if="task">
        <el-descriptions-item label="任务ID">{{ task.id }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusType(task.status)">{{ statusText(task.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="视频URL" :span="2">
          <a :href="task.url" target="_blank" style="color: #409eff;">{{ task.url }}</a>
        </el-descriptions-item>
        <el-descriptions-item label="清晰度">{{ task.quality }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatTime(task.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="开始时间">{{ formatTime(task.started_at) || '-' }}</el-descriptions-item>
        <el-descriptions-item label="完成时间">{{ formatTime(task.finished_at) || '-' }}</el-descriptions-item>
        <el-descriptions-item label="进度" :span="2">
          <el-progress :percentage="task.progress || 0" :status="task.progress >= 100 ? 'success' : ''" />
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 视频元数据 -->
    <el-card style="margin-top: 20px;" v-if="task?.metadata">
      <template #header>视频信息</template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="B站视频号">{{ task.metadata.bvid }}</el-descriptions-item>
        <el-descriptions-item label="作者">{{ task.metadata.author }}</el-descriptions-item>
        <el-descriptions-item label="标题" :span="2">{{ task.metadata.title }}</el-descriptions-item>
        <el-descriptions-item label="时长">{{ formatDuration(task.metadata.duration) }}</el-descriptions-item>
        <el-descriptions-item label="文件大小">{{ formatSize(task.metadata.file_size) }}</el-descriptions-item>
        <el-descriptions-item label="输出路径" :span="2">{{ task.metadata.output_path }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 性能指标 -->
    <el-card style="margin-top: 20px;" v-if="metrics">
      <template #header>性能指标</template>
      <el-row :gutter="20">
        <el-col :span="6">
          <div class="metric-item">
            <div class="metric-label">解析耗时</div>
            <div class="metric-value">{{ formatDuration(metrics.parse_time_ms / 1000) }}</div>
            <div class="metric-percent">({{ metrics.parse_percent }}%)</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-item">
            <div class="metric-label">下载耗时</div>
            <div class="metric-value">{{ formatDuration(metrics.download_time_ms / 1000) }}</div>
            <div class="metric-percent">({{ metrics.download_percent }}%)</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-item">
            <div class="metric-label">合并耗时</div>
            <div class="metric-value">{{ formatDuration(metrics.merge_time_ms / 1000) }}</div>
            <div class="metric-percent">({{ metrics.merge_percent }}%)</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-item">
            <div class="metric-label">总耗时</div>
            <div class="metric-value">{{ formatDuration(metrics.total_time_ms / 1000) }}</div>
          </div>
        </el-col>
      </el-row>

      <el-row :gutter="20" style="margin-top: 20px;">
        <el-col :span="8">
          <div class="metric-item">
            <div class="metric-label">平均速度</div>
            <div class="metric-value">{{ metrics.avg_speed_mbps || '-' }} MB/s</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="metric-item">
            <div class="metric-label">峰值速度</div>
            <div class="metric-value">{{ metrics.peak_speed_mbps || '-' }} MB/s</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="metric-item">
            <div class="metric-label">重试次数</div>
            <div class="metric-value">{{ metrics.retry_count || 0 }}</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 速度曲线 -->
    <el-card style="margin-top: 20px;" v-if="speedCurveData.length > 0">
      <template #header>下载速度曲线</template>
      <div ref="speedChartRef" style="height: 250px;"></div>
    </el-card>

    <!-- 错误日志 -->
    <el-card style="margin-top: 20px;" v-if="errors.length > 0">
      <template #header>错误日志</template>
      <el-timeline>
        <el-timeline-item 
          v-for="error in errors" 
          :key="error.id" 
          :timestamp="formatTime(error.created_at)"
          type="danger"
        >
          <p><strong>阶段:</strong> {{ error.stage }}</p>
          <p><strong>类型:</strong> {{ error.error_type }}</p>
          <p><strong>消息:</strong> {{ error.error_msg }}</p>
        </el-timeline-item>
      </el-timeline>
    </el-card>

    <!-- 操作按钮 -->
    <div style="margin-top: 20px; text-align: center;">
      <el-button @click="$router.back()">返回</el-button>
      <el-button 
        type="primary" 
        @click="handleRetry"
        v-if="['failed', 'cancelled'].includes(task?.status)"
      >
        重试任务
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getTaskDetailAPI, retryTaskAPI } from '@/api/task'
import { getTaskMetricsAPI, getSpeedCurveAPI } from '@/api/metrics'
import * as echarts from 'echarts'

const route = useRoute()
const router = useRouter()

const taskId = computed(() => route.params.id)

const task = ref(null)
const metrics = ref(null)
const errors = ref([])
const speedCurveData = ref([])
const loading = ref(false)

const speedChartRef = ref(null)

const statusMap = {
  created: { text: '已创建', type: 'info' },
  queued: { text: '排队中', type: 'warning' },
  parsing: { text: '解析中', type: 'warning' },
  downloading: { text: '下载中', type: 'primary' },
  merging: { text: '合并中', type: 'primary' },
  completed: { text: '已完成', type: 'success' },
  failed: { text: '已失败', type: 'danger' },
  cancelled: { text: '已取消', type: 'info' }
}

const statusType = (status) => statusMap[status]?.type || 'info'
const statusText = (status) => statusMap[status]?.text || status

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

const formatDuration = (seconds) => {
  if (!seconds) return '-'
  seconds = Math.floor(seconds)
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  return h > 0 ? `${h}时${m}分${s}秒` : m > 0 ? `${m}分${s}秒` : `${s}秒`
}

const formatSize = (bytes) => {
  if (!bytes) return '-'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  while (bytes >= 1024 && i < units.length - 1) {
    bytes /= 1024
    i++
  }
  return `${bytes.toFixed(2)} ${units[i]}`
}

const loadData = async () => {
  loading.value = true
  try {
    const [taskRes, metricsRes, speedRes] = await Promise.all([
      getTaskDetailAPI(taskId.value),
      getTaskMetricsAPI(taskId.value).catch(() => ({ data: null })),
      getSpeedCurveAPI(taskId.value).catch(() => ({ data: { speeds_bps: [] } }))
    ])

    task.value = taskRes.data
    metrics.value = metricsRes.data
    errors.value = taskRes.data.errors || []
    speedCurveData.value = speedRes.data.speeds_bps || []

    if (speedCurveData.value.length > 0) {
      setTimeout(() => renderSpeedChart(speedRes.data), 100)
    }

    if (task.value && ['completed', 'failed', 'cancelled'].includes(task.value.status)) {
      clearInterval(refreshTimer)
    }
  } catch (e) {
    ElMessage.error('加载任务详情失败')
  } finally {
    loading.value = false
  }
}

const formatSpeed = (bytesPerSec) => {
  if (bytesPerSec >= 1024 * 1024) {
    return `${(bytesPerSec / 1024 / 1024).toFixed(2)} MB/s`
  } else if (bytesPerSec >= 1024) {
    return `${(bytesPerSec / 1024).toFixed(1)} KB/s`
  } else {
    return `${bytesPerSec.toFixed(0)} B/s`
  }
}

const renderSpeedChart = (data) => {
  if (!speedChartRef.value) return

  const chart = echarts.init(speedChartRef.value)
  const speeds = data.speeds_bps || []

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const idx = params[0].dataIndex
        return `${data.timestamps[idx]}<br/>速度: ${formatSpeed(speeds[idx])}`
      }
    },
    legend: {
      data: ['下载速度'],
      top: 0
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '10%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: data.timestamps || [],
      axisLabel: {
        interval: Math.floor((data.timestamps?.length || 1) / 8)
      }
    },
    yAxis: {
      type: 'value',
      name: '速度',
      axisLabel: {
        formatter: (v) => formatSpeed(v)
      },
      splitLine: { lineStyle: { type: 'dashed', opacity: 0.3 } }
    },
    dataZoom: [{
      type: 'inside',
      start: 0,
      end: 100
    }],
    series: [{
      name: '下载速度',
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      itemStyle: { color: '#409eff' },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(64, 158, 255, 0.4)' },
            { offset: 1, color: 'rgba(64, 158, 255, 0.05)' }
          ]
        }
      },
      lineStyle: { width: 2 },
      data: speeds
    }]
  })

  window.addEventListener('resize', () => chart.resize())
}

const handleRetry = async () => {
  try {
    await retryTaskAPI(taskId.value)
    ElMessage.success('任务已重新提交')
    loadData()
  } catch (e) {
    console.error('重试失败:', e)
  }
}

// 定时刷新
let refreshTimer = null
onMounted(() => {
  loadData()
  refreshTimer = setInterval(loadData, 3000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.metric-item {
  text-align: center;
  padding: 10px;
}

.metric-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.metric-percent {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>
