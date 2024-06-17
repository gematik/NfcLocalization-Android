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
import pandas as pd

"""
FindNfcChipForHuawei is not working anymore since the website was taken down.
"""
class FindNfcChipForHuawei:
    @staticmethod
    def _load_all_new_phone_images(url, path, db_path, db_file_name):
        if not os.path.isdir(path):
            os.makedirs(path)

        website = requests.get(url)
        results = bs(website.content, 'html.parser')
        dropdown = results.find('div', class_='nfc')
        phones = dropdown.select('option')
        phones.pop(0)  # delete empty image
        for phone in phones:
            phone_src = phone.get('value')
            model_series_name = phone.text.strip()
            if '/' in model_series_name:
                split_name = model_series_name.split('/')
                model_series_name1 = split_name[0].strip()
                version_name = model_series_name1.split(' ')
                model_series_name2 = model_series_name1.replace(version_name[-1], split_name[1].lstrip())
                if not base.check_if_data_base_entry_exists(db_path, db_file_name, model_series_name1):
                    base.download_image(path, phone_src, model_series_name1, "https://consumer.huawei.com/")
                else:
                    print("Existing database entry found for: " + model_series_name1)
                if not base.check_if_data_base_entry_exists(db_path, db_file_name, model_series_name2):
                    base.download_image(path, phone_src, model_series_name2, "https://consumer.huawei.com/")
                else:
                    print("Existing database entry found for: " + model_series_name2)
            else:
                if not base.check_if_data_base_entry_exists(db_path, db_file_name, model_series_name):
                    base.download_image(path, phone_src, model_series_name, "https://consumer.huawei.com/")
                else:
                    print("Existing database entry found for: " + model_series_name)

    @staticmethod
    def _find_phone_edge_in_image(img, filename):
        # Preprocessing
        # convert image to grayscale
        img_gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        # blur
        img_blur = cv.GaussianBlur(img_gray, (1, 1), cv.BORDER_DEFAULT)
        # edge detection
        img_canny = cv.Canny(img_blur, 0, 155)
        for i in range(3, 10, 1):
            # merge edges
            img_dil = cv.dilate(img_canny, (3, 3), iterations=i)
            img_ero = cv.erode(img_dil, (3, 3), iterations=i)
            # contour detection
            contours, hierarchies = cv.findContours(img_ero, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
            contours = sorted(contours, key=cv.contourArea, reverse=True)
            # bad image quality -> outer edges might be artifacts -> take innerEdge if it is similar
            if len(contours) >= 2:
                outer_contour = contours[0]
                inner_contour = contours[1]
                matching_value = cv.matchShapes(inner_contour, outer_contour, 1, 0.0)
                if matching_value < 0.15:
                    peri = cv.arcLength(inner_contour, True)
                    approx = cv.approxPolyDP(inner_contour, 0.02 * peri, True)
                    x0, y0, w, h = cv.boundingRect(approx)
                    return x0, y0, (x0 + w), (y0 + h)
                else:
                    peri = cv.arcLength(outer_contour, True)
                    approx = cv.approxPolyDP(outer_contour, 0.02 * peri, True)
                    x0, y0, w, h = cv.boundingRect(approx)
                    return x0, y0, (x0 + w), (y0 + h)
        print("Could not find edge for " + filename)
        return -1, -1, -1, -1

    @staticmethod
    def _find_nfc_chip_via_color(img, filename):
        # Preprocessing
        hsv = cv.cvtColor(img, cv.COLOR_BGR2HSV)
        for hue in range(100, 111):
            lower_range = np.array([100, 120, 130])
            upper_range = np.array([hue, 255, 255])
            mask = cv.inRange(hsv, lower_range, upper_range)
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
                return x0, y0, x0 + w, y0 + h
        print("No nfc-chip found for " + filename)
        return -1, -1, -1, -1

    @staticmethod
    def _get_model_names_of_device_list(google_device_list, filename):
        full_name = filename.split(".")[0]
        if "HUAWEI" not in full_name:
            return google_device_list.loc[
                (google_device_list['Retail Branding'].str.lower() == "Huawei".lower()) &
                (google_device_list['Marketing Name'].str.lower() == full_name.lower())]['Model'].values.tolist()
        else:
            brand_name, rest = full_name.split(" ", 1)
            marketing_name = rest.split("-")[0]
            return google_device_list.loc[
                (google_device_list['Retail Branding'].str.lower() == brand_name.lower()) &
                (pd.Series(google_device_list['Marketing Name'].str.lower()).str.contains(marketing_name.lower()))][
                'Model'].values.tolist()

    @staticmethod
    def main():
        FindNfcChipForHuawei._load_all_new_phone_images('https://consumer.huawei.com/ch/support/huaweishare/specs/', 'huawei/phones/', 'nfcChipsOutput/', 'nfc_positions.json')
        images, filenames = base.load_all_images_of_folder('huawei/phones/')
        google_device_list = base.load_google_play_device_list()
        nfc_chip_locations = []
        for img, filename in zip(images, filenames):
            x0_nfc, y0_nfc, x1_nfc, y1_nfc = FindNfcChipForHuawei._find_nfc_chip_via_color(img, filename)
            x0_edge, y0_edge, x1_edge, y1_edge = FindNfcChipForHuawei._find_phone_edge_in_image(img, filename)
            if x0_edge != -1 & x0_nfc != -1:
                x0, y0, x1, y1 = base.nfc_chip_coordinates_in_percent(x0_nfc, y0_nfc, x1_nfc, y1_nfc, x0_edge, y0_edge,
                                                                      x1_edge, y1_edge)
                nfc_chip_locations.append( base.format_coordinates("Huawei", filename,
                                                                   FindNfcChipForHuawei._get_model_names_of_device_list(
                                                                       google_device_list, filename), x0, y0, x1, y1))
            else:
                print("Missing or wrong parameter to find the right coordinates for: " + filename)

        base.write_to_json_file(nfc_chip_locations, 'nfcChipsOutput/', 'nfc_positions.json')
        base.delete_all_files_in_folder('huawei/phones/')
