import cv2
import numpy as np
import os
from skimage.segmentation import slic
from skimage.segmentation import mark_boundaries
from skimage.util import img_as_float
from skimage import io
from matplotlib import pyplot as plt
import matplotlib.path as mplPath
import xml.etree.ElementTree as ET

def plotImage(img, size):
    fig, ax = plt.subplots(figsize=(size,size))
    #plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    plt.imshow(img)
    plt.xticks([]),
    plt.yticks([])
    plt.show()
    
def subplot(titles, images, rows, imgPerRows, size):
    fig, ax = plt.subplots(figsize=(size,size))
    for i in range(len(images)):
        plt.subplot(rows,imgPerRows,i+1),
        #plt.imshow(cv2.cvtColor(images[i], cv2.COLOR_BGR2RGB))
        plt.imshow(images[i])
        plt.title(titles[i])
        plt.xticks([]),
        plt.yticks([])
    plt.show()
    
def readPageImagesAndGroundTruth (folderPageImages, folderGroundTruth, subFolderGroundTruth) :
    listImages = []; listGroundTruth = []
    for fileGroundTruth in os.listdir(folderGroundTruth + "/" + subFolderGroundTruth) :
        if fileGroundTruth.endswith('.xml') :
            for file in os.listdir(folderPageImages) :
                if file.endswith('.jpg') and fileGroundTruth.find(file[0:5]) > -1 :
                    #image = cv2.imread(folderPageImages + "/" + file)
                    image = img_as_float(io.imread(folderPageImages + "/" + file))
                    listImages.append(image)
                    listGroundTruth.append(fileGroundTruth)
    return listImages, listGroundTruth

def resizeImages (images, factor):
    resizedImages = []
    for i in range (len(images)) :
        dim = (int(images[i].shape[1]*factor),int(images[1].shape[0]*factor))
        resizedImages.append(cv2.resize(images[i], dim, interpolation = cv2.INTER_AREA))
    return resizedImages

def groundThruthFindCountourPointsByRegion (pathGroundThruthFile, region) :
    listPixels = []
    polygonsByRegion = []
    pointsPolygon = []
    tree = ET.parse(pathGroundThruthFile)
    root = tree.getroot()

    for neighbor in root.iter('TextRegion') :
        if (neighbor.attrib['type'] == region) :
            pointsPolygon = []
            for coord in neighbor.findall('Coords') :
                for point in coord.findall('Point') :
                    pointsPolygon.append([point.attrib['x'], point.attrib['y']])
                polygonsByRegion.append(pointsPolygon)
                
    return polygonsByRegion

def isInsidePolygon (listPointsPolygon, x, y) :
    bbPath = mplPath.Path(listPointsPolygon)
    point = ([x, y])
    return bbPath.contains_point(point)

def paintPolygon (listPointPolygonRegion, listPointsInsidePolygon, image, factor, B, G, R) :
    imageWidth = image.shape[1] #Get image width
    imageHeight = image.shape[0] #Get image height
    xPos, yPos = 0, 0
    while xPos < imageWidth: #Loop through rows
        while yPos < imageHeight: #Loop through collumns
            if isInsidePolygon (listPointPolygonRegion, xPos*factor, yPos*factor) :
                image.itemset((yPos, xPos, 0), B)
                image.itemset((yPos, xPos, 1), G)
                image.itemset((yPos, xPos, 2), R)
                listPointsInsidePolygon.append([xPos,yPos])
            yPos = yPos + 1 #Increment Y position by 1

        yPos = 0
        xPos = xPos + 1 #Increment X position by 1    
        
def paintPointsOutsideList (listPoints, image, B, G, R) :
    imageWidth = image.shape[1] #Get image width
    imageHeight = image.shape[0] #Get image height
    #from IPython.core.debugger import Tracer; Tracer()() 
    xPos, yPos = 0, 0
    for i in range(len(listPoints)) :
        point = listPoints[i]
        x = point[0]
        y = point[1]
        while xPos < imageWidth: #Loop through rows
            while yPos < imageHeight: #Loop through collumns
                if xPos == x and yPos == y :
                    image.itemset((yPos, xPos, 0), B)
                    image.itemset((yPos, xPos, 1), G)
                    image.itemset((yPos, xPos, 2), R)

                yPos = yPos + 1 #Increment Y position by 1

            yPos = 0
            xPos = xPos + 1 #Increment X position by 1
            
