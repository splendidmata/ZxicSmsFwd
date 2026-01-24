import json
import os

def get_config(filename='config.json'):
    """
    读取配置文件并填充默认值
    
    Args:
        filename: 配置文件路径，默认为'config.json'
        
    Returns:
        dict: 配置字典
        
    Raises:
        FileNotFoundError: 配置文件不存在
        json.JSONDecodeError: 配置文件格式不正确
    """
    # 检查文件是否存在
    if not os.path.exists(filename):
        raise FileNotFoundError(f"配置文件不存在: {filename}")
    
    # 使用上下文管理器安全打开文件
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 解析JSON配置
    try:
        conf = json.loads(content)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"配置文件格式不正确: {str(e)}", e.doc, e.pos)
    
    # 填充默认配置值
    return fill_default_config(conf)

def set_config_default_value(config, key, value):
    """
    设置配置默认值（如果键不存在）
    
    Args:
        config: 配置字典
        key: 配置键
        value: 默认值
    """
    try:
        config[key]
    except KeyError:
        config[key] = value

def fill_default_config(config):
    """
    填充所有默认配置值
    
    Args:
        config: 配置字典
        
    Returns:
        dict: 填充后的配置字典
    """
    # Telegram 配置
    set_config_default_value(config, 'telegram_host', 'api.telegram.org')
    set_config_default_value(config, 'bot_token', '')
    set_config_default_value(config, 'telegram_chat_id', '')
    set_config_default_value(config, 'trust_command_from', [])
    
    # 调制解调器配置
    set_config_default_value(config, 'modems', [])
    
    # Server酱³ 配置
    set_config_default_value(config, 'server_chan_enabled', False)
    set_config_default_value(config, 'server_chan_uid', '')
    set_config_default_value(config, 'server_chan_sendkey', '')
    
    return config

def validate_config(config):
    """
    验证配置是否有效
    
    Args:
        config: 配置字典
        
    Returns:
        bool: 配置是否有效
        str: 错误信息（如果配置无效）
    """
    # 检查必要的配置项
    if not config.get('bot_token'):
        return False, "缺少必要的配置项: bot_token"
    
    if not config.get('telegram_chat_id'):
        return False, "缺少必要的配置项: telegram_chat_id"
    
    # 检查调制解调器配置
    modems = config.get('modems', [])
    for i, modem in enumerate(modems):
        if not modem.get('name'):
            return False, f"调制解调器 {i+1} 缺少名称"
        if not modem.get('modem_ip'):
            return False, f"调制解调器 {i+1} 缺少IP地址"
        if not modem.get('type'):
            return False, f"调制解调器 {i+1} 缺少类型"
        if not modem.get('login_password'):
            return False, f"调制解调器 {i+1} 缺少登录密码"
    
    # 检查Server酱³配置
    if config.get('server_chan_enabled'):
        if not config.get('server_chan_uid'):
            return False, "启用了Server酱³但缺少UID"
        if not config.get('server_chan_sendkey'):
            return False, "启用了Server酱³但缺少SendKey"
    
    return True, "配置有效"