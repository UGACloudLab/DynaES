


class Battery:
    """
    soc           : state of charge
    capacity      : capacity
    mini          : minimum energy
    standby       : standby time         # second
    leak_rate     : 1/self.standby     # percent / second
    base_consume  : basic energy consumption for each boot up
    
    """
    
    def __init__(self, soc, capacity, mini, standby, base_consume):
        self.soc = soc
        self.capacity = capacity
        self.mini = mini
        self.standby = standby              # second
        self.leak_rate = self.capacity / self.standby     # second
        self.base_consume = base_consume
        
    
    def drain(self, drain):
        soc = self.soc - drain
        self.soc = [0,soc][soc>0]
        
        
    def charge(self, gain):
        soc = self.soc + gain
        self.soc = [soc,self.capacity][soc>self.capacity]
        
        
    def leak(self, duration):
        self.soc -= (self.leak_rate * duration.total_seconds())
        
        
        