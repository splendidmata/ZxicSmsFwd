#!/bin/bash

# ZxicSmsFwd Debian 一键部署脚本
# 功能：自动安装依赖、下载代码、配置服务并部署为 systemd 系统服务

set -e

echo "================================"
echo "ZxicSmsFwd 部署脚本 (Debian)"
echo "================================"

# 1. 检查系统环境
echo "\n1. 检查系统环境..."
if [ ! -f "/etc/debian_version" ]; then
    echo "错误：此脚本仅适用于 Debian 系统"
    exit 1
fi

echo "系统检查通过，开始部署..."

# 2. 安装必要的系统依赖
echo "\n2. 安装系统依赖..."
sudo apt update
sudo apt install -y python3 python3-pip git

# 3. 创建部署目录
echo "\n3. 创建部署目录..."
DEPLOY_DIR="/opt/zxic-sms-fwd"
sudo mkdir -p "$DEPLOY_DIR"
sudo chown "$USER:$USER" "$DEPLOY_DIR"

# 4. 下载项目代码
echo "\n4. 下载项目代码..."
cd "$DEPLOY_DIR"
if [ -d ".git" ]; then
    echo "项目目录已存在，更新代码..."
    git pull
else
    echo "克隆项目代码..."
    git clone "https://github.com/yourusername/ZxicSmsFwd.git" .
fi

# 5. 安装项目依赖
echo "\n5. 安装项目依赖..."
pip3 install -r requirements.txt

# 6. 创建配置文件
echo "\n6. 配置文件设置..."
if [ ! -f "config.json" ]; then
    echo "创建配置文件..."
    cp "config.json.example" "config.json"
    
    echo "\n配置文件设置选项："
    echo "1. 自动交互式配置"
    echo "2. 手动编辑配置文件"
    echo "\n请选择配置方式 (1/2)："
    read -r CONFIG_OPTION
    
    if [ "$CONFIG_OPTION" = "1" ]; then
        echo "\n开始交互式配置..."
        
        # Telegram 配置
        echo "\n=== Telegram 配置 ==="
        read -r -p "请输入 Telegram 机器人令牌: " BOT_TOKEN
        read -r -p "请输入 Telegram 聊天 ID: " CHAT_ID
        read -r -p "请输入信任的用户 ID (多个用逗号分隔): " TRUST_IDS
        
        # 调制解调器配置
        echo "\n=== 调制解调器配置 ==="
        read -r -p "请输入调制解调器名称: " MODEM_NAME
        read -r -p "请输入调制解调器 IP 地址: " MODEM_IP
        read -r -p "请输入调制解调器类型 (zxic_web_new/zxic_web_old): " MODEM_TYPE
        read -r -p "请输入调制解调器登录密码: " MODEM_PASSWORD
        
        # Server酱³ 配置
        echo "\n=== Server酱³ 配置 (可选) ==="
        read -r -p "是否启用 Server酱³ 推送? (y/n): " ENABLE_SERVER_CHAN
        if [ "$ENABLE_SERVER_CHAN" = "y" ] || [ "$ENABLE_SERVER_CHAN" = "Y" ]; then
            read -r -p "请输入 Server酱³ UID: " SERVER_CHAN_UID
            read -r -p "请输入 Server酱³ SendKey: " SERVER_CHAN_SENDKEY
        fi
        
        # 构建配置文件
        cat > "config.json" << EOF
{
    "telegram_host": "api.telegram.org",
    "bot_token": "$BOT_TOKEN",
    "telegram_chat_id": "$CHAT_ID",
    "trust_command_from": [$(echo "$TRUST_IDS" | sed 's/,/","/g')],
    "modems": [
        {
            "name": "$MODEM_NAME",
            "modem_ip": "$MODEM_IP",
            "type": "$MODEM_TYPE",
            "login_password": "$MODEM_PASSWORD"
        }
    ],
    "server_chan_enabled": $(if [ "$ENABLE_SERVER_CHAN" = "y" ] || [ "$ENABLE_SERVER_CHAN" = "Y" ]; then echo "true"; else echo "false"; fi),
    "server_chan_uid": "$(if [ "$ENABLE_SERVER_CHAN" = "y" ] || [ "$ENABLE_SERVER_CHAN" = "Y" ]; then echo "$SERVER_CHAN_UID"; else echo ""; fi)",
    "server_chan_sendkey": "$(if [ "$ENABLE_SERVER_CHAN" = "y" ] || [ "$ENABLE_SERVER_CHAN" = "Y" ]; then echo "$SERVER_CHAN_SENDKEY"; else echo ""; fi)"
}
EOF
        
        echo "\n配置文件已生成！"
    else
        echo "\n请编辑配置文件 config.json 并填写相关信息："
        echo "- Telegram 机器人令牌"
        echo "- Telegram 聊天 ID"
        echo "- 调制解调器配置"
        echo "- Server酱³ 配置（可选）"
        echo "\n编辑完成后按 Enter 键继续..."
        read -r
    fi
else
    echo "配置文件已存在，跳过创建..."
    echo "\n是否查看当前配置文件内容？ (y/n):"
    read -r VIEW_CONFIG
    if [ "$VIEW_CONFIG" = "y" ] || [ "$VIEW_CONFIG" = "Y" ]; then
        cat "config.json"
        echo "\n按 Enter 键继续..."
        read -r
    fi
fi

# 7. 创建 systemd 服务文件
echo "\n7. 创建 systemd 服务文件..."
SERVICE_FILE="/etc/systemd/system/zxic-sms-fwd.service"

# 构建服务文件内容
SERVICE_CONTENT="[Unit]
Description=ZXIC SMS Forwarder Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$DEPLOY_DIR
ExecStart=/usr/bin/python3 $DEPLOY_DIR/__main__.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target"

# 写入服务文件
echo "$SERVICE_CONTENT" | sudo tee "$SERVICE_FILE" > /dev/null

# 8. 启用并启动服务
echo "\n8. 启用并启动服务..."
sudo systemctl daemon-reload
sudo systemctl enable zxic-sms-fwd
sudo systemctl start zxic-sms-fwd

# 9. 检查服务状态
echo "\n9. 检查服务状态..."
sleep 2
sudo systemctl status zxic-sms-fwd --no-pager

# 10. 部署完成
echo "\n================================"
echo "部署完成！"
echo "================================"
echo "\n服务信息："
echo "- 部署目录: $DEPLOY_DIR"
echo "- 服务名称: zxic-sms-fwd"
echo "- 启动命令: sudo systemctl start zxic-sms-fwd"
echo "- 停止命令: sudo systemctl stop zxic-sms-fwd"
echo "- 重启命令: sudo systemctl restart zxic-sms-fwd"
echo "- 状态命令: sudo systemctl status zxic-sms-fwd"
echo "- 日志命令: sudo journalctl -u zxic-sms-fwd -f"
echo "\n注意：请确保已正确配置 config.json 文件中的各项参数，"
echo "特别是 Telegram 机器人令牌、聊天 ID 和调制解调器配置。"
echo "================================"
