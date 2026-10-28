import { useCallback, useEffect, useRef, useState } from 'react'
import './App.css'
import './dashboard.css'
import {
  analyzeImage as apiAnalyzeImage,
  deleteAnalysis,
  getAnalysis,
  listAnalyses,
} from './api'
import ResultsDashboard from './components/ResultsDashboard'
import HistoryPanel from './components/HistoryPanel'
import Methodology from './components/Methodology'

function App() {
  const [selectedImage, setSelectedImage] = useState(null)
  const [preview, setPreview] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [error, setError] = useState('')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisResult, setAnalysisResult] = useState(null)
  const [analysisError, setAnalysisError] = useState('')
  const [historyItems, setHistoryItems] = useState([]);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState('');
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [openingId, setOpeningId] = useState(null);
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

    if (preview) URL.revokeObjectURL(preview)
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
      const data = await apiAnalyzeImage(selectedImage)
      setAnalysisResult(data)
      loadHistory()
      setTimeout(() => document.getElementById('analysis-results')?.scrollIntoView({ behavior: 'smooth' }), 50)
    } catch (err) {
      setAnalysisError(err.message || 'Something went wrong during analysis.')
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


  const loadHistory = useCallback(async () => {
    setIsHistoryLoading(true)
    setHistoryError('')
    try {
      const data = await listAnalyses(50, 0)
      setHistoryItems(data.items || [])
      setHistoryTotal(data.total ?? (data.items || []).length)
      setHistoryLoaded(true)
    } catch (err) {
      setHistoryError(err.message || 'Could not load analysis history.')
    } finally {
      setIsHistoryLoading(false)
    }
  }, [])

  useEffect(() => {
    loadHistory()
  }, [loadHistory])

  const openHistoricalAnalysis = async (analysisId) => {
    setHistoryError('')
    setOpeningId(analysisId)
    try {
      const data = await getAnalysis(analysisId)
      setAnalysisResult(data)
      setAnalysisError('')
      setTimeout(() => document.getElementById('analysis-results')?.scrollIntoView({ behavior: 'smooth' }), 50)
    } catch (err) {
      setHistoryError(err.message || 'Could not open this analysis.')
    } finally {
      setOpeningId(null)
    }
  }

  const deleteHistoricalAnalysis = async (analysisId) => {
    setHistoryError('')
    try {
      await deleteAnalysis(analysisId)
      if (analysisResult?.analysis_id === analysisId) setAnalysisResult(null)
      await loadHistory()
    } catch (err) {
      setHistoryError(err.message || 'Could not delete this analysis.')
    }
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
          <a href="#history">History</a>
          <a href="#how-it-works">How it works</a>
          <a href="#methodology">Methodology</a>
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
  <div className="face-scan-frame">
    <img
      src="/ai-human-face.png"
      alt="Split human and AI face for digital image forensics"
      className="hero-face-image"
    />

    <div className="face-scan-line" />

    <div className="face-image-label">
      <span className="face-label-dot" />
      HUMAN / AI ANALYSIS
    </div>
  </div>
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

        {analysisResult && <ResultsDashboard result={analysisResult} />}

        <HistoryPanel
          items={historyItems}
          total={historyTotal}
          loading={isHistoryLoading}
          loaded={historyLoaded}
          error={historyError}
          openingId={openingId}
          onRefresh={loadHistory}
          onOpen={openHistoricalAnalysis}
          onDelete={deleteHistoricalAnalysis}
        />

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
        <Methodology />
      </main>

      <footer className="footer">
        <a className="footer-brand" href="#home">DeepTrace<span> AI</span></a>
        <p>Explainable image forensics. Indicators are evidence to weigh, never proof of authenticity or forgery.</p>
        <nav className="dt-footer-links" aria-label="Footer">
          <a href="#analyzer">Analyzer</a>
          <a href="#history">History</a>
          <a href="#how-it-works">How it works</a>
          <a href="#methodology">Methodology &amp; privacy</a>
        </nav>
        <span>© 2026 DeepTrace AI · Evidence over assumptions.</span>
      </footer>
    </div>
  )
}

export default App