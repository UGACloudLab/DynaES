import json
import pandas as pd

class Reset:
    
    def __init__(self):
        pass
    
        
    def reset_sensor(self, sensor_file):
        # overwritten with backup file
        try:
            with open(sensor_file, "r") as f:
                loaded_dict = json.load(f)
        except:
            print("File not found!")
        with open(sensor_file, "w") as f:
            json.dump(loaded_dict, f)


    def reset_sch(self, path):
        # clean sch file
        df = pd.DataFrame()
        df.to_csv(path, index=False)


    def reset_files(self, sch_path, sensor_path):
        self.reset_sch(sch_path)
        self.reset_sensor(sensor_path)

    