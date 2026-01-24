import time
import requests
import json
import zxic_utils
#import traceback
import threading

class SmsForwarder:
    UPDATE_ID = 0
    TIMEOUT = 5
    __MSG_IDS = {}

    def __init__(self, config):
        # 验证配置
        from config_utils import validate_config
        is_valid, error_msg = validate_config(config)
        if not is_valid:
            raise ValueError(f"配置无效: {error_msg}")
        
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
        self.config = config
        self.telegram_url = f"https://{self.config['telegram_host']}/bot{self.config['bot_token']}/"
        self.server_chan_enabled = self.config.get('server_chan_enabled', False)
        if self.server_chan_enabled:
            self.server_chan_uid = self.config.get('server_chan_uid', '')
            self.server_chan_sendkey = self.config.get('server_chan_sendkey', '')
            self.server_chan_url = f"https://{self.server_chan_uid}.push.ft07.com/send/{self.server_chan_sendkey}.send"
        self.LOOP_ENABLED = True
        # 最新短信
        self.latest_sms = None
        self.init_modems()

    def init_modems(self):
        import zxic_utils
        self.sms_modems = []
        for i in self.config['modems']:
            if ' ' in i['name']:
                raise RuntimeError('Device name can not contains space.')
            controller = zxic_utils.ZxicUtils(i['modem_ip'], modem_type=i['type'])
            i['modem_status'] = 'online'
            i['controller'] = controller
            try:
                self.do_modem_init(i)
            except Exception as e:
                i['modem_status'] = 'offline'
                offline_msg = f"[设备掉线]\n设备名称：{i['name']}，Modem IP：{i['modem_ip']}"
                print(f"Modem offline: {offline_msg}")
                # 检查Telegram配置是否存在
                if self.config.get('telegram_chat_id'):
                    self.send_telegram_message(self.config['telegram_chat_id'], offline_msg)
                # 检查Server酱³是否启用
                if self.server_chan_enabled:
                    self.send_server_chan_message("设备掉线", offline_msg)
            self.sms_modems.append(i)

    def start(self):
        cmd_recv_thread = threading.Thread(target=self.do_process_commands_task)
        cmd_recv_thread.start()
        self.do_loop_get_sms_task()

    def get_telegram_commands(self):
        # 传递offset参数，避免重复处理已处理过的更新
        # offset值为当前最大UPDATE_ID + 1，这样只会获取新的更新
        params = {
            'offset': self.UPDATE_ID + 1
        }
        try:
            resp = self.session.get(
                self.telegram_url + 'getUpdates',
                timeout=self.TIMEOUT,
                params=params
            )
            result = json.loads(resp.text)
            if result['ok']:
                return result.get('result', [])
            else:
                error_code = result.get('error_code', 0)
                error_desc = result.get('description', 'Unknown error')
                print(f'Telegram API error: {error_code} - {error_desc}')
                # 对于401错误（未授权），记录错误但不抛出异常
                if error_code == 401:
                    print('Telegram bot token or chat ID is invalid. Please check your configuration.')
                return []
        except Exception as e:
            print(f"Error in get_telegram_commands: {e}")
            return []

    def send_telegram_message(self, chat_id, content):
        try:
            resp = self.session.post(
                self.telegram_url + 'sendMessage',
                timeout=self.TIMEOUT,
                data=json.dumps({
                'chat_id': chat_id,
                'text': content
            }))
            result = json.loads(resp.text)
        except Exception as e:
            print(f'Send Telegram message failed: {e}')
            return None
        if result['ok']:
            return result
        else:
            error_code = result.get('error_code', 0)
            error_desc = result.get('description', 'Unknown error')
            print(f'Telegram API error: {error_code} - {error_desc}')
            # 对于401错误（未授权），记录错误但不抛出异常
            if error_code == 401:
                print('Telegram bot token or chat ID is invalid. Please check your configuration.')
            return None
    
    def send_server_chan_message(self, title, content):
        if not self.server_chan_enabled:
            return None
        try:
            resp = self.session.post(
                self.server_chan_url,
                timeout=self.TIMEOUT,
                data=json.dumps({
                'title': title,
                'desp': content
            }))
            result = json.loads(resp.text)
        except:
            print('Send Server酱 message failed.')
            return None
        return result
    
    def do_modem_init(self, modem_controller):
        try:
            # 检查登录是否成功
            login_success = modem_controller['controller'].login(modem_controller['login_password'])
            if not login_success:
                print(f"Login failed for modem: {modem_controller['name']} ({modem_controller['modem_ip']})")
                raise Exception("Login failed")
            # 登录成功后禁用网络
            modem_controller['controller'].common_disable_network()
        except Exception as e:
            print(f"Error initializing modem {modem_controller['name']}: {e}")
            raise

    def do_get_sms_task(self):
        for ctrl in self.sms_modems:
            try:
                if not ctrl['controller'].check_login():
                    self.do_modem_init(ctrl)
                sms_list = ctrl['controller'].get_sms_list()
            except Exception as e:
                print(f"Error getting SMS list: {e}")
                if ctrl['modem_status'] == 'online':
                    ctrl['modem_status'] = 'offline'
                    offline_msg = f"[设备掉线]\n设备名称：{ctrl['name']}，Modem IP：{ctrl['modem_ip']}"
                    self.send_telegram_message(self.config['telegram_chat_id'], offline_msg)
                    if self.server_chan_enabled:
                        self.send_server_chan_message("设备掉线", offline_msg)
                continue
            if ctrl['modem_status'] == 'offline':
                ctrl['modem_status'] = 'online'
                self.do_modem_init(ctrl)
                online_msg = f"[设备上线]\n设备名称：{ctrl['name']}，Modem IP：{ctrl['modem_ip']}"
                self.send_telegram_message(self.config['telegram_chat_id'], online_msg)
                if self.server_chan_enabled:
                    self.send_server_chan_message("设备上线", online_msg)
            
            # 遍历短信列表
            print(f"Processing SMS list for device {ctrl['name']}, status: {ctrl['modem_status']}, found {len(sms_list)} SMS")
            for sms in sms_list:
                try:
                    print(f"Processing SMS: id={sms['id']}, tag={sms.get('tag', 'N/A')}, number={sms.get('number', 'N/A')}, date={sms.get('date', 'N/A')}")
                    
                    # 构建短信ID和唯一标识
                    msgid = f"{ctrl['name']}-{sms['id']}"
                    sms_key = f"{ctrl['name']}-{sms.get('number', 'N/A')}-{sms.get('date', 'N/A')}-{hash(sms.get('content', ''))}"
                    
                    # 获取短信tag值
                    sms_tag = sms.get('tag')
                    
                    # 处理发送状态的短信
                    if sms_tag in ['2', '3']:
                        print(f"Processing sent SMS with tag {sms_tag}, skipping notification")
                        # 这是一条发送状态的短信，不发送收到短信的通知
                        
                        # 处理发送成功的短信
                        if sms_tag == '2':
                            # 这是一条发送成功的短信，发送通知
                            success_msg = f"✅发送短信成功！\n设备：{ctrl['name']}\n号码：{sms.get('number', '未知')}"
                            # 发送到Telegram
                            self.send_telegram_message(self.config['telegram_chat_id'], success_msg)
                            # 发送到Server酱³（如果启用）
                            if self.server_chan_enabled:
                                self.send_server_chan_message("短信发送成功", success_msg)
                            
                            # 删除发送成功的短信记录
                            ctrl['controller'].delete_sms(sms['id'])
                        elif sms_tag == '3':
                            # 这是一条发送失败的短信
                            print(f"Sent SMS failed: tag={sms_tag}, deleting SMS {sms['id']}")
                            # 发送失败通知
                            fail_msg = f"❌发送短信失败！\n设备：{ctrl['name']}\n号码：{sms.get('number', '未知')}"
                            # 发送到Telegram
                            self.send_telegram_message(self.config['telegram_chat_id'], fail_msg)
                            # 发送到Server酱³（如果启用）
                            if self.server_chan_enabled:
                                self.send_server_chan_message("短信发送失败", fail_msg)
                            # 删除发送失败的短信记录，避免重复处理
                            ctrl['controller'].delete_sms(sms['id'])
                        continue
                    
                    # tag=1是接收到的短信，继续处理
                    if sms_tag == '1':
                        print(f"Processing received SMS with tag {sms_tag}")
                        # 继续处理，当作接收到的短信
                    
                    # 检查是否已经处理过这条短信
                    if msgid not in self.__MSG_IDS:
                        print(f"New SMS detected: {msgid}, will send notification")
                        # 这是一条新短信，发送通知
                        msg = f"[收到短信]\n接收设备：{ctrl['name']}\n来自：{sms.get('number', '未知')}\n收到日期：{sms.get('date', '未知')}\n{sms.get('content', '无内容')}"
                        
                        # 更新最新短信
                        self.latest_sms = {
                            "device": ctrl['name'],
                            "number": sms.get('number', '未知'),
                            "date": sms.get('date', '未知'),
                            "content": sms.get('content', '无内容'),
                            "timestamp": time.time()
                        }
                        
                        # 发送短信通知
                        print(f"Sending Telegram message to {self.config['telegram_chat_id']}")
                        telegram_result = self.send_telegram_message(self.config['telegram_chat_id'], msg)
                        print(f"Telegram send result: {telegram_result}")
                        
                        if telegram_result != None:
                            print(f"Telegram message sent successfully, deleting SMS {sms['id']}")
                            # 发送成功，删除短信并记录
                            ctrl['controller'].delete_sms(sms['id'])
                            self.__MSG_IDS[msgid] = {
                                'content': sms.get('content', ''),
                                'key': sms_key,
                                'timestamp': time.time()
                            }
                            
                            # 发送 Server酱³ 通知（如果启用）
                            if self.server_chan_enabled:
                                print(f"Sending ServerChan message")
                                self.send_server_chan_message("收到新短信", msg)
                        else:
                            print(f"Telegram message failed, recording but not deleting SMS {sms['id']}")
                            # 发送失败，记录但不删除短信
                            self.__MSG_IDS[msgid] = {
                                'content': sms.get('content', ''),
                                'key': sms_key,
                                'timestamp': time.time()
                            }
                    elif self.__MSG_IDS[msgid]['key'] != sms_key:
                        # 短信内容有变化，更新记录但不推送
                        print(f"SMS content changed: {msgid}, updating record")
                        self.__MSG_IDS[msgid] = {
                            'content': sms.get('content', ''),
                            'key': sms_key,
                            'timestamp': time.time()
                        }
                    else:
                        # 重复短信，跳过
                        print(f"Duplicate SMS detected: {msgid}, skipping")
                except Exception as e:
                    print(f"Error processing SMS: {e}")
                    continue
    
    def do_process_commands_task(self):
        while self.LOOP_ENABLED:
            try:
                commands = self.get_telegram_commands()
            except Exception as e:
                print(f"Error getting commands: {e}")
                time.sleep(5)
                continue
            
            # 处理 commands 变量
            updates = []
            if isinstance(commands, list):
                # commands 是直接返回的命令列表
                updates = commands
            elif isinstance(commands, dict) and 'result' in commands:
                # commands 是包含 'result' 键的字典
                updates = commands['result']
            else:
                # 无效的 commands 格式
                print(f"Invalid commands format: {type(commands)}")
                time.sleep(2)
                continue
            
            # 处理每个更新
            for update in updates:
                try:
                    # 检查更新 ID
                    update_id = update.get('update_id', 0)
                    if update_id <= self.UPDATE_ID:
                        continue
                    self.UPDATE_ID = update_id
                    
                    # 获取消息
                    message = update.get('message')
                    if not message:
                        continue
                    
                    # 检查发送者是否在信任列表中
                    sender_id = message.get('from', {}).get('id')
                    if not sender_id or sender_id not in self.config.get('trust_command_from', []):
                        continue
                    
                    # 获取命令
                    entities = message.get('entities', [])
                    command = None
                    cmd_offset = 0
                    cmd_length = 0
                    for entity in entities:
                        if entity.get('offset') == 0 and entity.get('type') == 'bot_command':
                            command = message['text'][entity['offset']:entity['offset'] + entity['length']]
                            cmd_offset = entity['offset']
                            cmd_length = entity['length']
                            break
                    if not command:
                        continue
                    
                    # 获取聊天 ID
                    chat_id = message.get('chat', {}).get('id')
                    if not chat_id:
                        continue
                    
                    # 处理命令
                    if command == '/init':
                        # 重新初始化调制解调器
                        self.init_modems()
                        # 发送初始化完成消息
                        self.send_telegram_message(chat_id, "[初始化完成]\n已重新初始化所有调制解调器")
                    elif command == '/get_devices':
                        # 发送设备状态，使用 send_devices_message 函数
                        self.send_devices_message(chat_id)
                    elif command == '/test':
                        # 发送测试消息
                        self.send_telegram_message(chat_id, "测试消息，来自短信转发器。")
                    elif command == '/send_sms':
                        # 解析命令参数
                        message_text = message.get('text', '')
                        if len(message_text) <= cmd_offset + cmd_length:
                            self.send_telegram_message(chat_id, '用法：/send_sms <设备名称> <目标手机号> <短信内容>')
                            continue
                        
                        command_params = message_text[cmd_offset + cmd_length:].strip().split(' ')
                        if len(command_params) < 3:
                            self.send_telegram_message(chat_id, '用法：/send_sms <设备名称> <目标手机号> <短信内容>')
                            continue
                        
                        device_name = command_params[0]
                        target_phone = command_params[1]
                        
                        # 构建短信内容
                        content = ' '.join(command_params[2:])
                        
                        # 发送短信
                        self.do_send_sms_task(chat_id, device_name, target_phone, content)
                    elif command == '/send_ussd':
                        # 解析命令参数
                        message_text = message.get('text', '')
                        if len(message_text) <= cmd_offset + cmd_length:
                            self.send_telegram_message(chat_id, '用法：/send_ussd <设备名称> <USSD代码>')
                            continue
                        
                        command_params = message_text[cmd_offset + cmd_length:].strip().split(' ')
                        if len(command_params) < 2:
                            self.send_telegram_message(chat_id, '用法：/send_ussd <设备名称> <USSD代码>')
                            continue
                        
                        device_name = command_params[0]
                        ussd_code = ' '.join(command_params[1:])
                        
                        # 发送 USSD 代码
                        self.do_send_ussd_task(chat_id, device_name, ussd_code)
                    else:
                        # 不合法的命令
                        self.send_telegram_message(chat_id, "不合法的命令")
                except Exception as e:
                    print(f"Error processing update: {e}")
            
            time.sleep(2)

    def do_send_sms_task(self, chat_id, device_name, target_phone, content):
        has_this_modem = False
        
        # 验证设备名称
        for i in self.sms_modems:
            if i['name'] == device_name:
                has_this_modem = True
                # 检查设备状态
                if i['modem_status'] != 'online':
                    error_msg = f'❗️发送短信失败，设备状态错误： {device_name} - {i["modem_status"]}\n请确保设备在线后重试'
                    self.send_telegram_message(chat_id, error_msg)
                    return
                # 发送短信并检查返回值
                try:
                    success = i['controller'].send_sms(target_phone, content)
                    if success:
                        # 只推送请求已提交的通知，实际发送结果将在设备生成状态记录后推送
                        submit_msg = f'📤发送短信请求已提交\n设备：{device_name}\n号码：{target_phone}\n内容：{content}\n\n请等待实际发送结果通知'
                        self.send_telegram_message(chat_id, submit_msg)
                    else:
                        error_msg = f'❌发送短信失败！\n设备：{device_name}\n号码：{target_phone}\n内容：{content}\n原因：发送失败，请检查设备状态和网络连接'
                        self.send_telegram_message(chat_id, error_msg)
                except Exception as e:
                    error_msg = f'❌发送短信失败！\n设备：{device_name}\n号码：{target_phone}\n内容：{content}\n错误：{str(e)}'
                    self.send_telegram_message(chat_id, error_msg)
                break
        if not has_this_modem:
            # 生成设备列表，帮助用户选择正确的设备名称
            device_list = "\n".join([f"  - {dev['name']}" for dev in self.sms_modems])
            error_msg = f'❗️发送短信失败，找不到指定的 Modem： {device_name}\n可用设备名称：{device_list}'
            self.send_telegram_message(chat_id, error_msg)
    
    def do_send_ussd_task(self, chat_id, device_name, ussd_code):
        has_this_modem = False
        
        # 验证设备名称
        for i in self.sms_modems:
            if i['name'] == device_name:
                has_this_modem = True
                # 检查设备状态
                if i['modem_status'] != 'online':
                    error_msg = f'❗️发送 USSD 失败，设备状态错误： {device_name} - {i["modem_status"]}\n请确保设备在线后重试'
                    self.send_telegram_message(chat_id, error_msg)
                    return
                # 发送 USSD 代码并检查返回值
                try:
                    success = i['controller'].send_ussd(ussd_code)
                    if success:
                        success_msg = f'📤发送 USSD 请求已提交\n设备：{device_name}\n代码：{ussd_code}'
                        self.send_telegram_message(chat_id, success_msg)
                        
                        # 获取 USSD 执行结果
                        print(f"Getting USSD result for device {device_name}")
                        ussd_result = i['controller'].get_ussd_result()
                        
                        # 检查是否有结果
                        if ussd_result and ussd_result['data']:
                            # 构建结果通知
                            result_msg = f"📤USSD 执行结果\n设备：{device_name}\n代码：{ussd_code}\n结果：{ussd_result['data']}"
                            print(f"USSD result: {result_msg}")
                            # 发送到 Telegram
                            self.send_telegram_message(chat_id, result_msg)
                            # 发送到 Server酱³（如果启用）
                            if self.server_chan_enabled:
                                self.send_server_chan_message("USSD 执行结果", result_msg)
                    else:
                        error_msg = f'❌发送 USSD 失败！\n设备：{device_name}\n代码：{ussd_code}\n原因：发送失败，请检查设备状态和网络连接'
                        self.send_telegram_message(chat_id, error_msg)
                except Exception as e:
                    error_msg = f'❌发送 USSD 失败！\n设备：{device_name}\n代码：{ussd_code}\n错误：{str(e)}'
                    self.send_telegram_message(chat_id, error_msg)
                break
        if not has_this_modem:
            # 生成设备列表，帮助用户选择正确的设备名称
            device_list = "\n".join([f"  - {dev['name']}" for dev in self.sms_modems])
            error_msg = f'❗️发送 USSD 失败，找不到指定的 Modem： {device_name}\n可用设备名称：{device_list}'
            self.send_telegram_message(chat_id, error_msg)

    def send_devices_message(self, chat_id):
        msg = '[设备列表]\n'
        for i in self.sms_modems:
            msg += f"📱设备名称： {i['name']}\n"
            msg += f"📟设备状态： {i['modem_status']}\n"
            msg += f"🔌IP 地址： {i['modem_ip']}\n"
            try:
                if i['modem_status'] == 'online':
                    device_status = i['controller'].get_network_status()
                    msg += f"📶运营商：{device_status['network_provider']}\n"
                    signal_num = int(device_status['signalbar'])
                    signal = ''
                    for i in range(0, signal_num):
                        signal += '⚫️'
                    for i in range(0, 5 - signal_num):
                        signal += '⚪️'
                    msg += f"📶设备信号：{signal}\n"
                    msg += f"📶网络类型：{device_status['network_type']}, {device_status['sub_network_type']}\n"
            except:
                msg += '设备状态无法取得数据。\n'
            msg += '\n'
        self.send_telegram_message(chat_id, msg)

    def do_loop_get_sms_task(self):
        while self.LOOP_ENABLED:
            try:
                self.do_get_sms_task()
                time.sleep(2)
            except KeyboardInterrupt:
                print("Keyboard interrupt received, stopping...")
                self.LOOP_ENABLED = False
                break
            except Exception as e:
                print(f"Error in do_loop_get_sms_task: {e}")
                # 继续运行，不退出
                time.sleep(2)