# -*- coding: utf-8 -*-
import copy
import os
import re

import itchat
import requests
from itchat.content import *
import sys
import time
import threading

try:
    reload(sys)
    sys.setdefaultencoding('utf-8')
except:
    import importlib
    importlib.reload(sys)

__author__ = 'tianshl'
__date__ = '2017/01/26'

# 开启自动聊天
OPEN_CHAT = True

# 开启群@自动回复
OPEN_GROUP = True

# 禁止自动回复的人
p_ban = set()

# 禁止自动回复的群组
g_ban = set()

# 历史信息
msgs = {}

# 表情包内容
meme = None

# 临时文件路径
tmp_dir = './.tmp/'
if not os.path.exists(tmp_dir):
    os.mkdir(tmp_dir)

# 图灵机器人
tl_data = {
    'key': '',
    'info': '',
    'loc': '青岛市崂山区',
    'userid': '',
}


def auto_chat(msg, uin=1):
    """
    自动回复
    :param msg: 
    :param uin: 
    :return: 
    """
    reply = ""
    tl_data.update({
        'info': msg,
        'userid': uin
    })
    resp = requests.post("http://www.tuling123.com/openapi/api", tl_data)
    if resp.status_code == 200:
        content = resp.json()
        code = content.get('code', 100000)
        if code == 100000:
            # 文本
            reply = content.get('text', '')
        elif code == 200000:
            # 链接
            reply = content.get('url', '')
    return reply


@itchat.msg_register(INCOME_MSG, True, True, True)
def receive(msg):
    """
    接收到的消息
    :param msg: 信息 
    :return:
    """
    global meme

    # 发送者
    _from = msg['FromUserName']
    # 接受者
    _to = msg['ToUserName']
    # 指令
    is_ins = _to == 'filehelper'

    # 是否为群聊
    is_group = 'IsAt' in msg
    actual_name = msg['ActualNickName'] if is_group else None

    # 消息发送者在好友列表中的备注
    remark = p_name(msg['ActualUserName'] if is_group else _from) or actual_name
    # 消息ID
    msg_id = msg['MsgId']
    # 消息类型
    msg_type = msg['Type']
    # 消息内容
    msg_content = None
    # 分享链接
    msg_share = None

    if msg_type in [TEXT, FRIENDS, SYSTEM]:
        # 消息为文本|好友推荐
        msg_content = msg['Text']

    elif msg_type in [PICTURE, VIDEO, RECORDING, ATTACHMENT]:
        # 消息为图片|视频|语音|附件
        msg_content = msg['FileName']
        # 保存文件
        msg['Text'](tmp_dir + msg_content)

    elif msg_type == CARD:
        # 消息为推荐的名片
        msg_content = '{}的名片性别为{}'.format(
            msg['RecommendInfo']['NickName'],
            '男' if msg['RecommendInfo']['Sex'] == 1 else '女'
        )

    elif msg_type == MAP:
        # 消息为位置信息
        x, y, location = re.search(
            "<location x=\"(.*?)\" y=\"(.*?)\".*label=\"(.*?)\".*",
            msg['OriContent']
        ).group(1, 2, 3)
        msg_content = location if location else '纬度->{} 经度->{}'.format(x, y)

    elif msg_type == SHARING:
        # 消息为分享
        msg_content = msg['Text']
        msg_share = msg['Url']

    meme = msg_content

    # 加入消息历史中
    msg_data = {
        "timestamp": int(time.time()),
        "msg_from": remark,
        "msg_type": msg_type,
        "msg_content": msg_content,
        "msg_share": msg_share
    }
    if is_group:
        msg_data['g_name'] = g_name(_from)
    msgs.update({
        msg_id: msg_data
    })

    # 不回复的类型: 图片
    if msg_type in [PICTURE, VIDEO, RECORDING, ATTACHMENT]:
        return

    # 判断是否为群聊
    if is_group:
        if OPEN_GROUP and msg['IsAt'] and _to not in g_ban:
            # 开启群回复 并且 是艾特我 并且 没在黑名单中
            resp = resolve(msg_content, is_ins, _from)
            resp = '@{}\n{}'.format(actual_name, resp)
            itchat.send(resp, _from)

    elif (OPEN_CHAT and _from not in p_ban) or is_ins:
        # 开启自动回复 并且 不在禁止自动回复列表中
        resp = resolve(msg_content, is_ins, _from)
        if is_ins:
            send_to_file_helper(resp)
        else:
            itchat.send(resp, _from)


