import cv2
from eraser.models.big_lama.model.config import LaMaConfig
from eraser.models.big_lama.model.lama import LaMa


def load_lama_model(device='cpu', config: LaMaConfig = LaMaConfig()):
    model = LaMa(device, config)
    return model


class LaMaWorkerConfig:
    def __init__(self, device: str = 'cpu'):
        self.device = device


class LaMaWorker:
    def __init__(self, worker_config: LaMaWorkerConfig = LaMaWorkerConfig(), model_config: LaMaConfig = LaMaConfig()):
        self.worker_config = worker_config
        self.model_config = model_config
        self.model = load_lama_model(self.worker_config.device, self.model_config)

    def input_check(self, images, masks) -> bool:
        flag = True
        for i, (img, msk) in enumerate(zip(images, masks)):
            if img.shape[:2] != msk.shape:
                flag = False
                masks[i] = cv2.resize(msk, (img.shape[1], img.shape[0]))
        return flag

    def process(self, input_image, input_mask):
        input_image = cv2.cvtColor(input_image, cv2.COLOR_BGR2RGB)
        images = [input_image]
        masks = [input_mask]
        self.input_check(images, masks)  # Ensure input is correct before inference
        results = self.model(images, masks)
        return results


# Ejemplo de cómo usarlo:
if __name__ == "__main__":
    # Carga tus imagenes
    input_image = cv2.imread("images/image1.png")
    input_mask = cv2.imread("images/image1_mask.png", cv2.IMREAD_GRAYSCALE)  # Asegurate que la mascara está en escala de grises

    # Inicializa el trabajador y procesa la imagen y la máscara
    worker = LaMaWorker()
    results = worker.process(input_image, input_mask)

    # Manipula los resultados como desees
    # Por ejemplo, guardando las imágenes resultantes:
    for idx, result in enumerate(results):
        output_path = f"output/result_{idx}.png"
        cv2.imwrite(output_path, result)
