"""
/*
 * Copyright (c) 2024 gematik GmbH
 *
 * Licensed under the EUPL, Version 1.2 or – as soon they will be approved by
 * the European Commission - subsequent versions of the EUPL (the Licence);
 * You may not use this work except in compliance with the Licence.
 * You may obtain a copy of the Licence at:
 *
 *     https://joinup.ec.europa.eu/software/page/eupl
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the Licence is distributed on an "AS IS" basis,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the Licence for the specific language governing permissions and
 * limitations under the Licence.
 *
 */
"""


import numpy as np
import cv2 as cv
from baselineFunctions import BaselineFunctions as base
import requests
import os
from bs4 import BeautifulSoup as bs
import easyocr


class FindNfcChipForGoogle:
    @staticmethod
    def _load_all_new_phone_images(url, image_path, db_path, db_file_name):
        if not os.path.isdir(image_path):
            os.makedirs(image_path)

        website = requests.get(url)
        results = bs(website.content, 'html.parser')
        content = results.find('div', class_='cc')
        model_names = content.findAll(class_='zippy')
        feature_lists = content.findAll('ol')
        images = content.findAll('img', class_='')

        nfc_feature_numbers = []
        marketing_names = []
        for img, model_name, feature_list in zip(images, model_names, feature_lists):
            img_src = img["src"]
            model_name = FindNfcChipForGoogle._get_model_name(model_name.text)
            feature_number = FindNfcChipForGoogle._get_nfc_feature_number(feature_list)
            if feature_number == -1:
                print('No nfc-feature for' + model_name)
                continue
            nfc_feature_numbers.append(feature_number)
            marketing_names.append(model_name)
            if not base.check_if_data_base_entry_exists(db_path, db_file_name, model_name):
                base.download_image(image_path, img_src, model_name, 'https:')
            else:
                print("Existing database entry found for: " + model_name)
        return nfc_feature_numbers, marketing_names

    @staticmethod
    def _get_model_name(model_name):
        model_name = model_name.replace('\xa0', ' ')
        pos = model_name.find('Pixel')
        return model_name[pos:len(model_name)] if pos != -1 else model_name

    @staticmethod
    def _get_nfc_feature_number(feature_list):
        feature_list = feature_list.findAll('li')
        for i, feature in enumerate(feature_list, start=1):
            if "NFC" in str(feature.text).upper():
                return i
        return -1

    @staticmethod
    def _find_phone_edge_in_image(img, file_name):
        dim = img.shape
        # Preprocessing
        # convert BGR to HSV
        img_hsv = cv.cvtColor(img, cv.COLOR_BGR2HSV)
        # create the Mask
        lower_range = np.array([20, 20, 20])
        upper_range = np.array([255, 255, 255])
        mask = cv.inRange(img_hsv, lower_range, upper_range)
        # inverse mask
        mask = cv.bitwise_not(mask)
        # convert image to grayscale
        img_gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        # blur
        img_blur = cv.GaussianBlur(img_gray, (1, 1), cv.BORDER_DEFAULT)
        # inverse if light image
        if np.mean(img) > 125:
            img = cv.bitwise_not(img_blur)
        # filter all colors
        res = cv.bitwise_and(img, img, mask=mask)
        # edge detection
        img_canny = cv.Canny(res, 0, 10)
        # merge edges
        img_dil = cv.dilate(img_canny, (3, 3), iterations=1)
        img_ero = cv.erode(img_dil, (3, 3), iterations=1)
        # contour detection
        contours, hierarchies = cv.findContours(img_ero, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        if contours is not None:
            contours = sorted(contours, key=cv.contourArea, reverse=True)
            for contour in contours:
                if cv.contourArea(contour) > 500:
                    peri = cv.arcLength(contour, True)
                    approx = cv.approxPolyDP(contour, 0.02 * peri, True)
                    x0, y0, w, h = cv.boundingRect(approx)
                    if x0 >= dim[1] / 2:  # contour is on the right side
                        return x0, y0, (x0 + w), (y0 + h)
        else:
            print("Could not find edge for " + file_name)
            return -1, -1, -1, -1

    @staticmethod
    def _find_nfc_chip_via_feature_number(img, file_name, feature_number):
        # Preprocessing
        # convert image to grayscale
        img_gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        # inverse if light image
        if np.mean(img) < 125:
            img_gray = cv.bitwise_not(img_gray)
        scaled_img = cv.resize(img_gray, None, fx=4.0, fy=4.0, interpolation=cv.INTER_LINEAR)
        x0_num, y0_num, x1_num, y1_num = FindNfcChipForGoogle._find_number_on_img_with_ocr(scaled_img, feature_number)
        x0, y0, x1, y1 = FindNfcChipForGoogle._find_nfc_chip_near_number_coordinates(img, x0_num, y0_num, x1_num, y1_num)
        if x0 != -1:
            return x0, y0, x1, y1
        else:
            print("Could not find nfc-chip for: " + file_name)
            return -1, -1, -1, -1

    @staticmethod
    def _find_nfc_chip_near_number_coordinates(img, x0_num, y0_num, x1_num, y1_num):
        # Preprocessing
        # convert BGR to HSV
        img_hsv = cv.cvtColor(img, cv.COLOR_BGR2HSV)
        # create the Mask
        lower_range = np.array([80, 20, 20])
        upper_range = np.array([130, 255, 255])
        mask_num = cv.inRange(img_hsv, lower_range, upper_range)
        # merge edges in mask
        img_canny = cv.Canny(mask_num, 0, 5)
        img_dil = cv.dilate(img_canny, (3, 3), iterations=2)
        # contour detection
        contours, hierarchies = cv.findContours(img_dil, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            if cv.contourArea(contour) > 100:
                peri = cv.arcLength(contour, True)
                approx = cv.approxPolyDP(contour, 0.02 * peri, True)
                x0, y0, w, h = cv.boundingRect(approx)
                x1, y1 = x0 + w, y0 + h
                # find corresponding contour to the pos of the number with 5% deviation
                if x0 * 0.95 <= x0_num and y0 * 0.95 <= y0_num and x1 * 1.05 >= x1_num and y1 * 1.05 >= y1_num:
                    nfc_chip_size = w if w < h else h
                    # number is on the top-left - nfc chip on opposite side of contour
                    if x0 - x0_num <= x1 - x1_num & y0 - y0_num <= y1 - y1_num:
                        return x1 - nfc_chip_size, y1 - nfc_chip_size, x1, y1
                    # number is on the bottom-left - nfc chip on opposite side of contour
                    elif x0 - x0_num <= x1 - x1_num & y0 - y0_num >= y1 - y1_num:
                        return x1 - nfc_chip_size, y0, x1, y0 + nfc_chip_size
                    # number is on the top-right - nfc chip on opposite side of contour
                    elif x0 - x0_num >= x1 - x1_num & y0 - y0_num <= y1 - y1_num:
                        return x0, y1 - nfc_chip_size, x0 + nfc_chip_size, y1
                    # number is on the bottom-right - nfc chip on opposite side of contour
                    else:
                        return x0, y0, x0 + nfc_chip_size, y0 + nfc_chip_size
        return -1, -1, -1, -1

    @staticmethod
    def _find_number_on_img_with_ocr(scaled_img, feature_number):
        # init textdetection
        reader = easyocr.Reader(['en'], gpu=False)
        result_list = reader.readtext(scaled_img, allowlist='0123456789')
        number_locations = []
        for result in result_list:
            if (result[1] == str(feature_number)) & (result[2] >= 0.8):  # found the right Number with 80% plausibility
                number_locations.append(result)
        if len(number_locations) == 0:  # if text detection did not find the number -> try with sharpened image
            # sharpen image
            kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
            sharpened_img = cv.filter2D(scaled_img, -1, kernel)
            result_list = reader.readtext(sharpened_img, allowlist='0123456789')
            for result in result_list:
                if (result[1] == str(feature_number)) & (
                        result[2] >= 0.8):  # found the right Number with 80% plausibility
                    number_locations.append(result)

        if number_locations is not None and len(number_locations) > 0:
            sorted(number_locations, key=lambda x: x[2], reverse=True)  # highest plausibility at pos[0]
            x0 = int(number_locations[0][0][0][0] / 4)
            y0 = int(number_locations[0][0][0][1] / 4)
            x1 = int(number_locations[0][0][2][0] / 4)
            y1 = int(number_locations[0][0][2][1] / 4)
            return x0, y0, x1, y1
        else:
            return -1, -1, -1, -1

    @staticmethod
    def _get_model_names_of_device_list(google_device_list, file_name):
        full_name = file_name.split(".")[0]
        marketing_name = full_name.split(" (2")[0]
        return google_device_list.loc[
            (google_device_list['Retail Branding'] == "Google") &
            (google_device_list['Marketing Name'] == marketing_name)]['Model'].values.tolist()

    @staticmethod
    def _find_feature_number_for_model(nfc_feature_numbers, marketing_names, file_name):
        name = file_name.split(".")[0]

        for i, marketing_name in enumerate(marketing_names):
            if marketing_name == name:
                return nfc_feature_numbers[i]
        return -1

    @staticmethod
    def main():
        nfc_feature_numbers, marketing_names = FindNfcChipForGoogle._load_all_new_phone_images(
            'https://support.google.com/pixelphone/answer/7157629?hl=de#zippy&zippy=', 'google/phones/',
            'nfcChipsOutput/', 'nfc_positions.json')
        images, file_names = base.load_all_images_of_folder('google/phones/')
        google_device_list = base.load_google_play_device_list()
        nfc_chip_locations = []
        for img, file_name in zip(images, file_names):
            feature_number = FindNfcChipForGoogle._find_feature_number_for_model(nfc_feature_numbers, marketing_names,
                                                                                 file_name)
            x0_nfc, y0_nfc, x1_nfc, y1_nfc = FindNfcChipForGoogle._find_nfc_chip_via_feature_number(img, file_name,
                                                                                                    feature_number)
            x0_edge, y0_edge, x1_edge, y1_edge = FindNfcChipForGoogle._find_phone_edge_in_image(img, file_name)
            if x0_edge != -1 & x0_nfc != -1:
                x0, y0, x1, y1 = base.nfc_chip_coordinates_in_percent(x0_nfc, y0_nfc, x1_nfc, y1_nfc, x0_edge, y0_edge,
                                                                      x1_edge, y1_edge)
                nfc_chip_locations.append(
                    base.format_coordinates("Google", file_name,
                                            FindNfcChipForGoogle._get_model_names_of_device_list(google_device_list,
                                                                                                 file_name),
                                            x0, y0, x1, y1))
            else:
                print("Missing or Wrong Parameter to find the right Coordinates for: " + file_name)

        base.write_to_json_file(nfc_chip_locations, 'nfcChipsOutput/', 'nfc_positions.json')
        base.delete_all_files_in_folder("google/phones/")


