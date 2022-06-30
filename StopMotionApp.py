from cv2 import rectangle
import kivy
from kivy.app import App
from kivy.uix.dropdown import DropDown
from kivy.core.window import Window

from kivy.config import Config
Config.set('graphics', 'width', '1920')
Config.set('graphics', 'height', '1080')
from kivy.properties import ObjectProperty

from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.behaviors.togglebutton import ToggleButtonBehavior

from kivy.metrics import Metrics, dp, cm
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.config import Config

from kivy.graphics.context_instructions import Color
from kivy.graphics.vertex_instructions import Rectangle, Line

import os
from numpy import take
from nikon import Nikon
import cv2

import glob

LIVE_VIEW_WIDTH = 1024
LIVE_VIEW_HEIGHT = 680

class KivyCV(Image):
    def my_init(self, camera, fps):
        print("**Initing KicyCV")
        self.camera = camera
        self.allow_stretch = True
        Clock.schedule_interval(self.update, 1.0 / fps)
        self.print = True
        self.overlay = None

    def set_selected_overlay(self, overlay):
        self.overlay = cv2.flip(overlay, 0)
        self.overlay = cv2.resize(self.overlay, (LIVE_VIEW_WIDTH, LIVE_VIEW_HEIGHT))

    def update(self, dt):
        if self.camera.dummy:
            jpg_frame = cv2.imread("./sample.jpg")
            frame = cv2.resize(jpg_frame, (LIVE_VIEW_WIDTH,LIVE_VIEW_HEIGHT))
        else:
            jpg_frame = self.camera.get_frame()
            frame = cv2.imdecode(jpg_frame, cv2.IMREAD_COLOR)

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

class PictureButton(ToggleButtonBehavior, Image):
    pass

class TouchyImage(PictureButton):
    def __init__(self, source, camera_view , **kwargs):
        PictureButton.__init__(self, **kwargs)
        self.source = source
        width = 100
        image = cv2.imread(source, cv2.IMREAD_COLOR)
        image = cv2.flip(image, 0)
        border_image = cv2.copyMakeBorder(
                 image, 
                 width, 
                 width, 
                 width, 
                 width,
                 cv2.BORDER_CONSTANT, 
                 value=(249,102,76)
              )
        border_image=cv2.resize(border_image, (image.shape[1],image.shape[0]))
        img1_texture = Texture.create(
            size = (image.shape[1], image.shape[0]), colorfmt='bgr'
        )
        img2_texture = Texture.create(
            size = (border_image.shape[1], border_image.shape[0]), colorfmt='bgr'
        )
        print(image.shape)
        print(border_image.shape)
        buf1 = image.tobytes()
        buf2 = border_image.tobytes()
        img1_texture.blit_buffer(buf1, colorfmt='bgr', bufferfmt='ubyte')
        img2_texture.blit_buffer(buf2, colorfmt='bgr', bufferfmt='ubyte')
        self.image = image
        self.regular_image = img1_texture
        self.selected_image = img2_texture
        self.camera_view = camera_view

    def set_camera_view(self, camera_view):
        self.camera_view = camera_view

    def on_state(self, widget, value):
        print("Touched", self.source, value)
        print(self.state)
        with self.canvas:
            # Add a red color
            if value == 'down':
                self.texture = self.selected_image
                self.camera_view.set_selected_overlay(self.image)

            if value == 'normal':
                self.texture = self.regular_image

class FilmStrip(ScrollView):
    def my_init(self, dirname = ".", camera_view=None):
        self.camera_view = camera_view
        self.update(dirname)

    def update(self, dirname):
        files = sorted(glob.glob(f"{dirname}/*.jpg"))
        print(files)
        contents = [TouchyImage(source = x, 
                            camera_view = self.camera_view,
                            size_hint=(None, None), 
                            size=(dp(90),dp(60))) for x in files]
        for c in contents:
            self.ids._layout.add_widget(c)

    def pressed(self, instance, touch):
        print("Pressed ", instance.source)

class PreviewVideo(BoxLayout):
    pass


class LoadDialog(FloatLayout):
    load = ObjectProperty(None)
    cancel = ObjectProperty(None)

class AppLayout(BoxLayout):
    pass

class StopMotionApp(App):
    def build(self):
        layout = AppLayout()
        print("******", layout.ids)
        self.camera = Nikon()
        self.camera_view = layout.ids._camera_view

        layout.ids._camera_view.my_init(camera = self.camera, fps = 30)
        layout.ids._film_strip.my_init(camera_view = 
                self.camera_view)
        layout.ids._fstop_chooser.values = self.camera.get_fstops()
        layout.ids._fstop_chooser.text = self.camera.get_fstop()
        layout.ids._shutter_speed_chooser.values = self.camera.get_shutter_speeds()
        layout.ids._shutter_speed_chooser.text = self.camera.get_shutter_speed()        
        layout.ids._iso_chooser.values = self.camera.get_isos()
        layout.ids._iso_chooser.text = self.camera.get_iso()

        layout.ids._iso_chooser.bind(text = self.set_iso)
        layout.ids._shutter_speed_chooser.bind(text = self.set_shutter_speed)
        layout.ids._fstop_chooser.bind(text = self.set_iso)

        layout.ids._preview_button.bind(on_press = self.show_video_preview)
        layout.ids._load_button.bind(on_press = self.show_load)

        self.dir = "."
        self.film_strip = layout.ids._film_strip
        self.load_button = layout.ids._load_button

        print("creating app")
        return layout

    def show_video_preview(self, event):
        preview = PreviewVideo()
        command_str = f"ffmpeg -y -framerate 2 \
                    -pattern_type glob -i '{self.dir}/*.jpg' \
                    -vf scale=600:400 -vcodec mjpeg -qscale 1 \
                    tmp.avi"
        print(command_str)
        os.system(command_str)
        popupWindow = Popup(title = "Preview", content=preview, size_hint=(None, None), size = (dp(800),dp(600) ))
        popupWindow.open()
        preview.ids._video_preview_button.bind(on_press = popupWindow.dismiss)

    def set_iso(self, spinner, text):
        self.camera.set_iso(text)

    def set_shutter_speed(self, spinner, text):
        self.camera.set_shutter_speed(text)
    
    def set_fstop(self, spinner, text):
        self.camera.set_fstop(text)

    def dismiss_popup(self):
        self._popup.dismiss()

    def show_load(self, event):
        content = LoadDialog(load=self.load, cancel=self.dismiss_popup)
        self._popup = Popup(title="Load file", content=content,
                            size_hint=(0.4, 0.6))
        self._popup.open()

    def load(self, path, filename):
        print(f"path: {path} filename: {filename}")
        folder = os.path.basename(path)
        self.dir = f"./projects/{folder}"

        self.load_button.text = folder
        self.dismiss_popup()

        self.film_strip.update(self.dir)
        
    def take_picture(self, instance):
        scale = 1.5
        filepath = self.camera.capture_image()
        self.new_pic.source = filepath
        new_image = cv2.imread(filepath)
        self.camera_view.overlay = cv2.resize(new_image, (1536, 1020))
        return None

    def on_stop(self):
        if not self.camera.dummy:
            self.camera.exit()

if __name__ == "__main__":
    StopMotionApp().run()