def segmentImageInSuperpixels (images, numSuperpixels) :
    listSegmentsByImage = []
    for i in range(len(images)) :
        segments = slic(images[i], n_segments = numSuperpixels, sigma = 5)
        listSegmentsByImage.append(segments)
    return listSegmentsByImage

def paintCentralPointsOrPatchesSegments (image, segments, radio, sizePatch, isPatch) :
    for (j , segVal) in enumerate(np.unique(segments)) :    
        mask = np.zeros(image.shape[:2], dtype = "uint8")
        mask[segments == segVal] = 255
        cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
        c = max(cnts, key=cv2.contourArea)
        M = cv2.moments(c)
        cX = int(M["m10"] / M["m00"])
        cY = int(M["m01"] / M["m00"])
        if isPatch :
            deltaSizePatch = int(sizePatch/2)
            cv2.rectangle(image,(cX-deltaSizePatch,cY-deltaSizePatch),(cX+deltaSizePatch,cY+deltaSizePatch),(255,0,0),2)   
        else :
            cv2.circle(image, (cX, cY), radio, (0, 0, 255), -1)

def doInputs (images, segmentsByX, sizePatch) :
    X = [] #list of lists, a collection of patches
    listCentralPoints = []
    for i in range (len(segmentsByX)) :                                                
        segments = segmentsByX[i];
        listPatches = []
        centralPoints = [] #list points
        for (j , segVal) in enumerate(np.unique(segments)) : 
            mask = np.zeros(images[i].shape[:2], dtype = "uint8")
            mask[segments == segVal] = 255
            cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
            c = max(cnts, key=cv2.contourArea)
            M = cv2.moments(c)
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
            centralPoint = ([cX,cY])
            deltaSizePatch = int(sizePatch/2)
            roiX = images[i][cY-deltaSizePatch:cY+deltaSizePatch, cX-deltaSizePatch:cX+deltaSizePatch]
            listPatches.append(roiX)
            centralPoints.append(centralPoint)
        X.append(listPatches)
        listCentralPoints.append(centralPoints)
    return X, listCentralPoints
        
def doLabels (images, X, xGT, folderGroundTruth, subFolderGroundTruth) :
    Y = []
    for i in range (len(X)) :
        patches = X[i]
        for j in range (len(patches)) :
            patch = patches[j]
            deltaSizePatch = int(patch.shape[0]/2)
            
    
#segmentsByX list of lists
#xGT list of lists
def doInputsAndLabelsFromSegments (images, segmentsByX, xGT, folderGroundTruth, subFolderGroundTruth, sizePatch) :
    X = [] #list of lists, a collection of patches
    Y = [] #list of lists, a collection of labels of patches
    regions = ['page','text','decoration','comment','periphery']
    for i in range (len(segmentsByX)) :
        segments = segmentsByX[i];
        listPatches = []
        listLabels = []
        for (j , segVal) in enumerate(np.unique(segments)) : 
            mask = np.zeros(images[i].shape[:2], dtype = "uint8")
            mask[segments == segVal] = 255
            cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
            c = max(cnts, key=cv2.contourArea)
            M = cv2.moments(c)
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
            deltaSizePatch = int(sizePatch/2)
            roiX = images[i][cY-deltaSizePatch:cY+deltaSizePatch, cX-deltaSizePatch:cX+deltaSizePatch]
            listPatches.append(roiX)
            for k in range(len(regions)) :
                listPolygons = groundThruthFindCountourPointsByRegion(
                               folderGroundTruth + "/" + subFolderGroundTruth + "/" + xGT[i],
                               regions[k])
                for t in range(len(listPolygons)) :
                    listPointPolygonRegion = listPolygons[t]
                    if (regions[k] == 'decoration') :
                        if isInsidePolygon(listPointPolygonRegion, cX, cY) :
                            listLabels.append('decoration')
                    elif (regions[k] == 'text') : 
                        if isInsidePolygon(listPointPolygonRegion, cX, cY) :    
                            listLabels.append('text')
                    elif (regions[k] == 'comment') : 
                        if isInsidePolygon(listPointPolygonRegion, cX, cY) :
                            listLabels.append('comment')
                    elif (regions[k] == 'page') : 
                        if isInsidePolygon(listPointPolygonRegion, cX, cY) : 
                            listLabels.append('page')
        X.append(listPatches)
        Y.append(listLabels)
    return X , Y
