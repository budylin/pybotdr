import numpy as np
from datetime import datetime
from os import mkdir, path

def mydump(up_0, down_0):
    savepath = "/home/dts050511/dumps/" + datetime.now().isoformat().replace(":", "-")
    mkdir(savepath)
    np.savetxt(path.join(savepath, "up_0.txt"), up_0)
    np.savetxt(path.join(savepath, "down_0.txt"), down_0)
