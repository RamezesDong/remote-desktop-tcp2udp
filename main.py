import tkinter
import tkinter.messagebox
import struct
import socket
import numpy as np
from PIL import Image, ImageTk
import threading
import re
from cv2 import cv2
import time
import sys
import platform

root = tkinter.Tk()

# 画面周期
IDLE = 0.05
# 放缩大小
scale = 1
# 原传输画面尺寸
fixw, fixh = 0, 0
# 放缩标志
wscale = False
# 屏幕显示画布
showcan = None
# socket缓冲区大小
bufsize = 10240
# 线程
th = None
# socket
soc = None
# socks5
socks5 = None
# 平台
PLAT = b''

if sys.platform == "win32":
    PLAT = b'win'
elif sys.platform == "darwin":
    PLAT = b'osx'
elif platform.system() == "Linux":
    PLAT = b'x11'
#!!!! 初始化socket
def SetSocket():
    global soc, host_en

    def byipv4(ip, port):
        return struct.pack(">BBBBBBBBH", 5, 1, 0, 1, ip[0], ip[1], ip[2], ip[3], port)

    def byhost(host, port):
        d = struct.pack(">BBBB", 5, 1, 0, 3)
        blen = len(host)
        d += struct.pack(">B", blen)
        d += host.encode()
        d += struct.pack(">H", port)
        return d
    host = host_en.get() # 得到host_en 内的内容，（就是输入框内的内容）
    if host is None:
        tkinter.messagebox.showinfo('提示', 'Host设置错误！')
        return
    hs = host.split(":")
    if len(hs) != 2:
        tkinter.messagebox.showinfo('提示', 'Host设置错误！')
        return
    if socks5 is not None:
        ss = socks5.split(":")
        if len(ss) != 2:
            tkinter.messagebox.showinfo('提示', '代理设置错误！')
            return
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #soc.connect((ss[0], int(ss[1])))
        conserver = (ss[0],int(ss[1]))    #the controled host
        soc.sendto(struct.pack(">BB", 5, 0),conserver)
        recv,addr = soc.recvfrom(2)
        if recv[1] != 0:
            tkinter.messagebox.showinfo('提示', '代理回应错误！')
            return
        if re.match(r'^\d+?\.\d+?\.\d+?\.\d+?:\d+$', host) is None:
            # host 域名访问
            hand = byhost(hs[0], int(hs[1]))
            soc.sendto(hand,conserver)
        else:
            # host ip访问
            ip = [int(i) for i in hs[0].split(".")]
            port = int(hs[1])
            hand = byipv4(ip, port)
            soc.sendto(hand,conserver)
        # 代理回应
        rcv = b''
        while len(rcv) != 10:
            data, addr= soc.recvfrom(10 - len(rcv))
            rcv += data
        if rcv[1] != 0:
            tkinter.messagebox.showinfo('提示', '代理回应错误！')
            return
    else:
        soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #soc.connect((hs[0], int(hs[1])))

# 通过移动滑条设置窗口的Scale
def SetScale(x):
    global scale, wscale
    scale = float(x) / 100
    wscale = True

# 设置代理相关的function
def ShowProxy():
    # 显示代理设置
    global root

    def set_s5_addr():
        global socks5
        socks5 = s5_en.get()
        if socks5 == "":
            socks5 = None
        pr.destroy()
    pr = tkinter.Toplevel(root)
    s5v = tkinter.StringVar()
    s5_lab = tkinter.Label(pr, text="Socks5 Host:")
    s5_en = tkinter.Entry(pr, show=None, font=('Arial', 14), textvariable=s5v)
    s5_btn = tkinter.Button(pr, text="OK", command=set_s5_addr)
    s5_lab.grid(row=0, column=0, padx=10, pady=10, ipadx=0, ipady=0)
    s5_en.grid(row=0, column=1, padx=10, pady=10, ipadx=40, ipady=0)
    s5_btn.grid(row=1, column=0, padx=10, pady=10, ipadx=30, ipady=0)
    s5v.set("192.168.187.137")


def ShowScreen():
    global showcan, root, soc, th, wscale
    if showcan is None:
        wscale = True
        showcan = tkinter.Toplevel(root)
        th = threading.Thread(target=run)
        th.start()
    else:
        #soc.close() upd without close()
        showcan.destroy()

# gui 的排版
val = tkinter.StringVar()
host_lab = tkinter.Label(root, text="Host:") # host:...
host_en = tkinter.Entry(root, show=None, font=('Arial', 14), textvariable=val)
sca_lab = tkinter.Label(root, text="Scale:") # scale的按钮
sca = tkinter.Scale(root, from_=10, to=100, orient=tkinter.HORIZONTAL, length=100,
                    showvalue=100, resolution=0.1, tickinterval=50, command=SetScale)
                    # 设置窗口scale
proxy_btn = tkinter.Button(root, text="Proxy", command=ShowProxy) # 代理的按钮
show_btn = tkinter.Button(root, text="Show", command=ShowScreen)  # show 的按钮配置

#按钮设置位置
host_lab.grid(row=0, column=0, padx=10, pady=10, ipadx=0, ipady=0)
host_en.grid(row=0, column=1, padx=0, pady=0, ipadx=40, ipady=0) # 输入host数字的框
sca_lab.grid(row=1, column=0, padx=10, pady=10, ipadx=0, ipady=0)
sca.grid(row=1, column=1, padx=0, pady=0, ipadx=100, ipady=0)
proxy_btn.grid(row=2, column=0, padx=0, pady=10, ipadx=30, ipady=0)
show_btn.grid(row=2, column=1, padx=0, pady=10, ipadx=30, ipady=0)
sca.set(100)
val.set('127.0.0.1:800')

