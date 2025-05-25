import tkinter as tk
from tkinter import ttk
from ttkbootstrap import Style
from PIL import Image, ImageTk, ImageDraw

class AreaChartFrame:
    def __init__(self, parent, chart_name, num_lines=2, labels=None, width=400, height=200):
        self.style = Style(theme="cyborg")
        self.root = self.style.master
        self.parent = parent
        self.width = width
        self.height = height
        self.max_values = 50
        self.max_value = 100
        
        self.left_pad = 40
        self.right_pad = 20
        self.top_pad = 20
        self.bottom_pad = 30
        
        self.num_lines = num_lines

        self.values = [[] for _ in range(num_lines)]
        self.colors = [
            '#d5d5d5', '#4fb3ff', '#ff4f81', '#4fff81', '#ffb34f', '#b34fff',
            '#ffd24f', '#4fffff', '#ff4fff', '#7f7fff'
        ]

        if labels is not None and len(labels) == num_lines:
            self.line_labels = labels
        else:
            self.line_labels = [f"Line {i+1}" for i in range(num_lines)]

        self.frame = ttk.Frame(parent, padding="5")
        self.frame.pack()
        
        self.title_label = ttk.Label(self.frame, text=chart_name, font=('Arial', 10))
        self.title_label.pack()
        
        self.chart_canvas = tk.Canvas(self.frame, width=width, height=height, bg='black')
        self.chart_canvas.pack()

        self.legend_frame = ttk.Frame(self.frame)
        self.legend_frame.pack(pady=(5, 0))
        self._draw_legend()

        self.update_chart([0]*num_lines, 100)

    def _draw_legend(self):
        for widget in self.legend_frame.winfo_children():
            widget.destroy()
        for idx, label in enumerate(self.line_labels):
            color_canvas = tk.Canvas(self.legend_frame, width=20, height=15, bg='black', highlightthickness=0)
            color_canvas.create_rectangle(0, 0, 20, 15, fill=self.colors[idx], outline='white')
            color_canvas.pack(side="left", padx=(5, 2))
            
            label_widget = ttk.Label(self.legend_frame, text=label)
            label_widget.pack(side="left", padx=(0, 10))

    def update_chart(self, current_values, max_value):
        self.max_value = max([max_value] + current_values + [10])
        
        for i, val in enumerate(current_values):
            if len(self.values[i]) >= self.max_values:
                self.values[i].pop(0)
            self.values[i].append(val)
        
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
        
        for idx, line_values in enumerate(self.values):
            if len(line_values) > 1:
                points = []
                for i, value in enumerate(line_values):
                    x = chart_left + (i * chart_width // (self.max_values - 1))
                    y = chart_bottom - (value * chart_height / self.max_value)
                    points.append((x, y))
                
                draw.line(points, fill=self.colors[idx], width=2)
        
        self.photo = ImageTk.PhotoImage(img)
        
        if not self.chart_canvas.winfo_exists():
            return
        
        self.chart_canvas.create_image(0, 0, anchor='nw', image=self.photo)
