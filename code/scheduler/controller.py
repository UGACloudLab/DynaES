import json, ast
import pandas as pd


class Scheduler:
    """
    Variables: 
        1. resolution is the time period we want to increase after each schedule. Unit: second.
            '1': 1 second
            'None': jump to next schedule time

        2. sch_columns: 
            'policy': policy
            'schd_time': schedule's time
            'sensors': schedule's sensors
            'start_soc': soc before sensor operation
            'end_soc': soc after operation
            'exed': if schedule is executed
            'exe_time': execute time. values:['second','hour']
            'info': log
    """
    
    def __init__(self, simulator, sensor_path, sch_path, battery, policy=None, duration=7*24, resolution=None):
        
        self.sch_columns = ['policy','schd_time','sensors','start_soc','end_soc','exed','exe_time','priority','info']    # all infos need to log
        self.sensor_path = sensor_path
        self.sensors = self.load_sensor(sensor_path)
        self.duration = duration
        self.sch_path = sch_path
        self.sch = self.load_sch(sch_path)
        self.next_sch = None
        self.simulator = simulator
        self.timer = self.simulator.timer
        self.plc = policy
        self.batt = battery
        self.resolution = resolution
        self.simul_end_time = self.simul_end(self.resolution, self.duration)
        
        
    def load_sensor(self, sensor_file):
        # load sensor profile
        with open(sensor_file, "r") as f:
            loaded_dict = json.load(f)
        return loaded_dict
    
    
    def load_sch(self, sch_path):
        # load schedule file to dataframe
        try:
            df = pd.read_csv(sch_path,parse_dates=['schd_time','exe_time'],dtype={'policy':str,'exed':bool})
            df['sensors'] = df['sensors'].apply(lambda x: ast.literal_eval(x) if isinstance(x,str) else x)
            df['priority'] = df['priority'].apply(lambda x: ast.literal_eval(x) if isinstance(x,str) else x)
            df['info'] = df['info'].apply(lambda x: ast.literal_eval(x) if isinstance(x,str) else x)
        except:
            df = pd.DataFrame([],columns=self.sch_columns)
            df.to_csv(sch_path, index=False)
        
        return df
    
    
    def save_df(self, df, path):
        df.to_csv(path, index=False)
        return df
    
    
    def simul_end(self, resolution, duration):
        # cal end time for simulation
        if 'hour' in resolution:
            simul_end_input = self.timer.init_time + pd.Timedelta(hours=duration)
        elif 'second' in resolution:
            simul_end_input = self.timer.init_time + pd.Timedelta(seconds=duration)
        self.simulator.load_energy_pred(resolution=resolution)      # prepare energy data
        nearest_end = min( simul_end_input, self.simulator.energy_hour.index[-1] )
        return nearest_end
    
    
    def reset_prior(self, curr_time, tgt, sensors):
        # reset sensors prio to 0
        for s in tgt:
            sensors[s]['last_used_time'] = curr_time.isoformat()
            sensors[s]['time_gap'] = 1
            sensors[s]['priority'] = 1
        return sensors
    
    
    def update_prior(self, curr_time, sensors):
        # update prior
        for s in sensors.keys():
            gap = 1+ (curr_time-pd.to_datetime(sensors[s]['last_used_time'])).total_seconds() /3600
            sensors[s]['time_gap'] = gap
            sensors[s]['priority'] = abs(gap / sensors[s]['ideal_interval'])    # priority formula
            
        return sensors
        
        
    def save_sensor(self, sensor, sensor_file):
        # save sensor profile
        for s in sensor.keys():
            if isinstance(sensor[s]['last_used_time'], pd.Timestamp):
                sensor[s]['last_used_time'] = sensor[s]['last_used_time'].isoformat()
        with open(sensor_file, "w") as f:
            json.dump(sensor,f)
        return None
    
              
    def save_df(self, df, path):
        # save next schedule to file
        df.to_csv(path, header=True, index=False)
        
        
        
    def run_policy(self, battery, timer, sensors, simulator, policy, resolution, sch):
        # run policy kernel
        sch = policy.run(sensor_profile=sensors, timer=timer, simulator=simulator, battery=battery, resolution=resolution, sch=self.sch)
        return sch
        
        
    def sch_gen(self):
        """
        Schedule generator
        """
        nx_sch_df = pd.DataFrame()   # next schedule in dataframe format
        if 'hour'==self.resolution:       # time increase by hour
            nx_sch = self.run_policy(self.batt, self.timer, self.sensors, self.simulator, self.plc, resolution=self.resolution, sch=self.sch)
            #nx_sch = self.run_policy(self.batt, self.timer, self.sensors, self.simulator.load_energy_pred(resolution=self.resolution), self.plc, resolution=self.resolution, sch=self.sch)
            nx_sch['time'] = self.timer.curr_time + pd.Timedelta(hours=nx_sch['time'])
        elif 'second'==self.resolution:   # time increase by second
            nx_sch = self.run_policy(self.batt, self.timer, self.sensors, self.simulator.load_energy_pred(resolution=self.resolution), self.plc, resolution=self.resolution)
            nx_sch['time'] = self.timer.curr_time + pd.Timedelta(seconds=nx_sch['time'])
        else:
            print("resolution not recognized. ['hour','second']")
        
        nx_sch_df = pd.DataFrame([[self.plc.name,nx_sch['time'],nx_sch['sensors'],pd.NA,pd.NA,False,pd.NA,pd.NA,[]]], columns=self.sch_columns)
        
        return nx_sch_df
        
        
        
    def start(self):
        #self.simulator.load_energy_pred(resolution=self.resolution)  # load data
        while self.timer.curr_time <= self.simul_end_time:      # simulating makespan
            
            # init var
            info = []
            start_soc = self.batt.soc
            
            # 1. read sch
            if self.sch.empty:       # if init sch is empty, create one
                self.sensors = self.update_prior(self.timer.curr_time, self.sensors)
                self.sch = self.sch_gen()
                self.sch['schd_time'] = self.timer.curr_time
            last_sch = self.sch.iloc[self.sch.tail(1).index.values[0],:]    # read last sch from file
            
            if self.plc.name != last_sch['policy']:        # if new policy in, continue
                self.sch = pd.concat([self.sch,self.sch_gen()], ignore_index=True)
                self.sch.loc[self.sch.tail(1).index.values[0],'schd_time'] = self.timer.curr_time

            # 2. exe sch
            if (not last_sch['exed']) and (last_sch['schd_time']<=self.timer.curr_time):   # not exed, time ok
                
                # 2.1 exe sch
                tot_drain = sum([self.sensors[s]['consum'] for s in last_sch['sensors']]) + self.batt.base_consume     # drain batt: sensors + pi(next bootup)
                
                # 2.2 check batt
                if (self.batt.soc - tot_drain) > 0:      # if soc is enough
                    self.batt.drain( tot_drain )
                    self.sch.loc[self.sch.tail(1).index.values[0],'exed'] = True    # mark sch exe-ed
                    self.sch.loc[self.sch.tail(1).index.values[0],'start_soc'] = start_soc
                    self.sch.loc[self.sch.tail(1).index.values[0],'end_soc'] = self.batt.soc
                    self.sch.loc[self.sch.tail(1).index.values[0],'exe_time']=self.timer.curr_time+pd.Timedelta(seconds=1)
                    self.sensors = self.reset_prior(self.timer.curr_time, last_sch['sensors'], self.sensors)   # reset exe-ed prior
                    
                else:
                    info.append('soc not enough')   # log failure
                    
            # 3. update prior
            self.sensors = self.update_prior(self.timer.curr_time, self.sensors)   # update all prior
            self.sch.loc[self.sch.tail(1).index.values[-1],'priority'] = str(self.sensors)
            
            # 4. sch next
            nx_sch_df = None
            if self.sch.tail(1)['exed'].values[0]:       # sch exed
                nx_sch_df = self.sch_gen()               # sch next
                self.sch = pd.concat([self.sch, nx_sch_df], ignore_index=True)
                self.save_df(self.sch, self.sch_path)           # save sch
            
            # 5. time +
            if ('hour'==self.resolution) or (None==self.resolution):
                time_step = pd.Timedelta(hours=1)    #nx_sch_df['schd_time'].values[0]
            elif 'second'==self.resolution:
                time_step = pd.Timedelta(seconds=1)
            
            self.batt.charge( self.simulator.load_energy_true(start=self.timer.curr_time, end=self.timer.curr_time+time_step, resolution=self.resolution)[0] )   # charge batt with GT energy
            self.batt.leak( time_step )           # battery leak
            self.timer.forward( time_step )       # time increase
            self.save_sensor(self.sensors, self.sensor_path)
            
            