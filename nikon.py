from multiprocessing.spawn import get_preparation_data
import gphoto2 as gp
import io
import locale
import numpy as np
import os

class Nikon:
    def __init__(self):
        locale.setlocale(locale.LC_ALL, '')
        def callback(level, domain, string, data=None):
            print('Callback: level =', level, ', domain =', domain, ', string =', string)
            if data:
                print('Callback data:', data)
        callback_obj = gp.check_result(
                            gp.gp_log_add_func(gp.GP_LOG_VERBOSE, callback))
        print('callback_obj', callback_obj)
        try: 
            self.camera = gp.Camera()
            self.camera.init()
            
            self.fstops = self.get_fstops()
            print("Fstops = ", self.fstops)
            self.shutter_speeds = self.get_shutter_speeds()
            print("Shutter Speeds = ", self.shutter_speeds)

            self.set_liveview_maxsize()
            self.set_image_quality()

            print("Initialized camera")
            summary = str(self.camera.get_summary())
            print(summary[:60])
            self.dummy = False

        except Exception as e:
            print("No camera or camera error -- falling back")
            self.camera = None
            self.fstops = ['4','5','6']
            self.shutter_speeds = ['1','2','3']
            self.dummy = True
            
    def set_liveview_maxsize(self):
        self.set_setting("Live View Size", "XGA")

    def get_frame(self):
        camera_file = self.camera.capture_preview()
        file_data = camera_file.get_data_and_size()
        data = memoryview(file_data)
        # print("Got data size", len(data))
        # image = io.BytesIO(data)
        data_as_array = np.asarray(data)
        return data_as_array

    def set_image_quality(self):
        self.set_setting("Image Quality", "JPEG Fine")

    def capture_image(self):
        file_path = self.camera.capture(gp.GP_CAPTURE_IMAGE)
        camera_file = self.camera.file_get(file_path.folder, file_path.name, gp.GP_FILE_TYPE_NORMAL)

        temp_name = "tmp-img.jpg"
        target = os.path.join("/tmp", temp_name)
        small_target = os.path.join("/tmp", f"small-{temp_name}")
        print("Copying image to", target)
        camera_file.save(target)

        cmd = f"ffmpeg -y -i {target} -vf scale=2048:-1 {small_target}"
        os.system(cmd)
        return target, small_target

    def get_fstops(self):
        if (self.camera is None):
            return ["1.8","2.8","4","5.6","8","16","22","56"]
        config = self.camera.get_config()
        fstop = config.get_child_by_label("F-Number")
        choices = [x for x in fstop.get_choices()]
        return choices

    def get_shutter_speeds(self):
        if (self.camera is None):
            return ["100","200","400","500","800","1000"]
        config = self.camera.get_config()
        speeds = config.get_child_by_label("Shutter Speed 2")
        choices = [x for x in speeds.get_choices()]
        return choices        

    def get_isos(self):
        if (self.camera is None):
            return ["100","200","400","800","1600"]
        config = self.camera.get_config()
        speeds = config.get_child_by_label("ISO Speed")
        choices = [x for x in speeds.get_choices()]
        return choices

    def get_setting(self, label):
        if (self.camera is None):
            return ["Err"]
        
        config = self.camera.get_config()
        s = config.get_child_by_label(label)
        return(s.get_value())

    def set_setting(self, label, value):
        if (self.camera is None):
            return ["Err"]
        config = self.camera.get_config()
        s = config.get_child_by_label(label)
        s.set_value(value)
        self.camera.set_config(config)

    def get_fstop(self):
        if (self.camera is None):
            return "8"
        return self.get_setting("F-Number")

    def get_shutter_speed(self):
        if (self.camera is None):
            return "200"
        return self.get_setting("Shutter Speed 2")

    def get_iso(self):
        if (self.camera is None):
            return "1600"
        else:
            return self.get_setting("ISO Speed")

    def set_fstop(self, value):
        print("Setting fstop to ", value)
        if (self.camera is None):
            return None
        return self.set_setting("F-Number", value)

    def set_shutter_speed(self, value):
        print("Setting shutter to ", value)

        if (self.camera is None):
            return None
        return self.set_setting("Shutter Speed 2", value)

    def set_iso(self, value):
        print("Setting iso to ", value)

        if (self.camera is None):
            return None
        else:
            return self.set_setting("ISO Speed", value)

    def get_next_in_list(self, the_list, item):
        return self.get_prev_in_list(reversed(the_list), item)

    def get_prev_in_list(self, the_list, item):
        v = list(the_list)
        while (v.pop() != item):
            pass
        if len(v) > 0:
            return v.pop()
        else:
            return item

    def exit(self):
        self.camera.exit()
