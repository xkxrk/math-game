/** API 客户端：封装所有后端请求。 */

const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  const text = await res.text()
  let data
  try {
    data = text ? JSON.parse(text) : {}
  } catch {
    data = { raw: text }
  }
  if (!res.ok) {
    throw new Error(data.detail || data.error || `HTTP ${res.status}`)
  }
  return data
}

export const api = {
  // 开奖数据
  getHistory: (limit = 50) => request(`/history?limit=${limit}`),
  getLatest: () => request('/latest'),
  getStats: (limit = 100) => request(`/stats?limit=${limit}`),
  triggerScrape: (limit = 200) => request(`/scrape?limit=${limit}`, { method: 'POST' }),

  // 预测
  predict: (count = 1) => request(`/predict?count=${count}`, { method: 'POST' }),
  getPredictions: (limit = 20) => request(`/predictions?limit=${limit}`),
  evaluate: () => request('/evaluate', { method: 'POST' }),

  // 后台
  adminStatus: () => request('/admin/status'),
  adminLogin: (username, password) =>
    request('/admin/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  adminLogout: () => request('/admin/logout', { method: 'POST' }),
  saveLlmConfig: (cfg) =>
    request('/admin/llm-config', {
      method: 'POST',
      body: JSON.stringify(cfg),
    }),
  changePassword: (oldPassword, newPassword) =>
    request('/admin/change-password', {
      method: 'POST',
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
    }),
  testLlm: () => request('/admin/test-llm', { method: 'POST' }),

  // 规则
  getRules: () => request('/rules'),
  health: () => request('/health'),

  // 回测
  getBacktestIssues: (limit = 100) => request(`/backtest/issues?limit=${limit}`),
  backtestPredict: (issue, count = 1) =>
    request('/backtest/predict', {
      method: 'POST',
      body: JSON.stringify({ issue, count }),
    }),
  simulateFixed: (redBalls, blueBalls, startIssue = '', endIssue = '') =>
    request('/backtest/simulate', {
      method: 'POST',
      body: JSON.stringify({
        red_balls: redBalls,
        blue_balls: blueBalls,
        start_issue: startIssue,
        end_issue: endIssue,
      }),
    }),
  aiSimulate: (issue, count = 1) =>
    request('/backtest/ai-simulate', {
      method: 'POST',
      body: JSON.stringify({ issue, count }),
    }),

  // 用户投注
  adoptBet: (redBalls, blueBalls, targetIssue = '', source = 'manual', reason = '') =>
    request('/bets/adopt', {
      method: 'POST',
      body: JSON.stringify({
        red_balls: redBalls,
        blue_balls: blueBalls,
        target_issue: targetIssue,
        source,
        reason,
      }),
    }),
  getBets: (status = 'all', limit = 100) =>
    request(`/bets?status=${status}&limit=${limit}`),
  getBetsSummary: () => request('/bets/summary'),
  deleteBet: (id) => request(`/bets/${id}`, { method: 'DELETE' }),
  evaluateBets: () => request('/bets/evaluate', { method: 'POST' }),

  // 号码分析
  diagnoseCombo: (redBalls, blueBalls) =>
    request('/analyze/combo', {
      method: 'POST',
      body: JSON.stringify({ red_balls: redBalls, blue_balls: blueBalls }),
    }),
  getMiss: (numType = 'red', limit = 200) =>
    request(`/analyze/miss?num_type=${numType}&limit=${limit}`),
  getFrequency: (numType = 'red', limit = 200) =>
    request(`/analyze/frequency?num_type=${numType}&limit=${limit}`),
  getSumDistribution: (limit = 200) =>
    request(`/analyze/sum-distribution?limit=${limit}`),
  getRatio: (ratioType = 'odd_even', limit = 200) =>
    request(`/analyze/ratio?ratio_type=${ratioType}&limit=${limit}`),
  getSpanDistribution: (limit = 200) =>
    request(`/analyze/span?limit=${limit}`),
  getPoolTrend: (limit = 100) =>
    request(`/analyze/pool-trend?limit=${limit}`),
  getDashboard: (limit = 200) =>
    request(`/analyze/dashboard?limit=${limit}`),

  // 实时预警快照（一次性，SSE 不可用时降级使用）
  getAlertsSnapshot: () => request('/sse/alerts/snapshot'),

  // 新增：期望值 / 策略对比 / 历史复盘 / 沙盒
  getExpectedValue: (limit = 100) =>
    request(`/analyze/expected-value?limit=${limit}`),
  strategyCompare: (limit = 100) =>
    request(`/analyze/strategy-compare?limit=${limit}`),
  reviewIssues: (limit = 50) =>
    request(`/analyze/review/issues?limit=${limit}`),
  reviewReveal: (issue) =>
    request('/analyze/review/reveal', {
      method: 'POST',
      body: JSON.stringify({ issue }),
    }),
  reviewScore: (issue, redBalls, blueBalls) =>
    request('/analyze/review/score', {
      method: 'POST',
      body: JSON.stringify({ issue, red_balls: redBalls, blue_balls: blueBalls }),
    }),
  sandboxSimulate: (rules, limit = 100) =>
    request(`/analyze/sandbox?limit=${limit}`, {
      method: 'POST',
      body: JSON.stringify(rules),
    }),
}
