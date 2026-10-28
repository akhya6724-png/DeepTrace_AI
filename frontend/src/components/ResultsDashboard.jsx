import { useState } from 'react'
import { absoluteUrl, downloadReport } from '../api'

const CATEGORY = {
  no_strong_indicators_found: {
    label: 'No strong indicators found',
    tone: 'neutral',
    note: 'This does not confirm the image is authentic or unedited.',
  },
  inconclusive: { label: 'Inconclusive', tone: 'amber', note: 'The available evidence is limited or mixed.' },
  potential_manipulation_indicators: {
    label: 'Potential inconsistencies detected',
    tone: 'amber',
    note: 'Indicators warrant closer review. They are not proof of manipulation.',
  },
  analysis_incomplete: { label: 'Analysis incomplete', tone: 'red', note: 'One or more checks could not run.' },
}

const STRENGTH_LABEL = { informational: 'Informational', weak: 'Weak indicator', moderate: 'Moderate indicator' }

const PROVENANCE_LABEL = {
  no_credentials_detected: 'No content credentials detected',
  credentials_detected_unverified: 'Credentials detected — NOT verified',
  error: 'Provenance check failed',
}

const AI_PREDICTION_LABEL = {
  ai_generated_likely: 'Detector leans: likely AI-generated',
  real_image_likely: 'Detector leans: likely real',
}

const INDICATOR_LABEL = {
  dimensions_and_aspect_ratio: 'Dimensions & aspect ratio',
  channel_statistics: 'Colour channel statistics',
  luminance_histogram: 'Luminance histogram',
  sharpness_laplacian_variance: 'Sharpness (Laplacian variance)',
  noise_estimate_sigma: 'Noise estimate (σ)',
  jpeg_quantization: 'JPEG quantization tables',
}

const prettify = (key) => INDICATOR_LABEL[key] || key.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase())

function formatValue(value) {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'number') return Number.isInteger(value) ? String(value) : String(Number(value.toFixed(4)))
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (typeof value === 'object') {
    return Object.entries(value)
      .map(([k, v]) => `${k.replace(/_/g, ' ')}: ${formatValue(v)}`)
      .join(' · ')
  }
  return String(value)
}

