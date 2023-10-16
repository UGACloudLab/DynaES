import pandas as pd



class Simulator:
    """
    Simulator for energy generation, both predicted and true energy.
    If 'start' and 'end' are given, that period's energy will return. Otherwise, a period of 5 days energy.
    'dc_alpha' is a discount factor for adjusting the solar panel size. If set to 1, the soar panel size is the default.
    
    """
    def __init__(self, timer, energy_pred_path, dc_alpha, energy_true_col, energy_pred_col):
        self.energy_pred_path = energy_pred_path
        self.timer            = timer
        self.dc_alpha         = dc_alpha
        self.energy_pred_col  = energy_pred_col  #'DC_prediction'
        self.energy_true_col  = energy_true_col  #'dc_power__422'
        self.energy_hour      = None             # dataframe of hourly data: pred & true
        self.energy_second    = None             # dataframe of sencondly data: pred & true
        self.load_energy_pred(resolution='hour')        
        self.load_energy_pred(resolution='second')        
       
 
    def load_energy_hour(self, start, end, column):
        if self.energy_hour is not None:
            df = self.energy_hour
        else:
            energy_pred = pd.read_csv(self.energy_pred_path)
            df = energy_pred #.iloc[:,[0,-2,-1]]
            df['time'] = pd.to_datetime(df['Time'])
            df = df.set_index('time')
            #df = df.drop('measured_on',axis=1)
            self.energy_hour = df
            
        res = df[ (df.index >= start) & (df.index < end) ][column]
        return res
        
        
    def load_energy_second(self, start, end, column):
        if self.energy_second is not None:
            df = self.energy_second
        else:
            # load hourly data
            if self.energy_hour is None:
                self.load_energy_hour(start, end, column)
            hour_data = self.energy_hour
            
            # break down hour into second
            df = hour_data[[self.energy_pred_col, self.energy_true_col]].copy()
            df[[self.energy_true_col, self.energy_pred_col]] = df[[self.energy_true_col, self.energy_pred_col]] / 3600
            
            # pad one row to break down the last row
            pad_row = df.tail(1).copy()
            pad_row.index = [pd.to_datetime(df.index[-1] + pd.Timedelta(hours=1))]    
            df = pd.concat([df, pad_row])
            
            df = df.resample('S').fillna(method='ffill').interpolate()
            df = df.drop(index=pad_row.index, axis=0)
            self.energy_second = df
        
        res = df[ (df.index >= start) & (df.index < end) ][column]
        return res
        
        
    def load_energy_driver(self, column, start=None, end=None, resolution='hour'):
        if not start:        
            start = self.timer.curr_time        # default start time is curr
        if not end:
            end = start + pd.Timedelta(days=5)  # default end time is in 5 days
        if 'hour' == resolution:
            return self.load_energy_hour(start, end, column).values * self.dc_alpha
        
        return self.load_energy_second(start, end, column).values * self.dc_alpha
        
        
    def load_energy_pred(self, start=None, end=None, resolution='hour', column=None):
        if not column:
            column = self.energy_pred_col
        return self.load_energy_driver(column=column, start=start, end=end, resolution=resolution)
        
        
    def load_energy_true(self, start=None, end=None, resolution='hour', column=None):
        if not column:
            column = self.energy_true_col
        return self.load_energy_driver(column=column, start=start, end=end, resolution=resolution)
        
    
    
    
    
