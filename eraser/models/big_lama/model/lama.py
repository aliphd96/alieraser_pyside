import os
from typing import List

import cv2
import numpy as np
import torch
from loguru import logger

from eraser.models.big_lama.model.utils import norm_batch_img, pad_batch_img_to_modulo, resize_batch_img
from eraser.models.big_lama.model.config import LaMaConfig

LAMA_MODEL_URL = os.environ.get(
    "LAMA_MODEL_URL",
    "https://github.com/Sanster/models/releases/download/add_big_lama/big-lama.pt",
)


class LaMa:
    # pad_mod = 8
    # pad_to_square = False
    # min_size = None

    def __init__(self, device='cpu', config: LaMaConfig = LaMaConfig()):
        self.config = config
        self.device = device
        # model_path = r'D:\code\SWDesign\hpc_backbone\models\big_lama\weight\big-lama.pt'  # fixed path
        model_path = self.config.path_to_model
        logger.info(f"Load LaMa model from: {model_path}")
        model = torch.jit.load(model_path, map_location=self.device)
        model = model.to(self.device)
        model.eval()

        self.model = model
        self.model_path = model_path

    def _pad_forward(self, images: List[np.ndarray], masks: List[np.ndarray]) -> List[np.ndarray]:
        origin_heights = [image.shape[0] for image in images]
        origin_widths = [image.shape[1] for image in images]

        pad_batch_image = pad_batch_img_to_modulo(images, mod=self.config.pad_mod, square=self.config.pad_to_square,
                                                  min_size=self.config.pad_min_size)

        pad_batch_mask = pad_batch_img_to_modulo(masks, mod=self.config.pad_mod, square=self.config.pad_to_square,
                                                 min_size=self.config.pad_min_size)

        logger.info(f"final forward pad size: {pad_batch_image[0].shape}")

        results = self.forward(pad_batch_image, pad_batch_mask)

        results = [results[i][0:origin_heights[i], 0:origin_widths[i], :] for i in range(len(results))]

        inpaintings = []
        for image, mask, result in zip(images, masks, results):
            mask = mask[:, :, np.newaxis]
            inpaintings.append(result * (mask / 255) + image[:, :, ::-1] * (1 - (mask / 255)))  # BGR Format

        return inpaintings  # BGR

    def forward(self, batch_image, batch_mask) -> List[np.ndarray]:
        """Input image and output image have same size
        image: [N, H, W, C] RGB
        mask: [N, H, W]
        return: BGR IMAGE
        """
        batch_image = norm_batch_img(batch_image)
        batch_mask = norm_batch_img(batch_mask)

        batch_mask = (batch_mask > 0) * 1
        # image = torch.from_numpy(image).unsqueeze(0).to(self.device)
        # mask = torch.from_numpy(mask).unsqueeze(0).to(self.device)

        batch_image = torch.from_numpy(batch_image).to(self.device)
        batch_mask = torch.from_numpy(batch_mask).to(self.device)

        inpainted_image = self.model(batch_image, batch_mask)

        cur_res = inpainted_image.permute(0, 2, 3, 1).detach().cpu().numpy()
        cur_res = np.clip(cur_res * 255, 0, 255).astype("uint8")
        # cur_res = cv2.cvtColor(cur_res, cv2.COLOR_RGB2BGR)
        cur_res = [cv2.cvtColor(img, cv2.COLOR_RGB2BGR) for img in cur_res]
        return cur_res

    @torch.no_grad()
    def __call__(self, images, masks):
        """
        images: [N, H, W, C] RGB, not normalized
        masks: [N, H, W]
        return: BGR IMAGE
        """
        logger.info(f"inference task start")
        origin_shapes = [img.shape[0:2] for img in images]

        reshape_images = resize_batch_img(images, self.config.resize_limit)
        reshape_masks = resize_batch_img(masks, self.config.resize_limit)

        results = self._pad_forward(reshape_images, reshape_masks)

        results = [
            cv2.resize(img, (shape[1], shape[0]), interpolation=cv2.INTER_CUBIC)
            for img, shape in zip(results, origin_shapes)
        ]

        for i in range(len(images)):
            origin_index = masks[i] < 127
            results[i][origin_index] = images[i][:, :, ::-1][origin_index]

        return results
