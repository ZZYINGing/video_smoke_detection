'''
CS512 Project
Smoke detection
Su Feng
Jingcheng Deng
'''

import cv2
import numpy as np
import math
import os
import sys
import skvideo
from guidedfilter import guided_filter
import time


imgf = "data/smk3.jpg"
m1 = "test/frame10.jpg"
m2 = "test/frame15.jpg"
imgsize = 500
MHI_DURATION = 20
DEFAULT_THRESHOLD = 30
MAX_TIME_DELTA = 3
MIN_TIME_DELTA = 2
colorth = 85
debug = False

class Node(object):
    def __init__(self, x, y, key):
        self.x = x
        self.y = y
        self.key = key

class Mhi:
    def __init__(self, h, w):
        self.h = h
        self.w = w
        self.timestamp = 0
        self.motion_history = np.zeros((h, w), np.float32)
        self.lastimg = np.zeros((h, w), np.float32)
    def update(mhi, img):
        img = cv2.resize(img,(mhi.w,mhi.h))
        if mhi.timestamp == 0:
            mhi.lastimg = img
            mhi.timestamp += 1
            return mhi.timestamp, np.uint8(mhi.motion_history)
        else:
            gry = motion(mhi.lastimg, img)
            et, motion_mask = cv2.threshold(gry, DEFAULT_THRESHOLD, 1, cv2.THRESH_BINARY)
            mhi.timestamp += 1
            mhi.lastimg = img
            cv2.motempl.updateMotionHistory(motion_mask, mhi.motion_history, mhi.timestamp, MHI_DURATION)
            vis = np.uint8(np.clip((mhi.motion_history-(mhi.timestamp-MHI_DURATION)) / MHI_DURATION, 0, 1)*255)
            return mhi.timestamp, vis


def svimg(img):
    cv2.imwrite('out.jpg',img)

def resizeimge(img, max):
    h = img.shape[0]
    w = img.shape[1]
    if h > max or w > max:
        scale = min(float(max)/float(h),float(max)/float(w))
        return cv2.resize(img,(int(w*scale),int(h*scale)))
    return img

def grey(img):
    global imgsize
    img = resizeimge(img, imgsize)
    if(len(img.shape)) > 2:
        return cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    return img

def motion(img1, img2):
    img1 = grey(img1)
    img2 = grey(img2)
    frameDelta = cv2.absdiff(img1, img2)
    return frameDelta

def motiondp(img1, img2):
    img1 = getDP(img1)
    img2 = getDP(img2)
    frameDelta = cv2.absdiff(img1, img2)
    return frameDelta

def colorAnalysis(img, alpha):
    img = resizeimge(img, imgsize)
    img = cv2.GaussianBlur(img, (5, 5), 5)
    h, w, d = img.shape
    red = img[:, :, 0]
    green = img[:, :, 1]
    blue = img[:, :, 2]
    gimg = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    for i in range(h):
        for j in range(w):
            if abs(int(red[i][j])-int(green[i][j])) < alpha and abs(int(red[i][j])-int(blue[i][j])) < alpha and abs(int(green[i][j])-int(blue[i][j])) < alpha and (int(red[i][j])+int(green[i][j])+int(blue[i][j]))/3 > 100:
                gimg[i][j] = 255
            else:
                gimg[i][j] = 0
    return gimg

