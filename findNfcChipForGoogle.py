import numpy as np
import cv2 as cv
import basicfunctions as base
import requests
import os
from bs4 import BeautifulSoup as bs
import easyocr


WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
BLUE = (255, 0, 0)
RED = (0, 0, 255)
BLACK = (0, 0, 0)


def loadAllNewPhoneImages(url, path):
    if not os.path.isdir(path):
        os.makedirs(path)

    website = requests.get(url)
    results = bs(website.content, 'html.parser')
    content = results.find('div', class_='cc')
    modelNames = content.findAll(class_='zippy')
    featureLists = content.findAll('ol')
    images = content.findAll('img', class_='')
    images.pop(0) #first image is not a hardwarediagram

    nfcFeatureNumbers = []
    for img, modelName, featureList in zip(images, modelNames, featureLists):
        imgSrc = img["src"]
        modelName = getModelName(modelName.text)
        featureNumber = getNfcFeatureNumber(featureList)
        if featureNumber == -1:
            print('No NFC-Feature for' + modelName)
            continue
        nfcFeatureNumbers.append(featureNumber)
        base.downloadFileIfNeccessary(path, imgSrc, modelName, 'https:')
    return reversed(nfcFeatureNumbers)


def getModelName(modelName):
    modelName = modelName.replace('\xa0', ' ')
    pos = modelName.find('Pixel')
    return modelName[pos:len(modelName)] if pos != -1 else modelName


def getNfcFeatureNumber(featureList):
    featureList = featureList.findAll('li')
    for i, feature in enumerate(featureList, start=1):
        if str(feature.text).upper().__contains__("NFC"):
            return i
    return -1


