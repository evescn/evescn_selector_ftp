# evescn_hosts_management_tools

> Python 使用的Python 3.6版本

> Server端代码使用：selectors

> Client端代码使用：socket

## FTP程序

```
服务要求：开发一个支持多用户在线的FTP程序

1、用户加密认证
2、允许同时多用户登录
3、每个用户有自己的家目录 ，且只能访问自己的家目录
4、对用户进行磁盘配额，每个用户的可用空间不同
5、允许用户在ftp server上随意切换目录
6、允许用户查看当前目录下文件
7、允许上传和下载文件，保证文件一致性
8、文件传输过程中显示进度条
9、附加功能：支持文件的断点续传
```

- 未实现功能

```
1、未实现只能访问自己的家目录
2、未实现用户磁盘配额
3、未实现上传下载文件一致性
```

- 不足

```
1. 用户的账户创建功能没有，只能参考Ftp_Server端，conf/gmkk.json文件内容，就行修改后创建用户
2. (客户端和服务器端同时运行在1台主机上测试)客户端下载文件速度，大于客户端上传文件速度，不知道是否是Server端使用seletors，而客户端使用socket导致，后续会写1个 seletors 的客户端代码
3. Server端代码进行了一些异常捕捉，优化了代码的健壮性，Client端并没有对异常进行捕捉
```

## 代码目录结构

```
+---Ftp_Client
|   |   ftp_client.py 	# 客户端程序
|   |   settings.py 	# 客户端配置信息文件，定义了连接端口IP等
|   |
|   +---Data
|       1	# 客户端下载文件存放位置，客户端上传文件存放的位置
|
\---Ftp_Server 	# FTP服务端程序
    +---bin		# 执行文件目录
    |   start.py  	# 程序入口
    |   __init__.py
    |
    +---conf	# 主要程序逻辑都在这个目录里
    |   gmkk.json		# ftp账户文件，报保存了用户的账户密码，家目录，磁盘配额等
    |   settings.py 	# 配置文件，监听的端口、IP，保存了日志等定义
    |   __init__.py
    |
    +---core 	# 主要程序逻辑都在这个目录里
    |   logger.py 	# 日志记录模块
    |   main.py		# 主要逻辑交互程序
    |   __init__.py
    |
    \---logs # 日志记录
        access.log # 日志
        transactions.log # 日志
        __init__.py
```

## 程序流程图

![](FTP程序.png)

##  程序启动

> 使用的依赖为：os, sys, json, selectors, socket, hashlib, logging

```
pip3 install json, selectors, socket, hashlib, logging
```

## 服务器端程序启动

```
cd Ftp_Server
python3 bin/start
```

## 执行程序(启动客户端程序)

```
cd Ftp_Client
python3 ftp_client.py
```

### 运行程序前 客户端Data目录 和服务器 /opt/ftp/gmkk/ 目录文件
> /opt/ftp/gmkk/  目录是 Ftp_Server/conf/gmkk.json中定义的用户服务端的家目录

- /opt/ftp/gmkk/ 目录文件情况

```
[root@192-168-3-168 gmkk]# pwd
/opt/ftp/gmkk
[root@192-168-3-168 gmkk]# ll
total 10569080
-rw-r--r--. 1 root root           6 Dec  1 16:15 1
-rw-r--r--. 1 root root         501 Dec  3 11:34 fstab
-rw-r--r--. 1 root root 10737418240 Dec  1 17:08 test1
-rw-r--r--. 1 root root    40299941 Dec  2 18:22 test.img.2
-rw-r--r--. 1 root root    45008228 Dec  2 18:25 test.img.3
```

- Client端目录情况


```
[root@192-168-3-168 Data]# pwd
/home/Ftp_Client/Data
[root@192-168-3-168 Data]# ll
total 39364
-rw-r--r--. 1 root root      501 Dec  3 11:34 fstab
-rw-r--r--. 1 root root 40299941 Dec  2 15:58 test.img.2
```

- 运行程序

```
 欢迎来到 FTP 系统 
username: gmkk
password: 123
user_password: 202cb962ac59075b964b07152d234b70
登陆信息： 登陆系统成功

## ls 功能
>> ls  					
cmd_total_size: 204
total 11G
-rw-r--r--. 1 root root   6 Dec  1 16:15 1
-rw-r--r--. 1 root root 10G Dec  1 17:08 test1
-rw-r--r--. 1 root root 39M Dec  2 18:22 test.img.2
-rw-r--r--. 1 root root 43M Dec  2 18:25 test.img.3

>> dir
cmd_total_size: 204
total 11G
-rw-r--r--. 1 root root   6 Dec  1 16:15 1
-rw-r--r--. 1 root root 10G Dec  1 17:08 test1
-rw-r--r--. 1 root root 39M Dec  2 18:22 test.img.2
-rw-r--r--. 1 root root 43M Dec  2 18:25 test.img.3

## pwd 功能
>> pwd
cmd_total_size: 13
/opt/ftp/gmkk

## get 功能
>> get 1
file_total_size 6
last receive: 6
[##################################################] 100%文件下载完成，文件路径； /home/Ftp_Client/Data/1
>> get 2
file_total_size -1
服务端文件不存在，无法下载
>> get 1
file_total_size 6
文件已存在，无需下载

## put 功能
>> put fstab.5
/home/Ftp_Client/Data/fstab.5 目录下不存在此文件，请确认后重新上传文件
>> put fstab
server_response: 200
[##################################################] 100%
>> put 1
server_response: 400
文件已存在
```

- 文件断点下载功能演示

```
 欢迎来到 FTP 系统 
username: gmkk
password: 123
user_password: 202cb962ac59075b964b07152d234b70
登陆信息： 登陆系统成功
>> get test.img.3
file_total_size 45008228
[######                                            ] 13%

##  Ctrl + C 终止程序
^C 

Traceback (most recent call last):
  File "ftp_client.py", line 376, in <module>
    ftp.interactive()
  File "ftp_client.py", line 110, in interactive
    func(cmd)
  File "ftp_client.py", line 238, in cmd_get
    self.cmd_get_get_data(des_filename, received_size, file_total_size)
  File "ftp_client.py", line 273, in cmd_get_get_data
    data = self.client.recv(size)
KeyboardInterrupt

# python3 ftp_client.py 
 欢迎来到 FTP 系统 
username: gmkk
password: 123
user_password: 202cb962ac59075b964b07152d234b70
登陆信息： 登陆系统成功
>> get test.img.3
file_total_size 45008228
文件已存在，但是不完整，需要断点续传
received_size: 5912576
[################################################# ] 99%
last receive: 356
[##################################################] 100%
文件下载完成，文件路径； /home/Ftp_Client/Data/test.img.3

```
