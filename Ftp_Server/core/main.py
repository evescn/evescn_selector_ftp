# -*- coding: utf-8 -*-
# @Author    : Evescn
# @time      : 2020/11/25 17:57
# @File      : main.py
# @Software  : PyCharm

import selectors
import socket
import json
import os
import hashlib
from conf import settings


class FTP_Server():
    def __init__(self):
        """
        初始化FTP_Server类，
        self.server：初始化套接字
        self.sel：初始化selectors
        self.user_data：定义用数据字典
        """
        self.server = socket.socket()
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sel = selectors.DefaultSelector()
        self.user_data = {}
        self.data = {}
        self.put_data = {}

    def server_listen(self, ip, port):
        """
        初始化服务端使用selectors监听
        :param ip: 监听的IP地址
        :param port: 监听的端口
        :return:
        """
        self.server.bind((ip, port))
        self.server.setblocking(False)
        self.server.listen()
        self.sel.register(self.server, selectors.EVENT_READ, self.accept)

    def interactive(self):
        """
        服务端交互程序，接受活跃的连接，并执行操作（建立新的连接，或处理老连接请求）
        :return:
        """
        while True:
            events = self.sel.select()
            for key, mask in events:
                settings.access_logger.info('key.data: %s' % key.data)
                callback = key.data
                callback(key.fileobj, mask)

    def accept(self, sock, mask):
        """
        判断当前客户端为一个新连接时，创建1个新的连接
        :param sock: 客户端的文件句柄
        :param mask:
        :return:
        """
        conn, addr = sock.accept()
        settings.access_logger.info('accepted：%s, from: %s' % (conn, addr))

        conn.setblocking(False)
        self.sel.register(conn, selectors.EVENT_READ, self.read)

    def read(self, conn, mask):
        """
        判断当前客户端为一个老连接时，处理客户端请求
        :param conn: 客户端的文件句柄
        :param mask:
        :return:
        """
        try:
            if not self.user_data.get(conn):
                """
                判断当前 客户端 是否登陆(self.user_data[conn]是否有值)，没有登陆就调用登陆函数
                """
                self.login(conn)
                settings.access_logger.info(self.user_data[conn])

            else:
                if self.user_data[conn]['is_authenticated']:
                    data = conn.recv(1024).strip().decode()
                    if data:
                        settings.access_logger.info('echoing: %s, to: %s' % (data, conn))
                        cmd_dic = json.loads(data)
                        action = cmd_dic["action"]
                        if hasattr(self, "cmd_%s" % action):
                            func = getattr(self, "cmd_%s" % action)
                            func(conn, cmd_dic)
                    else:
                        self.del_conn(conn)
                else:
                    """ 客户已登陆，但登陆状态异常，请重新登陆 """
                    conn.send(b'500')
                    self.user_data[conn] = {}

        except ConnectionResetError as e:
            settings.access_logger.error('err: %s' % e)
            self.del_conn(conn)

    def login(self, conn):
        """
        客户端登陆FTP服务器，登陆验证。客户端传输用户和密码（密码加密传输），验证登陆
        :param conn: 客户端的文件句柄
        :return: {
            200：登陆成功
            300：账号或密码不对
            400：账户不存在
        }
        """
        self.user_data[conn] = {}

        client_login_data = conn.recv(1024).strip().decode()
        settings.access_logger.info('client_login_data: %s' % client_login_data)
        if client_login_data:
            user_dic = json.loads(client_login_data)

            user_name = user_dic['user_name']
            user_password = user_dic['user_password']

            user_file = "%s/conf/%s.json" % (settings.BASE_DIR, user_name)
            settings.access_logger.info(user_file)

            if os.path.isfile(user_file):
                with open(user_file, mode='r', encoding='utf-8') as f:
                    _user_dic = json.load(f)
                    _user_name = _user_dic['name']
                    _user_password_str = _user_dic['password']

                    m = hashlib.md5()
                    m.update(_user_password_str.encode('utf-8'))
                    _user_password = m.hexdigest()

                    if user_name == _user_name and user_password == _user_password:
                        self.user_data[conn]['name'] = user_name
                        self.user_data[conn]['is_authenticated'] = True
                        self.user_data[conn]['dir'] = _user_dic['home']
                        self.user_data[conn]['disk_quota'] = _user_dic['disk_quota']

                        """登陆系统成功"""
                        conn.send(b'200')

                    else:
                        """账号或密码不对，请检查后重新输入"""
                        conn.send(b'300')

            else:
                """用户账号不存在，请联系管理员创建"""
                conn.send(b'400')
        else:
            self.del_conn(conn)

        return None

    def cmd_bash_common(self, conn, *args):
        """
        基础命令功能封装函数，ls,dir,pwd调用
        :param conn: 客户端的文件句柄
        :param args: [ls|dir|pwd]
        :return:
        """
        cmd_split = args[0][0]
        cmd_action = cmd_split['action']
        settings.access_logger.info('work_dir: %s' % self.user_data[conn]['dir'])
        if cmd_action == 'ls' or cmd_action == 'dir':
            cmd_str = "%s -lh %s" % (cmd_action, self.user_data[conn]['dir'])
            cmd_res = os.popen(cmd_str).read()
        else:
            cmd_res = self.user_data[conn]['dir']

        settings.access_logger.info('before send: %s' % len(cmd_res))
        if len(cmd_res) == 0:
            cmd_res = ". .."
        self.data[conn] = cmd_res
        # 先发大小给客户端
        conn.send(str(len(cmd_res)).encode('utf-8'))

        self.sel.modify(conn, selectors.EVENT_READ, self.cmd_bash_common_send_data)

        return None

    def cmd_bash_common_send_data(self, conn, mask):
        """
        基础命令，传输数据给客户端
        :param conn: 客户端的文件句柄
        :param mask:
        :return:
        """
        client_ack = conn.recv(1024).decode('utf-8')
        # print(client_ack)
        conn.send(self.data[conn].encode('utf-8'))
        settings.access_logger.info('common result send done!')
        del self.data[conn]

        self.sel.modify(conn, selectors.EVENT_READ, self.read)

    def cmd_ls(self, conn, *args):
        """
        显示服务端当前目录文件信息
        :param conn: 客户端文件句柄
        :param args: ls
        :return:
        """
        self.cmd_bash_common(conn, args)

    def cmd_dir(self, conn, *args):
        """
        显示服务端当前目录文件信息(windows测试使用)
        :param conn: 客户端文件句柄
        :param args: dir
        :return:
        """
        self.cmd_bash_common(conn, args)

    def cmd_pwd(self, conn, *args):
        """
        显示服务器当前路径信息
        :param conn: 客户端文件句柄
        :param args: pwd
        :return:
        """
        self.cmd_bash_common(conn, args)

    def cmd_cd(self, conn, *args):
        """
        切换服务端，当前所在目录
        :param conn: 客户端文件句柄
        :param args: cd dir 进入文件命令
        :return:
        """
        cmd_dic = args[0]
        dirname_client = cmd_dic['des_dir']
        if dirname_client == '../':
            dirname = os.path.dirname(self.user_data[conn]['dir'])
            print(dirname)
            self.user_data[conn]['dir'] = dirname
            conn.send(('已进入目录 %s' % dirname).encode('utf-8'))

        else:
            dirname = "%s/%s" % (self.user_data[conn]['dir'], dirname_client)
            if os.path.isdir(dirname):
                self.user_data[conn]['dir'] = dirname
                conn.send(('已进入目录 %s' % dirname).encode('utf-8'))
            else:
                conn.send('没有此目录!'.encode('utf-8'))

        return None

    def cmd_get(self, conn, *args):
        """
        解析客户端命令，下载文件
        :param conn: 客户端文件句柄
        :param args: get filename 下载文件的命令
        :return:
        """
        cmd_dic = args[0]
        filename_client = cmd_dic['src_filename']
        self.data[conn] = '%s/%s' % (self.user_data[conn]['dir'], filename_client)

        if os.path.isfile(self.data[conn]):
            file_total_size = os.stat(self.data[conn]).st_size
            settings.access_logger.info('file_size: %s' % file_total_size)
            conn.send(str(file_total_size).encode('utf-8'))
            self.sel.modify(conn, selectors.EVENT_READ, self.cmd_get_client_result)

        else:
            conn.send(b'-1')
            self.sel.modify(conn, selectors.EVENT_READ, self.cmd_get_client_result)

        return None

    def cmd_get_client_result(self, conn, mask):
        """
        传输下载文件数据，支持断点续传
        :param conn: 客户端文件句柄
        :return: {
            100: 服务端文件不存在
            200: 客户端文件不存在，需要下载，
            300：客户端存在文件，但是文件不完整，需要断点续传
            400：客户端存在文件，且文件完整，不需要下载了
            500: 客户端文件比服务器文件大，客户端文件错误，需要删除文件后，重新下载
        }
        """
        client_ack = int(conn.recv(1024).decode())

        if client_ack == 100:
            print('服务端文件不存在，无法下载')

        elif client_ack == 200:
            self.sel.modify(conn, selectors.EVENT_READ, self.cmd_get_send_data)

        elif client_ack == 300:
            self.sel.modify(conn, selectors.EVENT_READ, self.cmd_get_send_data)

        elif client_ack == 400:
            self.sel.modify(conn, selectors.EVENT_READ, self.read)

        elif client_ack == 500:
            self.sel.modify(conn, selectors.EVENT_READ, self.read)

        return None

    def cmd_get_send_data(self, conn, mask):
        """
        和客户端交互发送数据，客户端每次发送当前已接受数据，服务端从客户端终点获取数据，发送给客户端
        :param conn: 客户端文件句柄
        :param mask:
        :return:
        """
        try:
            client_data = conn.recv(1024).decode()
            if client_data:
                client_data = json.loads(client_data)
                file_total_size = client_data['file_total_size']
                client_data_size = client_data['client_data_size']
                settings.access_logger.info('client_data_size: %s' % client_data_size)

                if client_data_size < file_total_size:
                    with open(self.data[conn], mode='rb') as f:
                        f.seek(client_data_size, 0)
                        line = f.read(1024)
                        conn.send(line)

                else:
                    settings.access_logger.info('file download success...')
                    del self.data[conn]
                    self.sel.modify(conn, selectors.EVENT_READ, self.read)
                    return None
            else:
                self.del_conn(conn)

        except ConnectionResetError as e:
            settings.access_logger.error('error: %s' % e)
            del self.data[conn]
            self.del_conn(conn)

        return None

    def cmd_put(self, conn, *args):
        """
        上传文件，支持断点续传
        :param conn: 客户端文件句柄
        :param args: put filename 上传文件的命令
        :return: {
            200: 服务器端文件不存在，需要上传，
            300：服务器端存在文件，但是文件不完整，需要断点续传
            400：服务器端存在文件，且文件完整，不需要上传了
            500: 服务器端文件比服务器文件大，客户端文件错误，需要服务器端删除文件后，重新上传
        }
        """
        cmd_dic = args[0]
        filename_client = cmd_dic['src_filename']
        self.data[conn] = '%s/%s' % (self.user_data[conn]['dir'], filename_client)

        settings.access_logger.info('filename: %s' % self.data[conn])
        file_total_size = cmd_dic['size']

        if os.path.isfile(self.data[conn]):
            server_data_size = os.stat(self.data[conn]).st_size
            if server_data_size < file_total_size:
                conn.send(b'300')
                self.put_data[conn] = {
                    'file_total_size': file_total_size,
                    'server_data_size': server_data_size
                }
                self.sel.modify(conn, selectors.EVENT_READ, self.cmd_put_server_result)

            elif server_data_size == file_total_size:
                conn.send(b'400')

            else:
                conn.send(b'500')

        else:
            conn.send(b'200')
            self.put_data[conn] = {
                'file_total_size': file_total_size,
                'server_data_size': 0
            }
            self.sel.modify(conn, selectors.EVENT_READ, self.cmd_put_server_result)

        return None

    def cmd_put_server_result(self, conn, mask):
        """
        获取当前服务器端文件大小，然后调用 self.cmd_put_put_data 发送给客户端
        :param conn: 客户端文件句柄
        :param mask:
        :return:
        """
        client_data = conn.recv(1024)

        if client_data:
            file_total_size = self.put_data[conn]['file_total_size']
            server_data_size = self.put_data[conn]['server_data_size']

            if server_data_size < file_total_size:
                self.cmd_put_put_file_size_data(conn, server_data_size)
            else:
                settings.access_logger.info('文件上传完成')
                self.cmd_put_put_file_size_data(conn, server_data_size)
                del self.put_data[conn]
                self.sel.modify(conn, selectors.EVENT_READ, self.read)

        else:
            self.del_conn(conn)

        return None

    def cmd_put_put_file_size_data(self, conn, server_data_size):
        """
        想客户端发送当前服务器端文件大小
        :param conn: 客户端文件句柄
        :param server_data_size: 服务器端文件大小
        :return:
        """
        server_data = {
            'server_data_size': server_data_size
        }
        conn.send(json.dumps(server_data).encode('utf-8'))
        self.sel.modify(conn, selectors.EVENT_READ, self.cmd_put_get_data)

    def cmd_put_get_data(self, conn, mask):
        """
        和客户端交互发送数据，服务端每次发送当前已接受数据，客户端从服务端终点获取数据，发送给服务端
        :param conn: 客户端文件句柄
        :param mask:
        :return:
        """
        try:
            file_client_data = conn.recv(1024)
            with open(self.data[conn], mode='ab') as f:
                f.write(file_client_data)

            self.put_data[conn]['server_data_size'] += len(file_client_data)
            self.sel.modify(conn, selectors.EVENT_READ, self.cmd_put_server_result)

        except ConnectionResetError as e:
            settings.access_logger.error('error: %s' % e)
            self.del_conn(conn)

        return None

    def del_conn(self, conn):
        """
        关闭客户端连接句柄
        :param conn: 客户端文件句柄
        :return:
        """
        settings.access_logger.info('closing: %s' % conn)
        self.sel.unregister(conn)
        conn.close()


def start():
    ftp_server = FTP_Server()
    ftp_server.server_listen(settings.HOST_IP, settings.HOST_PORT)
    ftp_server.interactive()


if __name__ == '__main__':
    start()