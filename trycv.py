from kivy.config import Config
Config.set('graphics', 'width', '1920')
Config.set('graphics', 'height', '1080')


from kivy.app import App
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.core.window import Window


from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.config import Config

from numpy import take
from nikon import Nikon
import cv2

import glob

class KivyCV(Image):
    def __init__(self, camera, fps, **kwargs):
        Image.__init__(self, **kwargs)
        self.camera = camera
        Clock.schedule_interval(self.update, 1.0 / fps)
        self.print = True
        self.overlay = None

    def update(self, dt):
        if self.camera.dummy:
            return
        scale = 1.5
        jpg_frame = self.camera.get_frame()
       
        frame = cv2.imdecode(jpg_frame, cv2.IMREAD_COLOR)
        frame = cv2.resize(frame, None, fx=scale, fy=scale)
        if self.overlay is not None:
            merged_image = cv2.addWeighted(frame, 0.7, self.overlay, 0.3, 0)
            buf = cv2.flip(merged_image, 0).tobytes()
        else:
            buf = cv2.flip(frame, 0). tobytes()
        image_texture = Texture.create(
            size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
        if self.print:
            print(frame.shape[1], frame.shape[0])
            self.print = False
        image_texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        # display image from the texture
        self.texture = image_texture

class PreviewFrame(Image):
    def __init__(self, fps, dirname = ".", **kwargs):
        Image.__init__(self, **kwargs)
        self.fps = fps
        self.dirname = dirname
        self.update_list()
        self.play_event = None

    def update_list(self):
        self.list =  sorted(glob.glob(f"{self.dirname}/*.jpg"))

    def update(self, dt):
        jpg_frame = self.next_frame()
        if jpg_frame is None:
            return
        frame = cv2.imread(jpg_frame, cv2.IMREAD_COLOR)
        buf = cv2.flip(frame, 0).tobytes()
        image_texture = Texture.create(
            size=(frame.shape[1], frame.shape[0]),
             colorfmt='bgr'
        )
        image_texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        self.texture = image_texture

    def on_touch_up(self, touch):
        print("Playing Movie")
        self.update_list()
        self.play_event = Clock.schedule_interval(self.update, 1.0 / self.fps)

    def next_frame(self):
        if len(self.list) > 0:
            return self.list.pop()
        else:
            print("done movie")
            Clock.unschedule(self.play_event)
            return None

class TouchyImage(Button):
    def __init__(self, source, **kwargs):
        Button.__init__(self, **kwargs)
        self.background_normal = source
        self.bind(on_press = self.onpress)
    def onpress(self, event):
        print("Touched", self.background_normal, event)

class Pictures(ScrollView):
    def __init__(self, dirname = "."):
        ScrollView.__init__(self, size_hint_x=None, size=(0.6*Window.width, 300))
        self.layout = GridLayout(rows=1, spacing=10, size_hint_x=None)
        self.layout.bind(minimum_width=self.layout.setter('width'))
        self.add_widget(self.layout)
        self.update(dirname)

    def update(self, dirname):
        files = sorted(glob.glob(f"{dirname}/*.jpg"))
        print(files)
        contents = [TouchyImage(source = x, size_hint=(None, None), size=(600,400)) for x in files]
        for c in contents:
            self.layout.add_widget(c)

    def pressed(self, instance, touch):
        print("Pressed ", instance.source)

class OpenCVApp(App):
    def __init__(self):
        super(OpenCVApp, self).__init__()
        self.camera = Nikon()
        print("creating app")

    def build(self):
        self.window = GridLayout()
        self.window.cols = 1
        self.window.size_hint = (0.6,0.7)
        self.window.pos_hint = {"center_x": 0.5, "center_y": 0.5}
        self.my_camera = KivyCV(camera=self.camera, fps=30)
        self.take_picture_button = Button(text="Take Picture", size_hint = (1, 0.1))
        self.take_picture_button.bind(on_press=self.take_picture)

        self.pic_history = Pictures()

        self.window.add_widget(self.my_camera)
        self.window.add_widget(self.take_picture_button)
        self.window.add_widget(self.pic_history)

        self.fstops = BoxLayout(orientation='horizontal', size_hint=(1,0.1))
        self.fstop_minus = Button(text="-")
        self.fstop_minus.bind(on_press = self.prev_fstop)

        self.fstop_label = Label(text=self.camera.get_fstop())
        self.fstop_plus = Button(text="+")
        self.fstop_plus.bind(on_press = self.next_fstop)

        self.fstops.add_widget(self.fstop_minus)
        self.fstops.add_widget(self.fstop_label)
        self.fstops.add_widget(self.fstop_plus)
        self.window.add_widget(self.fstops)

        self.shutter_speeds = BoxLayout(orientation='horizontal', size_hint=(1,0.1))
        self.shutter_speed_minus = Button(text="-")
        self.shutter_speed_minus.bind(on_press = self.prev_shutter_speed)

        self.shutter_speed_label = Label(text=self.camera.get_shutter_speed())
        self.shutter_speed_plus = Button(text="+")
        self.shutter_speed_plus.bind(on_press = self.next_shutter_speed)

        self.shutter_speeds.add_widget(self.shutter_speed_minus)
        self.shutter_speeds.add_widget(self.shutter_speed_label)
        self.shutter_speeds.add_widget(self.shutter_speed_plus)
        self.window.add_widget(self.shutter_speeds)

        self.preview = PreviewFrame(fps=10)
        self.window.add_widget(self.preview)
        return self.window

    def next_fstop(self, instance):
        print("next FSTOP")

        fstop = self.camera.get_fstop()
        next_stop = self.camera.get_next_in_list(self.camera.fstops, fstop)
        self.camera.set_fstop(next_stop)
        self.fstop_label.text = next_stop

    def prev_fstop(self, instance):
        print("Prev FSTOP")
        fstop = self.camera.get_fstop()
        prev_stop = self.camera.get_prev_in_list(self.camera.fstops, fstop)
        self.camera.set_fstop(prev_stop)
        self.fstop_label.text = prev_stop

    def next_shutter_speed(self, instance):
        print("next SS")
        ss = self.camera.get_shutter_speed()
        next_ss= self.camera.get_next_in_list(self.camera.shutter_speeds, ss)
        self.camera.set_shutter_speed(ss)
        self.shutter_speed_label.text = next_ss

    def prev_shutter_speed(self, instance):
        print("prev SS")
        ss = self.camera.get_shutter_speed()
        prev_ss= self.camera.get_prev_in_list(self.camera.shutter_speeds, ss)
        self.camera.set_shutter_speed(ss)
        self.shutter_speed_label.text = prev_ss

    def take_picture(self, instance):
        scale = 1.5
        filepath = self.camera.capture_image()
        self.new_pic.source = filepath
        new_image = cv2.imread(filepath)
        self.my_camera.overlay = cv2.resize(new_image, (1536, 1020))
        return None

    def on_stop(self):
        if not self.camera.dummy:
            self.camera.exit()


if __name__ == '__main__':
    OpenCVApp().run()