@itchat.msg_register(NOTE, True, True, True)
def recall(msg):
    """
    消息撤回
    :param msg: 信息  
    :return:
    """
    global meme
    if '撤回了一条消息' in msg['Content']:
        msg_id = re.search("\<msgid\>(.*?)\<\/msgid\>", msg['Content']).group(1)
        old_msg = msgs.pop(msg_id, {})

        if len(msg_id) < 11:
            # 消息为表情包
            path = tmp_dir + meme
            itchat.send_file(path)
            os.remove(path)

        else:
            msg_content = old_msg.get('msg_content')
            msg_type = old_msg.get('msg_type')
            # 发送撤回的消息
            resp = (
                '<防撤回>\n{}\n'
                '人物: {}\n'
                '时间: {}\n'
                '{}事件: 撤回 {} 消息\n\n'
                '消息内容如下\n{}\n{}'
            ).format(
                '-' * 25,
                old_msg.get('msg_from'),
                time.strftime("%y-%m-%d %H:%M:%S", time.localtime()),
                '地点: {}\n'.format(
                    old_msg['g_name']) if 'g_name' in old_msg else '',
                msg_type,
                '-' * 25,
                msg_content
            )
            if msg_type == SHARING:
                resp = '{}\n就是这个链接\n{}'.format(resp, old_msg.get('msg_share'))

            # 发送撤回的消息
            send_to_file_helper(resp)

            # 发送文件
            if msg_type in [PICTURE, VIDEO, RECORDING, ATTACHMENT]:
                prefix = 'fil'
                if msg_type == PICTURE:
                    prefix = 'img'

                path = tmp_dir + msg_content
                send_to_file_helper('@{}@{}'.format(prefix, path))
                os.remove(path)


def resolve(content, is_ins, _from):
    """
    解析信息
    :param content: 信息 
    :param is_ins:  可能为指令 
    :param _from:   发送者 
    :return:        结果
    """
    global OPEN_CHAT
    global OPEN_GROUP

    if is_ins:
        # 针对某个人开启|关闭自动回复
        reg_ban = re.compile('(开启|关闭)\s+(.+)')
        match = reg_ban.match(content)

        # 针对某个群组开启|关闭自动回复
        reg_g_ban = re.compile('(开启|关闭)群\s+(.+)')
        if match:
            action, remark = match.groups()
            try:
                remove_p_ban(remark) if action == '开启' else add_p_ban(remark)
                return '已{}对{}的自动回复'.format(action, remark)
            except Exception as ex:
                print(ex)
                return '操作有误'
        elif reg_g_ban.match(content):
            action, remark = reg_g_ban.match(content).groups()
            try:
                remove_g_ban(remark) if action == '开启' else add_g_ban(remark)
                return '已{}对{}群的自动回复'.format(action, remark)
            except Exception as ex:
                print(ex)
                return '操作有误'

        elif content == '开启':
            OPEN_CHAT = True
            return '已经开启自动回复'

        elif content == '关闭':
            OPEN_CHAT = False
            return '已经关闭自动回复'

        elif content == '开启群回复':
            OPEN_GROUP = True
            return '已经开启群自动回复'

        elif content == '关闭群回复':
            OPEN_GROUP = False
            return '已经关闭群自动回复'

        elif content == '状态':
            return get_state()

        elif content == '黑名单':
            return get_bans()

        elif content == '菜单':
            return get_menu()

    return auto_chat(content, _from)


def clear(_msgs):
    """
    清理历史消息
    将不可能撤回(大于2分钟)的消息清除掉
    :return: 
    """
    while True:
        # 获取当前时间戳
        timestamp = int(time.time()) - 120
        # 两分钟前文件名
        before = time.strftime("%y%m%d-%H%M%S", time.localtime(timestamp))

        # 遍历消息历史
        cp = copy.copy(_msgs)
        for msg_id, msg in _msgs.items():
            # 清除两分钟前的消息
            if timestamp > msg.get('timestamp'):
                del cp[msg_id]
        _msgs = cp

        # 遍历临时文件列表
        for f in os.listdir(tmp_dir):
            if f.split('.')[0] < before:
                os.remove(tmp_dir + f)

        # 隔5分钟清理一次
        time.sleep(300)


def send_to_file_helper(msg):
    """
    给文件传输助手发送消息
    :param msg: 消息
    :return: 
    """
    itchat.send(msg, 'filehelper')


def p_username(remark):
    """
    根据昵称获取用户名
    :param remark: 昵称
    :return: 
    """
    return itchat.search_friends(name=remark)[0].get('UserName')


def g_username(remark):
    """
    根据群昵称获取用户名
    :param remark: 昵称
    :return: 
    """
    return itchat.search_chatrooms(name=remark)[0].get('UserName')


def p_name(username):
    """
    根据用户名获取昵称
    :param username: 用户名
    :return: 
    """
    friend = itchat.search_friends(userName=username)
    return friend.get('RemarkName') or friend.get('NickName')


def g_name(username):
    """
    根据群用户名获取昵称
    :param username: 用户名
    :return: 
    """
    friend = itchat.search_chatrooms(userName=username)
    return friend.get('RemarkName') or friend.get('NickName')


