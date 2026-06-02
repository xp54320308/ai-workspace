---
name: feishu-multi-bot-collab
description: 飞书群多机器人互相@mention协作的完整指南，含已知坑点和权限配置。
version: 1.0.0
---

# 飞书群多机器人 @mention 协作

## 适用场景
在飞书群中让多个机器人（Bot）互相 @mention、通信、协作完成任务。

## 前置条件
每个机器人需要在飞书后台开通权限：
> **获取群组中其他机器人和用户@当前机器人的消息**

位置：飞书开放平台 → 对应应用 → 机器人设置 → 事件与权限 → 勾选此开关

**未开通此权限 = Bot 收不到其他 Bot 的 @mention 消息。**

## 已知坑点

### 1. 同租户 App 不互推消息事件
同一个飞书租户（tenant）内的 App A 发消息，App B 通过 WebSocket **收不到事件推送**。
- 跨租户（如 Coze Bot）发消息 → 其他 Bot 能收到 ✅
- 同租户 App 发消息 → 其他 Bot 收不到 ❌

**解决**：开通上述权限后，同租户 Bot 的 @mention 也能收到。

### 2. Bot open_id 可能不是你想象的那个
- 用户的 `open_id` ≠ Bot 的 `open_id`
- Coze Bot 的 `open_id` 不等于 Coze 平台的用户 ID
- 通过 API `GET /open-apis/bot/v3/info` 获取的 `bot.open_id` 是正确的

**验证方法**：让 Bot 在群里发一条消息，在飞书事件日志中查看 `sender.sender_id.open_id`。

### 3. 发送 @mention 的正确格式
通过飞书 API 发消息时，必须用 `<at user_id="ou_xxx">名称</at>` 格式：

```python
# 正确：text 消息类型 + <at> 标签
msg_content = {
    "text": "<at user_id=\"ou_xxx\">Bot名称</at> 你的消息内容"
}

# 正确：post 富文本类型
post_content = {
    "zh_cn": {
        "title": "",
        "content": [
            [
                {"tag": "at", "user_id": "ou_xxx"},
                {"tag": "text", "text": " 你的消息内容"}
            ]
        ]
    }
}
```

**不要用**纯文本 `@Bot名称` — 飞书不会识别为真正的 @mention。

### 4. 不能用 `json=payload` 发送中文
`requests.post(url, json=payload)` 内部用 `ensure_ascii=True`，中文会变成 `\uXXXX`。

**正确做法**：
```python
body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
headers = {"Content-Type": "application/json; charset=utf-8"}
requests.post(url, data=body, headers=headers)
```

## 协作流程

```
用户在群里 @所有人 发任务
    ↓
Hermes 回复：数据采集/分析结果
    ↓
亚希AI 看到 Hermes 的回复 → 处理/写作
    ↓
扣子 看到前面的回复 → 优化/配图
    ↓
用户确认，Hermes 发布
```

**关键发现**：用户在一条消息中 @所有 Bot 时，所有 Bot 都能看到群里其他 Bot 的回复。不需要 Bot 之间互相 @。

## 配置检查清单

| 检查项 | 位置 |
|--------|------|
| Bot 权限：`im:message:send_as_bot` | 飞书后台 → 权限管理 |
| 事件订阅：`im.message.receive_v1` | 飞书后台 → 事件订阅 |
| 开通"获取其他机器人消息" | 飞书后台 → 机器人设置 |
| 群已在白名单或 `groupAllowFrom: ["*"]` | Bot 配置文件 |
| 正确的 Bot open_id（`ou_` 开头） | 通过 `/bot/v3/info` API 确认 |

## Hermes 读取群消息

Hermes 要读群消息需要开通 `im:message.group_msg` 权限。
开通后可用飞书 Open API 读取群消息，看到其他 Bot 的回复。凭据从 hermes 环境配置中获取。

⚠️ 飞书 API 返回的 app 消息中，@mention 的 `user_id` 会显示为 `@_user_1`、`@_user_2` 占位符，不是真实 open_id。需要通过 `user_name` 字段判断。

### 消息类型限制

| msg_type | API 能否读取内容 | 备注 |
|----------|-----------------|------|
| `text` | ✅ 完整读取 | `body.content.text` |
| `post` (富文本) | ✅ 完整读取 | JSON 结构，见下方解析 |
| `interactive` (卡片) | ❌ 无法读取 | 返回 `"请升级至最新版本客户端，以查看内容"` |

**卡片消息是客户端渲染的，API 层面拿不到内容。** 如果 Bot 用卡片格式发了文章，只能让它重发为纯文本 `post` 或 `text` 格式。

### 从 post 消息提取纯文本

飞书 `post` 类型消息是嵌套 JSON 结构。遍历 `content` → 每个段落 → 每个元素，根据 `tag` 拼接：`text` 取 `text` 字段，`a` 取 `text + href`，`at` 取 `user_name`。

### Gateway 未路由时的降级方案

当飞书 gateway 未能将群消息路由到 Hermes（比如其他 Bot 的回复没触发事件推送），可以**主动轮询**群消息作为降级：

1. 获取飞书 tenant_access_token（使用 hermes 配置中的飞书凭据）
2. 调用 `/im/v1/messages`（按 `ByCreateTimeDesc` 排序）拉取最近消息
3. 过滤出目标 Bot 发送的消息（按 `sender.id` 匹配）
4. 解析消息内容（text 直接读，post 解析 JSON，interactive 跳过）

这个模式适用于：等待协作 Bot 的回复、检查任务进度、获取文章初稿等场景。

## Bot 信息速查

| Bot | 平台 | open_id | 备注 |
|-----|------|---------|------|
| 龙虾 | 本地 OpenClaw | `ou_e490d3e3bb2bd407e1416fa5dad3f2e6` | 原名亚希AI |
| 扣子 | Coze | `ou_9476039d1b41c69c47afc491a879568d` | |
| Hermes | 飞书原生 | `ou_46c096598b8412c5995414be61b3ed04` | Bot open_id |
| 群 chat_id | — | `oc_681b09b5a353c05310a6e926ddc5db2d` | |
