import numpy as np
import cv2 as cv
import basicfunctions as base
import requests
import os
from bs4 import BeautifulSoup as bs

WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
BLUE = (255, 0, 0)
RED = (0, 0, 255)


def loadAllNewPhoneImages(url, path):
    if not os.path.isdir(path):
        os.makedirs(path)

    website = requests.get(url)
    results = bs(website.content, 'html.parser')
    dropdown = results.find('div', class_='nfc')
    phones = dropdown.select('option')
    phones.pop(0) #delete empty image
    for phone in phones:
        phoneSrc = phone.get('value')
        modelSeriesName = phone.text.strip()
        if modelSeriesName.__contains__('/'):
            splittedName = modelSeriesName.split('/')
            modelSeriesName1 = splittedName[0].strip()
            versionName = modelSeriesName1.split(' ')
            modelSeriesName2 = modelSeriesName1.replace(versionName[-1], splittedName[1].lstrip())
            base.downloadFileIfNeccessary(path, phoneSrc, modelSeriesName1, "https://consumer.huawei.com/")
            base.downloadFileIfNeccessary(path, phoneSrc, modelSeriesName2, "https://consumer.huawei.com/")
        else:
            base.downloadFileIfNeccessary(path, phoneSrc, modelSeriesName, "https://consumer.huawei.com/")


def findPhoneEdgeInImage(img, filename):
        #Preprocessing
        #convert image to grayscale
        imgGray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        #blur
        imgBlur = cv.GaussianBlur(imgGray, (1, 1), cv.BORDER_DEFAULT)
        #edge detection
        imgCanny = cv.Canny(imgBlur, 0, 155)
        for i in range(3, 10, 1):
            #merge edges
            imgDil = cv.dilate(imgCanny, (3, 3), iterations=i)
            imgEro = cv.erode(imgDil, (3, 3), iterations=i)
            #contour detection
            contours, hierarchies = cv.findContours(imgEro, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
            contours = sorted(contours, key=cv.contourArea, reverse=True)
            #bad image quality -> outer edges might be artifacts -> take innerEdge if it is similar
            if len(contours) >= 2:
                outerContour = contours[0]
                innerContour = contours[1]
                matchingValue = cv.matchShapes(innerContour, outerContour, 1, 0.0)
                if matchingValue < 0.15:
                    peri = cv.arcLength(innerContour, True)
                    approx = cv.approxPolyDP(innerContour, 0.02 * peri, True)
                    x0, y0, w, h = cv.boundingRect(approx)
                    return x0, y0, (x0+w), (y0+h)
                else:
                    peri = cv.arcLength(outerContour, True)
                    approx = cv.approxPolyDP(outerContour, 0.02 * peri, True)
                    x0, y0, w, h = cv.boundingRect(approx)
                    return x0, y0, (x0+w), (y0+h)
        print("Error 404: Could not find edge for " + filename)
        return -1, -1, -1, -1


def findNfcChipViaColor(img, filename):
    #Preprocessing
    hsv = cv.cvtColor(img, cv.COLOR_BGR2HSV)
    for hue in range(100, 111):
        lowerRange = np.array([100, 120, 130])
        upperRange = np.array([hue, 255, 255])
        mask = cv.inRange(hsv, lowerRange, upperRange)
        contours, hierarchy = cv.findContours(mask, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv.contourArea, reverse=True)
        if len(contours) != 0:
            if cv.contourArea(contours[0]) > 500:
                contour = contours[0]
                peri = cv.arcLength(contour, True)
                approx = cv.approxPolyDP(contour, 0.02 * peri, True)
                x0, y0, w, h = cv.boundingRect(approx)
            else:
                continue
            return x0, y0, x0+w, y0+h
    print("Error 404: No nfc-chip found for " + filename)
    return -1, -1, -1, -1


def main():
    loadAllNewPhoneImages('https://consumer.huawei.com/de/support/huaweishare/specs/', 'huawei/phones/')
    images, filenames = base.loadAllImagesOfFolder('huawei/phones/')
    nfcChipLocations = []
    for img, filename in zip(images, filenames):
        x0Nfc, y0Nfc, x1Nfc, y1Nfc = findNfcChipViaColor(img, filename)
        x0Edge, y0Edge, x1Edge, y1Edge = findPhoneEdgeInImage(img, filename)

        if x0Edge != -1 & x0Nfc != -1:
            x0, y0, x1, y1 = base.nfcChipCoordinatesInPercent(x0Nfc, y0Nfc, x1Nfc, y1Nfc, x0Edge, y0Edge, x1Edge, y1Edge)
        else:
            print("Error 400: Missing or Wrong Parameter to find the right Coordinates for: " + filename)
            x0, y0, x1, y1 = -1, -1, -1, -1

        nfcChipLocations.append(base.formatCoordinates(filename, x0, y0, x1, y1))
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
    base.writeJsonFile(nfcChipLocations, 'nfcChipsOutput/', 'nfcChipsHuawei.json')


#run Code
main()
