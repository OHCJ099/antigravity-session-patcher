import { defineStore } from 'pinia'
import { api, clearCache } from '../services/api'

export const useCTFStore = defineStore('ctf', {
  state: () => ({
    status: null,
    loading: false,
    installLoading: false,
    globalInstallLoading: false,
    antigravityInstallLoading: false,
    antigravityGlobalInstallLoading: false,
    claudeInstallLoading: false,
    opencodeInstallLoading: false,

    originalRequest: '',
    rewrittenRequest: '',
    rewriteStrategy: '',
    rewriteLoading: false,
    rewriteError: null,
    rewriteTarget: 'antigravity',

    prompts: {
      antigravity: { prompt: '', is_default: true, is_installed: false, loading: false },
      codex: { prompt: '', is_default: true, is_installed: false, loading: false },
      claude_code: { prompt: '', is_default: true, is_installed: false, loading: false },
      opencode: { prompt: '', is_default: true, is_installed: false, loading: false },
    },

    templates: {
      antigravity: [],
      codex: [],
      claude_code: [],
      opencode: [],
    },
  }),

  actions: {
    async fetchStatus() {
      this.loading = true
      clearCache('ctf/status')
      try {
        const response = await api.get('/ctf/status')
        this.status = response
      } catch (error) {
        console.error('获取 CTF 配置状态失败:', error)
      } finally {
        this.loading = false
      }
    },

    async installAntigravity() {
      this.antigravityInstallLoading = true
      try {
        const response = await api.post('/ctf/antigravity/install')
        if (response.success && response.status) this.status = response.status
        return response
      } catch (error) {
        return { success: false, message: error.message }
      } finally {
        this.antigravityInstallLoading = false
      }
    },

    async uninstallAntigravity() {
      this.antigravityInstallLoading = true
      try {
        const response = await api.post('/ctf/antigravity/uninstall')
        if (response.success && response.status) this.status = response.status
        return response
      } catch (error) {
        return { success: false, message: error.message }
      } finally {
        this.antigravityInstallLoading = false
      }
    },

    async installAntigravityGlobal() {
      this.antigravityGlobalInstallLoading = true
      try {
        const response = await api.post('/ctf/antigravity/global/install')
        if (response.success && response.status) this.status = response.status
        return response
      } catch (error) {
        return { success: false, message: error.message }
      } finally {
        this.antigravityGlobalInstallLoading = false
      }
    },

    async uninstallAntigravityGlobal() {
      this.antigravityGlobalInstallLoading = true
      try {
        const response = await api.post('/ctf/antigravity/global/uninstall')
        if (response.success && response.status) this.status = response.status
        return response
      } catch (error) {
        return { success: false, message: error.message }
      } finally {
        this.antigravityGlobalInstallLoading = false
      }
    },

    // Legacy Codex actions kept for API compatibility, hidden from Antigravity-first UI.
    async install(injectionMode = 'append') {
      this.installLoading = true
      try {
        const response = await api.post('/ctf/install', { injection_mode: injectionMode })
        if (response.success && response.status) this.status = response.status
        return response
      } catch (error) {
        return { success: false, message: error.message }
      } finally {
        this.installLoading = false
      }
    },

    async uninstall() {
      this.installLoading = true
      try {
        const response = await api.post('/ctf/uninstall')
        if (response.success && response.status) this.status = response.status
        return response
      } catch (error) {
        return { success: false, message: error.message }
      } finally {
        this.installLoading = false
      }
    },

    async installGlobal(injectionMode = 'append') {
      this.globalInstallLoading = true
      try {
        const response = await api.post('/ctf/global/install', { injection_mode: injectionMode })
        if (response.success && response.status) this.status = response.status
        return response
      } catch (error) {
        return { success: false, message: error.message }
      } finally {
        this.globalInstallLoading = false
      }
    },

    async uninstallGlobal() {
      this.globalInstallLoading = true
      try {
        const response = await api.post('/ctf/global/uninstall')
        if (response.success && response.status) this.status = response.status
        return response
      } catch (error) {
        return { success: false, message: error.message }
      } finally {
        this.globalInstallLoading = false
      }
    },

    async installClaude() {
      this.claudeInstallLoading = true
      try {
        const response = await api.post('/ctf/claude/install')
        if (response.success && response.status) this.status = response.status
        return response
      } catch (error) {
        return { success: false, message: error.message }
      } finally {
        this.claudeInstallLoading = false
      }
    },

    async uninstallClaude() {
      this.claudeInstallLoading = true
      try {
        const response = await api.post('/ctf/claude/uninstall')
        if (response.success && response.status) this.status = response.status
        return response
      } catch (error) {
        return { success: false, message: error.message }
      } finally {
        this.claudeInstallLoading = false
      }
    },

    async installOpencode() {
      this.opencodeInstallLoading = true
      try {
        const response = await api.post('/ctf/opencode/install')
        if (response.success && response.status) this.status = response.status
        return response
      } catch (error) {
        return { success: false, message: error.message }
      } finally {
        this.opencodeInstallLoading = false
      }
    },

    async uninstallOpencode() {
      this.opencodeInstallLoading = true
      try {
        const response = await api.post('/ctf/opencode/uninstall')
        if (response.success && response.status) this.status = response.status
        return response
      } catch (error) {
        return { success: false, message: error.message }
      } finally {
        this.opencodeInstallLoading = false
      }
    },

    async fetchPrompt(tool) {
      if (!this.prompts[tool]) return
      this.prompts[tool].loading = true
      try {
        const response = await api.get(`/ctf/prompt/${tool}`)
        this.prompts[tool].prompt = response.prompt
        this.prompts[tool].is_default = response.is_default
        this.prompts[tool].is_installed = response.is_installed
      } catch (error) {
        console.error(`获取 ${tool} 提示词失败:`, error)
      } finally {
        this.prompts[tool].loading = false
      }
    },

    async savePrompt(tool, prompt) {
      try {
        const response = await api.post(`/ctf/prompt/${tool}`, { prompt })
        if (response.success) {
          this.prompts[tool].prompt = prompt
          this.prompts[tool].is_default = false
        }
        return response
      } catch (error) {
        return { success: false, message: error.message }
      }
    },

    async fetchTemplates(tool) {
      try {
        const response = await api.get(`/ctf/prompt/${tool}/templates`)
        this.templates[tool] = response.templates || []
      } catch (error) {
        console.error(`获取 ${tool} 模板失败:`, error)
      }
    },

    async fetchTemplatePrompt(tool, templateName) {
      const response = await api.get(`/ctf/prompt/${tool}/templates/${encodeURIComponent(templateName)}`)
      return response.prompt || ''
    },

    async saveTemplate(tool, name, prompt) {
      try {
        const response = await api.post(`/ctf/prompt/${tool}/templates`, { name, prompt })
        if (response.success) this.templates[tool] = response.templates
        return response
      } catch (error) {
        return { success: false, message: error.message }
      }
    },

    async deleteTemplate(tool, templateName) {
      try {
        const response = await api.delete(`/ctf/prompt/${tool}/templates/${encodeURIComponent(templateName)}`)
        if (response.success) this.templates[tool] = response.templates
        return response
      } catch (error) {
        return { success: false, message: error.message }
      }
    },

    async resetPromptToDefault(tool) {
      try {
        const response = await api.post(`/ctf/prompt/${tool}/reset`)
        if (response.success) {
          this.prompts[tool].prompt = response.prompt
          this.prompts[tool].is_default = true
        }
        return response
      } catch (error) {
        return { success: false, message: error.message }
      }
    },

    async rewritePrompt(originalRequest, target = null) {
      this.rewriteLoading = true
      this.rewriteError = null
      this.originalRequest = originalRequest
      try {
        const response = await api.post('/prompt-rewrite', {
          original_request: originalRequest,
          target: target || this.rewriteTarget,
        })
        if (response.success) {
          this.rewrittenRequest = response.rewritten
          this.rewriteStrategy = response.strategy
        } else {
          this.rewriteError = response.error
        }
        return response
      } catch (error) {
        this.rewriteError = error.message
        return { success: false, error: error.message }
      } finally {
        this.rewriteLoading = false
      }
    },

    resetRewrite() {
      this.originalRequest = ''
      this.rewrittenRequest = ''
      this.rewriteStrategy = ''
      this.rewriteError = null
    },
  }
})
