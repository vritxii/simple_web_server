import socket
import time
import random
import re
import threading
import os
import json

res_root = "./HTML"
valid_ends = ['.py', '.txt', 'py3', '.java', '.jpg', '.mp3','.wav', '.ogg','.mp4', '.ico']
media_ends = ['.mp3', '.wav', '.mp4', '.jpg', '.ogg']
doc_ends = ['.py', '.txt', '.py3', '.java']

register_addr = ["127.0.0.1", 10087]

import json
class WebServer(object):
    def __init__(self, host_name, port):
        self.host_name = host_name
        self.port = port
        self.root_dir = "./HTML"
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(("127.0.0.1", self.port))
        self.server_socket.listen(128)

        self.heart_beat = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.heart_beat.bind(("127.0.0.1", self.port+1))
        self.online = False

        self.threads = []

    def run(self):
        '''
        每收到一个连接都会打开一个子线程把接收到的new_client_socket传给deal_request进行处理
        '''
        register_info = json.dumps([self.host_name, ["127.0.0.1", self.port]])
        self.heart_beat.sendto(register_info.encode(encoding='utf_8'), register_addr)
        self.t_heart_beat = threading.Thread(target=self.handle_heart_beat, args=())
        self.t_heart_beat.setDaemon(True)
        self.t_heart_beat.start()
        self.t_heart_beat.join(1)

        '''
        尝试几次向web服务器注册
        '''
        try_times = 5
        if not self.online:
            for i in range(try_times):
                self.heart_beat.sendto(self.host_name.encode(encoding='utf_8'), register_addr)
                time.sleep(0.5)
                if self.online:
                    break
        '''
        注册失败直接退出
        '''
        if not self.online:
            print("register failed")
            return

        print("register successful")

        #注册成功则开始监听资源请求
        while True:
            new_client_socket, new_client_socket_addr = self.server_socket.accept()
            print("get new_client_socket: "+json.dumps(new_client_socket_addr))
            t = threading.Thread(target=self.deal_request, args=([new_client_socket]))
            self.threads.append(t)
            t.setDaemon(True)
            t.start()

    def handle_heart_beat(self):
        '''
        监听web服务器发来的心跳检测，并将自己的自己的主机名返回给web服务器，
        如果收到收到的是注册成功响应，则不返回，将自己状态设为在线，并开始监听
        资源请求
        '''
        while True:
            response, server_check_addr = self.heart_beat.recvfrom(2048)
            if response.decode(encoding='utf_8') == self.host_name:
                self.online = True
                continue
            print("handle heart beat")
            self.heart_beat.sendto(self.host_name.encode(encoding='utf_8'), server_check_addr)


    def read_file(self, file_name, is_valid=True):
        '''
        读取文件文件内容，如果文件存在且是支持的文件格式，否则返回404响应
        '''
        file_name = res_root+file_name
        if os.path.exists(file_name) and is_valid:
            f = open(file_name, "rb")
            content = f.read()
            f.close()
            return content,1
        else:
            print("Can't open %s"%file_name)
            content = b"404 Not Found"
            cur_time = 'Current Time: %s' % time.ctime()
            content += b'\n<p>\n\t' + cur_time.encode() + b'\n</p>'
            return content,0


    def live_html(self, file_name, is_valid=True):
        '''
        根据文件后缀设置响应头的Content-Type以及Status Code
        '''
		
        print('live_html')
        content,ok = self.read_file(file_name, is_valid)
        if ok == 0:
            status = "404 Not Found"
        else:
            status = "200 OK"

        response_headers = [('Content-Type', 'text/html;charset=utf-8')]
        if file_name.endswith('.jpg'):
            response_headers = [('Content-Type', 'image/jpg')]
        if file_name.endswith('.mp4'):
            response_headers = [('Content-Type', 'video/mp4')]
        
        if file_name.endswith('.mp3'):
            response_headers = [('Content-Type', 'audio/mp3')]
        if file_name.endswith('.ogg'):
            response_headers = [('Content-Type', 'audio/ogg')]
        if file_name.endswith('.wav'):
            response_headers = [('Content-Type', 'audio/wav')]

        self.set_response_header(status, response_headers)
        return content

    def check_valid_end(self, ends, file_name):
        '''
        检查文件名类型是否在某一文件类型集合中
        '''
        if file_name.startswith("/media?"):
            return False
        print("check")
        for v_end in ends:
            if file_name.endswith(v_end):
                return True
        return False

    def deal_media(self, new_client_socket, file_name):
        '''
        处理media请求，并根据参数生成对应的html,支持文件格式为[mp3,wav,ogg,mp4]
        '''
        f_path = "/" + file_name.split("?")[1]
        print("deal_media")
        print("media: " + f_path)
        file_base = f_path.split(".")[0]
        f_end = f_path.split(".")[1]
        respond_header = ""
        respond_body = ""
        if not os.path.exists(res_root + f_path):
            respond_header = "HTTP/1.1 404 Not Found \r\n"
            respond_body = "404 Not Found"

        elif f_end == "mp4":
            respond_header = "HTTP/1.1 200 OK \r\n"
            f = open(res_root + "/video.html","r")
            respond_body = f.read()
            respond_body = respond_body.replace("{{video_file}}", file_base)
            f.close()
            
        elif f_end in ["mp3", "ogg", "wav"]:
            respond_header = "HTTP/1.1 200 OK \r\n"
            f = open(res_root + "/audio.html","r")
            respond_body = f.read()
            respond_body = respond_body.replace("{{audio_file}}", file_base)
            f.close()

        else:
            respond_header = "HTTP/1.1 200 OK \r\n"
            respond_body = "Unsupport format media,(only mp4,mp3,wav,ogg)"

        #print(respond_body)
        respond_header += "Content-Type: text/html; charset=utf-8\r\n"
        respond_header = respond_header + "\r\n"
        
        new_client_socket.send(respond_header.encode("utf-8") + respond_body.encode(encoding='utf_8'))
        new_client_socket.close()


    def deal_request(self, new_client_socket):
        '''
        响应请求，处理请求头消息并返回对应的文件内容
        '''
        recv_data = new_client_socket.recv(1024)
        recv_data = recv_data.decode("utf-8")
        print("deal request")
        #请求数据为空不处理直接返回
        if not recv_data:
            return

        recv_data_list = recv_data.splitlines()
        the_request_header = recv_data_list[0]
        file_name = self.get_file_name(the_request_header)
        print("请求的文件名为%s"%(file_name))
        is_valid = self.check_valid_end(valid_ends, file_name)
        print(is_valid)
        if file_name.endswith(".html") or file_name.endswith(".htm"):
            print("1")
            self.send_html(file_name, new_client_socket)
            new_client_socket.close()

        elif is_valid:
            print("2")
            dynamic_content = self.live_html(file_name)
            new_client_socket.send(self.response_header_info + dynamic_content)
            new_client_socket.close()

        elif file_name.startswith("/media?"):
            print("3")
            self.deal_media(new_client_socket, file_name)
        
        else:
            print("4")
            dynamic_content = self.live_html(file_name, is_valid)
            new_client_socket.send(self.response_header_info + dynamic_content)
            new_client_socket.close()


    def get_file_name(self, request_header):
        '''
        从请求头获取请求文件名
        '''
        file_name = request_header.split(" ")[1]
        if file_name == "/":
            file_name = "/index.html"
        return file_name

    def send_html(self, file_name, new_client_socket):
        '''
        请求类型为html或htm类型时直接读取对应文件内容返回，没有该文件返回404
        '''
        try:
            f = open(self.root_dir+file_name, "rb")
        except Exception:
            respond_header = "HTTP/1.1 404 Not Found \r\n"
            respond_body = "404 Not Found"
        else:
            respond_header = "HTTP/1.1 200 OK \r\n"
            respond_body = f.read()
        
        respond_header += "Content-Type: text/html; charset=utf-8\r\n"
        respond_header = respond_header + "\r\n"
        
        new_client_socket.send(respond_header.encode("utf-8"))
        new_client_socket.send(respond_body)

    def set_response_header(self, status, headers):
        '''
        设置响应头
        '''
        respond_header = "HTTP/1.1 " + status + " \r\n"
        respond_header += "%s:%s\r\n"%(headers[0][0], headers[0][1])
        respond_header += "\r\n"
        self.response_header_info =  respond_header.encode("utf-8")

import sys
if __name__ == "__main__":
    print(len(sys.argv))
    if len(sys.argv) <= 3:
        print("python3 webserver.py host_name port server_port")
        sys.exit(0)
    
    h_name = sys.argv[1]
    port = int(sys.argv[2])
    register_addr[1] = int(sys.argv[3])
    register_addr = tuple(register_addr)
    web_server = WebServer(h_name, port)
    print("web address 127.0.0.1:%d"%(port))
    web_server.run()
