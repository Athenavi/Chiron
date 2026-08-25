# 安全策略 (Security Policy)

## 报告漏洞 (Reporting a Vulnerability)

**请勿公开提交安全漏洞。** 请通过以下渠道私下报告:

1. **GitHub Security Advisory:** 在仓库页面点击 "Security" → "Report a vulnerability"
2. **邮件:** 发送至项目维护者 (可通过 GitHub 仓库获取联系方式)

我们承诺在收到报告后 **48 小时内** 确认，并尽快发布修复。

## 受支持的版本 (Supported Versions)

本项目为活跃开发阶段，仅接受针对最新版本的漏洞报告。

## 安全实践

- 敏感配置使用 `APP_SECRET` 派生密钥进行 AES-256-GCM 加密后落库
- JWT 令牌使用派发生成，支持降级启动
- 所有 API 端点经过认证与授权中间件
- 媒体文件上传经过类型校验与路径安全处理
- 支持租户级数据隔离与 RBAC 权限控制