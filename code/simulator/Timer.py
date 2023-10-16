import pandas as pd



class Timer:
    def __init__(self, init_time, curr_time=None):
        self.init_time = init_time
        self.curr_time = init_time if not curr_time else curr_time
        
    def step(self, size=1):
        # size unit: second
        self.curr_time += pd.Timedelta(seconds=size)
    
    def forward(self, step):
        self.curr_time += step


    def backward(self, step):
        self.curr_time -= step






