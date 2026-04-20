<template>
  <div class="config-page">
    <el-card>
      <template #header>系统配置</template>
      
      <el-form :model="configForm" label-width="150px" v-loading="loading">
        <el-form-item label="最大并发任务数">
          <el-input-number 
            v-model="configForm.max_concurrent_tasks" 
            :min="1" 
            :max="10"
          />
          <span class="form-tip">同时执行的任务数量，建议不超过10</span>
        </el-form-item>

        <el-form-item label="默认请求间隔">
          <el-input-number 
            v-model="configForm.default_rate_limit_ms" 
            :min="100" 
            :max="10000"
            :step="100"
          />
          <span class="form-tip">单位毫秒，1000 = 1秒，建议设置1000以上</span>
        </el-form-item>

        <el-form-item label="默认最大重试次数">
          <el-input-number 
            v-model="configForm.default_max_retries" 
            :min="0" 
            :max="10"
          />
          <span class="form-tip">任务失败后自动重试的次数</span>
        </el-form-item>

        <el-form-item label="默认视频清晰度">
          <el-select v-model="configForm.default_quality">
            <el-option label="4K" value="4K" />
            <el-option label="1080P60" value="1080P60" />
            <el-option label="1080P" value="1080P" />
            <el-option label="720P" value="720P" />
            <el-option label="480P" value="480P" />
            <el-option label="360P" value="360P" />
          </el-select>
        </el-form-item>

        <el-form-item label="临时下载目录">
          <el-input v-model="configForm.download_temp_dir" style="width: 400px;" />
          <span class="form-tip">临时文件存放目录，任务完成后会自动清理</span>
        </el-form-item>

        <el-form-item label="最终输出目录">
          <el-input v-model="configForm.download_output_dir" style="width: 400px;" />
          <span class="form-tip">下载完成的视频文件存放目录</span>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="saveConfig" :loading="saving">
            保存配置
          </el-button>
          <el-button @click="loadConfig">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 系统信息 -->
    <el-card style="margin-top: 20px;">
      <template #header>系统信息</template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="服务版本">1.0.0</el-descriptions-item>
        <el-descriptions-item label="前端版本">1.0.0</el-descriptions-item>
        <el-descriptions-item label="当前队列任务数">{{ queueStats.queue_size || 0 }}</el-descriptions-item>
        <el-descriptions-item label="正在执行任务数">{{ queueStats.running_count || 0 }}</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/api'

const loading = ref(false)
const saving = ref(false)
const queueStats = ref({})

const configForm = reactive({
  max_concurrent_tasks: 3,
  default_rate_limit_ms: 1000,
  default_max_retries: 3,
  default_quality: '1080P',
  download_temp_dir: '/tmp/bilibili-downloads',
  download_output_dir: './downloads'
})

const loadConfig = async () => {
  loading.value = true
  try {
    // 加载数据库配置
    const configRes = await request({ url: '/config', method: 'GET' })
    const configs = configRes.data.items || []
    
    configs.forEach(c => {
      if (c.config_key in configForm) {
        const val = c.config_value
        // 类型转换
        if (['max_concurrent_tasks', 'default_rate_limit_ms', 'default_max_retries'].includes(c.config_key)) {
          configForm[c.config_key] = parseInt(val) || 0
        } else {
          configForm[c.config_key] = val
        }
      }
    })
    
    // 加载默认配置
    const defaultsRes = await request({ url: '/config/defaults', method: 'GET' })
    const defaults = defaultsRes.data
    
    // 合并默认值
    for (const [key, def] of Object.entries(defaults)) {
      if (!(key in configForm) || !configForm[key]) {
        configForm[key] = def.value
      }
    }
    
    // 加载队列统计
    const statsRes = await request({ url: '/tasks/stats', method: 'GET' })
    queueStats.value = statsRes.data
    
  } catch (e) {
    console.error('加载配置失败:', e)
  } finally {
    loading.value = false
  }
}

const saveConfig = async () => {
  saving.value = true
  try {
    const configs = [
      { config_key: 'max_concurrent_tasks', config_value: String(configForm.max_concurrent_tasks) },
      { config_key: 'default_rate_limit_ms', config_value: String(configForm.default_rate_limit_ms) },
      { config_key: 'default_max_retries', config_value: String(configForm.default_max_retries) },
      { config_key: 'default_quality', config_value: configForm.default_quality },
      { config_key: 'download_temp_dir', config_value: configForm.download_temp_dir },
      { config_key: 'download_output_dir', config_value: configForm.download_output_dir }
    ]
    
    await request({
      url: '/config/batch',
      method: 'POST',
      data: { configs }
    })
    
    ElMessage.success('配置保存成功')
  } catch (e) {
    console.error('保存配置失败:', e)
  } finally {
    saving.value = false
  }
}

onMounted(loadConfig)
</script>

<style scoped>
.form-tip {
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}
</style>
