from __future__ import annotations

import json


def build_app_html(default_gitlab_url: str = "") -> str:
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GCS Serve</title>
  <style>
    :root {
      --bg: #edf1f7;
      --panel: rgba(249, 251, 254, 0.9);
      --panel-strong: rgba(255, 255, 255, 0.97);
      --panel-tint: rgba(241, 247, 252, 0.96);
      --panel-dark: #111a2b;
      --line: rgba(16, 24, 40, 0.09);
      --line-strong: rgba(16, 24, 40, 0.16);
      --text: #142033;
      --muted: #5f6f86;
      --muted-2: #7f8ca2;
      --accent: #0f6d8d;
      --accent-strong: #0d5c77;
      --accent-soft: rgba(15, 109, 141, 0.12);
      --success: #16784f;
      --success-soft: rgba(22, 120, 79, 0.14);
      --warn: #9a661f;
      --warn-soft: rgba(154, 102, 31, 0.14);
      --danger: #b54b45;
      --danger-soft: rgba(181, 75, 69, 0.14);
      --shadow-lg: 0 28px 90px rgba(34, 47, 74, 0.14);
      --shadow-md: 0 16px 44px rgba(34, 47, 74, 0.08);
      --shadow-sm: 0 8px 24px rgba(28, 40, 65, 0.05);
      --radius-xl: 30px;
      --radius-lg: 22px;
      --radius-md: 16px;
      --radius-sm: 12px;
      --sidebar-expanded: 282px;
    }
    * { box-sizing: border-box; }
    html, body {
      margin: 0;
      min-height: 100%;
      color: var(--text);
      font-family: "Avenir Next", "PingFang SC", "Noto Sans SC", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at 12% 14%, rgba(15, 109, 141, 0.12), transparent 22%),
        radial-gradient(circle at 88% 10%, rgba(49, 91, 160, 0.14), transparent 24%),
        linear-gradient(180deg, #f4f7fb 0%, #e8eef7 100%);
    }
    button, input, textarea { font: inherit; }
    button { cursor: pointer; border: 0; background: none; color: inherit; }
    a { color: inherit; text-decoration: none; }
    code {
      font-family: "SFMono-Regular", "Menlo", "Monaco", monospace;
      font-size: .92em;
      background: rgba(17,24,39,.06);
      padding: .15em .42em;
      border-radius: .55em;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      word-break: break-word;
    }
    .hidden { display: none !important; }
    .shell { width: min(1500px, calc(100% - 28px)); margin: 14px auto; min-height: calc(100vh - 28px); }
    .shell.standalone-shell { width: min(1880px, calc(100% - 24px)); }
    .login-shell { min-height: calc(100vh - 28px); display: grid; place-items: center; padding: 24px 12px; }
    .login-card, .panel, .workspace-card, .detail-card, .settings-panel, .empty-card, .log-card {
      border-radius: var(--radius-xl);
      border: 1px solid var(--line);
      box-shadow: var(--shadow-md);
      backdrop-filter: blur(18px);
    }
    .eyebrow, .label, .metric-label {
      font-size: 12px;
      letter-spacing: .14em;
      text-transform: uppercase;
    }
    .eyebrow, .metric-label { color: #96abc9; }
    .label { display: block; margin-bottom: 8px; color: var(--muted-2); }
    h1, h2, h3 {
      margin: 0;
      font-family: "Avenir Next Condensed", "DIN Alternate", "PingFang SC", sans-serif;
      letter-spacing: -.04em;
    }
    h1 { margin-top: 16px; font-size: clamp(40px, 5.4vw, 78px); line-height: .94; max-width: 720px; }
    h2 { font-size: clamp(26px, 3vw, 40px); line-height: 1; }
    h3 { font-size: 18px; line-height: 1.2; }
    p { margin: 0; }
    .copy, .meta, .section-copy, .helper { color: var(--muted); font-size: 14px; line-height: 1.7; }
    .dashboard-grid, .sub-grid, .task-list, .result-grid, .settings-grid, .note-grid, .audit-stack, .overview-grid, .summary-grid {
      display: grid;
      gap: 14px;
    }
    .metric-card, .brief-card, .stat-card, .overview-card, .summary-card {
      border-radius: var(--radius-lg);
      padding: 18px;
    }
    .metric-card strong, .stat-card strong, .overview-card strong, .summary-card strong {
      display: block;
      margin-top: 8px;
      font-size: 24px;
      font-weight: 700;
      letter-spacing: -.04em;
    }
    .login-card {
      width: min(560px, 100%);
      padding: 34px;
      background: linear-gradient(180deg, rgba(255,255,255,.9), rgba(244,248,253,.96));
      display: grid;
      align-content: center;
      gap: 18px;
    }
    .guide-card {
      padding: 16px;
      border-radius: 18px;
      background: rgba(15,109,141,.06);
      border: 1px solid rgba(15,109,141,.12);
      display: grid;
      gap: 10px;
    }
    .guide-title {
      font-size: 15px;
      font-weight: 700;
      color: var(--accent-strong);
    }
    .guide-list {
      margin: 0;
      padding-left: 18px;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.7;
    }
    .brand-mark, .top-mark, .side-mark {
      width: 50px;
      height: 50px;
      border-radius: 18px;
      display: grid;
      place-items: center;
      font-weight: 800;
      letter-spacing: -.04em;
    }
    .brand-mark {
      background: linear-gradient(135deg, #0f6d8d, #174e8a);
      color: #f5fbff;
      box-shadow: var(--shadow-sm);
    }
    .login-title { font-size: clamp(34px, 4vw, 52px); line-height: .98; }
    .field { margin-top: 4px; text-align: left; }
    .input, .textarea {
      width: 100%;
      border-radius: 16px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,.92);
      color: var(--text);
      padding: 14px 16px;
      outline: none;
      transition: border-color 140ms ease, box-shadow 140ms ease, background 140ms ease;
    }
    .textarea { min-height: 172px; resize: vertical; line-height: 1.65; }
    .input:focus, .textarea:focus {
      border-color: rgba(15,109,141,.36);
      box-shadow: 0 0 0 5px rgba(15,109,141,.09);
      background: #fff;
    }
    .button-row, .row, .status-row, .chip-row, .topbar-row, .toolbar-row, .action-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 44px;
      padding: 0 16px;
      border-radius: 999px;
      font-weight: 700;
      border: 1px solid transparent;
      transition: transform 140ms ease, background 140ms ease, border-color 140ms ease, color 140ms ease;
    }
    .btn:hover { transform: translateY(-1px); }
    .btn:disabled { opacity: .45; cursor: default; transform: none; }
    .btn.primary {
      background: linear-gradient(135deg, var(--accent), #2f5f9d);
      color: #f8fcff;
      box-shadow: 0 10px 28px rgba(28,83,141,.22);
    }
    .btn.secondary { background: rgba(255,255,255,.92); border-color: var(--line); color: var(--text); }
    .btn.ghost { color: var(--muted); background: rgba(255,255,255,.56); border-color: rgba(16,24,40,.05); }
    .btn.warn { background: var(--warn-soft); color: var(--warn); }
    .inline-link { display: inline-flex; gap: 8px; align-items: center; color: var(--accent-strong); font-weight: 700; }
    .frame { min-height: calc(100vh - 28px); display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 16px; align-items: start; }
    .sidebar-wrap {
      position: sticky;
      top: 0;
      width: var(--sidebar-expanded);
      height: calc(100vh - 28px);
      transition: none;
    }
    .sidebar {
      height: 100%;
      padding: 12px;
      border-radius: 28px;
      background: linear-gradient(180deg, rgba(14,23,38,.98), rgba(20,31,51,.94));
      color: #ebf4ff;
      border: 1px solid rgba(255,255,255,.05);
      box-shadow: var(--shadow-lg);
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .side-brand, .side-item, .side-footer { display: flex; align-items: center; gap: 12px; }
    .side-brand, .side-footer { padding: 8px; }
    .side-mark {
      flex: 0 0 auto;
      background: linear-gradient(135deg, #0f6d8d, #245e9b);
      color: #eef7ff;
    }
    .side-copy, .side-label {
      opacity: 1;
      max-width: 210px;
      overflow: hidden;
      white-space: nowrap;
    }
    .side-copy strong { display: block; font-size: 15px; }
    .side-copy span, .side-label { color: rgba(222,235,255,.66); font-size: 13px; }
    .side-nav { display: grid; gap: 8px; flex: 1; align-content: start; }
    .side-item { width: 100%; padding: 10px; border-radius: 18px; color: rgba(237,245,255,.74); text-align: left; }
    .side-item.active {
      background: rgba(84,177,206,.14);
      color: #f2f8ff;
      border: 1px solid rgba(84,177,206,.18);
    }
    .side-item.locked { opacity: .38; }
    .side-icon {
      width: 42px;
      height: 42px;
      border-radius: 14px;
      display: grid;
      place-items: center;
      background: rgba(255,255,255,.06);
      border: 1px solid rgba(255,255,255,.07);
      font-weight: 800;
      flex: 0 0 auto;
    }
    .main { min-width: 0; display: grid; gap: 14px; }
    .topbar {
      display: flex;
      justify-content: space-between;
      gap: 18px;
      align-items: center;
      padding: 8px 4px;
    }
    .top-title { display: grid; gap: 6px; }
    .top-title h2 { font-size: 34px; }
    .top-mark {
      width: 44px;
      height: 44px;
      border-radius: 16px;
      background: rgba(15,109,141,.1);
      color: var(--accent-strong);
    }
    .status-pill, .chip, .metric-pill, .download-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-height: 36px;
      padding: 0 12px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,.76);
      color: #33445a;
      font-size: 13px;
    }
    .topbar-row .status-pill {
      max-width: min(100%, 460px);
      white-space: normal;
      overflow-wrap: anywhere;
      word-break: break-word;
    }
    .chip.active, .download-pill.active {
      background: var(--accent-soft);
      color: var(--accent-strong);
      border-color: rgba(15,109,141,.2);
    }
    .metric-pill { background: rgba(20,32,51,.04); border-color: rgba(20,32,51,.06); }
    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #47c5e4;
      box-shadow: 0 0 0 6px rgba(71,197,228,.12);
    }
    .page { display: grid; gap: 14px; min-height: calc(100vh - 140px); }
    .panel, .detail-card, .settings-panel, .workspace-card, .empty-card, .log-card {
      padding: 20px;
      background: linear-gradient(180deg, rgba(255,255,255,.86), rgba(248,251,254,.95));
    }
    .workspace-card.primary {
      background: linear-gradient(180deg, rgba(255,255,255,.96), rgba(245,249,253,.95));
      box-shadow: var(--shadow-lg);
    }
    .workspace-card.tinted { background: linear-gradient(180deg, rgba(241,247,252,.98), rgba(247,250,254,.94)); }
    .section-head { display: flex; justify-content: space-between; gap: 12px; align-items: start; }
    .section-title { display: grid; gap: 6px; }
    .section-title strong { font-size: 26px; line-height: 1; letter-spacing: -.04em; }
    .dashboard-grid { grid-template-columns: 1.2fr .8fr; }
    .stat-strip {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
    }
    .stat-card, .overview-card, .summary-card {
      border-radius: 18px;
      border: 1px solid rgba(15,109,141,.08);
      background: linear-gradient(180deg, rgba(255,255,255,.96), rgba(243,248,253,.94));
    }
    .stat-card span, .overview-card span { color: var(--muted); line-height: 1.5; }
    .control-grid { display: grid; gap: 16px; margin-top: 14px; }
    .split-two { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; align-items: start; }
    .branch-mode-field { display: grid; align-content: start; }
    .branch-mode-row { min-height: 52px; align-items: center; }
    .project-grid { display: grid; gap: 8px; max-height: 360px; overflow: auto; padding-right: 2px; }
    .project-item, .task-card, .result-card, .batch-item, .audit-item {
      width: 100%;
      text-align: left;
      border-radius: 18px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,.8);
      transition: border-color 140ms ease, transform 140ms ease, box-shadow 140ms ease;
    }
    .project-item:hover, .task-card:hover, .result-card:hover, .batch-item:hover {
      transform: translateY(-1px);
      border-color: rgba(15,109,141,.18);
      box-shadow: var(--shadow-sm);
    }
    .project-item {
      display: flex;
      gap: 12px;
      align-items: start;
      padding: 14px;
    }
    .project-item.active { background: rgba(15,109,141,.07); border-color: rgba(15,109,141,.2); }
    .project-item input { margin-top: 4px; accent-color: var(--accent); }
    .project-item strong, .task-card strong, .result-card strong, .batch-item strong {
      display: block;
      font-size: 15px;
      line-height: 1.3;
    }
    .project-item small, .task-card small, .result-card small, .batch-item small {
      display: block;
      margin-top: 4px;
      color: var(--muted);
      line-height: 1.5;
    }
    .task-summary-row { display: grid; grid-template-columns: 1.2fr .8fr; gap: 14px; }
    .task-list { display: grid; gap: 10px; }
    .task-card { padding: 16px; display: grid; gap: 12px; }
    .task-card.active { border-color: rgba(15,109,141,.22); background: rgba(15,109,141,.06); }
    .progress {
      height: 10px;
      border-radius: 999px;
      background: rgba(20,32,51,.08);
      overflow: hidden;
    }
    .progress span {
      display: block;
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, #0f6d8d, #3b78ad);
    }
    .badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 28px;
      padding: 0 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      border: 1px solid transparent;
    }
    .badge.success { background: var(--success-soft); color: var(--success); }
    .badge.warn { background: var(--warn-soft); color: var(--warn); }
    .badge.muted { background: rgba(20,32,51,.08); color: var(--muted); }
    .badge.danger { background: var(--danger-soft); color: var(--danger); }
    .log-card {
      background: linear-gradient(180deg, rgba(14,23,38,.96), rgba(18,30,51,.98));
      color: #eaf3ff;
      border-color: rgba(255,255,255,.04);
    }
    .log-title { display: flex; justify-content: space-between; gap: 12px; align-items: center; margin-bottom: 12px; }
    .log-title .section-copy { color: rgba(222,235,255,.64); }
    .log-box {
      min-height: 340px;
      max-height: 560px;
      overflow: auto;
      padding: 16px;
      border-radius: 18px;
      background: rgba(1,8,18,.46);
      border: 1px solid rgba(255,255,255,.06);
      font-family: "SFMono-Regular", "Menlo", monospace;
      font-size: 12px;
      line-height: 1.8;
      color: #d7e5fa;
    }
    .queue-note {
      padding: 14px;
      border-radius: 18px;
      background: rgba(255,255,255,.06);
      color: rgba(228,237,251,.78);
      line-height: 1.7;
      border: 1px solid rgba(255,255,255,.06);
    }
    .result-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    .result-card { padding: 18px; display: grid; gap: 12px; }
    .result-card.active { border-color: rgba(15,109,141,.22); background: rgba(15,109,141,.06); }
    .result-metrics { display: flex; flex-wrap: wrap; gap: 8px; }
    .detail-layout { display: grid; grid-template-columns: 320px minmax(0, 1fr); gap: 16px; align-items: start; }
    .detail-layout.standalone { grid-template-columns: 1fr; }
    .batch-list { display: grid; gap: 10px; }
    .batch-item { padding: 16px; display: grid; gap: 10px; }
    .batch-item.active { border-color: rgba(15,109,141,.22); background: rgba(15,109,141,.06); }
    .detail-head { display: grid; gap: 14px; margin-bottom: 16px; }
    .standalone-topbar {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: center;
      margin-bottom: 14px;
    }
    .detail-toolbar {
      display: grid;
      gap: 12px;
      padding: 16px;
      border-radius: 20px;
      background: rgba(15,109,141,.04);
      border: 1px solid rgba(15,109,141,.08);
    }
    .summary-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
    .summary-card { background: rgba(255,255,255,.84); border: 1px solid var(--line); }
    .table-wrap {
      overflow: auto;
      border-radius: 20px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,.94);
    }
    .result-table { width: 100%; min-width: 1480px; border-collapse: collapse; font-size: 14px; }
    .result-table th, .result-table td {
      padding: 14px 16px;
      text-align: left;
      vertical-align: top;
      border-right: 1px solid rgba(16,24,40,.07);
      border-bottom: 1px solid rgba(16,24,40,.07);
    }
    .result-table th:last-child, .result-table td:last-child { border-right: 0; }
    .result-table thead th {
      position: sticky;
      top: 0;
      z-index: 1;
      background: #f4f8fc;
      color: var(--muted-2);
      font-size: 12px;
      letter-spacing: .12em;
      text-transform: uppercase;
    }
    .settings-grid { grid-template-columns: 1.05fr .95fr; align-items: start; }
    .overview-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .settings-form, .settings-side { display: grid; gap: 14px; min-width: 0; }
    .audit-stack { max-height: 460px; overflow: auto; }
    .audit-item { padding: 14px; display: grid; gap: 8px; }
    .audit-head { display: flex; justify-content: space-between; gap: 12px; align-items: center; }
    .note-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .note {
      padding: 16px;
      border-radius: 18px;
      background: rgba(15,109,141,.05);
      border: 1px solid rgba(15,109,141,.1);
      color: #314459;
      line-height: 1.7;
      min-width: 0;
      overflow-wrap: anywhere;
      word-break: break-word;
    }
    .settings-panel, .settings-grid, .overview-grid, .note-grid, .overview-card { min-width: 0; }
    .overview-card strong {
      overflow-wrap: anywhere;
      word-break: break-word;
      line-height: 1.22;
      font-size: clamp(19px, 2vw, 24px);
    }
    .note code {
      display: block;
      width: 100%;
      margin-top: 6px;
    }
    .empty-card {
      min-height: 260px;
      display: grid;
      place-items: center;
      text-align: center;
      color: var(--muted);
      line-height: 1.8;
    }
    .toast {
      position: fixed;
      right: 18px;
      bottom: 18px;
      max-width: 360px;
      padding: 14px 16px;
      border-radius: 18px;
      background: rgba(13,22,37,.94);
      color: #eef7ff;
      box-shadow: var(--shadow-lg);
      border: 1px solid rgba(255,255,255,.06);
      font-size: 14px;
      line-height: 1.6;
      z-index: 10;
    }
    @media (max-width: 1260px) {
      .dashboard-grid, .task-summary-row, .detail-layout, .settings-grid { grid-template-columns: 1fr; }
      .result-grid, .stat-strip, .summary-grid, .note-grid, .overview-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 980px) {
      .shell { width: min(100%, calc(100% - 20px)); margin: 10px auto; }
      .login-shell, .frame { grid-template-columns: 1fr; }
      .sidebar-wrap { position: static; width: 100%; height: auto; }
      .sidebar { height: auto; }
    }
    @media (max-width: 720px) {
      .stat-strip, .result-grid, .summary-grid, .note-grid, .overview-grid, .split-two { grid-template-columns: 1fr; }
      .panel, .detail-card, .settings-panel, .workspace-card, .log-card, .login-card {
        padding: 16px;
        border-radius: 24px;
      }
      h1 { font-size: 38px; }
      .topbar { flex-direction: column; align-items: start; }
    }
  </style>
