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
from kivy.core.window import Window
from kivy.uix.modalview import ModalView

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
from numpy import take, true_divide
from nikon import Nikon
import cv2
import random

import glob

LIVE_VIEW_WIDTH = 1024
LIVE_VIEW_HEIGHT = 680

root = None
project_dir = ""
app_dir = ""
main_app = None

def alert_box(info):
    view = ModalView(size_hint=(None, None), size=(dp(400), dp(200)))
    view.add_widget(Label(text=info))
    view.open()

class KivyCV(Image):
    def my_init(self, camera, fps):
        print("**Initing KicyCV")
        self.camera = camera
        self.allow_stretch = True
        Clock.schedule_interval(self.update, 1.0 / fps)
        self.fps = fps
        self.print = True
        self.overlay = None
        self.live = False
        self.preview = None
        self.image_is_selected = False

    def set_selected_overlay(self, overlay):
        self.overlay = cv2.flip(overlay, 0)
        self.overlay = cv2.resize(self.overlay, (LIVE_VIEW_WIDTH, LIVE_VIEW_HEIGHT))


    def set_selected_preview(self, preview):
        self.preview = cv2.flip(preview, 0)
        self.preview = cv2.resize(self.preview, (LIVE_VIEW_WIDTH, LIVE_VIEW_HEIGHT))

    def turn_live_on(self):
        print("Live view turned on")
        self.live = True
        self.update(1/30)

    def turn_live_off(self):
        print("Live view turned off")
        self.live = False
        self.update(1/30)

    def update(self, dt):
        # self.preview is 100% if there's no live view
        # self.overlay is 30% only if there's live view
        if self.live:
            if self.camera.dummy:
                jpg_frame = cv2.imread("./no-camera.png")
                frame = cv2.resize(jpg_frame, (LIVE_VIEW_WIDTH,LIVE_VIEW_HEIGHT))
            else:
                jpg_frame = self.camera.get_frame()
                frame = cv2.imdecode(jpg_frame, cv2.IMREAD_COLOR)
        else:
            if self.preview is not None:
                frame = self.preview
            else:
                jpg_frame = cv2.imread("./no-camera.png")
                frame = cv2.resize(jpg_frame, (LIVE_VIEW_WIDTH,LIVE_VIEW_HEIGHT))

        # the overlay should be the selected frame if any
        # or the most recent frame if none 
        #
        # print(self.image_is_selected, self.overlay.shape)       
        if self.image_is_selected and self.overlay is not None:
            # merge frame and overlay
            merged_image = cv2.addWeighted(self.overlay, 0.3, frame, 0.7, 0)
            buf = cv2.flip(merged_image, 0).tobytes()
        else:
            # only show frame
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

class LiveButton(ToggleButton):
    def push_down(self):
        self.state = "down"
        root.ids._camera_view.turn_live_on()

    def push_up(self):
        self.state = "normal"
        root.ids._camera_view.turn_live_off()

class TouchyImage(PictureButton):
    def __init__(self, source, filename, prev, next, camera_view, filmstrip, **kwargs):
        PictureButton.__init__(self, **kwargs)
        # the filename of the image, full path, small version
        self.source = source
        # the filename of the image, full path, large version
        self.filename = filename
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
        # the cv2 version of the image
        self.image = image
        # a drawable version of the image
        self.regular_image = img1_texture
        # a version of the image with a border
        self.selected_image = img2_texture
        # a pointer to the large central view of the window
        self.camera_view = camera_view
        # linked list pointers
        self.prev = prev
        self.next = next
        self.filmstrip = filmstrip

    def set_camera_view(self, camera_view):
        """ Define a pointer to the large central view of the window """
        self.camera_view = camera_view

    def on_state(self, widget, value):
        """ Respond to clicks on the image by selecting and outlining """
        print("Touched", self.source, value)
        toggle_button = root.ids._live_button

        print(self.state)
        with self.canvas:
            # Add a red color
            if value == 'down':
                self.select_image()
                toggle_button.push_up()
            if value == 'normal':
                self.deselect_image()    
                toggle_button.push_down()


    def select_image(self):
        self.texture = self.selected_image
        self.state = "down"
        # load the selected image in the large view
        self.camera_view.set_selected_preview(self.image)
        # and as the overlay
        self.camera_view.set_selected_overlay(self.image)
        self.camera_view.image_is_selected = True


        print("Selecting image, ", self)
        self.filmstrip.selected_widget = self
        print("Selected image, ", self.filmstrip.selected_widget)

    def deselect_image(self):
        self.texture = self.regular_image
        print("Deselecting image")
        self.filmstrip.selected_widget = None



