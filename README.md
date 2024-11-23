# AliEraser - Advanced Image Editor

AliEraser is an open-source image editing application that combines powerful AI-based image manipulation features with an intuitive user interface. Built with Python and PySide6, it leverages the LaMa (Large Mask) inpainting model for object removal and includes background removal capabilities.

![AliEraser App](https://img.shields.io/badge/App-AliEraser-blue)
![License](https://img.shields.io/badge/License-Open%20Source-green)
![Python](https://img.shields.io/badge/Python-3.7%2B-yellow)

## 🌟 Features

- **AI-Powered Object Removal**: Using LaMa (Large Mask) inpainting model
- **Background Removal**: Automatic background removal functionality
- **Interactive Drawing Tools**: 
  - Adjustable brush size
  - Undo/Redo functionality (Ctrl+Z / Ctrl+Shift+Z)
  - Mask visualization
- **Image Navigation**:
  - Zoom in/out (Mouse wheel)
  - Pan view (Middle mouse button or Ctrl + Left mouse button)
  - Grid background for better alignment
- **Image History**:
  - Keep track of previous edits
  - Easy access to editing history
  - Thumbnail preview
- **User-Friendly Interface**:
  - Progress indicators for processing
  - Status bar with helpful information
  - Intuitive toolbar layout

## 🚀 Getting Started

### Prerequisites

```bash
pip install -r requirements.txt
```

Required packages:
- PySide6
- OpenCV (cv2)
- NumPy
- rembg
- LaMa inpainting model dependencies

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/alieraser.git
cd alieraser
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python main.py
```

## 🎯 How to Use

1. **Open an Image**:
   - Click "Seleccionar Imagen" or use the file menu
   - Supported formats: PNG, JPG, XPM

2. **Remove Objects**:
   - Adjust brush size using the slider
   - Paint over the object you want to remove
   - Click "Borrar" to process
   - Wait for AI processing to complete

3. **Remove Background**:
   - Open your image
   - Click "Borrar Fondo"
   - Wait for automatic processing

4. **Image History**:
   - View previous edits in the bottom panel
   - Toggle history view with "Mostrar Lista de Imágenes"
   - Double-click thumbnails to restore previous versions

5. **Additional Tools**:
   - Use Ctrl+Z for undo
   - Use Ctrl+Shift+Z for redo
   - "Borrar Mascara" to clear current mask
   - "Volver a Original" to reset to original image

## 📺 Tutorial

Check out my YouTube tutorial for a detailed walkthrough of all features:
[Learn with Ali YouTube Channel](https://youtube.com/@learnwithaali)

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests

## ⚖️ License

This project is open source and available under the MIT License. Note: The sale of this software is prohibited.

## 🙏 Acknowledgments

- LaMa inpainting model creators
- rembg library developers
- PySide6 team
- All contributors and users

## 📞 Contact

- YouTube: [@learnwithaali](https://youtube.com/@learnwithaali)
- Created by Ali
