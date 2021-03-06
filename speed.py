# -*- coding: utf-8 -*-

from models import *
from utils import *
import os, sys, time, datetime, random
import torch
from torchvision import transforms
import matplotlib.pyplot as plt
import cv2
from PIL import Image
from tracker import CentroidTracker

model_config = 'yolov3.cfg'
model_weights = 'yolov3.weights'
class_path = 'coco.names'
video_path = 'video.mp4'
vehicle_labels = [1,2,3,4,6,8]
img_size=416
conf_thres=0.75
nms_thres=0.3

# Load model and weights
model = Darknet(model_config, img_size=img_size)
model.load_darknet_weights(model_weights)
model.cuda()
model.eval()
classes = load_classes(class_path)

model

def distance(p1,p2):
    return np.sqrt((p2[0]-p1[0])**2+(p2[1]-p1[1])**2)

def speed_on_vid(vid_path):
    video_reader = cv2.VideoCapture(vid_path)

    fps = video_reader.get(cv2.CAP_PROP_FPS)
    width  = video_reader.get(cv2.CAP_PROP_FRAME_WIDTH)  
    height = video_reader.get(cv2.CAP_PROP_FRAME_HEIGHT)

    count = 0
    video = cv2.VideoWriter('output.mp4',
                            cv2.VideoWriter_fourcc(*'MP4V'),
                            int(fps), 
                            (1920, 1080))  
    tracker = CentroidTracker()
    while True:
        ret, frame = video_reader.read()
        rects = []
        if ret is False:
            break
        count+=1
        # Converting to RGB beacuse image in opencv is BGR
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # frame = cv2.resize(frame,(416,416))
        img = Image.fromarray(frame)
        ratio = min(img_size/img.size[0], img_size/img.size[1])
        w = round(img.size[0] * ratio)
        h = round(img.size[1] * ratio)
        img_transforms = transforms.Compose([ transforms.Resize((h, w)),
            transforms.Pad((max(int((h-w)/2),0), max(int((w-h)/2),0), max(int((h-w)/2),0), max(int((w-h)/2),0)),
                            (128,128,128)),transforms.ToTensor()])
        img = img_transforms(img)
        img = img.unsqueeze_(0).to('cuda')
        with torch.no_grad():
            detections = model(img)
            detections = non_max_suppression(detections, conf_thres, nms_thres)
            obj = detections[0]
        pad_x = max(frame.shape[0] - frame.shape[1], 0) * (img_size / max(frame.shape))
        pad_y = max(frame.shape[1] - frame.shape[0], 0) * (img_size / max(frame.shape))
        unpad_h = img_size - pad_y
        unpad_w = img_size - pad_x

        if obj is not None:
            unique_labels = obj[:, -1].cpu().unique()
            n_cls_preds = len(unique_labels)

            for x in obj:
                x1, y1, x2, y2, _, cls_pred, obj_id = x
                box_h = int(((y2 - y1) / unpad_h) * frame.shape[0])
                box_w = int(((x2 - x1) / unpad_w) * frame.shape[1])
                y1 = int(((y1 - pad_y // 2) / unpad_h) * frame.shape[0])
                x1 = int(((x1 - pad_x // 2) / unpad_w) * frame.shape[1])
                
                box = (x1, y1, x1+box_w, y1+box_h)
                rects.append(box)
                cls = classes[int(obj_id)]
                cv2.rectangle(frame, (x1, y1), (x1+box_w, y1+box_h), (0,255,0), 4)
            objects,speeds = tracker.update(rects)
            # loop over the tracked objects
            for (objectID, centroid) in objects.items():
                # Write the speed of the centroid in the output frame
                text = "Speed: {} km/h".format(speeds[objectID])
                cv2.putText(frame, text, (centroid[0] - 10, centroid[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        video.write(frame)      
    cv2.destroyAllWindows()  
    video.release()

speed_on_vid(video_path)

