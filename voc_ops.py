from pathlib import Path
from PIL import Image

import shutil
import os

header_tmpl = \
    '''
    <annotation>
        <folder>VOC2007</folder>
        <filename>{}</filename>
        <source>
            <database>My Database</database>
            <annotation>CityPersons</annotation>
            <image>flickr</image>
            <flickrid>NULL</flickrid>
        </source>
        <owner>
            <flickrid>NULL</flickrid>
            <name>facevise</name>
        </owner>
        <size>
            <width>{}</width>
            <height>{}</height>
            <depth>3</depth>
        </size>
        <segmented>0</segmented>
    '''  # .format(img_name_with_ext, img_w, img_h)
object_tmpl = \
    '''
        <object>
            <name>{}</name>
            <pose>Unspecified</pose>
            <truncated>0</truncated>
            <difficult>0</difficult>
            <bndbox>
                <xmin>{:.3f}</xmin>
                <ymin>{:.3f}</ymin>
                <xmax>{:.3f}</xmax>
                <ymax>{:.3f}</ymax>
            </bndbox>
        </object>
    '''  # .format(lbl, x1, y1, x2, y2)
tail = '</annotation>'



class voc_formatter():
    def __init__(self, img_src_dir: Path, des_dir: Path, name_bbs_dict_train, name_bbs_dict_val, lbl_map,
                 file_exist_handling='PROCED'):
        self.img_src_dir = img_src_dir  # expected to have train/test/val dir and sub-dirs with city names
        self.des_dir = des_dir  # devkit dir
        self.dict_train = name_bbs_dict_train
        self.dict_val = name_bbs_dict_val
        '''
            key: img_name_with_ext
            value: 
                n* < lbl x1 y1 w h >
        '''
        self.file_exist_handling = file_exist_handling
        self.lbl_map = lbl_map
        if self.file_exist_handling == 'ABORT':
            self.rm = False
        elif self.file_exist_handling == 'PROCED':
            self.rm = True
        else:
            raise ValueError('''
            allowed option for "file_exist_handling":
            ABORT: abort the program
            PROCED: rm existing file
        ''')

        self.__prepare()
        self.train_set = []
        self.val_set = []

    def __prepare(self):
        '''
        -. create new dir at dest
        -. check src dir existence 
        -. check dict dimension
        :return: 
        '''
        # -. create new dir at dest
        if self.des_dir.exists():
            if self.rm:
                print('remove dir at {}'.format(self.des_dir.absolute()))
                os.system('rm -rf {}'.format(self.des_dir))
            else:
                raise FileExistsError("set file_exist_handling='PROCED'" +
                                      "to remove the dir at {}".format(self.des_dir.absolute()))
        data_dir = self.des_dir / 'data'
        self.anno_dir = data_dir / 'Annotations'
        self.set_dir = data_dir / 'ImageSets' / 'Main'
        self.img_dir = data_dir / 'JPEGImages'

        self.anno_dir.mkdir(parents=True)
        self.set_dir.mkdir(parents=True)
        self.img_dir.mkdir(parents=True)

        # -. check src dir existence
        self.img_train_dir = self.img_src_dir / 'train'
        self.img_val_dir = self.img_src_dir / 'val'
        if not self.img_train_dir.exists():
            raise FileNotFoundError('{} Not Found'.format(self.img_train_dir))
        if not self.img_val_dir.exists():
            raise FileNotFoundError('{} Not Found'.format(self.img_val_dir))

        # -. check dict dimension
        for tv, dict in zip(['train', 'val'], [self.dict_train, self.dict_val]):
            k = dict.keys()[0]  # check the 1st one
            if type(k) is not str:
                raise TypeError("[{} dict] Unexpected type: {}".format(tv, type(k)))
            bbs = dict[k]
            dim = bbs.shape[1]
            if dim != 5:
                raise ValueError("[{} dict] Unexpected dimension: ({} vs 5)".format(tv, dim))

    def __write_xml(self, img_name, w, h, bbs):
        content = header_tmpl.format(img_name, w, h)
        for bb in bbs:
            [lbl, x1, y1, x2, y2] = bb
            content += object_tmpl.format(self.lbl_map[lbl], x1, y1, x2, y2)
        content += tail
        xml_name = img_name.split('.')[0] + '.xml'
        xml_file = self.anno_dir / xml_name
        with open(xml_file, 'w') as f:
            f.write(content)

    def __run(self, src_img_dir: Path, name_bbs_dict: dict, name_set):
        '''
        1. get img w, h
        2. copy img
        3. write xml
        4. append name_set
        '''
        for k, v in name_bbs_dict.items():
            city_name = k.split('_')[0]
            img_file = src_img_dir / city_name / k

            # get img w, h
            with Image.open(img_file) as img:
                w, h = img.size

            # copy img
            dest_img = self.img_dir / k
            shutil.copyfile(img_file, dest_img)

            # write xml
            self.__write_xml(k, w, h, v)

            # append name_set
            name_set.append(k.split('.')[0])

    def __write_set_file(self, name_set, tv):
        set_file = self.set_dir / tv
        with open(set_file, 'w') as f:
            f.write('\n'.join(name_set))

    def run(self):
        '''
        1. process train/val
        2. write set file
        '''
        self.__run(self.img_train_dir, self.dict_train, self.train_set)
        self.__run(self.img_val_dir, self.dict_val, self.val_set)

        self.__write_set_file(self.train_set, 'train')
        self.__write_set_file(self.val_set, 'val')

        print('Done:')
        print('# train: {}'.format(len(self.train_set)))
        print('# val  : {}'.format(len(self.val_set)))


if __name__ == '__main__':

    vf = voc_formatter(0, Path('./test_devkit'), 0, 'PROCED')