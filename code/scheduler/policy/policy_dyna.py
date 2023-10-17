import pandas as pd

class Policy:
  """
  Policy
  return:
      { 'time': int, 'sensors': [] }
      time's unit is the energy_gain's step resolution
  """
  
  def __init__(self, name, energy_scaler_switch=True):
    self.name = name
    self.scaler_pred_col = 'DC_prediction_scaler'
    self.scaler_true_col = 'dc_actual'
    self.energy_pred_scale = None
    self.energy_true = None
    self.energy_scaler_switch = energy_scaler_switch

    
  def run(self, timer, battery, sensor_profile, simulator, resolution, sch):
    energy_gain = simulator.load_energy_pred(resolution=resolution)    # prep pred energy dataframe on simulator
    batt = battery

    # exe energy and sch
    if 'hour'==resolution:              # set cal range to
      energy_gain = energy_gain[:72]    # x hours
    elif 'second'==resolution:
      energy_gain = energy_gain[:259200]

    sensors = list(sensor_profile.keys())
    consums = [sensor_profile[x]['consum'] for x in sensors]
    ideal_intervals = [sensor_profile[x]['ideal_interval'] for x in sensors]
    last_used_times = [sensor_profile[x]['last_used_time'] for x in sensors]
    time_gaps = [sensor_profile[x]['time_gap'] for x in sensors]
    prioritys = [sensor_profile[x]['priority'] for x in sensors]
    
    # accu energy
    accu_energy = [energy_gain[0]+batt.soc]        # init the accumulated energy: ([0,10,20],1)->[1,11,31]
    for i in range(1,len(energy_gain)):
      accu_energy.append(accu_energy[i-1]+energy_gain[i])
    
    # allocate energy
    energy_gain_sum, priority_sum = accu_energy[-1], sum(prioritys)
    tot_energy = energy_gain_sum - batt.mini        # gain(soc) - mini
    if tot_energy <= 0:        # if low predicted energy gain, sleep 3 days
      if 'hour'==resolution:
        return {'time': 24*3, 'sensors': [] }
      elif 'second'==resolution:
        return {'time': 24*3*3600, 'sensors': [] }
    energy_priority_ratio = tot_energy / priority_sum
    allocated_energy = [x * energy_priority_ratio for x in prioritys]
    
    # operation amount
    sensing_times = [x/y for x,y in zip(allocated_energy,consums)]
    #sensing_times_w_order = [[x[0],energy_gain_sum/(x[1]*x[2]), []] for x in sorted(list(zip(range(len(sensors)), sensing_times, consums)), key=lambda x: x[1], reverse=True) ]     # tot_engery / times*consum. ?
    
    # cal time
    interval_all_sensors = [len(energy_gain) / x for x in sensing_times]
    min_sensing_interval = min(interval_all_sensors)
    nx_sensor = []
    for i in range(len(interval_all_sensors)):
      if interval_all_sensors[i] - min_sensing_interval <= 1:
        nx_sensor.append(i)
    schded_sensor = [sensors[x] for x in nx_sensor]
    
    nx_schd = {'sensors': schded_sensor, 'time': max([interval_all_sensors[x] for x in nx_sensor]) }    # select the most frequent sensor
    req_energy = batt.base_consume + sum([sensor_profile[x]['consum'] for x in schded_sensor])   # calculate the needed energy for next schedule
    if not nx_schd['time'].is_integer():      # make the max 'op time' of sensors integer
      nx_schd['time'] = int(nx_schd['time']) + 1  
    
    if nx_schd['time'] < len(accu_energy):    # if time is out of energy prediction range 
      avai_energy = accu_energy[ nx_schd['time'] ]+batt.soc-batt.mini       # get the total available energy for the energy prediction range
    else:                                     # if 'op time' is in the range
      nx_schd['time'] = len(accu_energy)
        
    # search for the cloest time point that have enough energy, in case not enough energy during low-energy-gain time
    for i in range(int(nx_schd['time']),len(accu_energy)): 
      if accu_energy[i] > req_energy:
        nx_schd['time'] = i 
        break
    if accu_energy[-1] < req_energy:  # if insufficient energy for the whole time
      nx_schd['time'] += int(len(accu_energy) * ((req_energy-accu_energy[-1])/accu_energy[-1]))  # ask delay(proportional) based on curr weather
    
    if batt.soc < batt.mini-1: # if batt is low, sleep more hours
      #print('low: ', batt.soc, batt.mini, (batt.mini-batt.soc)/batt.mini, ((batt.mini-batt.soc)/batt.mini)*10* 1.0 ) 
      nx_schd['time'] += int(((batt.mini-batt.soc)/batt.mini)*8* 2.0)  # delay if low soc. 10: levels, 1.0: hour/level, unit: hour
      #nx_schd['time'] += int( batt.mini/(batt.mini-batt.soc) )*10* 1.0)  # delay if low soc. 10: levels, 1.0: hour/level, unit: hour
      if 'second'==resolution:
        nx_schd['time'] *= 60*60 
    
    # prevention for abnormal values
    if nx_schd['time']<0: 
      print(timer.curr_time, 'Warning: Negative: ', nx_schd['time'], '. Force to 8.')
      nx_schd['time'] = 8
    elif nx_schd['time'] > 72:
      print(timer.curr_time, 'Warning: Too long: ', nx_schd['time'], '. Force to 24.')
      nx_schd['time'] = 24
    
    return nx_schd
  
