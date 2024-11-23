from eraser.models.big_lama.model.config import LaMaConfig
from torch.hub import download_url_to_file, get_dir
import os

from eraser.models.big_lama.model.lama import LaMa


def download_weight(path='models/big_lama/weight/big-lama.pt'):
    model_url = "https://github.com/Sanster/models/releases/download/add_big_lama/big-lama.pt"
    if os.path.exists(path):
        print("weight file already exists")
    else:
        print("download weight file from {}".format(model_url))
        download_url_to_file(path, model_url)
    return path


def load_lama_model(device='cpu', config: LaMaConfig = LaMaConfig()):
    model = LaMa(device, config)
    return model
