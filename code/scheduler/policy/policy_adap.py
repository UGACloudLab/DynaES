
class Policy:
  """
  Policy 
  return:
      { 'time': int, 'sensors': [] }
      time's unit is the energy_gain's step size
  """
  
  def __init__(self, name, interval=None):
    self.name = name
    self.interval = interval
    
    
  def run(self, battery, timer, sensor_profile, simulator, resolution, sch):
    if self.interval:
      interval = self.interval
    elif 'hour'==resolution:
      interval = 1
    elif 'second'==resolution:
      interval = 3600
    
    soc_perc = battery.soc/battery.capacity
    if soc_perc >= 0.8:
        interval = interval * 1
    elif soc_perc >= 0.6:
        interval = interval * 2
    elif soc_perc >= 0.4:
        interval = interval * 4
    elif soc_perc >= 0.2:
        interval = interval * 8

    nx_sch = {'time': interval, 'sensors': list(sensor_profile.keys())}
    
    
    return nx_sch