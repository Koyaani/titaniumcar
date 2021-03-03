import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

import pygame

import cv2

import string
import random
from math import atan
import colorsys

letters = string.ascii_lowercase

WHITE = (255, 255, 255)
BLUE = (0, 0, 255)

# input image dimensions
WIDTH, HEIGHT = 456, 228

class ImageManagement:
    """
    The images are:
        - loaded from a video
        - transformed in pygame format
        - saved with labels
        
    Moreover, there is undo feature.
    3 attributes manage the undo :
     - prev: the previous image (data)
     - prev_name: the filename of the saved images
     - keep: the buffer where the current image is stored 
             when the previous image is load
    """
    def __init__(self, videopath, imagefolder):
        """
        Open video, create random string for image names and init attributes
        
        @param videopath: string path to a video
        @param imagefolder: string path to the folder where the images will be saved
        """
        self.videopath = videopath
        
        if not os.path.exists(imagefolder):
            os.mkdir(imagefolder)
        self.imagefolder = imagefolder
        
        self.cap = cv2.VideoCapture(videopath)
        if (self.cap.isOpened()== False): 
            print("Error opening video stream or file")
            
        self.prev = None
        self.prev_name = None
        self.current = None
        self.keep = None
        
        self.i = 0
        
        # add prefix for filename to prevent overwritting
        self.rd_s = ''.join(random.choice(letters) for i in range(5))
        
    def goto(self, num):
        """
        Drop i frames from the video
        
        @param num: the number of frame to skip
        @return: bool indicate if the video is not finished
        """
        for _ in range(num):
            ret, _ = self.cap.read()
            if not ret:
                return False
        return True
            
    def format(self, frame):
        """
        Transform the frame to:
         - image to save (frame)
         - image to display (image)
         
        @param frame: an image rgb matrix
        @return: the gray reduce frame and the frame in pygame format
        """
        frame_b = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        frame_b = cv2.resize(
            frame, (0,0), fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA
        )
        
        image = pygame.image.frombuffer(frame, frame.shape[1::-1], "RGB")
        image = pygame.transform.scale(image, (WIDTH*2, HEIGHT*2))
        
        return frame_b, image
        
    def next_image(self):
        """
        Load an image from the buffer if it's not empty. In any other case, load it from the video
        
        @return: an image if the video is not finished else None
        """
        if self.keep is not None:
            self.current = self.keep
            self.keep = None
            return self.current[1]
        #return None
        
        ret, frame = self.cap.read()
        self.i += 1
        if ret:
            frame, image = self.format(frame)
            entry = (frame, image)
            self.current = entry
            return image
        
    def prev_image(self):
        """
        Undo the last image labeling.
        If there is no image before or if there was a undo just before
        
        @return: a frame if undo can be done else None
        """
        if self.prev is not None:
            self.keep = self.current
            self.current = self.prev
            self.prev = None
            
            if os.path.exists(self.prev_name):
                os.remove(self.prev_name)
            return self.current[1]
        else:
            return None
            
    def save_image(self, theta, norm, trash=False):
        """
        Save the last image send (in next_image or prev_image)
        and place this image in "previous" state
        But if trash is True, the image will not be save on the disk
        
        @param theta: an angle (value between -1 and 1)
        @param norm: an distance (value between 0 and 1)
        @param trash: boolean indicating if the image is not saved
        """
        filename = "{}{}_frame{}_{:.3f}_{:.3f}.png".format(
                    self.imagefolder,
                    self.rd_s,
                    self.i,
                    theta, norm)
        self.prev_name = filename
        self.prev = self.current
        frame = self.current[0]
        if trash:
            pass
        else:
            cv2.imwrite(filename, frame)