def findPhoneEdgeInImage(img, filename):
        dim = img.shape
        #Preprocessing
        lowerRange = np.array([20, 20, 20])
        upperRange = np.array([255, 255, 255])
        # convert BGR to HSV
        imgHSV = cv.cvtColor(img, cv.COLOR_BGR2HSV)
        # create the Mask
        mask = cv.inRange(imgHSV, lowerRange, upperRange)
        # inverse mask
        mask = cv.bitwise_not(mask)
        #convert image to grayscale
        imgGray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        #blur
        imgBlur = cv.GaussianBlur(imgGray, (1, 1), cv.BORDER_DEFAULT)
        #inverse if light image
        if np.mean(img) > 125:
            img = cv.bitwise_not(imgBlur)
        #filter all colors
        res = cv.bitwise_and(img, img, mask=mask)
        #edge detection
        imgCanny = cv.Canny(res, 0, 10)
        #merge edges
        imgDil = cv.dilate(imgCanny, (3, 3), iterations=1)
        imgEro = cv.erode(imgDil, (3, 3), iterations=1)
        #contour detection
        contours, hierarchies = cv.findContours(imgEro, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        if contours is not None:
            contours = sorted(contours, key=cv.contourArea, reverse=True)
            for contour in contours:
                if cv.contourArea(contour) > 500:
                    peri = cv.arcLength(contour, True)
                    approx = cv.approxPolyDP(contour, 0.02 * peri, True)
                    x0, y0, w, h = cv.boundingRect(approx)
                    if x0 >= dim[1]/2: #contour is on the right side
                        return x0, y0, (x0+w), (y0+h)
        else:
            print("Error 404: Could not find edge for " + filename)
            return -1, -1, -1, -1


def findNfcChipViaFeatureNumber(img, filename, featureNumber):
    #Preprocessing
    #convert image to grayscale
    imgGray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    #inverse if light image
    if np.mean(img) < 125:
        imgGray = cv.bitwise_not(imgGray)
    scaledImg = cv.resize(imgGray, None, fx=4.0, fy=4.0, interpolation=cv.INTER_LINEAR)
    x0Num, y0Num, x1Num, y1Num = findNumberOnImgWithOcr(scaledImg, featureNumber) #todo only right half -> increase performance

    x0, y0, x1, y1 = findNfcChipNearNumberCoordinates(img, x0Num, y0Num, x1Num, y1Num)
    if x0 != -1:
        return x0, y0, x1, y1
    else:
        print("Error 404: Could not find nfc-chip for: " + filename)
        return -1, -1, -1, -1


def findNfcChipNearNumberCoordinates(img, x0Num, y0Num, x1Num, y1Num):
    #Preprocessing
    lowerRange = np.array([80, 20, 20])
    upperRange = np.array([130, 255, 255])
    #convert BGR to HSV
    imgHSV = cv.cvtColor(img, cv.COLOR_BGR2HSV)
    #create the Mask
    maskNum = cv.inRange(imgHSV, lowerRange, upperRange)
    #find edges in mask
    imgCanny = cv.Canny(maskNum, 0, 5)
    imgDil = cv.dilate(imgCanny, (3, 3), iterations=2)
    #contour detection
    contours, hierarchies = cv.findContours(imgDil, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        if cv.contourArea(contour) > 100:
            peri = cv.arcLength(contour, True)
            approx = cv.approxPolyDP(contour, 0.02 * peri, True)
            x0, y0, w, h = cv.boundingRect(approx)
            x1, y1 = x0+w, y0+h

            if x0*0.95 <= x0Num and y0*0.95 <= y0Num and x1*1.05 >= x1Num and y1*1.05 >= y1Num: # find corresponding contour to the pos of the number with 5% deviation
                nfcChipSize = w if w < h else h
                if x0 - x0Num <= x1 - x1Num & y0 - y0Num <= y1 - y1Num: # number is on the top-left - nfc chip on opposite side of contour
                    return x1-nfcChipSize, y1-nfcChipSize, x1, y1
                elif x0 - x0Num <= x1 - x1Num & y0 - y0Num >= y1 - y1Num: # number is on the bottom-left - nfc chip on opposite side of contour
                    return x1-nfcChipSize, y0, x1, y0+nfcChipSize
                elif x0 - x0Num >= x1 - x1Num & y0 - y0Num <= y1 - y1Num: # number is on the top-right - nfc chip on opposite side of contour
                    return x0, y1-nfcChipSize, x0+nfcChipSize, y1
                else: # number is on the bottom-right - nfc chip on opposite side of contour
                    return x0, y0, x0+nfcChipSize, y0+nfcChipSize
    return -1, -1, -1, -1


def findNumberOnImgWithOcr(scaledImg, featureNumber):
    #init textdetection
    reader = easyocr.Reader(['en'], gpu=False)
    resultList = reader.readtext(scaledImg, allowlist='0123456789')
    numberLocations = []
    for result in resultList:
        if (result[1] == str(featureNumber)) & (result[2] >= 0.8): #found the right Number with 80% plausability
            numberLocations.append(result)
    if len(numberLocations) == 0: #if text detection did not find the number -> try with sharpened image
        #sharpen image
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        sharpendImg = cv.filter2D(scaledImg, -1, kernel)
        resultList = reader.readtext(sharpendImg, allowlist='0123456789')
        for result in resultList:
            if (result[1] == str(featureNumber)) & (result[2] >= 0.8): #found the right Number with 80% plausability
                numberLocations.append(result)

    if numberLocations is not None:
        sorted(numberLocations, key=lambda x: x[2], reverse=True) #highest plausibility at pos[0], probably not neccessary -> it is unlikely to find 2 results with plausability > 80%
        x0 = int(numberLocations[0][0][0][0]/4)
        y0 = int(numberLocations[0][0][0][1]/4)
        x1 = int(numberLocations[0][0][2][0]/4)
        y1 = int(numberLocations[0][0][2][1]/4)
        return x0, y0, x1, y1
    else:
        return -1, -1, -1, -1


def main():
    nfcFeatureNumbers = loadAllNewPhoneImages('https://support.google.com/pixelphone/answer/7157629?hl=de#zippy&zippy=', 'google/phones/')
    images, filenames = base.loadAllImagesOfFolder('google/phones/')
    nfcChipLocations = []
    for img, filename, featureNumber in zip(images, filenames, nfcFeatureNumbers):
        x0Nfc, y0Nfc, x1Nfc, y1Nfc = findNfcChipViaFeatureNumber(img, filename, featureNumber)
        x0Edge, y0Edge, x1Edge, y1Edge = findPhoneEdgeInImage(img, filename)
        if x0Edge != -1 & x0Nfc != -1:
            x0, y0, x1, y1 = base.nfcChipCoordinatesInPercent(x0Nfc, y0Nfc, x1Nfc, y1Nfc, x0Edge, y0Edge, x1Edge, y1Edge)
        else:
            print("Error 400: Missing or Wrong Parameter to find the right Coordinates for: " + filename)
            x0, y0, x1, y1 = -1, -1, -1, -1
        nfcChipLocations.append(base.formatCoordinates(filename, x0, y0, x1, y1))
        """
        #debug
        imgContours = img.copy()
        cv.rectangle(imgContours, (x0Nfc, y0Nfc), (x1Nfc, y1Nfc), BLUE, 5)
        cv.rectangle(imgContours, (x0Edge, y0Edge), (x1Edge, y1Edge), GREEN, 5)
        cv.imshow('img', img)
        cv.imshow('imgC', imgContours)
        if cv.waitKey(0) & 0xFF == ord('w'): #press w to reload
            continue
        if cv.waitKey(0) & 0xFF == ord('q'): #press q to quit
            break
        #end debug
        """
    base.writeJsonFile(nfcChipLocations, 'nfcChipsOutput/', 'nfcChipsGoogle.json')


#run Code
main()