class FilmStrip(ScrollView):
    def my_init(self, dirname = ".", camera_view=None):
        self.camera_view = camera_view
        self.image_list = []

        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_keyboard_down)
        self.undelete_list = []
        self.contents = []
        self.selected_widget = None
        self.dirname = None

    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        if keycode[1] == 'right':
            print("next")
            self.select_next()
        elif keycode[1] == 'left':
            print("prev")
            self.select_prev()
            print("selected = ", self.selected_widget)
        elif (keycode[1] == 'delete' or keycode[1] == 'backspace'):
            print("delete")
            self.delete_current()
        elif (keycode[1] == 'z'):
            print("undelete")
            self.undelete()
        elif (keycode[1] == 'spacebar'):
            print("Capture!")
            main_app.take_picture(None)
        else:
            print(keycode[1])
        return True

    def load_folder(self, dirname):
        """ Load the project in folder dirname, which
        must be in app_dir and start with projects/ """

        os.chdir(app_dir)
        self.dirname = dirname

        try:
            map = open(f"{dirname}/map.txt", "r")
        except:
            alert_box(f"No map.txt file in {app_dir}/{dirname}")
            return
        self.delete_all()
        files = map.readlines()
        try:
            fps = files.pop(0)
            fps = float(fps)
            fps = max(min(fps,30),2)
            root.ids._fps_slider.value = fps
        except Exception as e:
            print(e)
            print("Unable to set fps from file")
            if fps:
                files.insert(0, fps)
        files = [f"{dirname}/small-{f.strip()}" for f in files]
        print(files)
        self.image_list = [x for x in files]
        self.update()

    def write_map_file(self):
        if self.dirname:
           map_file = f"{self.dirname}/map.txt"
           map_backup = f"{self.dirname}/map_bk.txt"
           map = open(map_file, "w")
           os.system(f"cp {map_file} {map_backup}")
           pass
        else:
            alert_box(f"Unable to write map file at {app_dir}/{project_dir}/map.txt")
            return
        fps = root.ids._fps_slider.value
        fps = float(fps)
        map.write(f"{fps}\n")

        for file in self.image_list:
            entry = os.path.basename(file).replace("small-","") + "\n"
            map.write(entry)
        map.close()

    def update(self):
        self.contents = [TouchyImage(source = x,
                            filename = x.replace("small-", ""),
                            next = None,
                            prev = None,
                            camera_view = self.camera_view,
                            filmstrip = self,
                            size_hint=(None, None), 
                            size=(dp(90),dp(60))) for x in self.image_list]
        self.fix_pointers()   
        for c in self.contents:
            self.ids._layout.add_widget(c)

        if (len(self.contents) > 0) :
            self.selected_widget = self.contents[-1]
            self.selected_widget.select_image()
        else:
            self.selected_widget = None
    def fix_pointers(self):
        prev_widget = None
        minus_2 = None
        for c in self.contents:
            if prev_widget is not None:
                prev_widget.next = c
                prev_widget.prev = minus_2
            minus_2, prev_widget = prev_widget, c
        if len(self.contents) > 1:
            self.contents[-1].prev = self.contents[-2]
         
    def select_next(self):
        print("Advanced to next")
        current = self.selected_widget
        if current:
            next = current.next
            if next is not None:
                current.deselect_image()
                next.select_image()

    def select_prev(self):   
        print("Advanced to prev")
        current = self.selected_widget
        if current:
            print("select_prev, current = ", current)
            prev = current.prev
            print("select_prev, prev = ", prev)
            if prev is not None:
                current.deselect_image()
                prev.select_image()

    def delete_all(self):
        if not self.contents:
            return
        for c in list(self.contents):
            self.ids._layout.remove_widget(c)
            self.contents.remove(c)
            self.image_list.remove(c.source)

    def delete_current(self):
        current = self.selected_widget
        if current is None:
            return
        if current.prev is not None:
            current.prev.next = current.next
        if current.next is not None:
            current.next.prev = current.prev
            self.select_next()
        else:
            self.select_prev()
        self.ids._layout.remove_widget(current)
        self.contents.remove(current)
        self.image_list.remove(current.source)
        self.undelete_list.append((current, current.prev))
        self.write_map_file()

    def insert_after(self, new_elt, prev_elt):
        if prev_elt is not None and len(self.contents) > 0:
            for (i,c) in enumerate(self.contents):
                if c.source == prev_elt.source:
                    break
            loc = i+1
        else:
            loc = 0
        if loc < len(self.contents):
            self.contents.insert(loc, new_elt)
            self.image_list.insert(loc, new_elt.source)
            self.ids._layout.add_widget(new_elt, index = len(self.contents) - loc -1)
        else:
            self.contents.append(new_elt)
            self.image_list.append(new_elt.source)
            self.ids._layout.add_widget(new_elt)

        for c in self.contents:
            print(c.source)
        self.fix_pointers()
        if self.selected_widget:
            self.selected_widget.deselect_image()
        new_elt.select_image()
        self.write_map_file()

    def insert_after_selected(self, new_elt):
        prev_elt = self.selected_widget
        if prev_elt == None and len(self.contents) > 0:
            prev_elt = self.contents[-1]
        self.insert_after(new_elt, prev_elt)

    def undelete(self):
        if self.undelete_list is None or len(self.undelete_list) < 1:
            return
        elt, prev = self.undelete_list.pop()
        self.insert_after(elt, prev)
        elt.select_image()
    
    def export(self, event):
        for c, i in enumerate(self.contents):
            fromt = i.filename
            tot = os.path.dirname(fromt) + "/exports/" + "file" + f"{c:04}.jpg"
            os.system(f"cp {fromt} {tot}")
            print(f"exporting {fromt}")
        alert_box("Export Done")

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
        global root
        global app_dir
        global project_dir

        Window.size = (1440, 1080)
        Window.left = 0
        Window.top = 0

        app_dir = os.getcwd()

        self.layout = AppLayout()
        root = self.layout
        print("******", self.layout.ids)
        
        self.camera_view = self.layout.ids._camera_view
        self.film_strip = self.layout.ids._film_strip
        self.load_button = self.layout.ids._load_button
        self.connect_button = self.layout.ids._connect_button

        self.connect_camera(None)
        
        self.connect_button.bind(on_press = self.connect_camera)
        self.layout.ids._iso_chooser.bind(text = self.set_iso)
        self.layout.ids._shutter_speed_chooser.bind(text = self.set_shutter_speed)
        self.layout.ids._fstop_chooser.bind(text = self.set_iso)

        self.layout.ids._capture_button.bind(on_press = self.take_picture)
        self.layout.ids._preview_button.bind(on_press = self.show_video_preview)
        self.layout.ids._load_button.bind(on_press = self.show_load)
        self.layout.ids._export_button.bind(on_press = self.film_strip.export)
        self.layout.ids._live_button.bind(on_press = self.toggle_live_button)
        self.layout.ids._fps_slider.bind(on_touch_up = self.fps_changed)

        self.live_button = self.layout.ids._live_button

        print("creating app")
        return self.layout

    def connect_camera(self,event):
        self.camera = Nikon()

        self.layout.ids._camera_view.my_init(camera = self.camera, fps = 30)
        self.layout.ids._film_strip.my_init(camera_view = 
                self.camera_view)
        self.layout.ids._fstop_chooser.values = self.camera.get_fstops()
        self.layout.ids._fstop_chooser.text = self.camera.get_fstop()
        self.layout.ids._shutter_speed_chooser.values = self.camera.get_shutter_speeds()
        self.layout.ids._shutter_speed_chooser.text = self.camera.get_shutter_speed()        
        self.layout.ids._iso_chooser.values = self.camera.get_isos()
        self.layout.ids._iso_chooser.text = self.camera.get_iso()

    def show_video_preview(self, event):
        preview = PreviewVideo()
        os.chdir(app_dir)
        os.chdir(project_dir)
        print("Now in directory: ", os.getcwd())
        if not (os.path.exists("map.txt")):
            alert_box("No map file")
            os.chdir(app_dir)
            return
        try:
            print("Directory = ", os.getcwd())
            files = open("map.txt","r").readlines()
            ifile = open("input.txt", "w")
            framerate = self.layout.ids._fps_slider.value
            duration = 1/framerate
            for f in files:
                ifile.write(f"file {f.strip()}\n")
                ifile.write(f"duration {duration}\n")
            ifile.flush()
            ifile.close()
            command_str = f"ffmpeg -y -f concat -i input.txt -c:v libx264 -vf scale=600:400 -r 30 -pix_fmt yuv420p output.mp4"
            print(command_str)
            os.system(command_str)
            os.system("cat input.txt > i.txt")
            popupWindow = Popup(title = "Preview", content=preview, size_hint=(None, None), size = (dp(800),dp(600) ))
            popupWindow.open()
            preview.ids._video_player.source = f"{app_dir}/{project_dir}/output.mp4"
            preview.ids._video_preview_button.bind(on_press = popupWindow.dismiss)
        except Exception:
            alert_box("Unable to make preview")
        finally:
            os.chdir(app_dir)


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

    def toggle_live_button(self, event):
        live_button = self.layout.ids._live_button
        print("Live Button", live_button.state)

        state = live_button.state
        if live_button.state == 'down':
            live_button.push_down()
        elif live_button.state == 'normal':
            live_button.push_up()

    def load(self, path, filename):
        global project_dir

        print(f"path: {path} filename: {filename}")
        folder = os.path.basename(path)
        project_dir = f"projects/{folder}"

        self.load_button.text = folder
        self.dismiss_popup()

        self.film_strip.load_folder(project_dir)
    
    def fps_changed(self, event, touch):
        fps = self.layout.ids._fps_slider.value
        if touch.grab_current == self.layout.ids._fps_slider:
            print("Writing fps value: ", fps)
            self.film_strip.write_map_file()

    def take_picture(self, instance):

        id = random.randint(1000000,9999999)
        if self.camera.dummy:
            filepath, smallpath = "sample.jpg", "small-sample.jpg"
        else:
            filepath, smallpath = self.camera.capture_image()

        if project_dir == "":
            alert_box("No Project Selected!")
            return

        os.system(f"cp {filepath} {project_dir}/capture-{id}.jpg")
        os.system(f"cp {smallpath} {project_dir}/small-capture-{id}.jpg")
 
        filepath = f"{project_dir}/capture-{id}.jpg"
        smallpath = f"{project_dir}/small-capture-{id}.jpg"
        
        new_image = cv2.imread(filepath)
        new_elt = TouchyImage(source = smallpath,
                            filename = filepath,
                            next = None,
                            prev = None,
                            camera_view = self.camera_view,
                            filmstrip = self.film_strip,
                            size_hint=(None, None),
                            size=(dp(90),dp(60)))

        self.film_strip.insert_after_selected(new_elt)
        self.camera_view.overlay = cv2.resize(new_image, (LIVE_VIEW_WIDTH, LIVE_VIEW_HEIGHT))
        self.live_button.state = 'down'
        self.live_button.push_down()    
        return None

    def on_stop(self):
        if not self.camera.dummy:
            self.camera.exit()

if __name__ == "__main__":
    main_app = StopMotionApp()
    main_app.run()