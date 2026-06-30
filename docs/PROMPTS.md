# Prompt Templates

## Full Routing Prompt

```text
请使用 CD-Center：
1. 先全局扫描我电脑里已安装的 skill / plugin / MCP / agent。
2. 生成本地能力清单并打开本地调度页面。
3. 根据我的任务先做能力路由，再决定执行方案。
4. 回答时明确：候选能力、选择能力、不使用能力及原因。
```

## Scan Only Prompt

```text
请先使用 CD-Center 扫描我本机现有的 skills / plugins / MCP / agents，并输出能力摘要，不要直接执行任务。
```

## Route Then Execute Prompt

```text
请先用 CD-Center 扫描并做能力路由，然后再执行我的任务。先给我候选能力、选择能力、不使用能力及原因。
```
