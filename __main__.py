import os
import sys

# 添加当前目录到 Python 路径，确保可以导入同级模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sms_forwarder
import config_utils

# 普通模式运行
conf = config_utils.get_config('config.json')
forwarder = sms_forwarder.SmsForwarder(conf)
forwarder.start()