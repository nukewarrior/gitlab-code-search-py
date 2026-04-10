# 如何创建 GitLab Token

本工具需要使用 GitLab Personal Access Token 调用 API。

## 1. 进入 Token 页面

登录你的 GitLab 后，进入：

- `User Settings` -> `Access Tokens`

不同版本 GitLab 菜单可能略有差异，也可能叫：

- `Preferences` -> `Access Tokens`

## 2. 创建新 Token

创建时建议填写：

- `Token name`：例如 `gitlab-code-search`
- `Expiration date`：建议设置过期时间，避免长期有效

## 3. 勾选权限（必需）

至少勾选以下权限：

- `api`
- `read_api`

## 4. 复制并妥善保存 Token

GitLab 通常只会在创建成功时展示一次完整 token，请立即复制保存。

## 5. 在命令中使用

```bash
.venv/bin/gcs search \
  -u 'https://gitlab.example.com' \
  -t 'your_token' \
  -w 'businessSearch'
```

## 6. 安全建议

- 不要把真实 token 写入代码或提交到 Git 仓库
- 不要把 token 截图、粘贴到公开 issue 或聊天记录
- token 泄漏后立刻在 GitLab 执行撤销（revoke）或轮换（rotate）