last_send = time.time()


def BindEvents(canvas):
    global soc, scale
    conserver = ('127.0.0.1', 800)
    '''
    处理事件
    '''
    def EventDo(data):
        soc.sendto(data,conserver)
    # 鼠标左键

    def LeftDown(e):
        return EventDo(struct.pack('>BBHH', 1, 100, int(e.x/scale), int(e.y/scale)))

    def LeftUp(e):
        return EventDo(struct.pack('>BBHH', 1, 117, int(e.x/scale), int(e.y/scale)))
    canvas.bind(sequence="<1>", func=LeftDown)
    canvas.bind(sequence="<ButtonRelease-1>", func=LeftUp)

    # 鼠标右键
    def RightDown(e):
        return EventDo(struct.pack('>BBHH', 3, 100, int(e.x/scale), int(e.y/scale)))

    def RightUp(e):
        return EventDo(struct.pack('>BBHH', 3, 117, int(e.x/scale), int(e.y/scale)))
    canvas.bind(sequence="<3>", func=RightDown)
    canvas.bind(sequence="<ButtonRelease-3>", func=RightUp)

    # 鼠标滚轮
    if PLAT == b'win' or PLAT == 'osx':
        # windows/mac
        def Wheel(e):
            if e.delta < 0:
                return EventDo(struct.pack('>BBHH', 2, 0, int(e.x/scale), int(e.y/scale)))
            else:
                return EventDo(struct.pack('>BBHH', 2, 1, int(e.x/scale), int(e.y/scale)))
        canvas.bind(sequence="<MouseWheel>", func=Wheel)
    elif PLAT == b'x11':
        def WheelDown(e):
            return EventDo(struct.pack('>BBHH', 2, 0, int(e.x/scale), int(e.y/scale)))
        def WheelUp(e):
            return EventDo(struct.pack('>BBHH', 2, 1, int(e.x/scale), int(e.y/scale)))
        canvas.bind(sequence="<Button-4>", func=WheelUp)
        canvas.bind(sequence="<Button-5>", func=WheelDown)

    # 鼠标滑动
    # 100ms发送一次
    def Move(e):
        global last_send
        cu = time.time()
        if cu - last_send > IDLE:
            last_send = cu
            sx, sy = int(e.x/scale), int(e.y/scale)
            return EventDo(struct.pack('>BBHH', 4, 0, sx, sy))
    canvas.bind(sequence="<Motion>", func=Move)

    # 键盘
    def KeyDown(e):
        return EventDo(struct.pack('>BBHH', e.keycode, 100, int(e.x/scale), int(e.y/scale)))

    def KeyUp(e):
        return EventDo(struct.pack('>BBHH', e.keycode, 117, int(e.x/scale), int(e.y/scale)))
    canvas.bind(sequence="<KeyPress>", func=KeyDown)
    canvas.bind(sequence="<KeyRelease>", func=KeyUp)

# if click the "Show", the "run" will run
def run():
    global wscale, fixh, fixw, soc, showcan, conserver
    SetSocket()
    conserver = ('127.0.0.1', 800)
    # 发送平台信息
    soc.sendto(PLAT,conserver)
    lenb,addr = soc.recvfrom(5)
    imtype, le = struct.unpack(">BI", lenb)
    imb = b''
    while le > bufsize:
        t,addr = soc.recvfrom(bufsize)
        imb += t
        le -= len(t)
    while le > 0:
        t, addr = soc.recvfrom(le)
        imb += t
        le -= len(t)
    data = np.frombuffer(imb, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    h, w, _ = img.shape
    fixh, fixw = h, w
    imsh = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)
    imi = Image.fromarray(imsh)
    imgTK = ImageTk.PhotoImage(image=imi)
    cv = tkinter.Canvas(showcan, width=w, height=h, bg="white")
    cv.focus_set()
    BindEvents(cv)
    cv.pack()
    cv.create_image(0, 0, anchor=tkinter.NW, image=imgTK)
    h = int(h * scale)
    w = int(w * scale)
    while True:
        if wscale:
            h = int(fixh * scale)
            w = int(fixw * scale)
            cv.config(width=w, height=h)
            wscale = False
        try:
            lenb,addr = soc.recvfrom(5)
            imtype, le = struct.unpack(">BI", lenb)
            imb = b''
            while le > bufsize:
                t, addr = soc.recvfrom(bufsize)
                imb += t
                le -= len(t)
            while le > 0:
                t,addr = soc.recvfrom(le)
                imb += t
                le -= len(t)
            data = np.frombuffer(imb, dtype=np.uint8)
            ims = cv2.imdecode(data, cv2.IMREAD_COLOR)
            if imtype == 1:
                # 全传
                img = ims
            else:
                # 差异传
                img = img ^ ims
            imt = cv2.resize(img, (w, h))
            imsh = cv2.cvtColor(imt, cv2.COLOR_RGB2RGBA)
            imi = Image.fromarray(imsh)
            imgTK.paste(imi)
        except:
            showcan = None
            ShowScreen()
            return


root.mainloop()