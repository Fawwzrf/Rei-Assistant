export class CameraManager {
  constructor() {
    this.videoElement = document.createElement('video');
    this.videoElement.autoplay = true;
    this.videoElement.style.display = 'none'; // Hidden by default
    document.body.appendChild(this.videoElement);
    
    this.canvas = document.createElement('canvas');
    this.ctx = this.canvas.getContext('2d');
    this.stream = null;
    this.isActive = false;
  }

  async startCamera() {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: { ideal: 1280 }, height: { ideal: 720 } } 
      });
      this.videoElement.srcObject = this.stream;
      this.isActive = true;
      console.log('[Camera] Started successfully');
      return true;
    } catch (err) {
      console.error('[Camera] Error starting camera:', err);
      this.isActive = false;
      return false;
    }
  }

  stopCamera() {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.videoElement.srcObject = null;
      this.stream = null;
    }
    this.isActive = false;
    console.log('[Camera] Stopped');
  }

  /**
   * Captures the current video frame, resizes it to max 512x512,
   * and returns it as a Base64 JPEG string.
   */
  captureFrameBase64() {
    if (!this.isActive || !this.videoElement.videoWidth) {
      return null;
    }

    const maxWidth = 512;
    const maxHeight = 512;
    let width = this.videoElement.videoWidth;
    let height = this.videoElement.videoHeight;

    // Calculate aspect ratio
    if (width > maxWidth || height > maxHeight) {
      const ratio = Math.min(maxWidth / width, maxHeight / height);
      width = width * ratio;
      height = height * ratio;
    }

    this.canvas.width = width;
    this.canvas.height = height;
    this.ctx.drawImage(this.videoElement, 0, 0, width, height);

    // Get Base64 JPEG (quality 0.8)
    const base64DataUrl = this.canvas.toDataURL('image/jpeg', 0.8);
    // Remove the data:image/jpeg;base64, prefix for Ollama
    return base64DataUrl.replace(/^data:image\/\w+;base64,/, '');
  }
}