#def motionloop():
#    im1 = cv2.imread("test/frame180.jpg")
#    im1 = colorAnalysis(im1, colorth)
#    h, w = im1.shape
#    timestamp = 0
#    motion_history = np.zeros((h, w), np.float32)
#    for i in range(180, 660, 10):
#        im1 = cv2.imread("test/frame"+str(i)+".jpg")
#        im2 = cv2.imread("test/frame"+str(i+10)+".jpg")
#        grey = motion(im1, im2,i)
#        et, motion_mask = cv2.threshold(grey, DEFAULT_THRESHOLD, 1, cv2.THRESH_BINARY)
#        timestamp += 1
#        cv2.motempl.updateMotionHistory(motion_mask, motion_history, timestamp, MHI_DURATION)
#        mg_mask, mg_orient = cv2.motempl.calcMotionGradient( motion_history, MAX_TIME_DELTA, MIN_TIME_DELTA, apertureSize=5)
#        seg_mask, seg_bounds = cv2.motempl.segmentMotion(motion_history, timestamp, MAX_TIME_DELTA)
#        vis = np.uint8(np.clip((motion_history-(timestamp-MHI_DURATION)) / MHI_DURATION, 0, 1)*255)
#        cv2.imshow('motempl', vis)
#        if k == 27:
#            cv2.destroyAllWindows()
#            exit()

def mhi(fn, st, n, intv):
    im1 = cv2.imread(fn + "/frame" +str(st)+ ".jpg")
    im1 = grey(im1)
    h, w = im1.shape
    timestamp = 0
    motion_history = np.zeros((h, w), np.float32)
    for i in range(st, st+n*intv+1, intv):
        im1 = cv2.imread(fn + "/frame"+str(st)+".jpg")
        im2 = cv2.imread(fn + "/frame"+str(i+intv)+".jpg")
        gry = motion(im1, im2)
        et, motion_mask = cv2.threshold(gry, DEFAULT_THRESHOLD, 1, cv2.THRESH_BINARY)
        timestamp += 1
        cv2.motempl.updateMotionHistory(motion_mask, motion_history, timestamp, MHI_DURATION)
        mg_mask, mg_orient = cv2.motempl.calcMotionGradient( motion_history, MAX_TIME_DELTA, MIN_TIME_DELTA, apertureSize=5)
        seg_mask, seg_bounds = cv2.motempl.segmentMotion(motion_history, timestamp, MAX_TIME_DELTA)
        vis = np.uint8(np.clip((motion_history-(timestamp-MHI_DURATION)) / MHI_DURATION, 0, 1)*255)
    return vis



##########################################
# Darken channel helper function
# input: image, blocksize
# return: dark Channel
##########################################

def getDarkChannel(img, blocksize):
    b, g, r = cv2.split(img)
    minRBG = cv2.min(cv2.min(r, g), b)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (blocksize, blocksize))
    darkChannel = cv2.erode(minRBG, kernel)
    return darkChannel

##########################################
# Atmospheric Light helper function
# input: image, dark channel
# return: A
##########################################

def getAtomsLight(img, darkChannel):
    [h, w] = darkChannel.shape[:2]
    imgSize = h * w
    list = []
    A = 0
    for i in range(0, h):
        for j in range (0, w):
            item = Node(i, j, darkChannel[i, j])
            list.append(item)
    list.sort(key=lambda node: node.key, reverse=True)

    for i in range(0, int(imgSize * 0.1)):
        for j in range(0, 3):
            if img[list[i].x, list[i].y, j] < A:
                continue
            elif img[list[i].x, list[i].y, j] == A:
                continue
            elif img[list[i].x, list[i].y, j] > A:
                A = img[list[i].x, list[i].y, j]

    pixl = int(max(math.floor(imgSize/1000),1))
    darkReshape = darkChannel.reshape(imgSize, 1)
    imageReshape = img.reshape(imgSize, 3)
    I = darkReshape.argsort()
    I = I[imgSize-pixl::]

    at = np.zeros([1, 3])
    for i in range(1, pixl):
        at = at +imageReshape[I[i]]
    A = at/pixl
    return A

##########################################
# Transmission helper function
# input: image, dark channel
# return: A
##########################################

