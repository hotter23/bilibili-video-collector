<template>
  <el-config-provider :locale="zhCn">
    <div class="app-container">
      <el-container>
        <!-- 侧边栏 -->
        <el-aside width="200px">
          <div class="logo">
            <h3>📺 视频采集</h3>
          </div>
          <el-menu
            :default-active="activeMenu"
            router
            class="sidebar-menu"
          >
            <el-menu-item index="/">
              <el-icon><DataAnalysis /></el-icon>
              <span>任务看板</span>
            </el-menu-item>
            <el-menu-item index="/tasks">
              <el-icon><List /></el-icon>
              <span>任务列表</span>
            </el-menu-item>
            <el-menu-item index="/config">
              <el-icon><Setting /></el-icon>
              <span>系统配置</span>
            </el-menu-item>
          </el-menu>
        </el-aside>

        <!-- 主内容 -->
        <el-container>
          <el-header>
            <div class="header-title">{{ pageTitle }}</div>
            <div class="header-actions">
              <el-button type="primary" @click="showCreateDialog = true">
                <el-icon><Plus /></el-icon>
                创建任务
              </el-button>
            </div>
          </el-header>

          <el-main>
            <router-view />
          </el-main>
        </el-container>
      </el-container>
    </div>

    <!-- 创建任务对话框 -->
    <el-dialog v-model="showCreateDialog" title="创建采集任务" width="600px">
      <el-form :model="taskForm" label-width="100px">
        <el-form-item label="视频链接">
          <el-input
            v-model="taskForm.url"
            placeholder="https://www.bilibili.com/video/BV..."
            clearable
          />
        </el-form-item>
        <el-form-item label="清晰度">
          <el-select v-model="taskForm.quality" style="width: 100%">
            <el-option label="1080P" value="1080P" />
            <el-option label="720P" value="720P" />
            <el-option label="480P" value="480P" />
            <el-option label="360P" value="360P" />
          </el-select>
        </el-form-item>
        <el-form-item label="Cookie (可选)">
          <el-input
            v-model="taskForm.cookies"
            type="password"
            placeholder="登录后可下载更高清晰度"
            show-password
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createTask" :loading="creating">
          创建
        </el-button>
      </template>
    </el-dialog>
  </el-config-provider>
</template>

<script setup>
import { ref, computed, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import { createTaskAPI } from '@/api/task'

const route = useRoute()
const router = useRouter()

const showCreateDialog = ref(false)
const creating = ref(false)

const taskForm = reactive({
  url: '',
  quality: '1080P',
  cookies: ''
})

const activeMenu = computed(() => route.path)

const pageTitle = computed(() => {
  const titles = {
    '/': '任务看板',
    '/tasks': '任务列表',
    '/config': '系统配置'
  }
  return titles[route.path] || 'B站视频采集'
})

const createTask = async () => {
  if (!taskForm.url.trim()) {
    ElMessage.warning('请输入视频链接')
    return
  }

  creating.value = true
  try {
    await createTaskAPI({
      url: taskForm.url,
      quality: taskForm.quality,
      cookies: taskForm.cookies || undefined
    })
    ElMessage.success('任务创建成功')
    showCreateDialog.value = false
    taskForm.url = ''
    taskForm.cookies = ''
    window.dispatchEvent(new Event('task-created'))
    router.push('/tasks')
  } catch (e) {
    ElMessage.error(e.message || '创建失败')
  } finally {
    creating.value = false
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  background: #f5f7fa;
}

.app-container {
  height: 100vh;
}

.el-container {
  height: 100%;
}

.el-aside {
  background: #304156;
  color: #fff;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #3d4a5c;
}

.logo h3 {
  color: #fff;
  font-size: 16px;
}

.sidebar-menu {
  border-right: none;
  background: #304156;
}

.sidebar-menu .el-menu-item {
  color: #bfcbd9;
}

.sidebar-menu .el-menu-item:hover,
.sidebar-menu .el-menu-item.is-active {
  background: #263445;
  color: #409eff;
}

.el-header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  border-bottom: 1px solid #e6e6e6;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.el-main {
  padding: 20px;
}

.el-card {
  margin-bottom: 20px;
}
</style>