class App:
    """
    Oriented object of a pygame window
    """
    def __init__(self, manager):
        """
        Init numeric/bool attributes
        and add manager in attribute
        
        @param manage: an ImageManagement object
        """
        self._running = True
        self._display_surf = None
        self.size = self.weight, self.height = WIDTH*2, HEIGHT*2
        
        self.images = manager
        self.x_c, self.y_c = self.weight/2, self.height

    def on_init(self):
        """
        Init pygame to create a window
        """
        pygame.init()
        self._display_surf = pygame.display.set_mode(
            self.size, pygame.HWSURFACE | pygame.DOUBLEBUF
        )
        self.c = pygame.time.Clock()
        
        self._running = True

    def on_event(self, event):
        """
        Event manager
        
        @param event: Pygame event object
        """
        # quit
        if event.type == pygame.QUIT:
            self._running = False
            
        # save image
        elif event.type == pygame.MOUSEBUTTONUP:
            self.images.save_image(self.angle, self.distance)
            print(self.angle, self.distance)
            self.next()
                
        elif event.type == pygame.KEYUP:
            # load previous image
            if event.key == pygame.K_SPACE: 
                prev_image = self.images.prev_image()
                if prev_image is not None:
                    self.image2display = prev_image
            # trash image
            elif event.key == pygame.K_x: 
                self.images.save_image(0, 0, trash=True)
                self.next()
        
            
    def on_loop(self):
        """
        Call on each refresh
        """
        pass
        
    def on_render(self):
        """
        Drawing actions
        """
        self._display_surf.blit(self.image2display, (0, 0))
        
        # draw center line
        end = self.end
        start = self.x_c, self.y_c
        pygame.draw.line(self._display_surf, WHITE, start, (self.x_c, 0), 10)
        
        # draw direction line
        distance = self.distance
        if distance == 0:
            color = BLUE
        elif distance < 1:
            color = 120 - distance * 120 # magic num
            color = colorsys.hsv_to_rgb(color/356, 1, 1)
            color = [int(c*255) for c in color]
        else:
            color = BLUE
              
        if end[0]-start[0] < 0:
            x_new = -10000
        else: 
            x_new = 10000
            
        if end[0]-start[0] == 0:
            x_new, y_new = self.x_c, 10000
        else:
            slope = float(end[1]-start[1])/float(end[0]-start[0]) #slope
            y_new = start[0] + slope * (x_new - start[1])  
        
        pygame.draw.line(self._display_surf, color, start, (x_new, y_new), 10)
        
        # and paste
        pygame.display.flip()
        
    def on_cleanup(self):
        """
        Action before program exit
        """
        pygame.quit()

    def on_execute(self):
        """
        Method to init and refresh the window
        """
        if self.on_init() == False:
            self._running = False

        self.image2display = self.images.next_image()
        while self._running:
            self.process_label()
            for event in pygame.event.get():
                self.on_event(event)
            self.on_loop()
            self.on_render()
            self.c.tick(20)
        self.on_cleanup()
        
    def process_label(self):
        """
        Transform mouse (x, y) coordinates to normalized polar coordinates
        """
        x_m, y_m = pygame.mouse.get_pos()
        x_c, y_c = self.x_c, self.y_c
        distance = ((x_m-x_c)**2 + (y_m-y_c)**2)**0.5
        
        distance = (distance - 70) / (400-70) # magic num
        if distance < 0:
            distance = 0
        elif distance > 1:
            distance = 1
        self.distance = distance
        
        x = abs(x_m-x_c)
        y = abs(y_m-y_c)
        if x_m < x_c:
            self.angle = -atan(x/y)
        else:
            self.angle = atan(x/y)
        
        self.end = x_m, y_m
        
    def next(self):
        """
        Snippet to get the next image
        """
        next_image = self.images.next_image()
        if next_image is None:
            self._running = False
        else:
            self.image2display = next_image
        

if __name__ == "__main__" :
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("video", help="video path")
    parser.add_argument("output", help="path to output folder")
    parser.add_argument("--frame", help="start to the nth frame")
    args = parser.parse_args()
    
    if args.output[-1] != "/":
        args.output += "/"
    
    manager = ImageManagement(args.video, args.output)
    if args.frame:
        if not manager.goto(int(args.frame)):
            exit(0)
    
    theApp = App(manager)
    theApp.on_execute()