def transmission(img, A, blocksize, bol):
    omega = 0.95
    imageGray = np.empty(img.shape, img.dtype)
    # imageGray = np.min(img, axis=2)
    # print(A)
    for i in range(3):
        imageGray[:, :, i] = img[:, :, i]/A[0, i]
    #print(imageGray)
    #print(A)
    # print(getDarkChannel(imageGray, blocksize))
    t = 1 - omega * getDarkChannel(imageGray, blocksize)
    # print(t)
    t[t<0.1]= 0.1

    if bol == True:
        normI = (img - img.min()) / (img.max() - img.min())
        t = guided_filter(normI, t, 40, 0.0001)
    #print(t)
    return t

def getDP(image, bol):
    image = resizeimge(image, imgsize)
    I = image.astype('float64') / 255
    darkChannel = getDarkChannel(I, 15)
    A = getAtomsLight(I, darkChannel)
    t = transmission(I, A, 15, bol)
    #print('Done!')
    
    h, w, d = image.shape
    gimg = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    for i in range(h):
        for j in range(w):
            if t[i][j] < 0.4:
                gimg[i][j] = 255
            else:
                gimg[i][j] = 0
    return gimg
#print(t.shape)
#print(image.shape)
#cv2.imshow('DP', gimg)

def stack(img, img2, img3):
    out = img.copy()
    h,w = img.shape
    count = 0
    for i in range(h):
        for j in range(w):
            if img[i][j] > 75 and img2[i][j] > 1 and img3[i][j] > 75:
                out[i][j] = 255
                count += 1
            else:
                out[i][j] = 0
    return out, count

# input: original image,
def drawmask(img, mask, n=3):
    out = img.copy()
    overlay = img.copy()
    h,w = mask.shape
    for i in range(2,h-2,2*n):
        for j in range(2,w-2,2*n):
            if mask[i][j] == 255:
                cv2.rectangle(overlay, (j-n, i-n), (j+n, i+n),(0, 0, 255), -1)
    cv2.addWeighted(overlay, 0.5, out, 0.5,0, out)
    return out

def productVideo(bol, path):
    try:
        video_src = path
    except IndexError:
        print('Video Pass Error')
    cap = cv2.VideoCapture(video_src)
    ret, frame = cap.read()
    h, w, d= resizeimge(frame, imgsize).shape
    mhi = Mhi(h, w)
    frame_count = 1
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    out = cv2.VideoWriter('output.mp4', fourcc, 15.0, (w, h), True)
    if debug == True:
        out1 = cv2.VideoWriter('ColorAnalysis.mp4', fourcc, 15.0, (w, h), True)
        out2 = cv2.VideoWriter('MHI.mp4', fourcc, 15.0, (w, h), True)
        out3 = cv2.VideoWriter('DarkChannel.mp4', fourcc, 15.0, (w, h), True)
    while True:
        ret, frame = cap.read()

        if frame is None:
            print("Video reach end.")
            break
        frame = resizeimge(frame, imgsize)
        frame_count += 1
        if frame_count == 2 or frame_count == 3 or frame_count == 4:
            continue
        # frame = getDP(frame)
        # frame_width = int(frame.get(3))
        # frame_height = int(frame.get(4))
        img1 = colorAnalysis(frame, colorth)
        t, img2 = mhi.update(frame)
        img3 = getDP(frame, bol)
        final, count = stack(img1, img2, img3)
        ovl = drawmask(frame, final)
        if debug == True:
            img1 = cv2.cvtColor(img1, cv2.COLOR_GRAY2BGR)
            img2 = cv2.cvtColor(img2, cv2.COLOR_GRAY2BGR)
            # print(img2.dtype)
            # print(img1.dtype)
            img3 = cv2.cvtColor(img3, cv2.COLOR_GRAY2BGR)
            out1.write(img1)
            out2.write(img2)
            out3.write(img3)
        out.write(ovl)
        print(frame_count-1)
        if frame_count == 30:
            out.release()
            break

