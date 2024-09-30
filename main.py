from Experiment.Experiment import Experiment

def main():
    e = Experiment()
    e.start()

if __name__ == "__main__":
    main()

# old: (3,5,3, 0,0,0, 1,2,1, 2,4,2, 4,1,4, 5,3,5)
# new: (6,3,6, 0,0,0, 4,2,4, 2,1,2, 1,4,1, 5,6,5)
# Thermal Matching
# Pin   Color   MP1     MP2     MP3
# 27    Rot1    (?,?,?) (0,1,1) (1,1,0) 
# 29    Rot2    (0,0,0) (0,0,0) (0,0,0)
# 31    Gelb1   (1,0,0) (0,1,0) (1,0,0)
# 33    Gelb2   (0,1,0) (0,0,1) (0,1,0)
# 35    Rot3    (0,0,1) (1,0,0) (0,0,1)
# 37    Gelb3   (1,0,1) (1,1,0) (1,0,1)

# -242.02 C° => not connected 
# -241 C°    => shorted sensor
# 988.79 C°  => no sensor connected
