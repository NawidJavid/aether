export class AudioAnalyzer {
  private analyser: AnalyserNode;
  private dataArray: Uint8Array<ArrayBuffer>;

  constructor(audioContext: AudioContext, source: AudioNode) {
    this.analyser = audioContext.createAnalyser();
    this.analyser.fftSize = 256;
    this.analyser.smoothingTimeConstant = 0.6;
    source.connect(this.analyser);
    this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
  }

  /** Returns 0-1 amplitude representing current audio loudness. */
  getAmplitude(): number {
    this.analyser.getByteFrequencyData(this.dataArray);
    let sum = 0;
    for (let i = 0; i < this.dataArray.length; i++) sum += this.dataArray[i];
    const avg = sum / this.dataArray.length / 255;
    return Math.pow(avg, 0.7);
  }
}
