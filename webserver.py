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

class filehost:
    '''
    文件服务器管理类，实现了对文件服务器的心跳检测，对所有在线的文件服务器进行在线状态检测
    当文件服务器有三次不响应检测时将该文件服务器从记录中删除，收到响应会把之前的缺失响应计数会
    清空
    '''
    def __init__(self, web_name, port):
        self.host_num = 0
        self.hosts = {}
        self.host_name = web_name
        self.port = port
        self.beat_heart = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.beat_heart.bind(("127.0.0.1", self.port))
        self.hosts_state = {}
        self.rlock = threading.RLock()

    def start(self):
        '''
        开始发送心跳检测包，并监听响应
        '''
        self.t_check = threading.Thread(target=self.check_state, args=())
        self.t_check.setDaemon(True)
        self.t_check.start()

        self.t_handle = threading.Thread(target=self.hand_response, args=())
        self.t_handle.setDaemon(True)
        self.t_handle.start()

    def get_host_num(self):
        '''
        返回已连接文件服务器个数
        '''
        self.rlock.acquire()
        num = self.host_num
        self.rlock.release()
        return num

    def register(self, host):
        '''
        注册文件服务器，host为[host_name, (host_ip, host_port)]
        '''
        if host[0] in self.hosts.keys():
            return False

        print(host)
        self.rlock.acquire()
        self.hosts[host[0]]=host[1]
        self.host_num += 1
        self.hosts_state[host[0]] = 0
        self.rlock.release()
        print(self.hosts.keys())
        return True

    def url(self, host_name):
        '''
        根据主机名生成http链接
        '''
        self.rlock.acquire()
        host_url = "http://" + str(self.hosts[host_name][0]) + ":" + str(self.hosts[host_name][1])
        self.rlock.release()
        #print("select url")
        #print(host_url)
        return host_url

    def set_host_addr(self, html):
        '''
        设置html里的资源路径，即用生成url替换{{file_host}}字符串
        '''
        url = self.rand_select()
        print("get url: "+url)
        html = html.decode(encoding='utf_8')
        #print(html)
        html = html.replace("{{file_host}}", url)
        #print("***********")
        #print(html)
        return html.encode(encoding='utf_8')
    
    def rand_select(self):
        '''
        随机选择一个文件服务器并返回生成的http链接
        '''
        k = random.randint(1,self.host_num)
        i = 1
        #print("k = ", k)
        #print("len(keys): ", len(self.hosts.keys()))
        for key in self.hosts.keys():
            #print(i, key)
            if i == k:
                #print(i, key)
                return self.url(key)
            i+=1
        return self.url(self.host_name)

    def check_state(self):
        '''
        每隔一秒向所有文件服务器发送一次心跳检测包
        '''
        while True:
            #self.rlock.acquire()
            hosts = self.hosts
            #self.rlock.release()
            print("start heart beat")
            for k in hosts.keys():
                if k == self.host_name:
                    continue

                host_addr = hosts[k]
                print("send heart beat to " + k)
                print(host_addr)
                self.beat_heart.sendto(b"check_state", (host_addr[0], host_addr[1]+1))
                time.sleep(0.1)
                self.rlock.acquire()
                self.hosts_state[k] += 1
                self.rlock.release()
                print(k + " state = ", self.hosts_state[k])
                if self.hosts_state[k] >= 3:
                    print(k + " is outline")
                    self.rlock.acquire()
                    del self.hosts[k]
                    del self.hosts_state[k]
                    self.host_num -= 1
                    self.rlock.release()
                    break

            time.sleep(1)
            
    
    def hand_response(self):
        '''
        监听心跳检测包的响应，如果收到响应（文件服务器主机名),将该主机的缺失心跳检测次数清空
        '''
        while True:
            print("handle response")
            host_name, host_addr = self.beat_heart.recvfrom(2048)
            host_name = host_name.decode()
            self.rlock.acquire()
            self.hosts_state[host_name] = -1
            print(host_name + " state = ", self.hosts_state[host_name])
            self.rlock.release()
            print("get response from " + host_name)
            print(host_addr)

import json
class WebServer(object):
    def __init__(self, host_name, port):
        self.port = port
        self.host_name = host_name
        self.root_dir = "./HTML"
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(("127.0.0.1", self.port))
        self.server_socket.listen(128)

        self.register_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.register_socket.bind(("127.0.0.1", self.port+1))

        self.f_hosts = filehost(self.host_name, self.port+2)
        self.f_hosts.register((self.host_name, ("127.0.0.1", self.port)))

        self.threads = []
        self.t_register = None

    def run(self):
        '''
，每收到一个连接都会打开一个子线程把接收到的new_client_socket传给deal_request进行处理
        '''
        self.f_hosts.start()
        self.t_register = threading.Thread(target=self.handle_register, args=())
        self.t_register.setDaemon(True)
        self.t_register.start()

        while True:
            new_client_socket, new_client_socket_addr = self.server_socket.accept()
            print("get new_client_socket: "+json.dumps(new_client_socket_addr))
            t = threading.Thread(target=self.deal_request, args=([new_client_socket]))
            self.threads.append(t)
            t.setDaemon(True)
            t.start()
    
    def handle_register(self):
        '''
        监听文件服务器发来的注册请求
        '''
        while True:
            f_host_info, f_host_addr = self.register_socket.recvfrom(2048)
            f_host_info = json.loads(f_host_info.decode(encoding='utf_8'))
            print("new file host:" + f_host_info[0])
            register_status = self.f_hosts.register((f_host_info[0], tuple(f_host_info[1])))
            print(f_host_info)
            if register_status:
                self.register_socket.sendto(f_host_info[0].encode('utf_8'), f_host_addr)

            '''
            print("get new_client_socket: "+json.dumps(new_client_socket_addr))
            t = threading.Thread(target=self.deal_request, args=([new_client_socket]))
            self.threads.append(t)
            t.setDaemon(True)
            t.start()
            '''


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
        respond_header = respond_header.encode(encoding='utf_8')
        respond_body = self.f_hosts.set_host_addr(respond_body.encode(encoding='utf_8'))
        #print(respond_body.decode(encoding='utf_8'))
        new_client_socket.send(respond_header + respond_body)
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
        #print(is_valid)
        if file_name.endswith(".html") or file_name.endswith(".htm"):
            #print("1")
            self.send_html(file_name, new_client_socket)
            new_client_socket.close()

        elif is_valid:
            #print("2")
            dynamic_content = self.live_html(file_name)
            new_client_socket.send(self.response_header_info + dynamic_content)
            new_client_socket.close()

        elif file_name.startswith("/media?"):
            #print("3")
            self.deal_media(new_client_socket, file_name)
        
        else:
            #print("4")
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

        respond_body = self.f_hosts.set_host_addr(respond_body)
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
    if len(sys.argv) <= 2:
        print("python3 webserver.py host_name port")
        sys.exit(0)

    h_name = sys.argv[1]
    port = int(sys.argv[2])
    web_server = WebServer(h_name, port)
    print("web address 127.0.0.1:%d"%(port))
    web_server.run()