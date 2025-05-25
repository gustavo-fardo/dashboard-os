import tkinter as tk
from tkinter import ttk
from ttkbootstrap import Style
from PIL import Image, ImageTk, ImageDraw

class AreaChartFrame:
    def __init__(self, parent, chart_name, fill, width=400, height=200):
        self.style = Style(theme="cyborg")
        self.root = self.style.master
        self.parent = parent
        self.width = width
        self.height = height
        self.values = []
        self.max_values = 50
        self.max_value = 100
        
        self.left_pad = 40
        self.right_pad = 20
        self.top_pad = 20
        self.bottom_pad = 30
        
        self.fill_color = fill

        self.frame = ttk.Frame(parent, padding="5")
        self.frame.pack()
        
        self.title_label = ttk.Label(self.frame, text=chart_name, font=('Arial', 10))
        self.title_label.pack()
        
        self.chart_canvas = tk.Canvas(self.frame, width=width, height=height, bg='black')
        self.chart_canvas.pack()
        
        self.update_chart(0, 100)
    
    def update_chart(self, current_value, max_value):
        self.max_value = max(max_value, current_value, 10)
        
        if len(self.values) >= self.max_values:
            self.values.pop(0)
        self.values.append(current_value)
        
        img = Image.new('RGB', (self.width, self.height), 'black')
        draw = ImageDraw.Draw(img)
        
        chart_left = self.left_pad
        chart_right = self.width - self.right_pad
        chart_top = self.top_pad
        chart_bottom = self.height - self.bottom_pad
        chart_width = chart_right - chart_left
        chart_height = chart_bottom - chart_top
        
        draw.line([(chart_left, chart_top), (chart_left, chart_bottom)], fill='white', width=2)
        draw.line([(chart_left, chart_bottom), (chart_right, chart_bottom)], fill='white', width=2)
        
        for i in range(0, 11):
            value = self.max_value * i // 10
            y = chart_bottom - (i * chart_height // 10)
            
            draw.line([(chart_left, y), (chart_right, y)], fill="#000000")
            
            draw.text((5, y - 10), f"{value}", fill='white')
            
        if len(self.values) > 1:
            points = []
            for i, value in enumerate(self.values):
                x = chart_left + (i * chart_width // (self.max_values - 1))
                y = chart_bottom - (value * chart_height / self.max_value)
                points.append((x, y))
            
            
            points.append((points[-1][0], chart_bottom))
            points.append((points[0][0], chart_bottom))
            
            draw.polygon(points, fill=self.fill_color, outline="#d5d5d5")
            
        self.photo = ImageTk.PhotoImage(img)
        self.chart_canvas.create_image(0, 0, anchor='nw', image=self.photo)