def add_p_ban(remark):
    """
    添加ban位
    :param remark: 昵称
    :return: 
    """
    p_ban.add(p_username(remark))


def remove_p_ban(remark):
    """
    移除ban位
    :param remark: 昵称
    :return: 
    """
    p_ban.remove(p_username(remark))


def add_g_ban(remark):
    """
    添加群组ban位
    :param remark: 昵称
    :return: 
    """
    g_ban.add(g_username(remark))


def remove_g_ban(remark):
    """
    移除群组ban位
    :param remark: 昵称
    :return: 
    """
    g_ban.remove(g_username(remark))


def get_state():
    """
    获取当前自动回复状态
    :return: 
    """
    resp = '<状态>\n{}\n'.format('-' * 25)
    resp += '自动回复: {}\n'.format('开启' if OPEN_CHAT else '关闭')
    resp += '群回复: {}\n'.format('开启' if OPEN_GROUP else '关闭')
    return resp


def get_bans():
    """
    获取黑名单(禁止自动回复对象)
    :return: 
    """
    names = map(lambda u: p_name(u), p_ban)
    resp = '<黑名单>\n'
    resp += '禁止自动回复的好友列表:\n{}\n{}'.format('-' * 25, '\n'.join(names))
    resp += '\n\n{}\n\n'.format('=' * 18)
    names = map(lambda u: g_name(u), g_ban)
    resp += '禁止自动回复的群列表:\n{}\n{}'.format('-' * 25, '\n'.join(names))
    return resp


def get_menu():
    """
    获取菜单
    :return: 
    """
    return (
        '<帮助菜单>\n'
        '以下为可用指令及描述信息\n{0}\n'
        '开启|关闭\n'
        '{1}开启|关闭自动回复\n'
        '开启|关闭 人名\n'
        '{1}对人名开启|关闭自动回复\n'
        '开启|关闭群回复\n'
        '{1}开启|关闭群内艾特自动回复\n'
        '开启|关闭群 群名\n'
        '{1}对群名开启|关闭艾特自动回复\n'
        '状态\n'
        '{1}查看当前是否已经开启自动回复\n'
        '黑名单\n'
        '{1}获取被禁止自动回复的好友列表\n'
    ).format('-' * 27, ' ' * 5)


def run(tl_key, p_bans=tuple(), g_bans=tuple(), p_open=True, g_open=True, qr=2):
    """
    启动
    :param tl_key:  图灵key
    :param p_bans:  好友黑名单
    :param g_bans:  群组黑名单
    :param p_open:  开启自动回复
    :param g_open:  开启群艾特回复
    :param qr:      二维码类型
    :return: 
    """

    print("""

    ,---------. .-./`)    ____    ,---.   .--.   .-'''-. .---.  .---.   .---.      
    \          \\ .-.') .'  __ `. |    \  |  |  / _     \|   |  |_ _|   | ,_|      
     `--.  ,---'/ `-' \/   '  \  \|  ,  \ |  | (`' )/`--'|   |  ( ' ) ,-./  )      
        |   \    `-'`"`|___|  /  ||  |\_ \|  |(_ o _).   |   '-(_{;}_)\  '_ '`)    
        :_ _:    .---.    _.-`   ||  _( )_\  | (_,_). '. |      (_,_)  > (_)  )    
        (_I_)    |   | .'   _    || (_ o _)  |.---.  \  :| _ _--.   | (  .  .-'    
       (_(=)_)   |   | |  _( )_  ||  (_,_)\  |\    `-'  ||( ' ) |   |  `-'`-'|___  
        (_I_)    |   | \ (_ o _) /|  |    |  | \       / (_{;}_)|   |   |        \ 
        '---'    '---'  '.(_,_).' '--'    '--'  `-...-'  '(_,_) '---'   `--------` 

    """)

    global OPEN_CHAT, OPEN_GROUP

    # 设置图灵key
    tl_data['key'] = tl_key
    # 设置回复状态
    OPEN_CHAT = p_open
    OPEN_GROUP = g_open
    # 配置itchat
    itchat.auto_login(hotReload=True, enableCmdQR=qr)
    # 默认黑名单
    for ban in p_bans:
        try:
            add_p_ban(ban)
        except Exception as ex:
            print(ex)
            continue

    # 设置群黑名单
    for ban in g_bans:
        try:
            add_g_ban(ban)
        except Exception as ex:
            print(ex)
            continue

    # 提示信息
    send_to_file_helper('回复“菜单”二字，获得帮助。')

    # 定时清理历史消息
    t = threading.Thread(target=clear, args=(msgs,))
    t.setDaemon(True)
    t.start()
    # 启动
    itchat.run()


if __name__ == '__main__':
    p = ('搞事情',)
    g = ('',)
    k = ""

    run(k, p)
