# -*- coding: utf-8 -*-
# @Author    : Evescn
# @time      : 2020/11/25 11:10
# @File      : ftp_client.py
# @Software  : PyCharm

import json
import os
import socket
import sys
import hashlib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

import settings


class FTP_Client():

    def __init__(self):
        """
        初始化FTP_Client类
        self.client：初始化套接字
        """
        self.client = socket.socket()

    def connect(self, ip, port):
        """
        设置sockct连接
        :param ip: 连接的IP
        :param port: 连接的端口
        :return:
        """
        self.client.connect((ip, port))

    def msg(self):
        """
        提示信息
        :return:
        """
        msg_info = '''
        ls
        pwd
        cd [ dirname | ../ ]
        get filename
        put filename
        '''

        print(msg_info)

    def login(self):
        """
        登陆FTP服务端，输入用户和密码（密码加密传输），验证成功后登陆
        :return: {
            200：登陆成功
            300：账号或密码不对
            400：账户不存在
            500: 已登陆，但登陆状态异常
        }
        """
        login_msg = {
            '200': '登陆系统成功',
            '300': '账号或密码不对，请检查后重新输入',
            '400': '用户账号不存在，请联系管理员创建',
            '500': '客户已登陆，但登陆状态异常，请重新登陆',
        }

        while True:
            print('\033[1;31;1m 欢迎来到 FTP 系统 \033[0m')
            user_name = input('username: ').strip()
            user_password = input('password: ').strip()

            m = hashlib.md5()
            m.update(user_password.encode('utf-8'))
            user_password = m.hexdigest()

            user_dic = {
                'user_name': user_name,
                'user_password': user_password
            }

            self.client.send(json.dumps(user_dic).encode('utf-8'))
            login_result = self.client.recv(1024).decode()
            print('\033[1;31;1m 登陆信息： %s \033[0m' % login_msg[login_result])

            if login_result == '200':
                break

        return None

    def interactive(self):
        """
        交互函数，接受客户端命令，并调用对应函数，实现功能
        :return:
        """
        self.login()

        while True:
            print()
            cmd = input(">> ").strip()

            if len(cmd) == 0:
                continue

            cmd_str = cmd.split()[0]

            if hasattr(self, "cmd_%s" % cmd_str):
                func = getattr(self, "cmd_%s" % cmd_str)
                func(cmd)

            else:
                self.msg()

    def cmd_bash_common(self, *args):
        """
        基础命令功能封装函数，ls,dir,pwd调用
        :param args: [ls|dir|pwd]
        :return:
        """
        cmd_split = args[0][0].split()
        if len(cmd_split) == 1:
            cmd_action = cmd_split[0]

            msg_dic = {
                "action": cmd_action,
            }

            self.client.send(json.dumps(msg_dic).encode('utf-8'))
            cmd_total_size = self.client.recv(1024).decode()
            print('\033[1;31;1m cmd_total_size: % \033[0m' % cmd_total_size)
            self.client.send('已准备OK，可以接受'.encode('utf-8'))

            received_size = 0
            received_data = b''
            while received_size < int(cmd_total_size):
                data = self.client.recv(1024)
                received_size += len(data)
                received_data += data
            else:
                print(received_data.decode())

        else:
            print('\033[1;31;1m 命令格式错误！ len: %s \033[0m' % len(cmd_split))
            print(cmd_split)

        return None

    def cmd_ls(self, *args):
        """
        显示服务端当前目录文件信息
        :param args: ls
        :return:
        """
        self.cmd_bash_common(args)

    def cmd_dir(self, *args):
        """
        显示服务端当前目录文件信息(windows测试使用)
        :param args: dir
        :return:
        """
        self.cmd_bash_common(args)

    def cmd_pwd(self, *args):
        """
        显示服务器当前路径信息
        :param args: pwd
        :return:
        """
        self.cmd_bash_common(args)

    def cmd_cd(self, *args):
        """
        切换服务端，当前所在文件
        :param args: cd dir 进入文件命令
        :return:
        """
        cmd_split = args[0].split()
        if len(cmd_split) == 2:
            des_dir = cmd_split[1]
            msg_dic = {
                "action": "cd",
                "des_dir": des_dir
            }

            self.client.send(json.dumps(msg_dic).encode('utf-8'))
            return_msg = self.client.recv(1024).decode()

            print(return_msg)

        else:
            print('\033[1;31;1m 命令格式错误 \033[0m')

    def progress(self, percent):
        """
        打印 上传/下载 进度条函数
        :param percent:
        :return:
        """
        if percent > 1:
            percent = 1
        res = int(50 * percent) * '#'
        print('\033[1;31;1m \r[%-50s] %d%% \033[0m' % (res, int(100 * percent)), end='')

    def cmd_get(self, *args):
        """
        下载文件，支持断点续传
        :param args: get filename 下载文件的命令
        :return: {
            100: 服务端文件不存在
            200: 客户端文件不存在，可以直接下载，
            300：客户端存在文件，但是文件不完整，需要断点续传
            400：客户端存在文件，且文件完整，不需要下载了
            500: 客户端文件比服务器文件大，客户端文件错误，需要删除文件后，重新下载
        }
        """
        cmd_split = args[0].split()

        if len(cmd_split) == 2:
            src_filename = cmd_split[1]
            msg_dic = {
                "action": "get",
                "src_filename": src_filename
            }

            self.client.send(json.dumps(msg_dic).encode('utf-8'))
            file_total_size = int(self.client.recv(1024).decode())
            print('file_total_size', file_total_size)
            if file_total_size == -1:
                self.client.send(b'100')
                print('\033[1;31;1m 服务端文件不存在，无法下载\033[0m')
            else:
                des_filename = '%s/Data/%s' % (BASE_DIR, src_filename)
                if not os.path.isfile(des_filename):
                    self.client.send(b'200')
                    received_size = 0
                    self.cmd_get_get_data(des_filename, received_size, file_total_size)

                else:
                    received_size = os.stat(des_filename).st_size
                    if received_size < file_total_size:
                        """ 目标文件小于下载文件，进行断点续传 """
                        self.client.send(b'300')
                        print('\033[1;31;1m 文件已存在，但是不完整，需要断点续传\033[0m')
                        print('received_size:', received_size)
                        self.cmd_get_get_data(des_filename, received_size, file_total_size)

                    elif received_size == file_total_size:
                        """ 目标文件等于下载文件 """
                        self.client.send(b'400')
                        print('\033[1;31;1m 文件已存在，无需下载\033[0m')
                    else:
                        self.client.send(b'500')
                        print('\033[1;31;1m 客户端文件错误，请重新下载\033[0m')

        return None

    def cmd_get_get_data(self, des_filename, received_size, file_total_size):
        with open(des_filename, mode='ab') as f:
            while received_size < file_total_size:
                client_data = {
                    'file_total_size': file_total_size,
                    'client_data_size': received_size
                }
                self.client.send(json.dumps(client_data).encode('utf-8'))
                if file_total_size - received_size >= 1024:
                    size = 1024
                else:
                    size = file_total_size - received_size

                data = self.client.recv(size)
                received_size += len(data)
                f.write(data)
                f.flush()
                percent = received_size / file_total_size
                self.progress(percent)

            else:
                f.flush()
                client_data = {
                    'file_total_size': file_total_size,
                    'client_data_size': received_size
                }
                self.client.send(json.dumps(client_data).encode('utf-8'))
                print()
                print('\033[1;31;1m 文件下载完成，文件路径: %s\033[0m' % des_filename)

        return None

    def cmd_put(self, *args):
        """
        上传文件，支持断点续传
        :param args: put filename 上传文件的命令
        :return: {
            100：客户端文件不存在，命令错误
            200: 服务器端文件不存在，需要上传，
            300：服务器端存在文件，但是文件不完整，需要断点续传
            400：服务器端存在文件，且文件完整，不需要上传了
            500: 服务器端文件比服务器文件大，客户端文件错误，需要服务器端删除文件后，重新上传
        }
        """

        cmd_split = args[0].split()

        if len(cmd_split) == 2:
            src_filename = cmd_split[1]
            filename = '%s/Data/%s' % (BASE_DIR, src_filename)
            if os.path.isfile(filename):
                file_total_size = os.stat(filename).st_size
                msg_dic = {
                    "action": "put",
                    "src_filename": src_filename,
                    "size": file_total_size
                }

                self.client.send(json.dumps(msg_dic).encode('utf-8'))
                server_response = int(self.client.recv(1024).decode())
                print('server_response:', server_response)

                if server_response == 200:
                    self.cmd_put_put_data(file_total_size, filename)

                elif server_response == 300:  # 文件已存在，后续补充功能
                    print('\033[1;31;1m 文件已存在，但是不完整，需要断点续传\033[0m')
                    self.cmd_put_put_data(file_total_size, filename)

                elif server_response == 400:
                    print('\033[1;31;1m 文件已存在\033[0m')

                elif server_response == 500:
                    print('\033[1;31;1m 文件已存在服务器,但数据错误，请先删除服务器端文件\033[0m')

                else:
                    print('\033[1;31;1m 未知错误！\033[0m')

            else:
                """100: 客户端无此文件 """
                print('\033[1;31;1m %s 目录下不存在此文件，请确认后重新上传文件\033[0m' % filename)
        else:
            print('\033[1;31;1m 命令错误，请重新执行命令')

        return None

    def cmd_put_put_data(self, file_total_size, filename):
        upload_flag = True
        while upload_flag:
            self.client.send(b'200')
            server_data = self.client.recv(1024)
            server_data = json.loads(server_data)
            server_data_size = server_data['server_data_size']

            if server_data_size < file_total_size:
                with open(filename, mode='rb') as f:
                    f.seek(server_data_size, 0)
                    line = f.read(1024)
                    self.client.send(line)

            else:
                upload_flag = False

            percent = server_data_size / file_total_size
            self.progress(percent)

        return None


if __name__ == '__main__':
    # 创建类
    ftp = FTP_Client()

    # 初始化连接
    ftp.connect(settings.HOST_IP, settings.HOST_PORT)

    # 调用交互功能，执行操作
    ftp.interactive()