function formatBytes(bytes) {
  if (bytes == null) return '—'
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

function Bullets({ items }) {
  if (!items?.length) return null
  return (
    <ul className="dt-bullets">
      {items.map((item, i) => (
        <li key={i}>{item}</li>
      ))}
    </ul>
  )
}

function Card({ title, badge, badgeTone = 'neutral', children }) {
  return (
    <article className="dt-card">
      <header className="dt-card-head">
        <h3>{title}</h3>
        {badge && <span className={`dt-badge dt-badge-${badgeTone}`}>{badge}</span>}
      </header>
      {children}
    </article>
  )
}

function Limitations({ items, title = 'Limitations' }) {
  if (!items?.length) return null
  return (
    <details className="dt-details">
      <summary>{title}</summary>
      <Bullets items={items} />
    </details>
  )
}

function Finding({ finding }) {
  return (
    <li className="dt-finding">
      <div className="dt-finding-top">
        <strong>{finding.title}</strong>
        <span className={`dt-badge dt-badge-${finding.strength === 'informational' ? 'neutral' : 'amber'}`}>
          {STRENGTH_LABEL[finding.strength] || finding.strength}
        </span>
      </div>
      <p>{finding.observation}</p>
      <details className="dt-details">
        <summary>Method, meaning &amp; alternative explanations</summary>
        <p>
          <b>Method:</b> {finding.method}
        </p>
        <p>
          <b>Why it matters:</b> {finding.why_it_matters}
        </p>
        {finding.alternative_explanations?.length > 0 && (
          <>
            <b>Alternative explanations</b>
            <Bullets items={finding.alternative_explanations} />
          </>
        )}
        {finding.additional_evidence_needed?.length > 0 && (
          <>
            <b>Additional evidence that would help</b>
            <Bullets items={finding.additional_evidence_needed} />
          </>
        )}
      </details>
    </li>
  )
}

export default function ResultsDashboard({ result }) {
  const [downloadError, setDownloadError] = useState('')
  const [downloading, setDownloading] = useState(false)
  const [elaFailed, setElaFailed] = useState(false)

  const info = result.image_info || {}
  const meta = result.metadata || {}
  const ela = result.ela || {}
  const ai = result.ai_detection || {}
  const prov = result.provenance || {}
  const assessment = result.overall_assessment || {}
  const cat = CATEGORY[assessment.category] || { label: 'Unavailable', tone: 'neutral', note: '' }

  const onDownload = async () => {
    setDownloading(true)
    setDownloadError('')
    try {
      await downloadReport(result.analysis_id)
    } catch (err) {
      setDownloadError(err.message)
    } finally {
      setDownloading(false)
    }
  }

  const elaStats = ela.difference_statistics
  const previewEvidence = result.evidence?.find((e) => e.name === 'preview.jpg')

  return (
    <section className="dt-dashboard" id="analysis-results" aria-label="Analysis results">
      <div className="dt-dash-head">
        <div>
          <span className="section-kicker">FORENSIC ANALYSIS</span>
          <h2>Analysis results</h2>
          <p className="dt-muted">
            Report ID <code>{result.analysis_id}</code> · {new Date(result.created_at).toLocaleString()}
            {result.status === 'partial' && ' · partial result'}
          </p>
        </div>
        <div className="dt-actions">
          {result.report_url ? (
            <button type="button" className="dt-btn dt-btn-primary" onClick={onDownload} disabled={downloading}>
              {downloading ? 'Preparing PDF…' : 'Download PDF report'}
            </button>
          ) : (
            <span className="dt-badge dt-badge-red">Report unavailable</span>
          )}
        </div>
      </div>

      {downloadError && (
        <div className="dt-alert dt-alert-red" role="alert">
          {downloadError}
        </div>
      )}
      {result.warnings?.length > 0 && (
        <div className="dt-alert dt-alert-amber" role="status">
          <b>Warnings:</b> {result.warnings.join(' ')}
        </div>
      )}

      {/* Overall assessment */}
      <div className={`dt-assessment dt-tone-${cat.tone}`}>
        <div className="dt-assessment-main">
          <span className="dt-eyebrow">OVERALL ASSESSMENT</span>
          <h3>{cat.label}</h3>
          <p>{assessment.summary}</p>
          <p className="dt-muted">{cat.note}</p>
          <Bullets items={assessment.rationale} />
        </div>
        {previewEvidence && (
          <img
            className="dt-assessment-thumb"
            src={absoluteUrl(previewEvidence.url)}
            alt="Downscaled preview of the analysed image"
            loading="lazy"
          />
        )}
      </div>
      <p className="dt-caveat">
        {assessment.scoring_note ||
          'This assessment summarises transparent rules over the checks that ran. It is not a validated probability of authenticity.'}
      </p>

      {/* Checks actually executed */}
      {assessment.checks?.length > 0 && (
        <div className="dt-checks" aria-label="Techniques executed">
          {assessment.checks.map((c) => {
            const ok = ['ok', 'no_credentials_detected', 'credentials_detected_unverified'].includes(c.status)
            const tone = c.status === 'unavailable' ? 'neutral' : ok ? 'green' : 'red'
            return (
              <span key={c.name} className={`dt-chip dt-chip-${tone}`} title={c.detail || ''}>
                {c.name.replace(/_/g, ' ')}: {c.status.replace(/_/g, ' ')}
              </span>
            )
          })}
        </div>
      )}

      <div className="dt-grid">
        <Card title="Image properties">
          <dl className="dt-dl">
            <dt>File</dt>
            <dd>{info.original_filename || '—'}</dd>
            <dt>Format</dt>
            <dd>{info.format || '—'}</dd>
            <dt>Dimensions</dt>
            <dd>
              {info.width ?? '—'} × {info.height ?? '—'} px ({info.megapixels ?? '—'} MP)
            </dd>
            <dt>Colour mode</dt>
            <dd>{info.color_mode || '—'}</dd>
            <dt>File size</dt>
            <dd>{formatBytes(info.file_size_bytes)}</dd>
            <dt>SHA-256</dt>
            <dd className="dt-mono">{info.sha256 || '—'}</dd>
          </dl>
        </Card>

        <Card
          title="Metadata & EXIF"
          badge={meta.exif_present ? 'EXIF present' : 'No EXIF'}
          badgeTone={meta.exif_present ? 'green' : 'neutral'}
        >
          {meta.status === 'error' ? (
            <p className="dt-muted">Metadata analysis failed: {meta.error}</p>
          ) : (
            <>
              <dl className="dt-dl">
                <dt>Camera make</dt>
                <dd>{meta.summary?.camera_make || 'Not present'}</dd>
                <dt>Camera model</dt>
                <dd>{meta.summary?.camera_model || 'Not present'}</dd>
                <dt>Software</dt>
                <dd>{meta.summary?.software || meta.summary?.xmp_creator_tool || 'Not present'}</dd>
                <dt>GPS</dt>
                <dd>
                  {meta.gps?.present
                    ? meta.gps.values_included
                      ? 'Present (coordinates included)'
                      : 'Present — coordinates withheld for privacy'
                    : 'Not present'}
                </dd>
                {Object.entries(meta.summary?.timestamps || {}).map(([k, v]) => (
                  <div key={k} className="dt-dl-row">
                    <dt>{k.replace(/_/g, ' ')}</dt>
                    <dd>{String(v)}</dd>
                  </div>
                ))}
              </dl>
              {meta.findings?.length > 0 && (
                <ul className="dt-findings">
                  {meta.findings.map((f) => (
                    <Finding key={f.id} finding={f} />
                  ))}
                </ul>
              )}
              <p className="dt-muted">Missing metadata is common (social media and messaging apps strip it) and is not evidence of tampering.</p>
              <Limitations items={meta.limitations} />
            </>
          )}
        </Card>

        <Card
          title="Error Level Analysis (ELA)"
          badge={ela.status === 'ok' ? 'Visual aid' : ela.status}
          badgeTone={ela.status === 'ok' ? 'neutral' : 'red'}
        >
          {ela.evidence_url && !elaFailed ? (
            <img
              className="dt-ela"
              src={absoluteUrl(ela.evidence_url)}
              alt="Error Level Analysis map: brighter areas recompressed differently"
              onError={() => setElaFailed(true)}
              loading="lazy"
            />
          ) : (
            <p className="dt-muted">{elaFailed ? 'The ELA image could not be loaded.' : ela.error || 'No ELA image available.'}</p>
          )}
          <p>{ela.explanation}</p>
          {ela.interpretability && <p className="dt-muted">{ela.interpretability}</p>}
          {elaStats && (
            <dl className="dt-dl dt-dl-compact">
              <dt>Mean difference</dt>
              <dd>{formatValue(elaStats.mean)}</dd>
              <dt>95th percentile</dt>
              <dd>{formatValue(elaStats.p95)}</dd>
              <dt>Max channel difference</dt>
              <dd>{formatValue(elaStats.max_channel_difference)}</dd>
            </dl>
          )}
          <p className="dt-caveat">Bright regions are not proof of editing. Textures, edges and prior compression all change ELA output.</p>
          <Limitations items={ela.limitations} />
        </Card>

        <Card title="Noise & image statistics" badge={result.indicators?.length ? `${result.indicators.length} measurements` : 'Unavailable'}>
          {result.indicators?.length ? (
            <div className="dt-table-wrap">
              <table className="dt-table">
                <thead>
                  <tr>
                    <th>Measurement</th>
                    <th>Value</th>
                  </tr>
                </thead>
                <tbody>
                  {result.indicators.map((ind) => (
                    <tr key={ind.name} title={ind.explanation}>
                      <td>{prettify(ind.name)}</td>
                      <td className="dt-mono">{formatValue(ind.value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="dt-muted">Statistics could not be computed for this image.</p>
          )}
          <p className="dt-muted">These are descriptive measurements, not accusations. Hover a row for what it measures.</p>
          <Limitations items={[...new Set(result.indicators?.flatMap((i) => i.limitations || []))]} />
        </Card>

        <Card
          title="Provenance & content credentials"
          badge={PROVENANCE_LABEL[prov.status] || prov.status}
          badgeTone={prov.status === 'credentials_detected_unverified' ? 'amber' : 'neutral'}
        >
          <p>{prov.explanation}</p>
          <dl className="dt-dl dt-dl-compact">
            <dt>Signature verification</dt>
            <dd>{prov.verification === 'verified' ? 'Verified' : 'Not performed'}</dd>
          </dl>
          <Limitations items={prov.limitations} />
        </Card>

        <Card
          title="AI-generation detector"
          badge={ai.status === 'ok' ? 'Model score' : ai.status === 'unavailable' ? 'Unavailable' : 'Error'}
          badgeTone={ai.status === 'ok' ? 'neutral' : ai.status === 'error' ? 'red' : 'amber'}
        >
          {ai.status === 'ok' ? (
            <>
              <p className="dt-big">{AI_PREDICTION_LABEL[ai.prediction] || ai.prediction}</p>
              <dl className="dt-dl dt-dl-compact">
                <dt>Raw model score</dt>
                <dd className="dt-mono">{ai.confidence} (0 = real-leaning, 1 = AI-leaning; uncalibrated)</dd>
                <dt>Model</dt>
                <dd>{ai.method}</dd>
              </dl>
              <p>{ai.explanation}</p>
              <p className="dt-caveat">
                This is a single model’s output, not a probability or proof. Detectors are error-prone on unfamiliar generators,
                screenshots, and re-compressed images.
              </p>
            </>
          ) : (
            <p>{ai.explanation || 'AI-generation detection was not performed.'}</p>
          )}
          <Limitations items={ai.limitations} />
        </Card>
      </div>

      {assessment.findings?.length > 0 && (
        <Card title="All findings">
          <ul className="dt-findings">
            {assessment.findings.map((f) => (
              <Finding key={f.id} finding={f} />
            ))}
          </ul>
        </Card>
      )}

      <div className="dt-grid">
        {assessment.recommended_next_steps?.length > 0 && (
          <Card title="Recommended next steps">
            <Bullets items={assessment.recommended_next_steps} />
          </Card>
        )}
        <Card title="How to read these results">
          <Bullets items={result.limitations} />
        </Card>
      </div>
    </section>
  )
}
