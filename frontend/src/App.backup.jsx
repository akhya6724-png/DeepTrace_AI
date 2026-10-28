
import { useRef, useState } from 'react'
import './App.css'

function App() {
  const [selectedImage, setSelectedImage] = useState(null)
  const [preview, setPreview] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [error, setError] = useState('')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisResult, setAnalysisResult] = useState(null)
  const [analysisError, setAnalysisError] = useState('')
  const fileInputRef = useRef(null)

  const handleFile = (file) => {
    if (!file) return

    setError('')

    if (!file.type.startsWith('image/')) {
      setError('Please select a valid image file.')
      return
    }

    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp']

    if (!allowedTypes.includes(file.type)) {
      setError('Please upload a JPG, PNG, or WEBP image.')
      return
    }

    if (file.size > 10 * 1024 * 1024) {
      setError('Image size must be 10 MB or less.')
      return
    }

    setSelectedImage(file)
    setPreview(URL.createObjectURL(file))
  }

const analyzeImage = async () => {
  if (!selectedImage) {
    setAnalysisError('Please select an image first.')
    return
  }

  setIsAnalyzing(true)
  setAnalysisError('')
  setAnalysisResult(null)

  try {
    const formData = new FormData()
    formData.append('file', selectedImage)

    const response = await fetch(
      'http://127.0.0.1:8000/api/v1/analyze',
      {
        method: 'POST',
        body: formData,
      }
    )

    const data = await response.json()

    if (!response.ok) {
      throw new Error(
        data.detail || 'Image analysis failed. Please try again.'
      )
    }

    setAnalysisResult(data)
  } catch (err) {
    setAnalysisError(
      err.message === 'Failed to fetch'
        ? 'Backend se connection nahi ho pa raha. Check karo ki backend server running hai.'
        : err.message || 'Something went wrong during analysis.'
    )
  } finally {
    setIsAnalyzing(false)
  }
}
  const handleInputChange = (event) => {
    handleFile(event.target.files?.[0])
    event.target.value = ''
  }

  const handleDrop = (event) => {
    event.preventDefault()
    setIsDragging(false)
    handleFile(event.dataTransfer.files?.[0])
  }

  const removeImage = () => {
    if (preview) URL.revokeObjectURL(preview)
    setSelectedImage(null)
    setPreview('')
    setError('')
  }

  return (
    <div className="app-shell">
      <header className="navbar">
        <a className="brand" href="#home" aria-label="DeepTrace AI home">
          <span className="brand-icon">
            <svg viewBox="0 0 40 40" fill="none" aria-hidden="true">
              <path
                d="M20 3.5 34 9v10.5c0 8.2-5.7 13.7-14 17-8.3-3.3-14-8.8-14-17V9l14-5.5Z"
                stroke="currentColor"
                strokeWidth="2"
              />
              <circle cx="20" cy="18" r="6" stroke="currentColor" strokeWidth="2" />
              <path d="m24.5 22.5 4 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              <path d="M13 29h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </span>
          <span className="brand-copy">
            <strong>DeepTrace<span> AI</span></strong>
            <small>IMAGE FORENSICS PLATFORM</small>
          </span>
        </a>

        <nav className="nav-links" aria-label="Main navigation">
          <a className="nav-active" href="#home">Home</a>
          <a href="#analyzer">Image Analyzer</a>
          <a href="#how-it-works">How it works</a>
        </nav>

        <a className="nav-cta" href="#analyzer">
          Analyze an image <span aria-hidden="true">↗</span>
        </a>
      </header>

      <main id="home">
        <section className="hero-section">
          <div className="hero-content">
            <div className="eyebrow">
              <span className="status-dot" />
              DIGITAL IMAGE FORENSICS
            </div>

            <h1>
              Look closer.
              <br />
              <span>Know what you see.</span>
            </h1>

            <p className="hero-description">
              Examine images with forensic analysis tools. Explore metadata,
              compression differences, and available evidence—all in one place.
            </p>

            <div className="hero-actions">
              <a className="primary-button" href="#analyzer">
                <span>Analyze your image</span>
                <span aria-hidden="true">→</span>
              </a>
              <a className="text-button" href="#how-it-works">
                Discover how it works <span aria-hidden="true">↓</span>
              </a>
            </div>

            <div className="trust-note">
              <span className="trust-icon">✓</span>
              Evidence-led analysis
              <span className="trust-separator">•</span>
              <span className="trust-icon">✓</span>
              Transparent limitations
            </div>
          </div>
          <div className="hero-visual" aria-label="Digital image forensics illustration">
            <div className="visual-orbit orbit-one" />
            <div className="visual-orbit orbit-two" />
            <div className="visual-glow" />

            <div className="visual-card visual-card-back">
              <div className="mini-card-heading">
                <span>IMAGE SIGNAL</span>
                <span className="mini-live">● ACTIVE</span>
              </div>
              <div className="signal-grid">
                {Array.from({ length: 49 }, (_, index) => (
                  <span
                    key={index}
                    className={`signal-cell signal-${(index * 7 + index % 5) % 4}`}
                  />
                ))}
              </div>
              <div className="signal-footer">
                <span>PIXEL ANALYSIS</span>
                <span>01 / 04</span>
              </div>
            </div>

            <div className="visual-shield">
              <svg viewBox="0 0 160 175" fill="none" aria-hidden="true">
                <path
                  d="M80 8 137 30v43c0 38-23 67-57 88C46 140 23 111 23 73V30L80 8Z"
                  fill="url(#shieldGradient)"
                  fillOpacity=".14"
                  stroke="url(#shieldStroke)"
                  strokeWidth="2"
                />
                <circle cx="80" cy="72" r="25" stroke="#9CD8FF" strokeWidth="2.5" />
                <circle cx="80" cy="72" r="13" stroke="#9CD8FF" strokeWidth="2" />
                <path d="m98 90 16 16" stroke="#9CD8FF" strokeWidth="4" strokeLinecap="round" />
                <path d="M55 119h50" stroke="#72B9FF" strokeWidth="2" strokeLinecap="round" />
                <path d="M64 128h32" stroke="#72B9FF" strokeWidth="2" strokeLinecap="round" />
                <defs>
                  <linearGradient id="shieldGradient" x1="23" y1="8" x2="137" y2="161" gradientUnits="userSpaceOnUse">
                    <stop stopColor="#59B9FF" />
                    <stop offset="1" stopColor="#716BFF" />
                  </linearGradient>
                  <linearGradient id="shieldStroke" x1="23" y1="8" x2="137" y2="161" gradientUnits="userSpaceOnUse">
                    <stop stopColor="#8FD7FF" />
                    <stop offset="1" stopColor="#8A83FF" />
                  </linearGradient>
                </defs>
              </svg>
            </div>

            <div className="floating-tag tag-top">
              <span className="tag-check">⌕</span>
              <span><strong>Forensic insights</strong><small>Evidence-based checks</small></span>
            </div>

            <div className="floating-tag tag-bottom">
              <span className="tag-check tag-blue">↗</span>
              <span><strong>Transparent results</strong><small>No unsupported claims</small></span>
            </div>
          </div>
        </section>

        <section className="capabilities" aria-label="Analysis capabilities">
          <div className="capability">
            <span className="capability-icon">⌕</span>
            <div><strong>Metadata inspection</strong><small>Explore available image information</small></div>
          </div>
          <div className="capability">
            <span className="capability-icon">▧</span>
            <div><strong>Error Level Analysis</strong><small>Review JPEG compression differences</small></div>
          </div>
          <div className="capability">
            <span className="capability-icon">◈</span>
            <div><strong>Evidence summary</strong><small>Understand findings and limitations</small></div>
          </div>
        </section>

        <section className="analyzer-section" id="analyzer">
          <div className="section-heading">
            <div>
              <span className="section-kicker">START YOUR ANALYSIS</span>
              <h2>Inspect an image</h2>
              <p>Upload an image to begin your forensic examination.</p>
            </div>
            <div className="privacy-badge">
              <span>▣</span> Supported: JPG, PNG, WEBP
            </div>
          </div>

          <div className="upload-panel">
            {!preview ? (
              <div
                className={`dropzone ${isDragging ? 'dropzone-active' : ''}`}
                onDragOver={(event) => {
                  event.preventDefault()
                  setIsDragging(true)
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
                  onChange={handleInputChange}
                  hidden
                />

                <div className="upload-icon">
                  <svg viewBox="0 0 48 48" fill="none" aria-hidden="true">
                    <path d="M24 31V9m0 0-8 8m8-8 8 8" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                    <path d="M9 29v8a3 3 0 0 0 3 3h24a3 3 0 0 0 3-3v-8" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
                  </svg>
                </div>

                <h3>Drop your image here</h3>
                <p>or select a file from your device to get started</p>

                <button
                  type="button"
                  className="browse-button"
                  onClick={() => fileInputRef.current?.click()}
                >
                  Browse image
                </button>

                <div className="upload-footnote">
                  <span>Maximum file size: 10 MB</span>
                  <span>•</span>
                  <span>JPG, PNG, WEBP</span>
                </div>
              </div>
            ) : (
              <div className="preview-panel">
                <div className="preview-image-wrap">
                  <img src={preview} alt="Selected image preview" className="preview-image" />
                </div>
                <div className="preview-details">
                  <span className="section-kicker">IMAGE READY</span>
                  <h3>{selectedImage.name}</h3>
                  <p>{(selectedImage.size / 1024 / 1024).toFixed(2)} MB · {selectedImage.type || 'Image file'}</p>
                  <div className="preview-actions">
                    <button
                      className="browse-button"
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                    >
                      Choose another
                    </button>
                    <button className="remove-button" type="button" onClick={removeImage}>
                      Remove image
                    </button>
                  </div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
                    onChange={handleInputChange}
                    hidden
                  />
                </div>
              </div>
            )}

            {error && <div className="error-message" role="alert">{error}</div>}

            <div className="analyze-row">
              <div className="analyze-note">
                <span className="note-icon">i</span>
                Analysis results depend on the available forensic checks.
              </div>
              
              <button
                 className="primary-button analyze-button"
                   type="button"
                  disabled={!selectedImage || isAnalyzing}
                   onClick={analyzeImage}
                    >
                  {isAnalyzing ? 'Analyzing image...' : 'Analyze image'}
                   <span aria-hidden="true">{isAnalyzing ? ' ⏳' : ' →'}</span>
                    </button>
            </div>
          </div>
        </section>
        
{analysisError && (
  <div className="error-message" role="alert">
    {analysisError}
  </div>
)}

{analysisResult && (
  <section className="analyzer-section" id="analysis-results">
    <div className="section-heading">
      <div>
        <span className="section-kicker">FORENSIC ANALYSIS</span>
        <h2>Analysis results</h2>
        <p>Review the findings returned by the forensic analysis engine.</p>
      </div>
      <div className="privacy-badge">
        ✓ Analysis completed
      </div>
    </div>

    <div className="upload-panel">
      <h3>1. Image information</h3>

      <p><strong>Filename:</strong> {analysisResult.image_info?.original_filename || 'Unavailable'}</p>
      <p><strong>Format:</strong> {analysisResult.image_info?.format || 'Unavailable'}</p>
      <p><strong>Dimensions:</strong> {analysisResult.image_info?.width ?? '—'} × {analysisResult.image_info?.height ?? '—'} pixels</p>
      <p><strong>File size:</strong> {analysisResult.image_info?.file_size_bytes != null
        ? `${(analysisResult.image_info.file_size_bytes / 1024).toFixed(2)} KB`
        : 'Unavailable'}</p>
      <p><strong>SHA-256:</strong></p>
      <p style={{ overflowWrap: 'anywhere' }}>
        {analysisResult.image_info?.sha256 || 'Unavailable'}
      </p>

      <hr />

      <h3>2. Metadata inspection</h3>
      <p>
        <strong>EXIF metadata:</strong>{' '}
        {analysisResult.metadata?.exif_present === true
          ? 'Present'
          : analysisResult.metadata?.exif_present === false
            ? 'Not found'
            : 'Unavailable'}
      </p>

      <p>
        <strong>Camera make:</strong>{' '}
        {analysisResult.metadata?.summary?.camera_make || 'Not available'}
      </p>

      <p>
        <strong>Camera model:</strong>{' '}
        {analysisResult.metadata?.summary?.camera_model || 'Not available'}
      </p>

      <p>
        <strong>GPS metadata:</strong>{' '}
        {analysisResult.metadata?.gps?.present === true
          ? 'Present in metadata'
          : analysisResult.metadata?.gps?.present === false
            ? 'Not detected'
            : 'Unavailable'}
      </p>

      <p className="analyze-note">
        Metadata can be missing, edited, or removed. Its presence does not
        prove that an image is authentic.
      </p>

      <hr />

      <h3>3. Error Level Analysis (ELA)</h3>
      <p>
        <strong>Status:</strong>{' '}
        {analysisResult.ela?.status || 'Unavailable'}
      </p>

      <p>
        <strong>Method:</strong>{' '}
        {analysisResult.ela?.method || 'Not available'}
      </p>

      <p>
        <strong>Mean difference:</strong>{' '}
        {analysisResult.ela?.difference_statistics?.mean ?? '—'}
      </p>

      <p>
        <strong>95th percentile:</strong>{' '}
        {analysisResult.ela?.difference_statistics?.p95 ?? '—'}
      </p>

      {analysisResult.ela?.evidence_url && (
        <div style={{ marginTop: '18px' }}>
          <h4>ELA evidence image</h4>
          <img
            src={`http://127.0.0.1:8000${analysisResult.ela.evidence_url}`}
            alt="Error Level Analysis evidence"
            style={{
              display: 'block',
              width: '100%',
              maxWidth: '520px',
              borderRadius: '12px',
              border: '1px solid #dce4ee',
            }}
          />
        </div>
      )}

      <hr />

      <h3>4. AI-generated image detection</h3>
      <p>
        <strong>Status:</strong>{' '}
        {analysisResult.ai_detection?.status === 'unavailable'
          ? 'Detector not configured'
          : analysisResult.ai_detection?.status || 'Unavailable'}
      </p>

      <p>
        {analysisResult.ai_detection?.explanation ||
          'This installation does not currently provide a validated AI-image detector.'}
      </p>

      <hr />

      <h3>5. Overall assessment</h3>
      <p>
        <strong>
          {analysisResult.overall_assessment?.category
            ?.replaceAll('_', ' ') || 'Assessment unavailable'}
        </strong>
      </p>

      <p>
        {analysisResult.overall_assessment?.summary ||
          'No assessment summary was returned by the backend.'}
      </p>

      <p className="analyze-note">
        These checks cannot independently prove whether an image is genuine,
        manipulated, AI-generated, or a deepfake.
      </p>

      <hr />

      <h3>6. Download forensic report</h3>
      <p>
        Download the report generated by the backend for this analysis.
      </p>

      <a
        className="primary-button"
        href={`http://127.0.0.1:8000${analysisResult.report_url}`}
        target="_blank"
        rel="noreferrer"
      >
        Open PDF report <span aria-hidden="true">↗</span>
      </a>
    </div>
  </section>
)}
        <section className="how-section" id="how-it-works">
          <div className="how-heading">
            <span className="section-kicker">A CLEARER WAY TO EXAMINE IMAGES</span>
            <h2>From image to insight</h2>
            <p>Understand what the available evidence says—and what it cannot establish.</p>
          </div>

          <div className="steps-grid">
            <article className="step-card">
              <span className="step-number">01</span>
              <div className="step-icon">↥</div>
              <h3>Upload an image</h3>
              <p>Choose a supported image file from your device and review its preview.</p>
            </article>
            <article className="step-card">
              <span className="step-number">02</span>
              <div className="step-icon">⌕</div>
              <h3>Examine evidence</h3>
              <p>Review metadata, image properties, and compression-based forensic indicators.</p>
            </article>
            <article className="step-card">
              <span className="step-number">03</span>
              <div className="step-icon">▤</div>
              <h3>Review the report</h3>
              <p>Read the findings, their limitations, and available evidence in a report.</p>
            </article>
          </div>

          <div className="disclaimer">
            <span className="disclaimer-icon">!</span>
            <p><strong>Forensic transparency matters.</strong> ELA and metadata alone cannot prove that an image is fake, authentic, AI-generated, or a deepfake. Results must be interpreted in context.</p>
          </div>
        </section>
      </main>

      <footer className="footer">
        <a className="footer-brand" href="#home">DeepTrace<span> AI</span></a>
        <p>Image forensics with clarity, context, and transparency.</p>
        <span>© 2026 DeepTrace AI · Evidence over assumptions.</span>
      </footer>
    </div>
  )
}

export default App