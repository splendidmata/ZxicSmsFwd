# 中兴 LTE USB Dongle 短信转发器

## 项目简介

中兴 LTE USB Dongle 短信转发器是一个基于 Python 开发的工具，用于监控和转发中兴 LTE USB 调制解调器（Dongle）收到的短信到 Telegram 或 Server酱³ 等平台。该工具还支持通过 Telegram 机器人发送短信和执行 USSD 命令，方便用户远程管理和监控设备。

## 支持的设备

该工具支持以下类型的中兴 LTE USB 调制解调器：

- **固件类型**：
  - `zxic_web_new`：使用 `proc_get` API 的新固件
  - `zxic_web_old`：使用 `goform_get_cmd_process` API 的旧固件

- **设备状态**：
  - 支持在线状态监控
  - 支持自动重连和登录

## 安装和配置

### 前置要求

- Python 3.6 或更高版本
- 安装所需依赖：
  ```bash
  pip install -r requirements.txt
  ```

### 配置文件

配置文件为 `config.json`，位于项目根目录。您可以参考 `config.json.example` 创建自己的配置文件。

#### 配置文件示例

```json
{
    "telegram_host": "api.telegram.org",
    "bot_token": "1234567890:VGhpcyBib3QgdG9rZW4gaXMgaW52YWxpZC4",
    "telegram_chat_id": "1145141919",
    "trust_command_from": [
        1145141919
    ],
    "server_chan_enabled": false,
    "server_chan_uid": "",
    "server_chan_sendkey": "",
    "modems": [
        {
            "type": "zxic_web_new",
            "name": "13800138000",
            "modem_ip": "172.17.0.1",
            "login_password": "admin"
        },
        {
            "type": "zxic_web_old",
            "name": "15666666666",
            "modem_ip": "172.17.0.5",
            "login_password": "admin"
        }
    ]
}
```

#### 配置文件说明

| 配置项 | 说明 |
|-------|------|
| `telegram_host` | Telegram Bot API 的主机头，对于处于中国的用户可能有帮助 |
| `bot_token` | Telegram Bot 的 Token，用于转发短信至 Telegram |
| `telegram_chat_id` | 需要转发至的聊天 ID，可以是用户 ID、群组 ID 或频道 ID |
| `trust_command_from` | 可信任命令来源的发送者的 ID，只能是用户 ID，只有处于这个列表里面的用户才能使用机器人命令 |
| `server_chan_enabled` | 是否启用 Server酱³ 通知 |
| `server_chan_uid` | Server酱³ 的 UID |
| `server_chan_sendkey` | Server酱³ 的 SendKey |
| `modems` | 接受短信的设备，支持多个设备，以设备名（name）区分 |

#### 调制解调器配置说明

| 配置项 | 说明 |
|-------|------|
| `type` | 设备固件类型，只能是 `zxic_web_new` 或者 `zxic_web_old` 两个值 |
| `name` | 设备名称，用于在发送短信时区别不同的设备 |
| `modem_ip` | Modem 的后台管理界面的 IP |
| `login_password` | 登录 Modem 后台管理界面的密码 |

**如何确定设备类型**：
1. 使用浏览器打开后台管理界面
2. 按下 F12 按钮打开开发者工具，点到网络 Tab
3. 查看刷出来的内容是 `proc_get` 还是 `goform_get_cmd_process`
   - 如果是 `proc_get`，type 则填写 `zxic_web_new`
   - 如果是 `goform_get_cmd_process`，type 则填写 `zxic_web_old`

## 使用方法

### 启动程序

在项目根目录下执行：

```bash
python zxicsmsfwd/__main__.py
```

### Telegram 机器人命令

| 命令 | 说明 | 用法示例 |
|------|------|----------|
| `/init` | 重新初始化所有调制解调器 | `/init` |
| `/get_devices` | 获取设备列表及设备状态 | `/get_devices` |
| `/test` | 发送测试消息 | `/test` |
| `/send_sms` | 发送短信 | `/send_sms 13800138000 10086 cxll` |
| `/send_ussd` | 发送 USSD 代码 | `/send_ussd 13800138000 *#06#` |

### 功能特点

#### 1. 短信监控和转发
- **实时监控**：每 2 秒检查一次设备的短信列表
- **智能过滤**：自动过滤重复短信和发送状态短信
- **多平台通知**：支持转发到 Telegram 和 Server酱³
- **状态管理**：自动处理发送成功/失败的短信状态

#### 2. 短信发送
- **远程发送**：通过 Telegram 机器人远程发送短信
- **状态反馈**：发送结果会通过 Telegram 通知反馈
- **错误处理**：发送失败时会提示错误信息

#### 3. USSD 命令执行
- **远程执行**：通过 Telegram 机器人远程执行 USSD 命令
- **结果反馈**：USSD 执行结果会通过 Telegram 通知反馈
- **自动解码**：自动解码 USSD 响应数据，显示明文结果

#### 4. 设备管理
- **状态监控**：实时监控设备在线状态
- **自动重连**：设备掉线后自动尝试重连
- **网络信息**：获取设备的网络状态、信号强度等信息
- **安全管理**：自动禁用网络连接，提高安全性

## 技术实现

### 核心文件

- **`__main__.py`**：项目入口点，初始化配置和启动服务
- **`sms_forwarder.py`**：核心逻辑，处理短信转发和命令响应
- **`zxic_utils.py`**：设备交互工具，封装了与调制解调器的通信
- **`config_utils.py`**：配置文件处理工具，管理配置的读取和验证

### 工作流程

1. **初始化**：加载配置文件，初始化调制解调器控制器
2. **监控**：定期检查设备短信列表，处理新收到的短信
3. **转发**：将新短信转发到 Telegram 或 Server酱³
4. **命令处理**：监听并处理 Telegram 机器人命令
5. **状态管理**：监控设备状态，处理异常情况

### 数据安全

- **密码处理**：登录密码使用安全方式存储和传输
- **网络安全**：默认禁用网络连接，减少安全风险
- **命令安全**：只允许信任列表中的用户发送命令

## 常见问题

### 1. 设备状态显示离线

**可能原因**：
- 网络连接问题
- 登录密码错误
- 设备 IP 地址变更

**解决方案**：
- 检查网络连接
- 确认登录密码正确
- 确认设备 IP 地址正确

### 2. 短信发送失败

**可能原因**：
- 设备离线
- 网络连接问题
- 短信内容过长
- 手机号码格式错误

**解决方案**：
- 确认设备在线
- 检查网络连接
- 缩短短信内容
- 确认手机号码格式正确

### 3. USSD 执行结果乱码

**可能原因**：
- 编码格式不匹配
- 响应数据格式异常

**解决方案**：
- 系统已自动处理编码问题，确保显示明文结果

## 贡献指南

欢迎对本项目进行贡献！如果您有任何建议或改进，请：

1. Fork 本项目
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详情请参阅 [LICENSE](../LICENSE) 文件

## 致谢

- 感谢所有为本项目做出贡献的开发者
- 感谢中兴公司提供的设备和 API
- 感谢 Telegram 和 Server酱³ 提供的通知服务

---

**注意**：本工具仅用于个人使用和学习目的，请勿用于任何非法活动。使用本工具时，请遵守相关法律法规和服务条款。