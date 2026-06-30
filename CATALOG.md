# Capability Catalog

The default registry is intentionally generic. These entries demonstrate how CD-Center can organize capability choices without exposing a private tool inventory.

| Capability | Category | Scope | Use |
|---|---|---|---|
| 界面评审 | UI / 前端 | shared | Review hierarchy, layout, responsiveness, accessibility, and interaction states. |
| 前端实现 | UI / 前端 | local, remote | Implement usable pages, components, or tool surfaces. |
| 代码审查 | 代码 / 后端 | local | Find bugs, regressions, missing tests, and maintainability issues. |
| 接口实现 | 代码 / 后端 | local | Design or update APIs, validation, errors, and contracts. |
| 网页调研 | 网页 / 自动化 | remote | Read public sources and summarize evidence. |
| 内容制作 | 视频 / 内容 | local, remote | Draft scripts, structures, captions, and publishing copy. |
| 知识整理 | 知识 / 记忆 | local | Turn materials into maintainable project knowledge. |
| 部署检查 | 部署 | remote | Check build, environment, permissions, rollback, and release validation. |
| 安全审查 | 代码 / 后端 | shared | Check disclosure risk, permissions, dependencies, input validation, and release blockers. |
| 发布验收 | 部署 | shared | Confirm validation, visibility, sensitive-term scan, commit completeness, and rollback. |

## Adapting The Catalog

When replacing the example registry:

- Keep capability names generic unless the repository is team-private.
- Avoid real account names, machine paths, internal deployment URLs, tokens, cookies, logs, or private tool inventories.
- Keep `env` as an array containing `local`, `remote`, or `shared`.
- Keep category names aligned with `index.html`.
