from pydantic import BaseModel


class LaMaConfig(BaseModel):
    path_to_model:str = r'eraser/models/big_lama/weight/big-lama.pt'
    pad_mod: int = 8
    pad_to_square: bool = False
    resize_limit: int = 512
    pad_min_size: int = 128
