const TECHNIQUES = [
  {
    name: 'Metadata & EXIF',
    does: 'Reads camera, software, timestamp and GPS fields embedded in the file.',
    cannot: 'It cannot prove an image is genuine: metadata is trivially edited or forged. Missing metadata is normal for images shared through social platforms and is not evidence of manipulation or AI generation.',
  },
  {
    name: 'Error Level Analysis (ELA)',
    does: 'Re-compresses the image as JPEG and visualises where the difference from the original is larger or smaller.',
    cannot: 'Bright areas are not proof of editing. Sharp edges, textures, resizing and repeated saving all alter the map. It is a visual aid for a human reviewer, not an automatic verdict, and DeepTrace never scores it automatically.',
  },
  {
    name: 'Noise & image statistics',
    does: 'Measures sharpness, a noise estimate, histogram entropy, channel statistics and JPEG quantization tables.',
    cannot: 'These are descriptive numbers. Beauty filters, denoising, screenshots and heavy compression change them for entirely innocent reasons, so no fixed threshold is used to accuse an image.',
  },
  {
    name: 'Provenance (C2PA content credentials)',
    does: 'Detects whether a C2PA/Content Credentials structure is embedded in the file.',
    cannot: 'Detection is not verification: DeepTrace does not validate signatures or certificate chains. Absence of credentials means little, because most tools and platforms strip them.',
  },
  {
    name: 'AI-generation detector',
    does: 'Runs a pretrained ONNX image classifier (when installed) and reports its raw score.',
    cannot: 'The score is uncalibrated and the model can be wrong on new generators, screenshots and re-compressed images. When the model or runtime is missing, the app says “unavailable” rather than guessing.',
  },
]

export default function Methodology() {
  return (
    <section className="dt-method" id="methodology" aria-label="Methodology">
      <span className="section-kicker">METHODOLOGY</span>
      <h2>What each technique can and cannot establish</h2>
      <p className="dt-muted">
        Forensic indicators are evidence to weigh, not verdicts. Several independent signals that point the same way are more
        informative than any single one, and a lack of indicators never proves an image is authentic.
      </p>
      <div className="dt-grid">
        {TECHNIQUES.map((t) => (
          <article className="dt-card" key={t.name}>
            <h3>{t.name}</h3>
            <p>
              <b>What it does.</b> {t.does}
            </p>
            <p>
              <b>What it cannot tell you.</b> {t.cannot}
            </p>
          </article>
        ))}
      </div>
      <div className="dt-alert dt-alert-amber">
        <b>Responsible use.</b> Do not use DeepTrace output as sole grounds to accuse a person or publish a claim of forgery. Combine it
        with source tracing, reverse-image search and expert review.
      </div>
      <div className="dt-card">
        <h3>Privacy &amp; data handling</h3>
        <ul className="dt-bullets">
          <li>The uploaded file is analysed in memory and is not written to disk by the backend.</li>
          <li>Stored per analysis: the result, a downscaled preview, the ELA map and the PDF report, in the backend’s local storage.</li>
          <li>Analyses are deleted on request from the History panel, and automatically after the configured retention period (default 30 days) when the backend starts.</li>
          <li>GPS coordinates and personal EXIF fields are redacted from stored results by default.</li>
          <li>There is no authentication; run this on a trusted machine or network.</li>
        </ul>
      </div>
    </section>
  )
}
