import json
import logging
import os
import sys
import tkinter
from inspect import currentframe, getframeinfo
from tkinter.filedialog import askdirectory, askopenfilename
sys.path.append('../..')

import numpy as np

import cv2
from src.support.msg_box import MessageBox
from src.view.component_app import EntryThermalComponentViewer


__FILE__ = os.path.abspath(getframeinfo(currentframe()).filename)
LOGGER = logging.getLogger(__name__)

class EntryThermalComponentAction(EntryThermalComponentViewer):
    def __init__(self):
        super().__init__()
        # path
        self._thermal_dir_path = None
        self._component_dir_path = None
        self._transform_matrix_path = None
        self._contour_path = None
        self._output_dir_path = None

        # file
        self._component_img = None
        self._transform_matrix = None
        self._contour_meta = None

        self.btn_thermal_txt_upload.config(command=self._load_thermal_dir)
        self.btn_component_upload.config(command=self._load_component_img)
        self.btn_transform_matrix_upload.config(command=self._load_transform_matrix)
        self.btn_contour_meta_upload.config(command=self._load_contour_meta)
        self.btn_convert.config(command=self._convert)
        self._sync_generate_save_path()

    # load thermal directory
    def _load_thermal_dir(self):
        self._thermal_dir_path = askdirectory(
            initialdir=os.path.abspath(os.path.join(__FILE__, '../../../')),
            title=u'選擇溫度檔資料夾 (.txt)'
        )

        if self._thermal_dir_path:
            LOGGER.info('Thermal txt directory - {}'.format(self._thermal_dir_path))
            self.label_thermal_path.config(text=self._thermal_dir_path)

    # load original image path
    def _load_component_img(self):
        self._component_dir_path = askdirectory(
            initialdir=os.path.abspath(os.path.join(__FILE__, '../../../')),
            title=u'選擇部位原圖資料夾'
        )

        if self._component_dir_path:
            LOGGER.info('Original image file - {}'.format(self._component_dir_path))
            filename = self._component_dir_path.split(os.sep)[-1].split('.')[0]
            self.label_component_path.config(text=self._component_dir_path)
            try:
                self._component_img = {
                    'foreleft': cv2.imread(os.path.join(self._component_dir_path, '{}_fore_left.png').format(filename)),
                    'foreright': cv2.imread(os.path.join(self._component_dir_path, '{}_fore_right.png').format(filename)),
                    'backleft': cv2.imread(os.path.join(self._component_dir_path, '{}_back_left.png').format(filename)),
                    'backright': cv2.imread(os.path.join(self._component_dir_path, '{}_back_right.png').format(filename)),
                    'body': cv2.imread(os.path.join(self._component_dir_path, '{}_body.png').format(filename))
                }
            except Exception as e:
                LOGGER.exception(e)
                Mbox = MessageBox()
                Mbox.alert(string=u'無法正確開啟原圖')

            # try to generate other necessary data path
            if self._contour_path is None or not self._contour_path:
                self._contour_path = os.path.join(self._component_dir_path.split('.')[0], '{}.json'.format(filename))
                self.label_contour_meta_path.config(text=self._contour_path)
                LOGGER.info('Contour meta - {}'.format(self._contour_path))
                with open(self._contour_path, 'r') as f:
                    self._contour_meta = json.load(f)

    # load transform matrix path
    def _load_transform_matrix(self):
        self._transform_matrix_path = askopenfilename(
            initialdir=os.path.abspath(os.path.join(__FILE__, '../../../')),
            title=u'選擇轉換矩陣路徑',
            filetypes=(('Numpy array', '*.dat'),)
        )

        if self._transform_matrix_path:
            LOGGER.info('Transform matrix file - {}'.format(self._transform_matrix_path))
            self.label_transform_matrix_path.config(text=self._transform_matrix_path)
            self._transform_matrix = np.fromfile(self._transform_matrix_path)
            self._transform_matrix = self._transform_matrix.reshape(3, 3)

    # load contour metadata path
    def _load_contour_meta(self):
        self._contour_path = askopenfilename(
            initialdir=os.path.abspath(os.path.join(__FILE__, '../../../')),
            title=u'選擇輪廓資訊路徑',
            filetypes=(('JSON file', '*.json'),)
        )

        if self._contour_path:
            LOGGER.info('Contour meta - {}'.format(self._contour_path))
            self.label_contour_meta_path.config(text=self._contour_path)
            with open(self._contour_path, 'r') as f:
                self._contour_meta = json.load(f)

    # sync save path
    def _sync_generate_save_path(self):
        if self._thermal_dir_path and self.val_filetype.get():
            self._output_dir_path = '{}_warp_{}'.format(self._thermal_dir_path, self.val_filetype.get())
            self.label_output_path.config(text=self._output_dir_path)

        self.label_output_path.after(10, self._sync_generate_save_path)

    # check if all necessary data is prepared
    def _check_data(self):
        if self._thermal_dir_path is None or not self._thermal_dir_path:
            LOGGER.warning('Please choose the thermal text data directory')
            Mbox = MessageBox()
            Mbox.alert(string=u'請選擇溫度圖檔案的資料夾')
            return False
        elif self._component_img is None:
            LOGGER.warning('Please provide the proper component image directory')
            Mbox = MessageBox()
            Mbox.alert(string=u'請上傳適當的圖檔')
            return False
        elif self._transform_matrix is None:
            LOGGER.warning('Please provide the proper transforma matrix file')
            Mbox = MessageBox()
            Mbox.alert(string=u'請上傳適當的轉換矩陣檔案')
            return False
        elif self._contour_meta is None or 'components_contour' not in self._contour_meta:
            LOGGER.warning('Please provide the proper contour metadata')
            Mbox = MessageBox()
            Mbox.alert(string=u'請上傳適當的輪廓資料')
            return False
        elif self._output_dir_path is None:
            Mbox = MessageBox()
            Mbox.alert(string=u'無存檔路徑')
            LOGGER.error('No output path')
            return False
        else:
            return True

    # convert
    def _convert(self):
        if self._check_data():
            output_file_format = self.val_filetype.get()
            thermal_frames = [os.path.join(self._thermal_dir_path, f) for f in os.listdir(self._thermal_dir_path)]
            thermal_frames = sorted(thermal_frames, key=lambda x: int(x.split(os.sep)[-1].split('.')[0].split('_')[-1]))
            component_cnts = {
                'foreleft': self._contour_meta['components_contour']['forewings']['left'],
                'foreright': self._contour_meta['components_contour']['forewings']['right'],
                'backleft': self._contour_meta['components_contour']['backwings']['left'],
                'backright': self._contour_meta['components_contour']['backwings']['right'],
                'body': self._contour_meta['components_contour']['body']
            }

            # original image resize > threshold > get mask
            _ = np.loadtxt(open(thermal_frames[0], 'rb'), delimiter=',', skiprows=1)
            component_mask = {}
            for part, img in self._component_img.items():
                img = cv2.resize(img, _.shape[:2][::-1])
                img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                ret, mask = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY)
                component_mask[part] = mask

            # process each frame
            for idx, frame in enumerate(thermal_frames):
                frame_data = np.loadtxt(open(frame, 'rb'), delimiter=',', skiprows=1)

                # process each component
                for part, cnt in component_cnts.items():
                    savedir = os.path.join(self._output_dir_path, part)
                    if not os.path.exists(savedir):
                        os.makedirs(savedir)

                    # warp thermal frame > mask
                    warp_component = cv2.warpPerspective(frame_data, self._transform_matrix, frame_data.shape[:2][::-1])
                    warp_component[np.where(component_mask[part] == 0)] = 0

                    # save
                    saveframe = os.path.join(savedir, frame.split(os.sep)[-1].split('.')[0])
                    savefile = None
                    if output_file_format == 'npy':
                        savefile = saveframe + '.npy'
                        np.save(savefile, warp_component)
                    elif output_file_format == 'dat':
                        savefile = saveframe + '.dat'
                        warp_component.tofile(savefile)
                    elif output_file_format == 'txt':
                        savefile = saveframe + '.txt'
                        np.savetxt(savefile, warp_component)
                    LOGGER.info('Save - {}'.format(savefile))

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(filename)12s:L%(lineno)3s [%(levelname)8s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        stream=sys.stdout
    )

    entry = EntryThermalComponentAction()
    entry.mainloop()