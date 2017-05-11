import os
import cv2
import math
import logging
import numpy as np

from scipy.spatial.distance import cosine


class GraphCut(object):
    '''
    ===============================================================================
    Interactive Image Segmentation

    This sample shows interactive image segmentation using grabcut algorithm.

    README FIRST:
        Two windows will show up, one for input and one for output.

    Key 'Esc' - To exit the program
    Key 'r' - To reset the setup
    Key 'a' - Shift mirror line to left side
    Key 'd' - Shift mirror line to right side
    ===============================================================================
    '''
    def __init__(self, filename, orig_image=None):
        self.filename = filename
        self.BLUE = [255,0,0]
        self.RED = [0,0,255]
        self.GREEN = [0,255,0]
        self.BLACK = [0,0,0]
        self.WHITE = [255,255,255]
        self.CLEAR_UPWARD = {'color': self.BLACK}
        self.CLEAR_DOWNWARD = {'color': self.BLACK}

        if os.name == 'posix':
            self.KEY_LEFT = 81
            self.KEY_RIGHT = 83
        elif os.name == 'nt':
            self.KEY_LEFT = 2424832
            self.KEY_RIGHT = 2555904

        # flags & others
        self.__transparent_bg = None
        self.__is_body = False
        self.__was_left_draw = False
        self.__is_left_draw = False
        self.__is_left_label = False
        self.__was_right_draw = False
        self.__is_right_draw = False
        self.__is_right_label = False

        # image
        if orig_image is None:
            self.__orig_img = cv2.imread(filename)
        else:
            self.__orig_img = orig_image

        self.__panel_img = self.__orig_img.copy()
        self.__show_img = self.gen_transparent_bg(self.__orig_img)

        # metadata
        self.__mirror_line = self.gen_mirror_line(self.__orig_img)
        self.__mirror_shift = None
        self.__label_l_block = []
        self.__label_r_block = []
        self.__label_l_track = []
        self.__label_r_track = []
        self.__forewings_color = {'left': None, 'right': None}
        self.__backwings_color = {'left': None, 'right': None}
        self.__body_color = None
        self.__forewings_coor = {'left': None, 'right': None}
        self.__backwings_coor = {'left': None, 'right': None}
        self.__body_coor = None
        self.__forewings = None
        self.__backwings = None
        self.__body = None

    @property
    def orig_image(self):
        return self.__orig_img.copy()

    @property
    def show_image(self):
        show_img = tuple()
        if self.__forewings is not None: show_img += (self.__forewings,)
        if self.__body is not None: show_img += (self.__body,)
        if self.__backwings is not None: show_img += (self.__backwings,)
        if show_img:
            show_img = np.vstack(show_img)
            h, w, channels = show_img.shape
            show_img = cv2.resize(show_img, (int(w/2), int(h/2)))
            show_img = show_img.astype('uint8')
            return show_img
        else:
            return self.__transparent_bg

    @property
    def mirror_line(self):
        return self.__mirror_line

    @mirror_line.setter
    def mirror_line(self, ptx):
        assert isinstance(ptx, tuple) and len(ptx) == 2
        self.__mirror_line = ptx

    def init_wings_image(self):
        self.__forewings = self.__transparent_bg.copy()
        self.__backwings = self.__transparent_bg.copy()

    def gen_transparent_bg(self, image):
        '''
        generate transparents background
        '''
        # assert isinstance(shape, tuple) and len(shape) == 3
        img = np.zeros(image.shape) * 255
        h, w, channel = img.shape
        _col = [False, True] * math.ceil((w/2))
        _row = [_col[1:], _col[:-1]] * int(h/2)

        if h % 2: _row.append(_col[1:])
        _mat = _row
        _mat = np.array(_mat)

        img[_mat] = 125
        self.__transparent_bg = img
        return img

    def gen_mirror_line(self, image, scope=10):
        '''
        generate mirror line when initial
        '''
        img = image.copy()
        h, w, _ = img.shape
        line_x = int(w/2)
        approach_x = [line_x]

        while True:
            max_similarity = None

            for x in range(line_x-scope, line_x+scope):
                min_w = min(x, w-x)
                sim = cosine(
                   img[0:h, x-min_w:x].flatten(),
                    np.fliplr(img[0:h, x:x+min_w].copy()).flatten())

                if max_similarity is None or sim > max_similarity[1]:
                    max_similarity = (x, sim)

            if max_similarity[0] == line_x: break
            else: line_x = max_similarity[0]

        logging.info('generate mirror line {0}'.format(((line_x, 0), (line_x, h))))
        return ((line_x, 0), (line_x, h))

    def reset(self):
        '''
        reset all metadata and image
        '''
        self.__panel_img = self.__orig_img.copy()

        if self.__was_left_draw or self.__was_right_draw:
            self.__was_left_draw = False
            self.__is_left_draw = False
            self.__is_left_label = False
            self.__was_right_draw = False
            self.__is_right_draw = False
            self.__is_right_label = False
            self.__label_l_track = []
            self.__label_r_track = []
            self.__forewings_color = {'left': None, 'right': None}
            self.__backwings_color = {'left': None, 'right': None}
            self.__body_color = None
            self.__forewings_coor = {'left': None, 'right': None}
            self.__backwings_coor = {'left': None, 'right': None}
            self.__body_coor = None
            self.__forewings = None
            self.__backwings = None
            self.__body = None
        elif self.__is_body:
            self.__is_body = False
            self.__mirror_shift = None

        self.draw()

    def draw(self):
        '''
        draw all metadata on image
        '''
        h, w, channel = self.__panel_img.shape

        if self.__mirror_line:
            pt1, pt2 = self.__mirror_line
            cv2.line(self.__panel_img, pt1, pt2, self.BLACK, 2)

            if self.__mirror_shift:
                shift = self.__mirror_shift
                l_x, r_x = (pt1[0]-shift, pt1[0]+shift)
                cv2.line(self.__panel_img, (l_x, 0), (l_x, h), self.BLUE, 2)
                cv2.line(self.__panel_img, (r_x, 0), (r_x, h), self.BLUE, 2)

        if self.__label_l_track:
            track = [ptx for block in self.__label_l_track for ptx in block]
            for l_ptx in track:
                cv2.circle(self.__panel_img, l_ptx, 2, self.BLACK)

        if self.__label_r_track:
            track = [ptx for block in self.__label_r_track for ptx in block]
            for r_ptx in track:
                cv2.circle(self.__panel_img, r_ptx, 2, self.BLACK)

    def get_component_by(self, threshold, nth, by):
        '''
        return nth connected component by the value in stat matrix
        in descending sequences
            cv2.CC_STAT_LEFT The leftmost (x) coordinate
            cv2.CC_STAT_TOP The topmost (y) coordinate
            cv2.CC_STAT_WIDTH The horizontal size of the bounding box
            cv2.CC_STAT_HEIGHT The vertical size of the bounding box
            cv2.CC_STAT_AREA The total area (in pixels) of the connected component
        '''
        output = cv2.connectedComponentsWithStats(threshold, 4, cv2.CV_32S)
        assert by in [
            cv2.CC_STAT_LEFT, cv2.CC_STAT_TOP,
            cv2.CC_STAT_WIDTH, cv2.CC_STAT_HEIGHT, cv2.CC_STAT_AREA]
        assert 0 < nth < output[0]

        cond_sequence = [(i ,output[2][i][by]) for i in range(output[0]) if i != 0]
        cond_sequence = sorted(cond_sequence, key=lambda x: x[1], reverse=True)
        return np.where(output[1] == cond_sequence[nth-1][0])

    def fixed(self, image, track, mode):
        fixed_img = image.copy()
        erase_img = np.zeros(image.shape)

        for block in track:
            if not block: continue
            block = sorted(block, key=lambda ptx: ptx[0])
            xp = [p[0] for p in block]
            fp = [p[1] for p in block]
            track = [(
                int(i), int(np.interp(i, xp, fp))
                ) for i in range(min(xp), max(xp)+1)]

            for ptx in track:
                x, y = ptx
                if mode is self.CLEAR_UPWARD:
                    erase_img[0:y, x] = image[0:y, x].copy()
                    erase_img = erase_img.astype('uint8')
                    fixed_img[0:y, x] = 255
                elif mode is self.CLEAR_DOWNWARD:
                    erase_img[y:, x] = image[y:, x].copy()
                    erase_img = erase_img.astype('uint8')
                    fixed_img[y:, x] = 255

        return (fixed_img, erase_img)

    def split_component(self):
        '''
        get the connected component by current stat
        '''

        def save_wings(forewings, backwings, side):
            assert side in self.__forewings_color.keys()
            assert side in self.__backwings_color.keys()

            # connected component
            foreparts = cv2.cvtColor(forewings, cv2.COLOR_BGR2GRAY)
            ret, threshold = cv2.threshold(foreparts, 250, 255, cv2.THRESH_BINARY_INV)
            foreparts = self.get_component_by(threshold, 1, cv2.CC_STAT_AREA)

            backparts = cv2.cvtColor(backwings, cv2.COLOR_BGR2GRAY)
            ret, threshold = cv2.threshold(backparts, 250, 255, cv2.THRESH_BINARY_INV)
            backparts = self.get_component_by(threshold, 1, cv2.CC_STAT_AREA)

            self.__forewings_color[side] = forewings[foreparts]
            self.__forewings_coor[side] = foreparts
            self.__forewings[foreparts] = forewings[foreparts]
            self.__forewings = self.__forewings.astype('uint8')
            self.__backwings_color[side] = backwings[backparts]
            self.__backwings_coor[side] = backparts
            self.__backwings[backparts] = backwings[backparts]
            self.__backwings = self.__backwings.astype('uint8')

        def clear_wings(value):
            img = self.__orig_img.copy()
            img[self.__forewings_coor['left']] = value
            img[self.__forewings_coor['right']] = value
            img[self.__backwings_coor['left']] = value
            img[self.__backwings_coor['right']] = value
            return img

        if self.__is_body:
            if self.__label_l_track or self.__label_r_track:
                self.init_wings_image()

                if self.__label_l_track:
                    x = self.__mirror_line[0][0]-self.__mirror_shift
                    y = max([ptx[1] for block in self.__label_l_track for ptx in block])

                    # fixed
                    forewings = self.__orig_img.copy()
                    forewings[:, x:] = 255
                    forewings[y:, :] = 255
                    forewings, remained = self.fixed(
                        forewings, self.__label_l_track, self.CLEAR_DOWNWARD)

                    backwings = self.__orig_img.copy()
                    backwings[:, x:] = 255
                    backwings[:y, :] = 255
                    padding = np.where(remained != [0])
                    backwings[padding] += remained[padding] - 255

                    save_wings(forewings, backwings, 'left')

                if self.__label_r_track:
                    x = self.__mirror_line[0][0]+self.__mirror_shift
                    y = max([ptx[1] for block in self.__label_r_track for ptx in block])

                    # fixed
                    forewings = self.__orig_img.copy()
                    forewings[:, :x] = 255
                    forewings[y:, :] = 255
                    forewings, remained = self.fixed(
                        forewings, self.__label_r_track, self.CLEAR_DOWNWARD)

                    backwings = self.__orig_img.copy()
                    backwings[:, :x] = 255
                    backwings[:y, :] = 255
                    padding = np.where(remained != [0])
                    backwings[padding] += remained[padding] - 255

                    save_wings(forewings, backwings, 'right')

                self.__body = self.__transparent_bg.copy()
                body = clear_wings(255)
                bodyparts = cv2.cvtColor(body, cv2.COLOR_BGR2GRAY)
                ret, threshold = cv2.threshold(bodyparts, 250, 255, cv2.THRESH_BINARY_INV)
                bodyparts = self.get_component_by(threshold, 1, cv2.CC_STAT_AREA)
                self.__body_color = bodyparts
                self.__body[bodyparts] = body[bodyparts]
                self.__body = self.__body.astype('uint8')

    def onmouse(self, event, x, y, flags, params):
        '''
        mouse event callback for opencv
        Phase 1: get body region by self.__is_body
        Phase 2: split forewings and backwings
            by self.__is_right_label and self.__is_left_label
        '''
        def save_track(side):
            if side == 'left':
                self.__label_l_track.append(self.__label_l_block)
                self.__label_l_block = []
                self.__is_left_draw = False
            elif side == 'right':
                self.__label_r_track.append(self.__label_r_block)
                self.__label_r_block = []
                self.__is_right_draw = False

        def handle_track(side):
            h, w, channels = self.__panel_img.shape
            pt1, pt2 = self.__mirror_line
            shift = abs(pt1[0] - x)
            l_ptx, r_ptx = ((pt1[0] - shift, y), (pt1[0] + shift, y))

            if side == 'left':
                if 0 < l_ptx[0] < pt1[0] - self.__mirror_shift:
                    self.__label_l_block.append(l_ptx)
                    cv2.circle(self.__panel_img, l_ptx, 2, self.BLACK, -1)
                elif l_ptx[0] == pt1[0] - self.__mirror_shift:
                    save_track(side)
                    self.__is_left_label = True
                    print('label left')

            elif side == 'right':
                if pt1[0] + self.__mirror_shift < r_ptx[0] < w:
                    self.__label_r_block.append(r_ptx)
                    cv2.circle(self.__panel_img, r_ptx, 2, self.BLACK, -1)
                elif r_ptx[0] == pt1[0] + self.__mirror_shift:
                    save_track(side)
                    self.__is_right_label = True
                    print('label right')

        if event == cv2.EVENT_LBUTTONDOWN:
            if self.__is_body:
                pt1, pt2 = self.__mirror_line

                if x < pt1[0] - self.__mirror_shift:
                    if not self.__was_left_draw:
                        self.__panel_img = self.__orig_img.copy()
                        self.__is_left_label = False
                        self.__label_l_track = []
                        self.draw()
                    self.__was_left_draw = True
                    self.__is_left_draw = True
                    self.__label_l_block = []
                    self.__label_r_block = []
                elif x > pt1[0] + self.__mirror_shift:
                    if not self.__was_right_draw:
                        self.__panel_img = self.__orig_img.copy()
                        self.__is_right_label = False
                        self.__label_r_track = []
                        self.draw()
                    self.__was_right_draw = True
                    self.__is_right_draw = True
                    self.__label_l_block = []
                    self.__label_r_block = []
                else:
                    logging.warning('Not valid region for labeling')

        elif event == cv2.EVENT_LBUTTONUP:
            if not self.__is_body:
                pt1, pt2 = self.__mirror_line
                self.__mirror_shift = abs(pt1[0] - x)
                self.__is_body = True
                self.draw()

            elif self.__is_left_draw:
                save_track('left')

            elif self.__is_right_draw:
                save_track('right')

            self.split_component()

        elif event == cv2.EVENT_MOUSEMOVE:
            # deside body region
            if not self.__is_body:
                h, w, channel = self.__orig_img.shape
                self.__panel_img = self.__orig_img.copy()
                self.draw()

                pt1, pt2 = self.__mirror_line
                shift = abs(pt1[0] - x)
                l_x, r_x = (pt1[0]-shift, pt1[0]+shift)
                cv2.line(self.__panel_img, (l_x, 0), (l_x, h), self.RED, 2)
                cv2.line(self.__panel_img, (r_x, 0), (r_x, h), self.RED, 2)

            # split forewings and backwings symmetrically
            elif self.__is_left_draw or self.__is_right_draw:

                if x < self.__mirror_line[0][0] and self.__is_left_draw:
                    handle_track('left')
                    if not self.__was_right_draw:
                        handle_track('right')
                if x > self.__mirror_line[0][0] and self.__is_right_draw:
                    handle_track('right')
                    if not self.__was_left_draw:
                        handle_track('left')

    def run(self):
        '''
        core function to do graph cut
        '''
        print(self.__doc__)
        self.reset()
        self.draw()
        cv2.namedWindow('displayed')

        if os.name == 'posix':
            cv2.namedWindow('panel', cv2.WINDOW_GUI_NORMAL + cv2.WINDOW_AUTOSIZE)
        elif os.name == 'nt':
            cv2.namedWindow('panel')

        cv2.setMouseCallback('panel', self.onmouse)
        cv2.moveWindow('panel', self.__panel_img.shape[1]+10, 0)

        while True:
            cv2.imshow('displayed', self.show_image)
            cv2.imshow('panel', self.__panel_img)
            k = cv2.waitKey(1)

            if k == 27:
                break
            elif k == ord('r'):
                self.reset()
            elif k == self.KEY_LEFT or k == ord('a'):
                # left
                pt1, pt2 = self.__mirror_line
                pt1 = (pt1[0]-1, pt1[1])
                pt2 = (pt2[0]-1, pt2[1])
                self.__mirror_line = (pt1, pt2)
                self.__panel_img = self.__orig_img.copy()
                self.draw()
            elif k == self.KEY_RIGHT or k == ord('d'):
                # right
                pt1, pt2 = self.__mirror_line
                pt1 = (pt1[0]+1, pt1[1])
                pt2 = (pt2[0]+1, pt2[1])
                self.__mirror_line = (pt1, pt2)
                self.__panel_img = self.__orig_img.copy()
                self.draw()

        cv2.destroyAllWindows()

