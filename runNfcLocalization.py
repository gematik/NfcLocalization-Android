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


from findNfcChipForGoogle import FindNfcChipForGoogle as google
from findNfcChipForSamsung import FindNfcChipForSamsung as samsung
from findNfcChipForHuawei import FindNfcChipForHuawei as huawei


class RunNfcLocalization:

    @staticmethod
    def main():
        print("Wählen Sie für welche Datenbankeinträge aktualisiert werden sollen.")
        chosen_option = input("Tippen Sie '0' ein, um alle Datenbankeinträge zu aktualisieren. \n"
                              "Tippen Sie '1' ein, um Samsungs Datenbankeinträge zu aktualisieren. \n"
                              "Tippen Sie '2' ein, um Googles Datenbankeinträge zu aktualisieren. \n"
                              # Huawei website was taken down
                              # "Tippen Sie '3' ein, um Huaweis Datenbankeinträge zu aktualisieren. \n"
                              "Bestätigen Sie die Eingabe mit Enter. \n"
                              "Jegliche anderweitige Eingabe beendet das Programm.\n")
        if chosen_option == "0":
            samsung.main()
            # huawei.main()
            google.main()
        elif chosen_option == "1":
            samsung.main()
        elif chosen_option == "2":
            google.main()
        # elif chosen_option == "3":
            # huawei.main()
        else:
            quit()


# run code
RunNfcLocalization.main()