def realtime(path):
    try:
        video_src = path
    except IndexError:
        print('Video Pass Error')
    cap = cv2.VideoCapture(video_src)
    smoke = False
    font = cv2.FONT_HERSHEY_SIMPLEX
    bottomLeftCornerOfText = (30, 30)
    fontScale = 1
    fontColor = (0, 0, 255)
    lineType = 2
    ret, frame = cap.read()
    h, w, d= resizeimge(frame, imgsize).shape
    mhi = Mhi(h, w)

    while True:
        ret, frame = cap.read()
        if frame is None:
            print("Video reach end.")
            break
        frame = resizeimge(frame, imgsize)
        img1 = colorAnalysis(frame, colorth)
        t, img2 = mhi.update(frame)
        img3 = getDP(frame, False)
        final, count = stack(img1, img2, img3)
        print(count)
        if smoke == True:
            cv2.putText(frame, 'SMOKE SMOKE SMOKE!',
                        bottomLeftCornerOfText,
                        font,
                        fontScale,
                        fontColor,
                        lineType)
        if count > 500 and smoke == False:
            smoke = True
        elif count < 500 and smoke == True:
            smoke = False
        cv2.imshow('realtime', frame)
        cv2.waitKey(10)




def extract_frames(fn):
    try:
        video_src = fn
    except IndexError:
        print('Video Pass Error')
    cap = cv2.VideoCapture(video_src)
    frame_count = 1
    while True:
        ret, frame = cap.read()
        if frame is None:
            print("Video reach end.")
            break
        # extract frames for every X frame
        
        if frame_count % 5 == 0:
            cv2.imwrite("test2/frame%d.jpg" % frame_count, frame)
            cv2.imshow('ext', frame)
        
        # Press Key Q to exit
        if (cv2.waitKey(10) & 0xFF) == 'Q':
            break
        frame_count += 1

def ftou(img):
    ret = img*255
    return ret.astype(np.uint8)

def main():
    global debug
    print("-----------Smoke detect System-----------")
    while True:
        sorce = input("Please enter video path: ")
        mode = input("Please enter detect mode(video/realtime/debug): ")
        filter = input("Do you want to apply guided filter for better result but slow the process?(Y/N):")

        print("Video Path:" + sorce + " Mode: " + mode + " Guided_Filter: " + filter)

        if mode == "video":
            if filter == "Y":
                productVideo(True, sorce)
            elif filter == "N":
                productVideo(False, sorce)
            else:
                print("Please enter correct filter, choosen from Y, N!")
        elif mode == "debug":
            debug = True
            print("Enter debug mode!")
            if filter == "Y":
                productVideo(True, sorce)
            elif filter == "N":
                productVideo(False, sorce)
            else:
                print("Please enter correct filter, choosen from Y, N!")
        elif mode == "realtime":
            # print("realtime")
            realtime(sorce)
        else:
            print("Please Enter correct mode! Choosen from video, realtime, debug!")

        quit = input("Do you want to exit? Y/N:")
        if quit == "N":
            continue
        else:
            break


    # motionloop()
    #
    # img = cv2.imread("test/frame190.jpg")
    # # img = resizeimge(img, imgsize)
    # h,w,d = img.shape
#    img1 = colorAnalysis(img,colorth)
#    #cv2.imshow('grey', img1)
#     img2 = getDP(img)
#     svimg(img2)
#img3 = mhi("test2", 255, 5, 5)
#cv2.imshow('mhi', img3)
#    final = stack(img1,img2,img3)
#    cv2.imshow('final', final)
#    ovl = drawmask(img, final)
#    cv2.imshow('overlay', ovl)
#
#     mhi = Mhi(h, w)
#     tsp, ret = mhi.update(img)
#     for i in range(260, 300, 5):
#         img = cv2.imread("test2/frame"+str(i)+".jpg")
#         tsp, ret = mhi.update(img)
#     print(tsp)
#     cv2.imshow('img', ret)
    # productVideo()
    print('Done!')
    


#extract_frames("videos/simple_smoke.mp4")
    cv2.waitKey(0)


#
#

if __name__ == "__main__":
    main()