</head>
<body>
  <div id="app"></div>
  <script>
    const DEFAULT_GITLAB_URL = __DEFAULT_GITLAB_URL__;
    const state = {
      me: null,
      view: 'search',
      toast: '',
      loginExpanded: false,
      patGuideExpanded: false,
      login: { token: '', gitlabUrl: DEFAULT_GITLAB_URL || '' },
      search: {
        gitlabUrl: '',
        keywords: '',
        branchMode: 'all',
        branchName: 'main',
        formats: ['xlsx', 'csv', 'json'],
        projects: [],
        projectQuery: '',
        selectedProjectIds: []
      },
      jobs: [],
      completedJobs: [],
      resultTask: null,
      resultRows: [],
      resultFilter: '',
      resultPage: 1,
      resultPageSize: 100,
      resultTotalCount: 0,
      resultTotalPages: 1,
      resultsQuery: '',
      settings: null,
      auditLogs: []
    };

    function esc(v){ return String(v ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;'); }
    function projectLabelById(id) {
      const project = state.search.projects.find((item) => String(item.id) === String(id));
      if (!project) return String(id);
      return project.name || project.path_with_namespace || String(id);
    }
    function projectScopeLabel(projectIds) {
      if (!projectIds || !projectIds.length) return '全部项目';
      return projectIds.map((id) => projectLabelById(id)).join(', ');
    }
    function branchModeLabel(mode) {
      if (mode === 'all') return '全部分支';
      if (mode === 'specific') return '指定分支';
      if (mode === 'default') return '默认分支';
      return mode || '';
    }
    function statusCount(statuses) {
      return state.jobs.filter((job) => statuses.includes(job.status)).length;
    }
    function activeJobs() {
      return state.jobs.filter((job) => job.status === 'queued' || job.status === 'running');
    }
    function resolvedLoginGitlabUrl() {
      return (state.login.gitlabUrl || '').trim() || DEFAULT_GITLAB_URL || '';
    }
    function patCreateUrl() {
      const baseUrl = resolvedLoginGitlabUrl();
      if (!baseUrl) return '';
      const normalizedBaseUrl = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
      return normalizedBaseUrl + '/-/profile/personal_access_tokens';
    }
    function createLogLines(job) {
      if (!job) return ['暂无日志。'];
      const lines = [];
      lines.push('[job] ' + job.id);
      lines.push('[status] ' + (job.status || 'unknown'));
      lines.push('[scope] ' + projectScopeLabel(job.project_ids || []));
      lines.push('[branch] ' + (job.branch_mode || 'default') + (job.branch_name ? ' / ' + job.branch_name : ''));
      lines.push('[formats] ' + (job.formats || []).join(', '));
      if (job.created_at) lines.push('[created] ' + job.created_at);
      if (job.started_at) lines.push('[started] ' + job.started_at);
      if (job.finished_at) lines.push('[finished] ' + job.finished_at);
      if (job.failure_reason) lines.push('[error] ' + job.failure_reason);
      else if (job.status === 'completed') lines.push('[info] result_count=' + String(job.result_count || 0));
      else lines.push('[info] progress=' + String(job.progress || 0) + '%');
      return lines;
    }
    function projectBranchUrl(row) {
      if (!row || !row.project_url) return '';
      const branch = row.branch || '';
      if (!branch) return row.project_url;
      const baseUrl = row.project_url.endsWith('/') ? row.project_url.slice(0, -1) : row.project_url;
      const branchPath = branch
        .split('/')
        .map((segment) => encodeURIComponent(segment))
        .join('/');
      return baseUrl + '/-/tree/' + branchPath;
    }
    function resultRoute(jobId) {
      return '/#result/' + encodeURIComponent(jobId);
    }
    function resultIdFromHash() {
      const hash = window.location.hash || '';
      if (!hash.startsWith('#result/')) return '';
      return decodeURIComponent(hash.slice('#result/'.length));
    }
    function isStandaloneResultView() {
      return !!resultIdFromHash();
    }
    function setResultHash(jobId) {
      const next = jobId ? '#result/' + encodeURIComponent(jobId) : '';
      if (window.location.hash === next) return;
      window.location.hash = next;
    }
    async function hydrateResultFromHash() {
      const jobId = resultIdFromHash();
      if (!jobId || !state.me) return;
      const task = state.completedJobs.find((item) => item.id === jobId) || state.jobs.find((item) => item.id === jobId);
      if (!task) return;
      if (!state.resultTask || state.resultTask.id !== jobId) {
        state.resultFilter = '';
        state.resultPage = 1;
      }
      state.resultTask = task;
      state.view = 'result-detail';
      render();
      await refreshResultRows();
    }
    function toast(msg){ state.toast = msg; render(); clearTimeout(window.__toastTimer); window.__toastTimer = setTimeout(() => { state.toast = ''; render(); }, 2400); }
    async function api(path, options = {}) {
      const response = await fetch(path, { credentials: 'same-origin', headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options });
      const isJson = (response.headers.get('Content-Type') || '').includes('application/json');
      const payload = isJson ? await response.json() : null;
      if (!response.ok) throw new Error(payload && payload.error ? payload.error : 'request failed');
      return payload;
    }
    async function loadMe() {
      try {
        const payload = await api('/api/me');
        state.me = payload.user;
        state.search.gitlabUrl = state.me.gitlab_url;
        state.login.gitlabUrl = state.me.gitlab_url;
        if (!state.me.is_admin) {
          state.settings = null;
          state.auditLogs = [];
        }
      } catch (_) {
        state.me = null;
        state.settings = null;
        state.auditLogs = [];
      }
    }
    async function login() {
      captureInputs();
      if (!state.login.token.trim()) {
        state.loginExpanded = !resolvedLoginGitlabUrl();
        state.patGuideExpanded = true;
        render();
        scrollToElement('pat-guide');
        toast(resolvedLoginGitlabUrl() ? '还没有 Token？可按下方指引先去 GitLab 创建 PAT。' : '请先填写 GitLab 地址，再按下方指引去创建 PAT。');
        return;
      }
      try {
        const payload = await api('/api/auth/login', { method: 'POST', body: JSON.stringify({ token: state.login.token, gitlab_url: state.login.gitlabUrl }) });
        state.me = payload.user;
        state.search.gitlabUrl = payload.user.gitlab_url;
        state.view = 'search';
        if (!state.me.is_admin) {
          state.settings = null;
          state.auditLogs = [];
        }
        toast('登录成功，已进入检索工作台');
        await refreshAll();
      } catch (err) { toast(err.message); }
    }
    async function logout() {
      try { await api('/api/auth/logout', { method: 'POST', body: '{}' }); } catch (_) {}
      state.me = null;
      state.view = 'search';
      state.jobs = [];
      state.completedJobs = [];
      state.resultTask = null;
      state.resultRows = [];
      state.settings = null;
      state.auditLogs = [];
      render();
    }
    async function refreshProjects(options = {}) {
      if (!state.me) return;
      const query = options.query ?? state.search.projectQuery ?? '';
      const requestKey = JSON.stringify([query, state.search.gitlabUrl || '']);
      state.__projectRequestKey = requestKey;
      try {
        captureInputs();
        const payload = await api('/api/projects?q=' + encodeURIComponent(query) + '&gitlab_url=' + encodeURIComponent(state.search.gitlabUrl || ''));
        if (state.__projectRequestKey !== requestKey) return;
        state.search.projects = payload.projects || [];
        render();
        if (options.restoreFocus) restoreInputFocus('project-query', options.selectionStart, options.selectionEnd);
      } catch (err) { toast(err.message); }
    }
    async function refreshJobs() {
      if (!state.me) return;
      try {
        const payload = await api('/api/jobs');
        state.jobs = payload.jobs || [];
        state.completedJobs = state.jobs.filter((job) => job.status === 'completed');
        if (state.resultTask) {
          const current = state.jobs.find((job) => job.id === state.resultTask.id);
          if (current) state.resultTask = current;
        }
        const hashJobId = resultIdFromHash();
        if (hashJobId) {
          const hashTask = state.jobs.find((job) => job.id === hashJobId);
          if (hashTask) {
            state.resultTask = hashTask;
            state.view = 'result-detail';
          }
        }
        render();
      } catch (err) { toast(err.message); }
    }
    async function refreshSettings() {
      if (!state.me || !state.me.is_admin) {
        state.settings = null;
        state.auditLogs = [];
        return;
      }
      try {
        const [settingsPayload, auditPayload] = await Promise.all([api('/api/admin/settings'), api('/api/admin/audit-logs')]);
        state.settings = settingsPayload.settings;
        state.auditLogs = auditPayload.logs || [];
        render();
      } catch (err) { toast(err.message); }
    }
    async function refreshAll() { await Promise.all([refreshJobs(), refreshProjects(), refreshSettings()]); }
    async function createJob() {
      captureInputs();
      if (!state.search.keywords.trim()) { toast('请先输入至少一个关键字'); return; }
      if (!state.search.formats.length) { toast('请至少选择一种导出格式'); return; }
      if (!state.search.gitlabUrl.trim()) { toast('请填写 GitLab 地址'); return; }
      if (state.search.branchMode === 'specific' && !state.search.branchName.trim()) { toast('指定分支模式下必须填写分支名'); return; }
      try {
        await api('/api/jobs', { method: 'POST', body: JSON.stringify({
          gitlab_url: state.search.gitlabUrl,
          keywords: state.search.keywords,
          branch_mode: state.search.branchMode,
          branch_name: state.search.branchMode === 'specific' ? state.search.branchName : '',
          formats: state.search.formats,
          project_ids: state.search.selectedProjectIds
        })});
        state.view = 'tasks';
        toast('后台任务已提交');
        await refreshJobs();
      } catch (err) { toast(err.message); }
    }
    async function rerunJob(jobId) {
      try {
        await api('/api/jobs/' + encodeURIComponent(jobId) + '/rerun', { method: 'POST', body: '{}' });
        toast('已重新创建任务');
        await refreshJobs();
      } catch (err) { toast(err.message); }
    }
    async function cancelJob(jobId) {
      try {
        await api('/api/jobs/' + encodeURIComponent(jobId) + '/cancel', { method: 'POST', body: '{}' });
        toast('任务已取消');
        await refreshJobs();
      } catch (err) { toast(err.message); }
    }
    async function openResult(jobId, options = {}) {
      if (options.newTab !== false && !isStandaloneResultView()) {
        window.open(resultRoute(jobId), '_blank', 'noopener');
        return;
      }
      const task = state.completedJobs.find((item) => item.id === jobId) || state.jobs.find((item) => item.id === jobId);
      if (!task) return;
      state.resultTask = task;
      state.resultFilter = '';
      state.resultPage = 1;
      state.resultTotalCount = Number(task.result_count || 0);
      state.resultTotalPages = Math.max(1, Math.ceil(state.resultTotalCount / state.resultPageSize));
      state.view = 'result-detail';
      setResultHash(jobId);
      render();
      await refreshResultRows();
    }
    async function refreshResultRows(options = {}) {
      if (!state.resultTask) return;
      try {
        const payload = await api(
          '/api/jobs/' + encodeURIComponent(state.resultTask.id)
          + '/results?q=' + encodeURIComponent(state.resultFilter || '')
          + '&page=' + encodeURIComponent(String(state.resultPage))
          + '&page_size=' + encodeURIComponent(String(state.resultPageSize))
        );
        state.resultRows = payload.rows || [];
        state.resultTotalCount = Number(payload.total_count || 0);
        state.resultPage = Number(payload.page || state.resultPage || 1);
        state.resultPageSize = Number(payload.page_size || state.resultPageSize || 100);
        state.resultTotalPages = Number(payload.total_pages || Math.max(1, Math.ceil(state.resultTotalCount / state.resultPageSize)));
        render();
        if (options.restoreFocus) restoreInputFocus('result-filter', options.selectionStart, options.selectionEnd);
      } catch (err) { toast(err.message); }
    }
    async function setResultPage(page) {
      if (!state.resultTask) return;
      const nextPage = Math.max(1, Math.min(Number(page) || 1, state.resultTotalPages || 1));
      if (nextPage === state.resultPage) return;
      state.resultPage = nextPage;
      render();
      await refreshResultRows();
    }
    async function saveSettings() {
      if (!state.settings) return;
      captureInputs();
      try {
        const payload = await api('/api/admin/settings', { method: 'PUT', body: JSON.stringify({ default_gitlab_url: state.settings.default_gitlab_url || '' }) });
        state.settings = payload.settings;
        toast('设置已保存');
        await refreshSettings();
      } catch (err) { toast(err.message); }
    }
    function toggleFormat(format) {
      const set = new Set(state.search.formats);
      set.has(format) ? set.delete(format) : set.add(format);
      state.search.formats = [...set];
      render();
    }
    function toggleProject(id) {
      const set = new Set(state.search.selectedProjectIds);
      set.has(id) ? set.delete(id) : set.add(id);
      state.search.selectedProjectIds = [...set];
      render();
    }
    function clearProjects() {
      state.search.selectedProjectIds = [];
      render();
    }
    function statusBadge(status) {
      if (status === 'completed') return '<span class="badge success">已完成</span>';
      if (status === 'running') return '<span class="badge warn">运行中</span>';
      if (status === 'queued') return '<span class="badge muted">排队中</span>';
      if (status === 'failed') return '<span class="badge danger">失败</span>';
      if (status === 'interrupted' || status === 'cancelled') return '<span class="badge muted">已中断</span>';
      return '<span class="badge muted">' + esc(status) + '</span>';
    }
    function renderLogin() {
      const helper = resolvedLoginGitlabUrl()
        ? '输入 GitLab PAT 后即可登录。'
        : '请填写 GitLab PAT 和实例地址后登录。';
      const createUrl = patCreateUrl();
      return `
        <div class="shell">
          <div class="login-shell">
            <section class="login-card">
              <p class="copy">${esc(helper)}</p>
              <div class="field">
                <span class="label">GitLab Personal Access Token</span>
                <input class="input" id="login-token" value="${esc(state.login.token)}" placeholder="glpat-xxxx" />
              </div>
              <button type="button" class="inline-link" onclick="toggleLoginExpanded()">${state.loginExpanded ? '收起 GitLab 地址' : '展开填写 GitLab 地址'}</button>
              ${state.loginExpanded ? `
                <div class="field">
                  <span class="label">GitLab 地址</span>
                  <input class="input" id="login-gitlab" value="${esc(state.login.gitlabUrl)}" placeholder="https://gitlab.example.com" />
                  <p class="copy" style="margin-top:8px;">留空时使用服务默认地址。</p>
                </div>
              ` : ''}
              <button type="button" class="inline-link" onclick="togglePatGuideExpanded()">${state.patGuideExpanded ? '收起创建 Token 指引' : '没有 Token？展开创建指引'}</button>
              ${state.patGuideExpanded ? `
                <div class="guide-card" id="pat-guide">
                  <div class="guide-title">创建 GitLab Token</div>
                  <div class="button-row">
                    ${createUrl
                      ? `<a class="btn secondary" href="${esc(createUrl)}" target="_blank" rel="noreferrer">去创建 Token</a>`
                      : `<button type="button" class="btn secondary" onclick="toggleLoginExpanded()">先填写 GitLab 地址</button>`}
                  </div>
                  <ol class="guide-list">
                    <li>打开 GitLab 的 Access Tokens 页面。</li>
                    <li>新建 token，名称可填 gitlab-code-search。</li>
                    <li>至少勾选 api 和 read_api 权限。</li>
                    <li>创建后立即复制，回来粘贴到这里登录。</li>
                  </ol>
                  <p class="copy">如果页面路径和你的 GitLab 版本不一致，可按菜单进入 User Settings / Preferences 中的 Access Tokens。</p>
                </div>
              ` : ''}
              <div class="button-row">
                <button type="button" class="btn primary" onclick="login()">登录</button>
              </div>
            </section>
          </div>
        </div>`;
    }
    function renderSidebar() {
      return `
        <div class="sidebar-wrap">
          <aside class="sidebar">
            <div class="side-brand">
              <div class="side-mark">G</div>
              <div class="side-copy">
                <strong>GCS Workbench</strong>
                <span>${state.me ? esc(state.me.display_name) : ''}</span>
              </div>
            </div>
            <div class="side-nav">
              <button type="button" class="side-item ${state.view === 'search' ? 'active' : ''}" onclick="setView('search')"><span class="side-icon">S</span><span class="side-label">搜索</span></button>
              <button type="button" class="side-item ${state.view === 'tasks' ? 'active' : ''}" onclick="setView('tasks')"><span class="side-icon">T</span><span class="side-label">任务管控</span></button>
              <button type="button" class="side-item ${state.view === 'results' || state.view === 'result-detail' ? 'active' : ''}" onclick="setView('results')"><span class="side-icon">R</span><span class="side-label">结果批次</span></button>
              <button type="button" class="side-item ${state.view === 'settings' ? 'active' : ''} ${state.me && state.me.is_admin ? '' : 'locked'}" onclick="setView('settings')"><span class="side-icon">A</span><span class="side-label">系统设置</span></button>
            </div>
            <button type="button" class="side-item" onclick="logout()"><span class="side-icon">↩</span><span class="side-label">退出会话</span></button>
          </aside>
        </div>`;
    }
    function renderTopbar() {
      return `
        <div class="topbar">
          <div class="top-title">
            <div class="row"><div class="top-mark">G</div><h2>${esc(state.me.display_name)}</h2></div>
            <div class="meta">当前 GitLab：${esc(state.me.gitlab_url)}</div>
          </div>
          <div class="topbar-row">
            <span class="status-pill"><span class="dot"></span>serve active</span>
            <span class="status-pill">运行任务 ${activeJobs().length}</span>
            <span class="status-pill">完成批次 ${state.completedJobs.length}</span>
            ${state.me && state.me.is_admin && state.settings ? `<span class="status-pill">workdir ${esc(state.settings.workdir)}</span>` : ''}
          </div>
        </div>`;
    }
    function renderSearchPage() {
      const selected = state.search.projects.filter((project) => state.search.selectedProjectIds.includes(project.id));
      const active = activeJobs()[0] || null;
      const previewJobs = state.jobs.filter((job) => !active || job.id !== active.id).slice(0, 3);
      const keywords = state.search.keywords.split(/\\n|,/).map((item) => item.trim()).filter(Boolean);
      return `
        <div class="page">
          <div class="stat-strip">
            <div class="stat-card"><div class="metric-label">关键词</div><strong>${keywords.length}</strong><span>当前草稿中待检索的关键字数量。</span></div>
            <div class="stat-card"><div class="metric-label">项目范围</div><strong>${selected.length || 'ALL'}</strong><span>${selected.length ? '已显式圈定项目范围。' : '未选择项目时默认搜索可见项目。'}</span></div>
            <div class="stat-card"><div class="metric-label">导出格式</div><strong>${state.search.formats.length}</strong><span>${esc(state.search.formats.join(' / ').toUpperCase())}</span></div>
            <div class="stat-card"><div class="metric-label">当前队列</div><strong>${activeJobs().length}</strong><span>搜索任务异步执行，不阻塞当前页面。</span></div>
          </div>
          <div class="dashboard-grid">
            <section class="workspace-card primary">
              <div class="section-head">
                <div class="section-title">
                  <strong>搜索</strong>
                  <div class="section-copy">配置关键词、搜索范围和导出格式后即可提交后台任务。</div>
                </div>
                <div class="chip-row"></div>
              </div>
              <div class="control-grid">
                <div class="field">
                  <span class="label">关键词列表</span>
                  <textarea class="textarea" id="keywords" placeholder="输入关键字，按行或逗号分隔">${esc(state.search.keywords)}</textarea>
                </div>
                <div class="split-two">
                  <div class="field" style="margin-top:0;">
                    <span class="label">GitLab 地址</span>
                    <input class="input" id="search-gitlab" value="${esc(state.search.gitlabUrl)}" placeholder="https://gitlab.example.com" />
                  </div>
                  <div class="field branch-mode-field" style="margin-top:0;">
                    <span class="label">分支策略</span>
                    <div class="row branch-mode-row">
                      <button type="button" class="chip ${state.search.branchMode === 'all' ? 'active' : ''}" onclick="setBranchMode('all')">全部分支</button>
                      <button type="button" class="chip ${state.search.branchMode === 'default' ? 'active' : ''}" onclick="setBranchMode('default')">默认分支</button>
                      <button type="button" class="chip ${state.search.branchMode === 'specific' ? 'active' : ''}" onclick="setBranchMode('specific')">指定分支</button>
                    </div>
                  </div>
                </div>
                ${state.search.branchMode === 'specific' ? `
                  <div class="field" style="margin-top:0;">
                    <span class="label">指定分支名</span>
                    <input class="input" id="branch-name" value="${esc(state.search.branchName)}" placeholder="例如 release/2026-q2" />
                  </div>
                ` : ''}
                <div class="field" style="margin-top:0;">
                  <span class="label">导出格式</span>
                  <div class="row">
                    <button type="button" class="chip ${state.search.formats.includes('xlsx') ? 'active' : ''}" onclick="toggleFormat('xlsx')">XLSX</button>
                    <button type="button" class="chip ${state.search.formats.includes('csv') ? 'active' : ''}" onclick="toggleFormat('csv')">CSV</button>
                    <button type="button" class="chip ${state.search.formats.includes('json') ? 'active' : ''}" onclick="toggleFormat('json')">JSON</button>
                    ${state.me && state.me.is_admin && state.settings ? `<span class="metric-pill">SQLite：${esc(state.settings.db_path)}</span>` : ''}
                  </div>
                </div>
                <div class="button-row">
                  <button type="button" class="btn primary" onclick="createJob()">开始搜索</button>
                  <button type="button" class="btn ghost" onclick="setView('tasks')">查看任务态势</button>
                </div>
              </div>
            </section>
            <div class="sub-grid">
              <section class="workspace-card tinted">
                <div class="section-head">
                  <div class="section-title">
                    <strong>项目范围</strong>
                    <div class="section-copy">支持项目筛选和多选；留空时搜索全部可见项目。</div>
                  </div>
                  ${selected.length ? `<button type="button" class="btn ghost" onclick="clearProjects()">清空选择</button>` : ''}
                </div>
                <div class="field">
                  <span class="label">搜索项目名称或 group 路径</span>
                  <input class="input" id="project-query" value="${esc(state.search.projectQuery)}" placeholder="例如 finance / search-bff" />
                </div>
                <div class="row">
                  ${selected.length
                    ? selected.map((project) => `<span class="chip active">${esc(project.name)} <button type="button" onclick="toggleProject(${project.id})">×</button></span>`).join('')
                    : '<span class="metric-pill">当前未选择项目，提交后将搜索全部项目</span>'}
                </div>
                <div class="project-grid">
                  ${state.search.projects.length
                    ? state.search.projects.map((project) => `<button type="button" class="project-item ${state.search.selectedProjectIds.includes(project.id) ? 'active' : ''}" onclick="toggleProject(${project.id})"><input type="checkbox" tabindex="-1" ${state.search.selectedProjectIds.includes(project.id) ? 'checked' : ''} /><div><strong>${esc(project.name)}</strong><small>${esc(project.web_url || project.path_with_namespace || '')}</small></div></button>`).join('')
                    : '<div class="empty-card">正在加载项目列表...</div>'}
                </div>
              </section>
              <section class="workspace-card">
                <div class="section-head">
                  <div class="section-title">
                    <strong>近期执行概览</strong>
                    <div class="section-copy">查看最近任务和当前进展。</div>
                  </div>
                </div>
                ${active ? `<div class="task-card active"><div class="row">${statusBadge(active.status)}<span class="metric-pill">${esc(active.id)}</span>${active.status === 'completed' ? `<span class="chip active">命中 ${esc(active.result_count || 0)}</span>` : ''}</div><strong>${esc(projectScopeLabel(active.project_ids || []))}</strong><small>分支：${esc(branchModeLabel(active.branch_mode))} ｜ 导出：${esc((active.formats || []).join(', '))}</small><div class="progress"><span style="width:${active.progress || 0}%"></span></div></div>` : '<div class="empty-card" style="min-height:140px;">当前没有活动任务。</div>'}
                <div class="task-list">
                  ${previewJobs.length
                    ? previewJobs.map((job) => `<button type="button" class="task-card ${active && job.id === active.id ? 'active' : ''}" onclick="${job.status === 'completed' ? `openResult('${job.id}')` : `setView('tasks')`}"><div class="row">${statusBadge(job.status)}<span class="metric-pill">${esc(job.created_at || '')}</span>${job.status === 'completed' ? `<span class="chip active">命中 ${esc(job.result_count || 0)}</span>` : ''}</div><strong>${esc(job.id)}</strong><small>${esc(projectScopeLabel(job.project_ids || []))} ｜ 关键字 ${(job.keywords || []).length} 个</small></button>`).join('')
                    : '<div class="empty-card" style="min-height:140px;">当前还没有任务。</div>'}
                </div>
              </section>
            </div>
          </div>
        </div>`;
    }
    function renderTasksPage() {
      if (!state.jobs.length) return `<div class="page"><div class="empty-card">当前还没有任务。回到搜索页发起一次检索。</div></div>`;
      const active = activeJobs()[0] || state.jobs[0];
      const remainingJobs = state.jobs.filter((job) => !active || job.id !== active.id);
      return `
        <div class="page">
          <div class="stat-strip">
            <div class="stat-card"><div class="metric-label">运行中</div><strong>${statusCount(['running'])}</strong><span>正在占用 worker 的后台任务。</span></div>
            <div class="stat-card"><div class="metric-label">排队中</div><strong>${statusCount(['queued'])}</strong><span>等待进入 worker 池的任务数。</span></div>
            <div class="stat-card"><div class="metric-label">已完成</div><strong>${statusCount(['completed'])}</strong><span>可以直接进入结果详情页查看和下载。</span></div>
            <div class="stat-card"><div class="metric-label">中断 / 失败</div><strong>${statusCount(['interrupted','failed','cancelled'])}</strong><span>保留历史记录，便于复盘和审计。</span></div>
          </div>
          <div class="task-summary-row">
            <section class="panel">
              <div class="section-head">
                <div class="section-title">
                  <strong>任务编排台</strong>
                  <div class="section-copy">查看当前活动任务、队列历史和操作入口。</div>
                </div>
                <div class="chip-row">
                  ${state.settings ? `<span class="metric-pill">worker ${esc(state.settings.workers)}</span>` : ''}
                  <span class="metric-pill">只显示当前用户自己的任务</span>
                </div>
              </div>
              ${active ? `<div class="task-card active" style="margin-top:14px;"><div class="row">${statusBadge(active.status)}<span class="metric-pill">${esc(active.id)}</span>${active.status === 'completed' ? `<span class="chip active">命中 ${esc(active.result_count || 0)}</span>` : ''}</div><strong>${esc(projectScopeLabel(active.project_ids || []))}</strong><small>关键字：${esc((active.keywords || []).join(', '))} ｜ 分支：${esc(branchModeLabel(active.branch_mode))} ｜ 导出：${esc((active.formats || []).join(', '))}</small><div class="progress"><span style="width:${active.progress || 0}%"></span></div><div class="action-row">${active.status === 'completed' ? `<button type="button" class="btn primary" onclick="openResult('${active.id}')">打开结果</button>` : ['interrupted','failed','cancelled'].includes(active.status) ? `<button type="button" class="btn secondary" onclick="rerunJob('${active.id}')">重新跑</button>` : `<button type="button" class="btn warn" onclick="cancelJob('${active.id}')">取消任务</button>`}<button type="button" class="btn ghost" onclick="setView('search')">返回搜索页</button></div></div>` : ''}
              <div class="task-list" style="margin-top:14px;">
                ${remainingJobs.length
                  ? remainingJobs.map((job) => `<div class="task-card"><div class="row">${statusBadge(job.status)}<span class="metric-pill">${esc(job.created_at || '')}</span>${job.status === 'completed' ? `<span class="chip active">命中 ${esc(job.result_count || 0)}</span>` : ''}</div><strong>${esc(job.id)}</strong><small>${esc(projectScopeLabel(job.project_ids || []))}</small><div class="row"><span class="chip">${esc(branchModeLabel(job.branch_mode))}</span><span class="chip">${esc((job.formats || []).join(', '))}</span></div><div class="progress"><span style="width:${job.progress || 0}%"></span></div><div class="action-row">${job.status === 'completed' ? `<button type="button" class="btn secondary" onclick="openResult('${job.id}')">查看结果</button>` : ['interrupted','failed','cancelled'].includes(job.status) ? `<button type="button" class="btn secondary" onclick="rerunJob('${job.id}')">重新跑</button>` : `<button type="button" class="btn ghost" onclick="cancelJob('${job.id}')">取消</button>`}</div></div>`).join('')
                  : '<div class="empty-card" style="min-height:180px;">当前没有其他任务。</div>'}
              </div>
            </section>
            <section class="log-card">
              <div class="log-title">
                <div>
                  <strong style="font-size:24px; letter-spacing:-.04em;">执行日志流</strong>
                  <div class="section-copy">查看任务状态和关键执行信息。</div>
                </div>
                ${active ? `<span class="metric-pill" style="background: rgba(255,255,255,.08); color:#edf4ff; border-color: rgba(255,255,255,.1);">${esc(active.id)}</span>` : ''}
              </div>
              <div class="queue-note">任务会排队进入后台 worker 池执行。</div>
              <div class="log-box" style="margin-top:12px;">${createLogLines(active).map((line) => `<div>${esc(line)}</div>`).join('')}</div>
            </section>
          </div>
        </div>`;
    }
    function renderResultsPage() {
      if (!state.completedJobs.length) return `<div class="page"><div class="empty-card">当前还没有已完成结果。等任务跑完后，这里会出现所有结果批次与下载入口。</div></div>`;
      const filtered = state.completedJobs.filter((job) => {
        const query = (state.resultsQuery || '').trim().toLowerCase();
        if (!query) return true;
        return job.id.toLowerCase().includes(query) || (job.keywords || []).join(' ').toLowerCase().includes(query) || projectScopeLabel(job.project_ids || []).toLowerCase().includes(query);
      });
      return `
        <div class="page">
          <div class="stat-strip">
            <div class="stat-card"><div class="metric-label">已完成批次</div><strong>${state.completedJobs.length}</strong><span>以批次卡片管理历史搜索结果。</span></div>
            <div class="stat-card"><div class="metric-label">总命中预览</div><strong>${state.completedJobs.reduce((sum, job) => sum + Number(job.result_count || 0), 0)}</strong><span>基于结果计数的汇总视图。</span></div>
            <div class="stat-card"><div class="metric-label">导出类型</div><strong>3</strong><span>XLSX / CSV / JSON 在详情页统一下载。</span></div>
            <div class="stat-card"><div class="metric-label">查看方式</div><strong>批次 -> 明细</strong><span>先按任务看，再进入单次检索详情。</span></div>
          </div>
          <section class="panel">
            <div class="section-head">
                <div class="section-title">
                  <strong>结果批次总览</strong>
                  <div class="section-copy">查看已完成任务的批次信息和命中统计。</div>
                </div>
              <div class="field" style="margin-top:0; min-width:300px;">
                <span class="label">在已完成批次中搜索</span>
                <input class="input" id="result-batch-query" value="${esc(state.resultsQuery)}" placeholder="按任务号、项目范围或关键字过滤" />
              </div>
            </div>
            <div class="result-grid" style="margin-top:16px;">
              ${filtered.map((job) => `<button type="button" class="result-card ${state.resultTask && state.resultTask.id === job.id ? 'active' : ''}" onclick="openResult('${job.id}')"><div class="row">${statusBadge(job.status)}<span class="metric-pill">${esc(job.created_at || '')}</span></div><strong>${esc(job.id)}</strong><small>项目范围：${esc(projectScopeLabel(job.project_ids || []))}</small><div class="result-metrics"><span class="chip active">关键字 ${(job.keywords || []).length}</span><span class="chip">命中 ${esc(job.result_count || 0)}</span><span class="chip">${esc(branchModeLabel(job.branch_mode))}</span></div><small>${esc((job.keywords || []).join(', '))}</small></button>`).join('')}
            </div>
            ${filtered.length ? '' : '<div class="empty-card" style="margin-top:16px;">当前过滤条件下没有匹配的结果批次。</div>'}
          </section>
        </div>`;
    }
    function renderResultDetailPage() {
      if (!state.resultTask) return `<div class="page"><div class="empty-card">当前没有可查看的已完成结果。</div></div>`;
      const hasResults = (state.resultTask.result_count || 0) > 0;
      const standalone = isStandaloneResultView();
      const pageStart = hasResults ? ((state.resultPage - 1) * state.resultPageSize) + 1 : 0;
      const pageEnd = hasResults ? Math.min(state.resultPage * state.resultPageSize, state.resultTotalCount || 0) : 0;
      return `
        <div class="page">
          <div class="detail-layout ${standalone ? 'standalone' : ''}">
            ${standalone ? '' : `
            <section class="workspace-card">
              <div class="section-title">
                <strong>结果批次</strong>
                <div class="section-copy">选择要查看的结果批次。</div>
              </div>
              <div class="batch-list" style="margin-top:14px;">
                ${state.completedJobs.map((job) => `<button type="button" class="batch-item ${state.resultTask && state.resultTask.id === job.id ? 'active' : ''}" onclick="openResult('${job.id}', { newTab: false })"><div class="row">${statusBadge(job.status)}<span class="metric-pill">${esc(job.created_at || '')}</span></div><strong>${esc(job.id)}</strong><small>${esc(projectScopeLabel(job.project_ids || []))}</small><div class="row"><span class="chip active">命中 ${esc(job.result_count || 0)}</span><span class="chip">关键字 ${(job.keywords || []).length}</span></div></button>`).join('')}
              </div>
            </section>`}
            <section class="detail-card">
              ${standalone ? `<div class="standalone-topbar"><div class="row"><button type="button" class="btn ghost" onclick="window.location='/'">← 返回首页</button><button type="button" class="btn secondary" onclick="setView('results'); setResultHash('');">返回结果列表</button></div><div class="topbar-row"><span class="status-pill">独立结果页</span><span class="status-pill">${esc(state.resultTask.id)}</span></div></div>` : ''}
              <div class="detail-head">
                ${standalone ? '' : `<div class="row"><button type="button" class="btn ghost" onclick="setView('results'); setResultHash('');">← 返回结果总览</button></div>`}
                <div class="section-title">
                  <strong>${esc(state.resultTask.id)}</strong>
                  <div class="section-copy">查看批次概况、下载导出文件并筛选结果内容。</div>
                </div>
                <div class="summary-grid">
                  <div class="summary-card"><div class="metric-label">项目范围</div><strong>${state.resultTask.project_ids && state.resultTask.project_ids.length ? state.resultTask.project_ids.length : 'ALL'}</strong></div>
                  <div class="summary-card"><div class="metric-label">关键字</div><strong>${(state.resultTask.keywords || []).length}</strong></div>
                  <div class="summary-card"><div class="metric-label">命中行</div><strong>${esc(state.resultTask.result_count || 0)}</strong></div>
                  <div class="summary-card"><div class="metric-label">分支模式</div><strong>${esc(branchModeLabel(state.resultTask.branch_mode))}</strong></div>
                </div>
              </div>
              <div class="detail-toolbar">
                <div class="toolbar-row">
                  <span class="metric-pill">项目范围：${esc(projectScopeLabel(state.resultTask.project_ids || []))}</span>
                  <span class="metric-pill">关键字：${esc((state.resultTask.keywords || []).join(', '))}</span>
                  <span class="metric-pill">GitLab：${esc(state.resultTask.gitlab_url || '')}</span>
                </div>
                <div class="toolbar-row">
                  ${(state.resultTask.formats || []).map((format) => `<button type="button" class="download-pill active" ${hasResults ? `onclick="window.location='/api/jobs/${encodeURIComponent(state.resultTask.id)}/exports/${format}'"` : 'disabled'}>${format.toUpperCase()} 下载</button>`).join('')}
                </div>
                <div class="field" style="margin-top:0;">
                  <span class="label">结果内过滤</span>
                  <input class="input" id="result-filter" value="${esc(state.resultFilter)}" placeholder="按关键字、分支、文件名、行号或命中内容过滤" />
                </div>
                <div class="toolbar-row">
                  <span class="metric-pill">当前第 ${esc(state.resultPage)} / ${esc(state.resultTotalPages)} 页</span>
                  <span class="metric-pill">本页 ${esc(state.resultRows.length)} 行</span>
                  <span class="metric-pill">显示 ${esc(pageStart)} - ${esc(pageEnd)} / ${esc(state.resultTotalCount)} 行</span>
                </div>
                <div class="button-row">
                  <button type="button" class="btn secondary" onclick="setResultPage(1)" ${state.resultPage <= 1 ? 'disabled' : ''}>第一页</button>
                  <button type="button" class="btn secondary" onclick="setResultPage(${state.resultPage - 1})" ${state.resultPage <= 1 ? 'disabled' : ''}>上一页</button>
                  <button type="button" class="btn secondary" onclick="setResultPage(${state.resultPage + 1})" ${state.resultPage >= state.resultTotalPages ? 'disabled' : ''}>下一页</button>
                  <button type="button" class="btn secondary" onclick="setResultPage(${state.resultTotalPages})" ${state.resultPage >= state.resultTotalPages ? 'disabled' : ''}>最后一页</button>
                </div>
              </div>
              <div class="table-wrap">
                <table class="result-table">
                  <thead>
                    <tr>
                      <th>关键字</th>
                      <th>分支</th>
                      <th>项目</th>
                      <th>文件</th>
                      <th>代码链接</th>
                      <th>命中内容</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${state.resultRows.length
                      ? state.resultRows.map((row) => `<tr><td>${esc(row.word)}</td><td>${esc(row.branch)}</td><td>${projectBranchUrl(row) ? `<a href="${esc(projectBranchUrl(row))}" target="_blank" rel="noreferrer" style="color: var(--accent-strong); font-weight: 700;">${esc(row.project_name)}</a>` : esc(row.project_name)}</td><td>${esc(row.file_name)}</td><td><a href="${esc(row.line_url)}" target="_blank" rel="noreferrer" style="color: var(--accent-strong); font-weight: 700;">打开代码</a></td><td>${esc(row.data)}</td></tr>`).join('')
                      : '<tr><td colspan="6" style="text-align:center; color:#6b6c72;">当前过滤条件下没有匹配结果。</td></tr>'}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        </div>`;
    }
    function renderSettingsPage() {
      if (!state.me || !state.me.is_admin) return `<div class="page"><div class="empty-card">系统设置只对管理员 PAT 开放。</div></div>`;
      if (!state.settings) return `<div class="page"><div class="empty-card">正在加载设置...</div></div>`;
      return `
        <div class="page">
          <section class="settings-panel">
            <div class="section-head">
                <div class="section-title">
                  <strong>系统设置</strong>
                  <div class="section-copy">查看服务配置、存储路径和审计记录。</div>
                </div>
              <div class="chip-row">
                <span class="metric-pill">admin only</span>
                <span class="metric-pill">workdir locked</span>
              </div>
            </div>
            <div class="overview-grid" style="margin-top:16px;">
              <div class="overview-card"><div class="metric-label">Workdir</div><strong>${esc(state.settings.workdir)}</strong><span>SQLite 与导出目录都围绕这个目录自动组织。</span></div>
              <div class="overview-card"><div class="metric-label">SQLite</div><strong>${esc(state.settings.db_path)}</strong><span>不存在时启动自动创建。</span></div>
              <div class="overview-card"><div class="metric-label">Exports</div><strong>${esc(state.settings.exports_dir)}</strong><span>XLSX / CSV / JSON 都写入此目录。</span></div>
              <div class="overview-card"><div class="metric-label">Admin Identity</div><strong>${esc(state.settings.admin_identity)}</strong><span>管理员身份与 workdir 绑定，不能随意切换。</span></div>
            </div>
            <div class="settings-grid" style="margin-top:16px;">
              <div class="settings-form">
                <div class="workspace-card primary">
                  <div class="section-title">
                    <strong>可编辑项</strong>
                    <div class="section-copy">修改当前服务使用的默认 GitLab 地址。</div>
                  </div>
                  <div class="control-grid">
                    <div class="field">
                      <span class="label">默认 GitLab 地址</span>
                      <input class="input" id="settings-default-gitlab" value="${esc(state.settings.default_gitlab_url || '')}" placeholder="https://gitlab.example.com" />
                    </div>
                    <div class="split-two">
                      <div class="overview-card"><div class="metric-label">Host</div><strong>${esc(state.settings.host)}</strong><span>当前服务监听地址。</span></div>
                      <div class="overview-card"><div class="metric-label">Workers</div><strong>${esc(state.settings.workers)}</strong><span>后台搜索 worker 数量。</span></div>
                    </div>
                    <div class="button-row">
                      <button type="button" class="btn primary" onclick="saveSettings()">保存设置</button>
                    </div>
                  </div>
                </div>
                <div class="note-grid">
                  <div class="note"><strong style="display:block; margin-bottom:6px;">建议启动命令</strong><code>.venv/bin/gcs serve --host ${esc(state.settings.host)} --port ${esc(state.settings.port)} --workdir ${esc(state.settings.workdir)} --admin-token glpat-xxxx${state.settings.default_gitlab_url ? ' --gitlab-url ' + esc(state.settings.default_gitlab_url) : ''}</code></div>
                  <div class="note"><strong style="display:block; margin-bottom:6px;">导出目录</strong>${esc(state.settings.exports_dir)}</div>
                </div>
              </div>
              <div class="settings-side">
                <div class="workspace-card tinted">
                  <div class="section-title">
                    <strong>审计记录</strong>
                    <div class="section-copy">查看关键管理操作记录。</div>
                  </div>
                  <div class="audit-stack" style="margin-top:14px;">
                    ${state.auditLogs.length
                      ? state.auditLogs.map((log) => `<div class="audit-item"><div class="audit-head"><strong>${esc(log.action)}</strong>${statusBadge(log.status === 'success' ? 'completed' : log.status)}</div><div class="meta">${esc(log.created_at)}</div><div class="section-copy">${esc(log.summary)}</div></div>`).join('')
                      : '<div class="empty-card" style="min-height:200px;">当前没有审计记录。</div>'}
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>`;
    }
    function renderApp() {
      if (!state.me) return renderLogin();
      if (isStandaloneResultView() && state.view === 'result-detail') {
        return `
          <div class="shell standalone-shell">
            ${renderResultDetailPage()}
          </div>`;
      }
      return `
        <div class="shell">
          <div class="frame">
            ${renderSidebar()}
            <main class="main">
              ${renderTopbar()}
              ${state.view === 'search' ? renderSearchPage() : ''}
              ${state.view === 'tasks' ? renderTasksPage() : ''}
              ${state.view === 'results' ? renderResultsPage() : ''}
              ${state.view === 'result-detail' ? renderResultDetailPage() : ''}
              ${state.view === 'settings' ? renderSettingsPage() : ''}
            </main>
          </div>
        </div>`;
    }
    function captureInputs() {
      const loginToken = document.getElementById('login-token');
      const loginGitlab = document.getElementById('login-gitlab');
      const searchGitlab = document.getElementById('search-gitlab');
      const branchName = document.getElementById('branch-name');
      const keywords = document.getElementById('keywords');
      const projectQuery = document.getElementById('project-query');
      const resultFilter = document.getElementById('result-filter');
      const resultBatchQuery = document.getElementById('result-batch-query');
      const settingsDefaultGitlab = document.getElementById('settings-default-gitlab');
      if (loginToken) state.login.token = loginToken.value;
      if (loginGitlab) state.login.gitlabUrl = loginGitlab.value;
      if (searchGitlab) state.search.gitlabUrl = searchGitlab.value;
      if (branchName) state.search.branchName = branchName.value;
      if (keywords) state.search.keywords = keywords.value;
      if (projectQuery) state.search.projectQuery = projectQuery.value;
      if (resultFilter) state.resultFilter = resultFilter.value;
      if (resultBatchQuery) state.resultsQuery = resultBatchQuery.value;
      if (settingsDefaultGitlab && state.settings) state.settings.default_gitlab_url = settingsDefaultGitlab.value;
    }
    function restoreInputFocus(id, selectionStart, selectionEnd) {
      requestAnimationFrame(() => {
        const input = document.getElementById(id);
        if (!input) return;
        input.focus();
        const start = Math.min(selectionStart ?? input.value.length, input.value.length);
        const end = Math.min(selectionEnd ?? start, input.value.length);
        input.setSelectionRange(start, end);
      });
    }
    function getFocusedInputState() {
      const active = document.activeElement;
      if (!active || !active.id) return null;
      if (!(active instanceof HTMLInputElement) && !(active instanceof HTMLTextAreaElement)) return null;
      return {
        id: active.id,
        selectionStart: active.selectionStart ?? active.value.length,
        selectionEnd: active.selectionEnd ?? active.selectionStart ?? active.value.length
      };
    }
    function scrollToElement(id) {
      requestAnimationFrame(() => {
        const element = document.getElementById(id);
        if (!element) return;
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      });
    }
    function syncInputs() {
      const loginToken = document.getElementById('login-token');
      const loginGitlab = document.getElementById('login-gitlab');
      const searchGitlab = document.getElementById('search-gitlab');
      const branchName = document.getElementById('branch-name');
      const keywords = document.getElementById('keywords');
      const projectQuery = document.getElementById('project-query');
      const resultFilter = document.getElementById('result-filter');
      const resultBatchQuery = document.getElementById('result-batch-query');
      const settingsDefaultGitlab = document.getElementById('settings-default-gitlab');
      if (loginToken) loginToken.addEventListener('input', (e) => { state.login.token = e.target.value; });
      if (loginGitlab) loginGitlab.addEventListener('input', (e) => { state.login.gitlabUrl = e.target.value; });
      if (searchGitlab) searchGitlab.addEventListener('input', (e) => { state.search.gitlabUrl = e.target.value; });
      if (branchName) branchName.addEventListener('input', (e) => { state.search.branchName = e.target.value; });
      if (keywords) keywords.addEventListener('input', (e) => { state.search.keywords = e.target.value; });
      if (projectQuery) {
        projectQuery.addEventListener('input', (e) => {
          state.search.projectQuery = e.target.value;
          clearTimeout(window.__projectQueryTimer);
          const selectionStart = e.target.selectionStart ?? e.target.value.length;
          const selectionEnd = e.target.selectionEnd ?? selectionStart;
          window.__projectQueryTimer = setTimeout(() => {
            refreshProjects({ query: state.search.projectQuery, restoreFocus: true, selectionStart, selectionEnd });
          }, 180);
        });
      }
      if (resultFilter) {
        resultFilter.addEventListener('input', (e) => {
          state.resultFilter = e.target.value;
          state.resultPage = 1;
          clearTimeout(window.__resultFilterTimer);
          const selectionStart = e.target.selectionStart ?? e.target.value.length;
          const selectionEnd = e.target.selectionEnd ?? selectionStart;
          window.__resultFilterTimer = setTimeout(() => {
            refreshResultRows({ restoreFocus: true, selectionStart, selectionEnd });
          }, 140);
        });
      }
      if (resultBatchQuery) {
        resultBatchQuery.addEventListener('input', (e) => {
          state.resultsQuery = e.target.value;
          const selectionStart = e.target.selectionStart ?? e.target.value.length;
          const selectionEnd = e.target.selectionEnd ?? selectionStart;
          render();
          restoreInputFocus('result-batch-query', selectionStart, selectionEnd);
        });
      }
      if (settingsDefaultGitlab) settingsDefaultGitlab.addEventListener('input', (e) => { state.settings.default_gitlab_url = e.target.value; });
    }
    function setView(view) {
      if (view === 'settings' && (!state.me || !state.me.is_admin)) { toast('只有管理员可以访问设置页'); return; }
      if ((view === 'results' || view === 'result-detail') && state.completedJobs.length && !state.resultTask) state.resultTask = state.completedJobs[0];
      state.view = view;
      render();
      if (view === 'results' || view === 'tasks' || view === 'result-detail') refreshJobs();
      if (view === 'settings') refreshSettings();
      if (view === 'result-detail' && state.resultTask) refreshResultRows();
    }
    function toggleLoginExpanded(){ state.loginExpanded = !state.loginExpanded; render(); }
    function togglePatGuideExpanded(){ state.patGuideExpanded = !state.patGuideExpanded; render(); }
    function setBranchMode(mode){ state.search.branchMode = mode; render(); }
    function render() {
      const focusedInput = getFocusedInputState();
      document.getElementById('app').innerHTML = renderApp() + (state.toast ? `<div class="toast">${esc(state.toast)}</div>` : '');
      syncInputs();
      if (focusedInput) restoreInputFocus(focusedInput.id, focusedInput.selectionStart, focusedInput.selectionEnd);
    }
    window.login = login;
    window.logout = logout;
    window.toggleLoginExpanded = toggleLoginExpanded;
    window.togglePatGuideExpanded = togglePatGuideExpanded;
    window.setView = setView;
    window.setResultHash = setResultHash;
    window.setResultPage = setResultPage;
    window.setBranchMode = setBranchMode;
    window.toggleFormat = toggleFormat;
    window.toggleProject = toggleProject;
    window.clearProjects = clearProjects;
    window.createJob = createJob;
    window.rerunJob = rerunJob;
    window.cancelJob = cancelJob;
    window.openResult = openResult;
    window.saveSettings = saveSettings;
    (async function init(){
      await loadMe();
      if (state.me) await refreshAll();
      await hydrateResultFromHash();
      render();
      setInterval(refreshJobs, 4000);
    })();
    window.addEventListener('hashchange', async () => {
      if (!state.me) return;
      const jobId = resultIdFromHash();
      if (!jobId) {
        if (state.view === 'result-detail') {
          state.view = 'results';
          render();
        }
        return;
      }
      await refreshJobs();
      await hydrateResultFromHash();
    });
  </script>
</body>
</html>"""
    return html.replace("__DEFAULT_GITLAB_URL__", json.dumps(default_gitlab_url or ""))
