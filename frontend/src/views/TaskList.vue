<template>
  <div class="task-list">
    <!-- 筛选栏 -->
    <el-card>
      <el-form :inline="true" :model="filters">
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable style="width: 120px;">
            <el-option label="全部" value="" />
            <el-option label="排队中" value="queued" />
            <el-option label="解析中" value="parsing" />
            <el-option label="下载中" value="downloading" />
            <el-option label="合并中" value="merging" />
            <el-option label="已完成" value="completed" />
            <el-option label="已失败" value="failed" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="filters.keyword" placeholder="搜索URL" clearable />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadTasks">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 任务列表 -->
    <el-card style="margin-top: 20px;">
      <template #header>
        <span>任务列表 ({{ pagination.total }})</span>
      </template>

      <el-table :data="tasks" stripe style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="任务ID" width="250" show-overflow-tooltip />
        <el-table-column prop="url" label="视频链接" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <a :href="row.url" target="_blank" style="color: #409eff;">
              {{ row.url }}
            </a>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">
              {{ statusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="progress" label="进度" width="150">
          <template #default="{ row }">
            <el-progress 
              :percentage="row.progress || 0" 
              :status="row.progress >= 100 ? 'success' : ''"
            />
          </template>
        </el-table-column>
        <el-table-column prop="quality" label="清晰度" width="80" />
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewDetail(row)">
              详情
            </el-button>
            <el-button 
              link 
              type="danger" 
              @click="handleCancel(row)"
              v-if="['queued', 'parsing', 'downloading', 'merging'].includes(row.status)"
            >
              取消
            </el-button>
            <el-button 
              link 
              type="warning" 
              @click="handleRetry(row)"
              v-if="['failed', 'cancelled'].includes(row.status)"
            >
              重试
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div style="margin-top: 20px; text-align: right;">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.per_page"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadTasks"
          @current-change="loadTasks"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getTaskListAPI, cancelTaskAPI, retryTaskAPI } from '@/api/task'

const router = useRouter()

const tasks = ref([])
const loading = ref(false)

const filters = reactive({
  status: '',
  keyword: ''
})

const pagination = reactive({
  page: 1,
  per_page: 20,
  total: 0
})

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

const loadTasks = async () => {
  loading.value = true
  try {
    const res = await getTaskListAPI({
      page: pagination.page,
      per_page: pagination.per_page,
      status: filters.status || undefined,
      keyword: filters.keyword || undefined
    })
    tasks.value = res.data.items
    pagination.total = res.data.total
  } catch (e) {
    console.error('加载任务列表失败:', e)
  } finally {
    loading.value = false
  }
}

const resetFilters = () => {
  filters.status = ''
  filters.keyword = ''
  pagination.page = 1
  loadTasks()
}

const viewDetail = (row) => {
  router.push(`/tasks/${row.id}`)
}

const handleCancel = async (row) => {
  try {
    await ElMessageBox.confirm('确定要取消该任务吗？', '取消任务')
    await cancelTaskAPI(row.id)
    ElMessage.success('任务已取消')
    loadTasks()
  } catch (e) {
    if (e !== 'cancel') {
      console.error('取消任务失败:', e)
    }
  }
}

const handleRetry = async (row) => {
  try {
    await retryTaskAPI(row.id)
    ElMessage.success('任务已重新提交')
    loadTasks()
  } catch (e) {
    console.error('重试任务失败:', e)
  }
}

// 定时刷新
let refreshTimer = null
onMounted(() => {
  loadTasks()
  window.addEventListener('task-created', loadTasks)
  // 每5秒刷新一次（如果有正在执行的任务）
  refreshTimer = setInterval(() => {
    const hasRunning = tasks.value.some(t =>
      ['queued', 'parsing', 'downloading', 'merging'].includes(t.status)
    )
    if (hasRunning) {
      loadTasks()
    }
  }, 5000)
})

onUnmounted(() => {
  window.removeEventListener('task-created', loadTasks)
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>
