<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon total">
              <el-icon><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.total || 0 }}</div>
              <div class="stat-label">总任务数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon completed">
              <el-icon><SuccessFilled /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.completed || 0 }}</div>
              <div class="stat-label">已完成</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon running">
              <el-icon><Loading /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.running_count || 0 }}</div>
              <div class="stat-label">执行中</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon failed">
              <el-icon><CircleCloseFilled /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.failed || 0 }}</div>
              <div class="stat-label">失败</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="12">
        <el-card>
          <template #header>任务状态分布</template>
          <div ref="statusChartRef" style="height: 280px;"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>平均阶段耗时</template>
          <div ref="stageChartRef" style="height: 280px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 性能指标 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="8">
        <el-card>
          <template #header>平均耗时</template>
          <div class="metric-value">{{ formatDuration(stats.avg_duration_ms) }}</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header>平均速度</template>
          <div class="metric-value">{{ formatSpeed(stats.avg_speed_bps) }}</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header>成功率</template>
          <div class="metric-value success">{{ (stats.success_rate || 0).toFixed(1) }}%</div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getDashboardAPI } from '@/api/metrics'
import { getTaskStatsAPI } from '@/api/task'
import * as echarts from 'echarts'

const stats = reactive({
  total: 0,
  completed: 0,
  failed: 0,
  running_count: 0,
  success_rate: 0,
  avg_duration_ms: 0,
  avg_speed_bps: 0,
  stage_distribution: { parse: 0, download: 0, merge: 0 }
})

const statusChartRef = ref(null)
const stageChartRef = ref(null)

const formatDuration = (ms) => {
  if (!ms) return '0s'
  const s = Math.floor(ms / 1000)
  return s < 60 ? `${s}秒` : `${Math.floor(s / 60)}分${s % 60}秒`
}

const formatSpeed = (bps) => {
  if (!bps) return '-'
  return `${(bps / 1024 / 1024).toFixed(2)} MB/s`
}

const loadDashboard = async () => {
  try {
    const [dashRes, statsRes] = await Promise.all([
      getDashboardAPI(),
      getTaskStatsAPI()
    ])

    Object.assign(stats, {
      ...statsRes.data,
      ...dashRes.data
    })

    renderCharts()
  } catch (e) {
    console.error('加载看板数据失败:', e)
  }
}

const renderCharts = () => {
  if (statusChartRef.value) {
    const statusChart = echarts.init(statusChartRef.value)
    statusChart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { bottom: 0 },
      series: [{
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['50%', '45%'],
        data: [
          { name: '已完成', value: stats.completed || 0, itemStyle: { color: '#67c23a' } },
          { name: '进行中', value: stats.running_count || 0, itemStyle: { color: '#409eff' } },
          { name: '失败', value: stats.failed || 0, itemStyle: { color: '#f56c6c' } }
        ].filter(d => d.value > 0)
      }]
    })
  }

  if (stageChartRef.value) {
    const stageData = stats.stage_distribution || { parse: 0, download: 0, merge: 0 }
    const parseSec = stageData.parse / 1000
    const downloadSec = stageData.download / 1000
    const mergeSec = stageData.merge / 1000
    const maxVal = Math.max(parseSec, downloadSec, mergeSec, 1)
    const yMax = Math.ceil(maxVal / 30) * 30 || 150

    const stageChart = echarts.init(stageChartRef.value)
    stageChart.setOption({
      tooltip: { trigger: 'axis', formatter: (params) => `${params[0].name}: ${params[0].value}秒` },
      xAxis: { type: 'category', data: ['解析', '下载', '合并'] },
      yAxis: {
        type: 'value',
        name: '秒',
        min: 0,
        max: yMax,
        interval: 30
      },
      series: [{
        type: 'bar',
        data: [
          { value: Number(parseSec), itemStyle: { color: '#e6a23c' } },
          { value: Number(downloadSec), itemStyle: { color: '#409eff' } },
          { value: Number(mergeSec), itemStyle: { color: '#67c23a' } }
        ],
        barWidth: '50%',
        itemStyle: { borderRadius: [4, 4, 0, 0] }
      }]
    })
  }
}

onMounted(() => {
  loadDashboard()
  window.addEventListener('resize', () => {
    echarts.getInstanceByDom(statusChartRef.value)?.resize()
    echarts.getInstanceByDom(stageChartRef.value)?.resize()
  })
})
</script>

<style scoped>
.stat-card {
  display: flex;
  align-items: center;
  gap: 20px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: #fff;
}

.stat-icon.total { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.stat-icon.completed { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
.stat-icon.running { background: linear-gradient(135deg, #2193b0 0%, #6dd5ed 100%); }
.stat-icon.failed { background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%); }

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}

.metric-value {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  text-align: center;
  padding: 20px 0;
}

.metric-value.success {
  color: #67c23a;
}
</style>
